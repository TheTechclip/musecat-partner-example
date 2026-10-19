import base64
import io
import html
import json
import tempfile
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet

from partner import create_app
from partner.common import ProtocolError, remote
from partner.recovery import ADVICE, GROUPS, LABELS, upstream_error


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = create_app(
            {
                "TESTING": True,
                "DATA_DIR": self.directory.name,
                "PARTNER_ORIGIN": "https://partner.example",
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
        )

        @self.app.get("/test-error/<code>")
        def fail(code):
            raise ProtocolError(code, 403)

        @self.app.get("/api/test-error")
        def protocol_fail():
            raise ProtocolError("invalid_client", 401)

        self.http = self.app.test_client()

    def upstream(self, status, error, headers=None):
        return urllib.error.HTTPError(
            "https://db-dev.musecat.app/oauth/token",
            status,
            "UNTRUSTED MESSAGE",
            headers or {},
            io.BytesIO(json.dumps(error).encode()),
        )

    def test_localized_browser_and_json_negotiation(self):
        for locale in ("en", "ko", "ja"):
            response = self.http.get(
                "/test-error/invalid_origin",
                base_url="https://partner.example",
                headers={"Accept": "text/html", "Accept-Language": locale},
            )
            self.assertEqual(response.status_code, 403)
            self.assertIn('lang="' + locale + '"', response.text)
            self.assertIn(ADVICE["origin"][locale][0], html.unescape(response.text))
            self.assertIn(LABELS[locale][3], response.text)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        for accept in ("application/json", "*/*", "text/html,application/json"):
            response = self.http.get(
                "/test-error/invalid_origin",
                base_url="https://partner.example",
                headers={"Accept": accept},
            )
            self.assertEqual(response.json, {"error": "invalid_origin"})
        self.assertEqual(
            self.http.get(
                "/test-error/invalid_origin?format=json",
                base_url="https://partner.example",
                headers={"Accept": "text/html"},
            ).json,
            {"error": "invalid_origin"},
        )
        self.assertEqual(
            self.http.get(
                "/api/test-error",
                base_url="https://partner.example",
                headers={"Accept": "text/html"},
            ).json,
            {"error": "invalid_client"},
        )

    def test_codes_are_escaped_and_recovery_has_no_callback_replay(self):
        from urllib.parse import quote

        code = '<img src=x onerror="alert(1)">'
        response = self.http.get(
            "/test-error/" + quote(code, safe=""),
            base_url="https://partner.example",
            headers={"Accept": "text/html"},
        )
        self.assertNotIn("<img", response.text)
        self.assertIn("&lt;img", response.text)
        self.assertNotIn("http-equiv", response.text)
        self.assertNotIn("/oauth/musecat/callback", response.text)
        for group in GROUPS:
            self.assertEqual(set(ADVICE[group]), {"en", "ko", "ja"})
            for locale, (cause, step) in ADVICE[group].items():
                self.assertTrue(cause and step, locale)

    def test_upstream_codes_bounded_and_descriptions_discarded(self):
        error = upstream_error(
            self.upstream(
                400,
                {
                    "error": "invalid_grant",
                    "error_description": "SECRET TOKEN <script>",
                },
            )
        )
        self.assertEqual((error.code, error.status), ("invalid_grant", 400))
        for data in (
            {"error": "SECRET TOKEN <script>"},
            {"error": {"token": "SECRET"}},
            ["invalid_grant"],
            {"error": "invalid_client", "pad": "x" * 9000},
        ):
            error = upstream_error(self.upstream(400, data))
            self.assertEqual(
                (error.code, error.status), ("musecat_request_failed", 502)
            )
        self.assertEqual(
            upstream_error(self.upstream(503, {"error": "invalid_client"})).code,
            "musecat_unavailable",
        )

    def test_rate_limit_delay_is_bounded(self):
        for delay, expected in (
            ("45", 45),
            ("999999999999999999999", None),
            ("9999", None),
            ("-1", None),
            ("Wed, 21 Oct 2026 00:00:00 GMT", None),
            ("１２", None),
        ):
            error = upstream_error(self.upstream(429, {}, {"Retry-After": delay}))
            self.assertEqual(
                (error.code, error.status, error.retry_after),
                ("rate_limited", 429, expected),
            )
        with self.app.test_request_context("/test-error/rate_limited"):
            from partner.recovery import error_response

            response = error_response(
                ProtocolError("rate_limited", 429, retry_after=45)
            )
            self.assertEqual(response.headers["Retry-After"], "45")
            self.assertEqual(response.json, {"error": "rate_limited"})

    def test_remote_dedicated_oidc_client_auth_and_safe_failure(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = (
            b'{"access_token":"test"}'
        )
        with (
            self.app.app_context(),
            patch("urllib.request.build_opener", return_value=opener),
        ):
            self.assertEqual(
                remote(
                    "POST",
                    "/oauth/token",
                    {"grant_type": "authorization_code"},
                    form=True,
                    client_auth=("login_client", "login_secret"),
                ),
                {"access_token": "test"},
            )
            sent = opener.open.call_args.args[0]
            self.assertEqual(
                sent.get_header("Authorization"),
                "Basic " + base64.b64encode(b"login_client:login_secret").decode(),
            )
            remote("POST", "/oauth/token", {}, form=True)
            sent = opener.open.call_args.args[0]
            self.assertEqual(
                sent.get_header("Authorization"),
                "Basic "
                + base64.b64encode(("example_test:" + "m" * 43).encode()).decode(),
            )
            for failure, code, status in (
                (
                    self.upstream(
                        401, {"error": "invalid_client", "message": "SECRET"}
                    ),
                    "invalid_client",
                    401,
                ),
                (urllib.error.URLError("SECRET"), "musecat_unavailable", 503),
            ):
                opener.open.side_effect = failure
                with self.assertRaises(ProtocolError) as caught:
                    remote("POST", "/oauth/token", {}, form=True)
                self.assertEqual(
                    (caught.exception.code, caught.exception.status), (code, status)
                )
            opener.open.side_effect = None
            opener.open.return_value.__enter__.return_value.read.return_value = (
                b"not-json SECRET"
            )
            with self.assertRaises(ProtocolError) as caught:
                remote("GET", "/oauth/userinfo")
            self.assertEqual(
                (caught.exception.code, caught.exception.status),
                ("invalid_musecat_response", 502),
            )
