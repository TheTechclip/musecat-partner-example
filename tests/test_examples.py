import io
import json
import unittest
import urllib.error
from unittest.mock import patch
from urllib.parse import urlencode

from partner.api_examples import METHODS, OPERATIONS, SPEC, curl_example
from partner.client import save_link
from partner.common import ProtocolError, ledger
from tests import test_protocol as protocol

ORIGIN = protocol.ORIGIN


class Response:
    code = 200
    headers = {"Content-Type": "application/json"}

    def __init__(self, body):
        self.body = body

    def read(self, limit):
        return json.dumps(self.body).encode()[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class ApiExampleTests(unittest.TestCase):
    def setUp(self):
        self.case = protocol.ProtocolTests()
        self.case.setUp()
        self.app, self.http = self.case.app, self.case.http
        with self.app.app_context(), ledger().transaction() as tx:
            save_link(
                tx,
                "alice",
                {
                    "access_token": "secret-access",
                    "refresh_token": "secret-refresh",
                    "expires_in": 600,
                },
                {"sub": "subject", "nickname": "Alice"},
                {},
            )

    def tearDown(self):
        self.case.tearDown()

    def run_example(self, operation, **fields):
        return self.case.post(
            "/api-examples/run",
            form={"csrf": self.case.csrf(), "operation": operation, **fields},
        )

    def test_bulk_arcade_list_is_not_executable(self):
        for path in ["/developer/v1/arcades", "/developer/v1/account/arcades"]:
            self.assertNotIn(path, SPEC["paths"])
            for method in ["GET", "HEAD"]:
                response = self.run_example(method + " " + path)
                self.assertEqual(response.status_code, 400)

    def test_catalog_covers_every_official_operation_and_media(self):
        expected = {
            method.upper() + " " + path
            for path, route in SPEC["paths"].items()
            for method in route
            if method in METHODS
        }
        self.assertEqual(set(OPERATIONS), expected)
        for operation in OPERATIONS.values():
            for media in operation["request_content"] or {"": {}}:
                page = self.http.get(
                    "/api-examples?"
                    + urlencode({"operation": operation["id"], "media": media}),
                    base_url=ORIGIN,
                )
                self.assertEqual(page.status_code, 200, operation["id"])
                self.assertIn("curl --request", page.text)
                self.assertNotIn("secret-access", page.text)
                self.assertNotIn("secret-refresh", page.text)
            self.assertIn(
                operation["method"], curl_example(operation, "https://issuer.example")
            )

    def test_executor_uses_only_documented_paths_and_keeps_token_server_side(self):
        with patch("partner.explorer.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = Response({"nickname": "Alice"})
            response = self.run_example("GET /developer/v1/account/user/me")
            self.assertEqual(response.status_code, 200)
            upstream = opener.return_value.open.call_args.args[0]
            self.assertEqual(
                upstream.full_url,
                "https://db-dev.musecat.app/developer/v1/account/user/me",
            )
            self.assertEqual(
                upstream.get_header("Authorization"), "Bearer secret-access"
            )
            self.assertNotIn("secret-access", response.text)
            self.assertIn("Alice", response.text)
            opener.reset_mock()
            for operation in [
                "GET https://evil.example",
                "POST /oauth/token",
                "DELETE /user/authorizations/{id}",
            ]:
                self.assertEqual(self.run_example(operation).status_code, 400)
            opener.return_value.open.assert_not_called()

    def test_mutation_requires_confirmation_and_valid_json_and_blocks_session_credentials(
        self,
    ):
        operation = "PUT /developer/v1/account/user/countries"
        with patch("partner.explorer.urllib.request.build_opener") as opener:
            for values in [
                {"body": "{}"},
                {"confirm": "DELETE", "body": "{}"},
                {"confirm": "PUT", "body": "broken"},
            ]:
                self.assertEqual(self.run_example(operation, **values).status_code, 400)
            opener.return_value.open.assert_not_called()
            opener.return_value.open.return_value = Response({"countries": ["AU"]})
            self.assertEqual(
                self.run_example(
                    operation,
                    confirm="PUT",
                    body='{"countries":["AU"],"country_mode":"manual"}',
                ).status_code,
                200,
            )
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.method, "PUT")
            self.assertEqual(json.loads(request.data)["countries"], ["AU"])
        self.assertEqual(
            self.case.post(
                "/api-examples/run", form={"operation": "GET /developer/v1/me"}
            ).status_code,
            403,
        )

    def test_multipart_keeps_documented_files_and_never_forwards_placeholder_bytes(
        self,
    ):
        with patch("partner.explorer.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = Response({"ok": True})
            response = self.http.post(
                "/api-examples/run",
                base_url=ORIGIN,
                data={
                    "csrf": self.case.csrf(),
                    "operation": "POST /developer/v1/account/arcade/photo/upload",
                    "confirm": "POST",
                    "media": "multipart/form-data",
                    "body": '{"arcade":"abcdefghijklmn1","photos":["<UPLOAD_FILE>"]}',
                    "photos": (io.BytesIO(b"sample-image-bytes"), "test.png"),
                },
            )
            self.assertEqual(response.status_code, 200)
            upstream = opener.return_value.open.call_args.args[0]
            self.assertIn(b'name="photos"; filename="test.png"', upstream.data)
            self.assertIn(b"Content-Type: image/png", upstream.data)
            self.assertIn(b"sample-image-bytes", upstream.data)
            self.assertNotIn(b"<UPLOAD_FILE>", upstream.data)
            self.assertIn(
                "multipart/form-data; boundary=", upstream.get_header("Content-type")
            )

    def test_all_languages_render_the_new_console_and_profile_sections(self):
        for locale in ("en", "ko", "ja"):
            with self.http.session_transaction(base_url=ORIGIN) as session:
                session["locale"] = locale
            response = self.http.get("/api-examples", base_url=ORIGIN)
            self.assertEqual(response.status_code, 200)
            self.assertIn('lang="' + locale + '"', response.text)
            self.assertIn(f"{len(OPERATIONS)} operations", response.text)

    def test_http_error_is_shown_without_hiding_status(self):
        error = urllib.error.HTTPError(
            "https://db-dev.musecat.app",
            403,
            "Forbidden",
            {"Content-Type": "application/json"},
            io.BytesIO(b'{"error":"insufficient_scope"}'),
        )
        with patch("partner.explorer.urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = error
            response = self.run_example("GET /developer/v1/account/user/me")
            self.assertEqual(response.status_code, 200)
            self.assertIn("403", response.text)
            self.assertIn("insufficient_scope", response.text)

    def test_profile_uses_existing_account_endpoints_and_preserves_partial_errors(self):
        calls = []

        def remote(method, path, token=None):
            calls.append(path)
            self.assertEqual(method, "GET")
            self.assertEqual(token, "secret-access")
            if path == "/developer/v1/me":
                return {"sub": "subject"}
            if path.endswith("/user/me"):
                return {
                    "id": "abcdefghijklmn1",
                    "nickname": "Alice",
                    "username": "alice",
                    "level": 7,
                    "countries": ["AU"],
                    "series": [{"en": "CHUNITHM"}],
                    "favorite_arcades": [
                        {"name": "Test arcade", "country": "AU", "address": "Sydney"}
                    ],
                }
            if "/user/activity" in path:
                raise ProtocolError("offline", 502)
            return {"total_visits": 26}

        with patch("partner.client.remote", side_effect=remote):
            response = self.case.post(
                "/musecat/profile", form={"csrf": self.case.csrf(), "format": "json"}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["profile"]["series"][0]["en"], "CHUNITHM")
            self.assertEqual(response.json["passport"]["data"]["total_visits"], 26)
            self.assertEqual(response.json["activity"]["status"], "unavailable")
            self.assertNotIn("secret-access", response.text)
            page = self.case.post("/musecat/profile", form={"csrf": self.case.csrf()})
            self.assertIn("Test arcade", page.text)
            self.assertIn("CHUNITHM", page.text)
            self.assertIn("AU", page.text)
        self.assertTrue(
            any("/user/changelog?user=abcdefghijklmn1" in path for path in calls)
        )

    def test_disconnect_during_read_does_not_display_stale_account_data(self):
        def remote(*args, **kwargs):
            with ledger().transaction() as tx:
                ledger().delete(tx, "link", "alice")
            return {"sub": "subject", "id": "abcdefghijklmn1"}

        with patch("partner.client.remote", side_effect=remote):
            response = self.case.post(
                "/musecat/profile", form={"csrf": self.case.csrf(), "format": "json"}
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json["error"], "connection_changed")
