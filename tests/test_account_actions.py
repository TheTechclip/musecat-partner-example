"""Dedicated account forms must use real domain routes without leaking tokens."""

import json
import unittest
from unittest.mock import patch

from tests import test_examples as examples

Response = examples.Response
ORIGIN = examples.ORIGIN


class AccountActionTests(unittest.TestCase):
    setUp = examples.ApiExampleTests.setUp
    tearDown = examples.ApiExampleTests.tearDown

    def post_action(self, action, **fields):
        return self.case.post(
            "/account-actions",
            form={
                "csrf": self.case.csrf(),
                "action": action,
                "arcade": "fixture_arcade",
                **fields,
            },
        )

    def opener(self, status=200):
        class Opener:
            def __init__(inner):
                inner.calls = []

            def open(inner, request, timeout):
                inner.calls.append(request)
                if request.method != "GET":
                    response = Response({"saved": True})
                    response.code = status
                    return response
                if "/arcade?" in request.full_url:
                    return Response(
                        {
                            "basic": {
                                "id": "revision_1",
                                "name": "Synthetic arcade",
                                "address": "",
                                "direction": "",
                            },
                            "game": {
                                "items": [
                                    {
                                        "id": "state_1",
                                        "arcade_game_id": "stable_machine",
                                        "series": {"en": "Test game"},
                                        "version": {"en": "Test version"},
                                    }
                                ]
                            },
                        }
                    )
                return Response({"items": [{
                    "campaign": {"id": "test_campaign", "from_version": {"version": {"en": "Before"}}, "to_version": {"version": {"en": "After"}}},
                    "target": {"status": "pending", "game": {"id": "stable_machine"}}
                }]})

        return Opener()

    def test_render_prefill_is_read_only_and_all_locales_render(self):
        with patch("partner.account_actions.urllib.request.build_opener") as network:
            for locale in ["en", "ko", "ja"]:
                with self.http.session_transaction(base_url=ORIGIN) as session:
                    session["locale"] = locale
                page = self.http.get(
                    "/account-actions?arcade=fixture_arcade&lat=-33&lon=151",
                    base_url=ORIGIN,
                )
                self.assertEqual(page.status_code, 200)
                self.assertIn('value="fixture_arcade"', page.text)
                self.assertNotIn("secret-access", page.text)
            network.assert_not_called()

    def test_load_requires_csrf_and_a_connected_owner(self):
        self.assertEqual(
            self.case.post(
                "/account-actions", form={"action": "load", "arcade": "fixture_arcade"}
            ).status_code,
            403,
        )
        with self.app.app_context():
            from partner.common import ledger

            with ledger().transaction() as tx:
                ledger().delete(tx, "link", "alice")
        self.assertEqual(self.post_action("load").status_code, 409)

    def test_load_uses_fixed_issuer_and_stable_machine_id(self):
        opener = self.opener()
        with patch(
            "partner.account_actions.urllib.request.build_opener", return_value=opener
        ):
            page = self.post_action("load")
        self.assertEqual(page.status_code, 200)
        self.assertIn('value="stable_machine"', page.text)
        self.assertIn('Before → After', page.text)
        for request in opener.calls:
            self.assertTrue(
                request.full_url.startswith(
                    "https://db-dev.musecat.app/developer/v1/account/"
                )
            )
            self.assertEqual(
                request.get_header("Authorization"), "Bearer secret-access"
            )
        self.assertNotIn("secret-access", page.text)

    def test_typed_mutations_and_concurrency_token(self):
        cases = [
            (
                "basic",
                {
                    "name": "New name",
                    "address": "Test street",
                    "direction": "Test entrance",
                    "base_basic_id": "revision_1",
                },
                "/arcade/basic",
                "PUT",
            ),
            (
                "fault",
                {
                    "game_id": "stable_machine",
                    "message": "Synthetic fault",
                    "disruption": "minor",
                },
                "/arcade/flag",
                "POST",
            ),
            (
                "visit",
                {"lat": "-33", "lon": "151", "accuracy": "10"},
                "/arcade/visit",
                "POST",
            ),
            (
                "campaign",
                {
                    "game_id": "stable_machine",
                    "campaign": "test_campaign",
                    "result": "still_old",
                },
                "/campaign/check",
                "POST",
            ),
        ]
        for action, fields, path, method in cases:
            opener = self.opener()
            with patch(
                "partner.account_actions.urllib.request.build_opener",
                return_value=opener,
            ):
                page = self.post_action(action, confirm=action, **fields)
            self.assertEqual(page.status_code, 200, page.text)
            request = opener.calls[0]
            self.assertTrue(request.full_url.endswith(path))
            self.assertEqual(request.method, method)
            payload = json.loads(request.data)
            self.assertEqual(payload["arcade"], "fixture_arcade")
            if action == "campaign":
                self.assertIs(payload["bypass_location"], False)
            if action == "basic":
                self.assertEqual(payload["base_basic_id"], "revision_1")
                self.assertNotIn("location", payload)

    def test_reject_invalid_inputs_without_calling_upstream(self):
        with patch("partner.account_actions.urllib.request.build_opener") as network:
            for action, fields in [
                (
                    "fault",
                    {
                        "confirm": "fault",
                        "game_id": "../secret",
                        "message": "Test",
                        "disruption": "minor",
                    },
                ),
                (
                    "visit",
                    {"confirm": "visit", "lat": "nan", "lon": "1", "accuracy": "10"},
                ),
                (
                    "visit",
                    {"confirm": "visit", "lat": "1", "lon": "1", "accuracy": "151"},
                ),
                (
                    "campaign",
                    {
                        "confirm": "campaign",
                        "game_id": "machine",
                        "campaign": "campaign",
                        "result": "anything",
                    },
                ),
                ("basic", {"name": "Name"}),
            ]:
                self.assertEqual(self.post_action(action, **fields).status_code, 400)
            network.assert_not_called()

    def test_http_error_is_visible_without_retries(self):
        opener = self.opener(status=403)
        with patch(
            "partner.account_actions.urllib.request.build_opener", return_value=opener
        ):
            page = self.post_action(
                "campaign",
                confirm="campaign",
                game_id="machine",
                campaign="campaign",
                result="updated",
            )
        self.assertIn("HTTP 403", page.text)
        self.assertEqual(sum(request.method != "GET" for request in opener.calls), 1)


if __name__ == "__main__":
    unittest.main()
