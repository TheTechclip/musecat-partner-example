"""Independent OAuth flows must not implicitly create a bilateral connection."""

import re
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from partner.common import challenge, ledger, musecat_callback
from tests import test_protocol as protocol

ORIGIN = protocol.ORIGIN


class OneWayTests(unittest.TestCase):
    def setUp(self):
        self.case = protocol.ProtocolTests()
        self.case.setUp()
        self.app, self.http = self.case.app, self.case.http
        self.app.config["PARTNER_TO_MUSECAT_KEY"] = ""

    def tearDown(self):
        self.case.tearDown()

    def test_a_completes_without_joint_key_or_reverse_grant(self):
        page = self.http.get("/", base_url=ORIGIN).text
        form = re.search(r'<form action="/connect/musecat".*?</form>', page, re.S)[0]
        self.assertNotIn("disabled", form)
        issuer = self.app.config["MUSECAT_ISSUER"]
        with patch(
            "partner.client.remote",
            return_value={
                "issuer": issuer,
                "authorization_endpoint": issuer + "/oauth/authorize",
            },
        ):
            response = self.case.post(
                "/connect/musecat", form={"csrf": self.case.csrf()}
            )
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response.location).query)
        self.assertEqual(query["scope"], ["account:access"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        with patch(
            "partner.client.remote",
            side_effect=[
                {
                    "token_type": "Bearer",
                    "scope": "account:access",
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 600,
                },
                {"sub": "one-way-subject", "nickname": "Alice"},
            ],
        ) as remote:
            response = self.http.get(
                "/oauth/musecat/callback",
                base_url=ORIGIN,
                query_string={
                    "state": query["state"][0],
                    "code": "code",
                    "iss": issuer,
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(remote.call_count, 2)
        with self.app.app_context(), ledger().transaction() as tx:
            link = ledger().get(tx, "link", "alice")
            self.assertFalse(link["pair_id"])
            self.assertFalse(link["partial"])
            self.assertEqual(ledger().items(tx, "grant"), [])
        self.case.post("/disconnect", form={"csrf": self.case.csrf()})
        with self.app.app_context(), ledger().transaction() as tx:
            self.assertIsNone(ledger().get(tx, "link", "alice"))
            self.assertEqual(len(ledger().items(tx, "outbox")), 1)

    def test_b_consent_records_and_revoke_without_reverse_access(self):
        self.app.config["MUSECAT_CLIENT_SECRET"] = ""
        with self.app.app_context():
            callback = musecat_callback()
        query = {
            "client_id": "musecat",
            "redirect_uri": callback,
            "response_type": "code",
            "scope": "profile chunithm:read",
            "state": "one-way-b",
            "code_challenge_method": "S256",
            "code_challenge": challenge("v" * 43),
        }
        page = self.http.get("/oauth/authorize", base_url=ORIGIN, query_string=query)
        self.assertEqual(page.status_code, 200)
        response = self.case.post(
            "/oauth/authorize",
            form={**query, "csrf": self.case.csrf(), "decision": "approve"},
        )
        code = parse_qs(urlsplit(response.location).query)["code"][0]
        response = self.case.exchange(code)
        self.assertEqual(response.status_code, 200)
        token = response.json["access_token"]
        headers = {"Authorization": "Bearer " + token}
        self.assertEqual(
            self.http.get(
                "/api/records/chunithm", base_url=ORIGIN, headers=headers
            ).status_code,
            200,
        )
        with self.app.app_context(), ledger().transaction() as tx:
            self.assertIsNone(ledger().get(tx, "link", "alice"))
            grants = ledger().items(tx, "grant")
            self.assertEqual(len(grants), 1)
            self.assertIsNone(grants[0][1]["pair_id"])
        home = self.http.get("/", base_url=ORIGIN).text
        self.assertIn("Active record permissions issued by this sample: 1", home)
        self.case.post("/oauth/revoke", headers=self.case.basic, form={"token": token})
        self.assertEqual(
            self.http.get(
                "/api/records/chunithm", base_url=ORIGIN, headers=headers
            ).status_code,
            401,
        )

    def test_registration_templates_are_flow_specific(self):
        for flow in ["a", "b", "joint"]:
            response = self.http.get("/onboarding.json?flow=" + flow, base_url=ORIGIN)
            self.assertEqual(response.status_code, 200)
            self.assertIn("direction_a", response.json)
            self.assertEqual("direction_b" in response.json, flow != "a")
            self.assertEqual("joint" in response.json, flow == "joint")
        self.assertEqual(
            self.http.get("/onboarding.json?flow=unknown", base_url=ORIGIN).status_code,
            400,
        )
