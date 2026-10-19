"""All game samples, exact omission and durable privacy notifications."""

import unittest
from unittest.mock import patch
from partner.common import ledger
from partner.oauth import create_grant, issue_tokens
from partner.record_examples import SERVICES, envelope
from partner.worker import deliver
from tests import test_protocol as protocol

ORIGIN = protocol.ORIGIN


class RecordAdaptersTests(unittest.TestCase):
    def setUp(self):
        self.case = protocol.ProtocolTests()
        self.case.setUp()
        self.app, self.http = self.case.app, self.case.http
        with self.app.app_context(), ledger().transaction() as tx:
            grant = create_grant(
                tx, "alice", ["profile", *[g + ":read" for g in SERVICES]]
            )
            grant["exchanged"] = True
            ledger().put(tx, "grant", grant["id"], grant, grant["expires"])
            self.auth = {
                "Authorization": "Bearer " + issue_tokens(tx, grant)["access_token"]
            }

    def tearDown(self):
        self.case.tearDown()

    def test_five_games_preserve_units_and_recent_history(self):
        for game in SERVICES:
            response = self.http.get(
                "/api/records/" + game, base_url=ORIGIN, headers=self.auth
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json
            self.assertEqual(payload["game_schema"], "musecat-game/" + game + "/v1")
            self.assertEqual(payload["sub"], "sample:alice")
            self.assertEqual(len(payload["recent_plays"]["plays"]), 1)
            self.assertEqual(payload["recent_plays"]["plays"][0]["song"]["image_url"], ORIGIN + "/static/synthetic-song.svg")
            self.assertEqual(
                self.http.get("/record-examples/" + game, base_url=ORIGIN).json["sub"],
                "sample:synthetic",
            )
        with self.app.app_context():
            achievement = envelope("maimai")["recent_plays"]["plays"][0]["fields"][0]
            self.assertEqual(achievement["value"], 100.1234)
            self.assertEqual(achievement["type"], "decimal")
        self.assertEqual(
            self.http.get(
                "/api/records/other", base_url=ORIGIN, headers=self.auth
            ).status_code,
            404,
        )

    def test_selection_removes_data_and_invalidates_only_selected_game(self):
        response = self.case.post(
            "/records/selection",
            form={
                "csrf": self.case.csrf(),
                "service": "nostalgia",
                "excluded": ["player", "recent_plays"],
            },
        )
        self.assertEqual(response.status_code, 302)
        payload = self.http.get(
            "/api/records/nostalgia", base_url=ORIGIN, headers=self.auth
        ).json
        self.assertNotIn("player", payload)
        self.assertNotIn("recent_plays", payload)
        self.assertEqual(
            payload["selection"],
            [
                {"key": "player", "status": "denied"},
                {"key": "recent_plays", "status": "denied"},
            ],
        )
        self.assertIn(
            "recent_plays",
            self.http.get(
                "/api/records/chunithm", base_url=ORIGIN, headers=self.auth
            ).json,
        )
        with patch("partner.worker.remote", return_value={}) as remote:
            self.assertEqual(deliver(self.app), 1)
            self.assertEqual(remote.call_args.args[1], "/partner/v1/records/invalidate")
            self.assertEqual(
                remote.call_args.args[2],
                {"sub": "sample:alice", "service": "nostalgia"},
            )

    def test_missing_key_rolls_back_selection_for_active_grant(self):
        self.app.config["PARTNER_TO_MUSECAT_KEY"] = ""
        response = self.case.post(
            "/records/selection",
            form={
                "csrf": self.case.csrf(),
                "service": "chunithm",
                "excluded": "recent_plays",
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn(
            "recent_plays",
            self.http.get(
                "/api/records/chunithm", base_url=ORIGIN, headers=self.auth
            ).json,
        )

    def test_invalid_selection_does_not_modify_records(self):
        response = self.case.post(
            "/records/selection",
            form={
                "csrf": self.case.csrf(),
                "service": "chunithm",
                "excluded": "secret",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.http.get(
                "/api/records/chunithm", base_url=ORIGIN, headers=self.auth
            ).json["selection"],
            [],
        )

    def test_b_template_declares_all_games_without_changing_joint_manifest(self):
        b = self.http.get("/onboarding.json?flow=b", base_url=ORIGIN).json
        self.assertEqual({s["id"] for s in b["direction_b"]["services"]}, set(SERVICES))
        joint = self.http.get("/onboarding.json", base_url=ORIGIN).json
        self.assertEqual(
            joint["direction_b"]["services"],
            [{"id": "chunithm", "scope": "chunithm:read"}],
        )

    def test_localhost_only_http_origin_and_avatar_allowlist(self):
        from partner import create_app
        from partner.common import profile_picture

        for origin in [
            "http://localhost:8088",
            "http://127.0.0.1:8088",
        ]:
            app = create_app({**self.case.config, "PARTNER_ORIGIN": origin})
            self.assertFalse(app.config["SESSION_COOKIE_SECURE"])
            self.assertEqual(
                app.test_client().get("/health", base_url=origin).status_code, 200
            )
        with self.assertRaises(ValueError):
            create_app(
                {
                    **self.case.config,
                    "PARTNER_ORIGIN": "http://localhost.attacker.example:8088",
                }
            )
        with self.app.app_context():
            issuer = self.app.config["MUSECAT_ISSUER"]
            self.assertEqual(
                profile_picture(issuer + "/api/files/user_info/id/avatar.png"),
                issuer + "/api/files/user_info/id/avatar.png",
            )
            self.assertIsNone(profile_picture("https://attacker.example/avatar.png"))
            self.assertIsNone(profile_picture(issuer + "/not-an-avatar"))
        self.assertTrue(self.app.config["SESSION_COOKIE_SECURE"])
        csp = self.http.get("/", base_url=ORIGIN).headers["Content-Security-Policy"]
        self.assertIn("img-src 'self' " + self.app.config["MUSECAT_ISSUER"], csp)
