"""All game samples, exact omission and durable privacy notifications."""

import unittest
from unittest.mock import patch
from partner import create_app
from partner.common import ProtocolError, ledger, now
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

    def test_privacy_invalidates_only_games_in_active_exchanged_grants(self):
        with self.app.app_context(), ledger().transaction() as tx:
            for gid, grant in ledger().items(tx, "grant"):
                grant["scopes"] = ["profile", "chunithm:read"]
                ledger().put(tx, "grant", gid, grant, grant["expires"])
            other = create_grant(tx, "bob", ["profile", "maimai:read"])
            issue_tokens(tx, other)
            create_grant(tx, "alice", ["profile", "sdvx:read"])
            revoked = create_grant(tx, "alice", ["profile", "nostalgia:read"])
            revoked.update(exchanged=True, revoked=True)
            ledger().put(tx, "grant", revoked["id"], revoked, revoked["expires"])
        response = self.case.post(
            "/records/privacy", form={"csrf": self.case.csrf(), "private": "yes"}
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context(), ledger().transaction() as tx:
            jobs = ledger().items(tx, "outbox")
            self.assertEqual(
                [job["body"] for _, job in jobs],
                [{"sub": "sample:alice", "service": "chunithm"}],
            )

    def test_privacy_preserves_notifications_for_all_five_authorized_games(self):
        self.case.post(
            "/records/privacy", form={"csrf": self.case.csrf(), "private": "yes"}
        )
        with patch("partner.worker.remote", return_value={}) as remote:
            self.assertEqual(deliver(self.app), len(SERVICES))
            self.assertEqual(
                {call.args[2]["service"] for call in remote.call_args_list},
                set(SERVICES),
            )

    def test_worker_preserves_no_audience_jobs_as_cancellation_receipts(self):
        originals = {}
        with self.app.app_context(), ledger().transaction() as tx:
            for gid, grant in ledger().items(tx, "grant"):
                grant["scopes"] = ["profile", "chunithm:read"]
                ledger().put(tx, "grant", gid, grant, grant["expires"])
            for game in set(SERVICES) - {"chunithm"}:
                for index in range(2):
                    jid = game + "-" + str(index)
                    job = {
                        "kind": "records",
                        "body": {"sub": "sample:alice", "service": game},
                        "attempts": 11,
                        "next": 0,
                    }
                    originals[jid] = job
                    ledger().put(tx, "outbox", jid, job, now() + 86400)
        with patch("partner.worker.remote") as remote:
            self.assertEqual(deliver(self.app), 0)
            remote.assert_not_called()
        restarted = create_app(self.case.config)
        with restarted.app_context(), ledger().transaction() as tx:
            self.assertEqual(ledger().items(tx, "outbox"), [])
            receipts = dict(ledger().items(tx, "outbox_cancelled"))
            self.assertEqual(set(receipts), set(originals))
            for jid, receipt in receipts.items():
                self.assertEqual(receipt["reason"], "no_audience")
                self.assertGreater(receipt["cancelled_at"], 0)
                self.assertEqual(
                    {key: receipt[key] for key in originals[jid]}, originals[jid]
                )

    def test_worker_keeps_failed_notifications_with_an_eligible_audience_pending(self):
        self.case.post(
            "/records/selection",
            form={"csrf": self.case.csrf(), "service": "chunithm"},
        )
        with patch(
            "partner.worker.remote", side_effect=ProtocolError("invalid_request", 400)
        ) as remote:
            self.assertEqual(deliver(self.app), 0)
            remote.assert_called_once()
        with self.app.app_context(), ledger().transaction() as tx:
            jobs = ledger().items(tx, "outbox")
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0][1]["attempts"], 1)
            self.assertEqual(ledger().items(tx, "outbox_cancelled"), [])

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
