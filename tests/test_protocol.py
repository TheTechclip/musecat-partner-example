import base64
import re
import tempfile
from pathlib import Path
import unittest
import uuid
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from cryptography.fernet import Fernet

from partner import create_app
from partner.client import save_link
from partner.common import (
    MANIFEST,
    ProtocolError,
    challenge,
    ledger,
    musecat_callback,
    now,
    stamp,
)
from partner.oauth import create_grant, issue_code
from partner.storage import digest
from partner.worker import deliver

ORIGIN = "https://partner.example"


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = {
            "TESTING": True,
            "DATA_DIR": self.directory.name,
            "PARTNER_ORIGIN": ORIGIN,
            "PARTNER_ID": "example_test",
            "PARTNER_OAUTH_CLIENT_ID": "musecat",
            "PARTNER_OAUTH_CLIENT_SECRET": "s" * 43,
            "MUSECAT_TO_PARTNER_KEY": "k" * 43,
            "PARTNER_TO_MUSECAT_KEY": "p" * 43,
            "MUSECAT_CLIENT_SECRET": "m" * 43,
            "DEMO_PASSWORD": "d" * 43,
            "SESSION_SECRET": "x" * 43,
            "DATA_KEY": Fernet.generate_key().decode(),
        }
        self.app = create_app(self.config)
        self.http = self.app.test_client()
        self.login(self.http)
        self.basic = {
            "Authorization": "Basic "
            + base64.b64encode(("musecat:" + "s" * 43).encode()).decode()
        }

    def test_language_selection_and_session_lifecycle(self):
        from partner.i18n import LANGUAGES, MESSAGES
        from string import Formatter

        for translations in MESSAGES.values():
            self.assertEqual(set(translations), set(LANGUAGES))
            placeholders = [
                {field for _, field, _, _ in Formatter().parse(value) if field}
                for value in translations.values()
            ]
            self.assertTrue(all(fields == placeholders[0] for fields in placeholders))
        for locale in LANGUAGES:
            anonymous = self.app.test_client()
            page = anonymous.get(
                "/login", base_url=ORIGIN, headers={"Accept-Language": locale}
            ).text
            self.assertIn('lang="' + locale + '"', page)
            response = self.post(
                "/language",
                form={"csrf": self.csrf(), "locale": locale, "next": "/login"},
            )
            self.assertEqual(response.status_code, 302)
            self.login(self.http)
            self.assertIn(
                'lang="' + locale + '"', self.http.get("/", base_url=ORIGIN).text
            )
            self.post("/logout", form={"csrf": self.csrf()})
            self.assertIn(
                'lang="' + locale + '"', self.http.get("/login", base_url=ORIGIN).text
            )

    def test_language_redirect_validation_and_consent_locale(self):
        for target in [
            "https://evil.example/",
            "//evil.example/",
            "/disconnect",
            "/#fragment",
        ]:
            response = self.post(
                "/language", form={"csrf": self.csrf(), "locale": "ja", "next": target}
            )
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.post("/language", form={"locale": "ja"}).status_code, 403)
        self.assertEqual(
            self.post(
                "/language", form={"csrf": self.csrf(), "locale": "xx"}
            ).status_code,
            400,
        )
        target = "/oauth/authorize?state=example&code_challenge=public"
        response = self.post(
            "/language", form={"csrf": self.csrf(), "locale": "ja", "next": target}
        )
        self.assertEqual(response.location, target)
        response = self.post("/connect/joint", form={"csrf": self.csrf()})
        self.assertIn("/ja/connect/example_test?", response.location)

    def test_synthetic_record_vocabulary_matches_profile_presentation(self):
        code = self.code()
        token = self.exchange(code).json["access_token"]
        response = self.http.get(
            "/api/records/chunithm",
            base_url=ORIGIN,
            headers={"Authorization": "Bearer " + token},
        )
        self.assertEqual(response.status_code, 200)
        record = response.json
        self.assertEqual(record["sub"], "sample:alice")
        self.assertIn("synthetic", record["source"]["name"])
        fields = {field["key"]: field for field in record["fields"]}
        self.assertEqual(fields["rating"]["value"], 16.42)
        self.assertEqual(fields["rating_max"]["value"], 16.58)
        self.assertEqual(fields["played_chart_count"]["value"], 123)
        self.assertEqual(fields["full_combo_count"]["value"], 80)
        self.assertEqual(fields["all_justice_count"]["value"], 30)
        ranks = record["sections"][0]
        self.assertEqual(ranks["key"], "rank_distribution")
        self.assertEqual(sum(row[1] for row in ranks["rows"]), 123)
        self.assertTrue(
            all(set(field["label"]) == {"en", "ko", "ja"} for field in record["fields"])
        )

    def tearDown(self):
        self.directory.cleanup()

    def csrf(self, client=None):
        page = (client or self.http).get("/", base_url=ORIGIN).text
        return re.search(r'name="csrf" value="([^"]+)"', page).group(1)

    def login(self, client, username="alice"):
        page = client.get("/login", base_url=ORIGIN).text
        csrf = re.search(r'name="csrf" value="([^"]+)"', page).group(1)
        response = client.post(
            "/login",
            base_url=ORIGIN,
            data={"csrf": csrf, "username": username, "password": "d" * 43},
        )
        self.assertEqual(response.status_code, 302)

    def post(self, path, body=None, headers=None, form=None, client=None):
        return (client or self.http).post(
            path, base_url=ORIGIN, json=body, data=form, headers=headers or {}
        )

    def code(self, scopes=None):
        with self.app.app_context(), ledger().transaction() as tx:
            grant = create_grant(tx, "alice", scopes or ["profile", "chunithm:read"])
            return issue_code(tx, grant, challenge("v" * 43))

    def exchange(self, code, verifier="v" * 43):
        with self.app.app_context():
            uri = musecat_callback()
        return self.post(
            "/oauth/token",
            headers=self.basic,
            form={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": uri,
            },
        )

    def start_joint(self):
        response = self.post("/connect/joint", form={"csrf": self.csrf()})
        self.assertEqual(response.status_code, 302)
        intent = parse_qs(urlsplit(response.location).query)["intent"][0]
        looked = self.joint(
            "/intents/lookup", {"intent": intent, "partner_id": "example_test"}
        )
        self.assertEqual(looked.status_code, 200)
        return intent, looked.json

    def joint(self, suffix, body, request_id=None, key=None):
        return self.post(
            "/api/joint" + suffix,
            body,
            {
                "Authorization": "Bearer " + (key or "k" * 43),
                "X-Request-Id": request_id or str(uuid.uuid4()),
            },
        )

    def receipt(self, intent, looked):
        with self.app.app_context():
            uri = musecat_callback()
        return {
            "intent": intent,
            "correlation_id": looked["correlation_id"],
            "manifest": MANIFEST,
            "generation": "generation1",
            "musecat_code": "private-musecat-code",
            "musecat_code_expires_at": stamp(now() + 85),
            "code_challenge": challenge("v" * 43),
            "redirect_uri": uri,
        }

    def test_pkce_rotation_replay_and_private_records(self):
        code = self.code()
        self.assertEqual(self.exchange(code, "z" * 43).status_code, 400)
        token = self.exchange(code).json
        auth = {"Authorization": "Bearer " + token["access_token"]}
        self.assertEqual(
            self.http.get("/oauth/userinfo", base_url=ORIGIN, headers=auth).json["sub"],
            "sample:alice",
        )
        self.assertEqual(
            self.http.get("/api/records/chunithm", base_url=ORIGIN, headers=auth).json[
                "spec"
            ],
            "musecat-records/v1",
        )
        self.post("/records/privacy", form={"csrf": self.csrf(), "private": "yes"})
        self.assertEqual(
            self.http.get("/api/records/chunithm", base_url=ORIGIN, headers=auth).json[
                "error"
            ],
            "records_private",
        )
        rotated = self.post(
            "/oauth/token",
            headers=self.basic,
            form={
                "grant_type": "refresh_token",
                "refresh_token": token["refresh_token"],
            },
        )
        self.assertEqual(rotated.status_code, 200)
        self.assertEqual(
            self.post(
                "/oauth/token",
                headers=self.basic,
                form={
                    "grant_type": "refresh_token",
                    "refresh_token": token["refresh_token"],
                },
            ).status_code,
            400,
        )
        self.assertEqual(
            self.http.get(
                "/oauth/userinfo",
                base_url=ORIGIN,
                headers={"Authorization": "Bearer " + rotated.json["access_token"]},
            ).status_code,
            401,
        )

    def test_code_replay_revokes_and_identity_scope_cannot_read_records(self):
        code = self.code(["profile"])
        token = self.exchange(code).json
        auth = {"Authorization": "Bearer " + token["access_token"]}
        self.assertEqual(
            self.http.get(
                "/api/records/chunithm", base_url=ORIGIN, headers=auth
            ).status_code,
            403,
        )
        self.assertEqual(self.exchange(code).status_code, 400)
        self.assertEqual(
            self.http.get("/oauth/userinfo", base_url=ORIGIN, headers=auth).status_code,
            401,
        )
        self.assertEqual(
            self.post(
                "/oauth/revoke", headers=self.basic, form={"token": "unknown"}
            ).status_code,
            200,
        )

    def test_redirect_pkce_csrf_and_bearer_boundaries(self):
        with self.app.app_context():
            uri = musecat_callback()
        query = {
            "client_id": "musecat",
            "redirect_uri": uri,
            "scope": "profile",
            "state": "state",
            "response_type": "code",
            "code_challenge": challenge("v" * 43),
            "code_challenge_method": "plain",
        }
        self.assertEqual(
            self.http.get(
                "/oauth/authorize", base_url=ORIGIN, query_string=query
            ).status_code,
            400,
        )
        query.update(
            code_challenge_method="S256", redirect_uri="https://evil.example/callback"
        )
        self.assertEqual(
            self.http.get(
                "/oauth/authorize", base_url=ORIGIN, query_string=query
            ).status_code,
            400,
        )
        self.assertEqual(self.post("/connect/joint", form={}).status_code, 403)
        self.assertEqual(self.joint("/intents/lookup", {}, key="bad").status_code, 401)
        self.assertEqual(
            self.http.get(
                "/connect/musecat/start",
                base_url=ORIGIN,
                query_string={
                    "correlation_id": str(uuid.uuid4()),
                    "return_to": "https://evil.example",
                },
            ).status_code,
            400,
        )

    def test_receipt_atomic_idempotent_and_generation_scoped_revocation(self):
        handle, looked = self.start_joint()
        body, request_id = self.receipt(handle, looked), str(uuid.uuid4())
        first = self.joint("/receipts", body, request_id)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.joint("/receipts", body, request_id).json, first.json)
        self.assertEqual(
            self.joint(
                "/receipts", {**body, "generation": "other"}, request_id
            ).status_code,
            409,
        )
        self.assertEqual(self.joint("/receipts", body).status_code, 409)
        token = self.exchange(first.json["partner_code"]).json
        payload = {
            "pair_id": looked["correlation_id"],
            "generation": "wrong",
            "reason": "user",
            "revoked_at": stamp(),
        }
        self.assertEqual(
            self.joint("/revocations", payload).json["status"], "unknown_generation"
        )
        auth = {"Authorization": "Bearer " + token["access_token"]}
        self.assertEqual(
            self.http.get("/oauth/userinfo", base_url=ORIGIN, headers=auth).status_code,
            200,
        )
        payload["generation"] = "generation1"
        self.assertEqual(self.joint("/revocations", payload).json["status"], "revoked")
        self.assertEqual(
            self.joint("/revocations", payload).json["status"], "already_revoked"
        )
        self.assertEqual(
            self.http.get("/oauth/userinfo", base_url=ORIGIN, headers=auth).status_code,
            401,
        )

    def test_joint_callback_requires_same_session_and_both_exchanges(self):
        handle, looked = self.start_joint()
        receipt = self.joint("/receipts", self.receipt(handle, looked)).json
        self.exchange(receipt["partner_code"])
        query = {
            "state": looked["correlation_id"],
            "code": "private-musecat-code",
            "iss": "https://db-dev.musecat.app",
        }
        other = self.app.test_client()
        self.login(other, "bob")
        self.assertEqual(
            other.get(
                "/oauth/musecat/callback", base_url=ORIGIN, query_string=query
            ).status_code,
            400,
        )

        def remote(method, path, *args, **kwargs):
            if path == "/oauth/token":
                return {
                    "access_token": "a-secret",
                    "refresh_token": "r-secret",
                    "expires_in": 600,
                    "scope": "account:access",
                    "token_type": "Bearer",
                }
            if path == "/developer/v1/me":
                return {"sub": "pairwise-user", "nickname": "Test user"}
            return {
                "status": "connected",
                "generation": "generation1",
                "musecat_access": True,
                "partner_access": True,
            }

        with patch("partner.client.remote", side_effect=remote):
            self.assertEqual(
                self.http.get(
                    "/oauth/musecat/callback", base_url=ORIGIN, query_string=query
                ).status_code,
                302,
            )
        with self.app.app_context(), ledger().transaction() as tx:
            link = ledger().get(tx, "link", "alice")
            self.assertFalse(link["partial"])
        raw = Path(self.directory.name + "/sample.db").read_bytes()
        self.assertNotIn(b"r-secret", raw)
        self.assertNotIn(b"private-musecat-code", raw)

    def test_expired_intent_and_invalid_receipt_do_not_issue_codes(self):
        handle, looked = self.start_joint()
        body = self.receipt(handle, looked)
        body["redirect_uri"] = "https://evil.example/callback"
        self.assertEqual(self.joint("/receipts", body).status_code, 400)
        self.assertEqual(
            self.joint(
                "/intents/lookup", {"intent": handle, "partner_id": "example_test"}
            ).status_code,
            200,
        )
        with self.app.app_context(), ledger().transaction() as tx:
            intent = ledger().get(tx, "intent", digest(handle))
            intent["expires"] = now() - 1
            ledger().put(tx, "intent", digest(handle), intent, now() + 86400)
        self.assertEqual(
            self.joint(
                "/intents/lookup", {"intent": handle, "partner_id": "example_test"}
            ).json["error"],
            "intent_expired",
        )

    def test_previous_joint_key_is_accepted_only_during_rotation_window(self):
        self.app.config.update(
            MUSECAT_TO_PARTNER_PREVIOUS_KEY="previous" * 8,
            PREVIOUS_KEY_EXPIRES_AT=now() + 86400,
        )
        handle, _ = self.start_joint()
        payload = {"intent": handle, "partner_id": "example_test"}
        self.assertEqual(
            self.joint("/intents/lookup", payload, key="previous" * 8).status_code, 200
        )
        self.app.config["PREVIOUS_KEY_EXPIRES_AT"] = now() - 1
        self.assertEqual(
            self.joint("/intents/lookup", payload, key="previous" * 8).status_code, 401
        )

    def test_form_referrer_policy_preserves_origin_without_accepting_null(self):
        response = self.http.get("/login", base_url=ORIGIN)
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
        self.assertEqual(
            self.post(
                "/login",
                form={"csrf": self.csrf(), "username": "alice", "password": "d" * 43},
                headers={"Origin": "null"},
            ).status_code,
            403,
        )
        response = self.post(
            "/login",
            form={"csrf": self.csrf(), "username": "alice", "password": "d" * 43},
            headers={"Origin": ORIGIN},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.http.get("/oauth/musecat/callback", base_url=ORIGIN).headers[
                "Referrer-Policy"
            ],
            "no-referrer",
        )

    def test_uncertain_refresh_is_not_replayed_but_can_still_be_revoked(self):
        token = {
            "access_token": "old-access",
            "refresh_token": "old-refresh",
            "expires_in": 600,
        }
        with self.app.app_context(), ledger().transaction() as tx:
            save_link(tx, "alice", token, {"sub": "user"}, {})
        form = {"csrf": self.csrf(), "refresh": "yes"}
        with patch(
            "partner.client.remote", side_effect=ProtocolError("offline", 502)
        ) as remote:
            self.assertEqual(self.post("/musecat/profile", form=form).status_code, 409)
            self.assertEqual(self.post("/musecat/profile", form=form).status_code, 409)
            self.assertEqual(remote.call_count, 1)
        self.post("/disconnect", form={"csrf": self.csrf()})
        with self.app.app_context(), ledger().transaction() as tx:
            jobs = ledger().items(tx, "outbox")
            self.assertEqual(jobs[0][1]["token"], "old-refresh")
            self.assertIsNone(ledger().get(tx, "link", "alice"))

    def test_outbox_survives_restart_and_failed_delivery(self):
        with self.app.app_context(), ledger().transaction() as tx:
            ledger().put(
                tx,
                "outbox",
                str(uuid.uuid4()),
                {
                    "kind": "joint",
                    "body": {"pair_id": str(uuid.uuid4()), "generation": "g"},
                    "next": 0,
                    "attempts": 0,
                },
                now() + 86400,
            )
        restarted = create_app(self.config)
        with patch("partner.worker.remote", side_effect=ProtocolError("offline", 502)):
            self.assertEqual(deliver(restarted), 0)
        with restarted.app_context(), ledger().transaction() as tx:
            jobs = ledger().items(tx, "outbox")
            self.assertEqual(jobs[0][1]["attempts"], 1)
            job = jobs[0][1]
            job["next"] = 0
            ledger().put(tx, "outbox", jobs[0][0], job, now() + 86400)
        with patch("partner.worker.remote", return_value={"status": "revoked"}):
            self.assertEqual(deliver(restarted), 1)


if __name__ == "__main__":
    unittest.main()
