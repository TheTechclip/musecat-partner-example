"""Cryptographic verification, one-use callbacks and separate local login sessions."""

import json
import time
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from partner.common import ProtocolError, ledger
from partner.oidc import validate_id_token
from partner.worker import deliver
from tests import test_protocol as protocol

ORIGIN = protocol.ORIGIN


class OIDCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        cls.jwk.update(kid="test-key", alg="RS256", use="sig")

    def setUp(self):
        self.case = protocol.ProtocolTests()
        self.case.setUp()
        self.app, self.http = self.case.app, self.case.http
        self.app.config.update(
            MUSECAT_LOGIN_CLIENT_ID="login-app", MUSECAT_LOGIN_CLIENT_SECRET="l" * 43
        )
        self.issuer = self.app.config["MUSECAT_ISSUER"]
        self.metadata = {
            "issuer": self.issuer,
            **{
                key: self.issuer + path
                for key, path in {
                    "authorization_endpoint": "/oauth/authorize",
                    "token_endpoint": "/oauth/token",
                    "userinfo_endpoint": "/oauth/userinfo",
                    "jwks_uri": "/oauth/jwks",
                }.items()
            },
        }

    def tearDown(self):
        self.case.tearDown()

    def token(self, overrides=None):
        claims = {
            "iss": self.issuer,
            "sub": "app-specific-subject",
            "aud": "login-app",
            "iat": int(time.time()),
            "exp": int(time.time()) + 600,
            "nonce": "nonce",
        }
        claims.update(overrides or {})
        return jwt.encode(
            claims, self.key, algorithm="RS256", headers={"kid": "test-key"}
        )

    def start(self):
        with patch("partner.oidc.remote", return_value=self.metadata):
            response = self.case.post("/oidc/login", form={"csrf": self.case.csrf()})
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response.location).query)
        self.assertEqual(query["scope"], ["openid profile arcade:read"])
        self.assertNotIn("account:access", query["scope"][0])
        self.assertEqual(query["redirect_uri"], [ORIGIN + "/oidc/callback"])
        return query

    def finish(self, query, identity=None, token_overrides=None):
        token = {
            "token_type": "Bearer",
            "scope": "openid profile arcade:read",
            "expires_in": 600,
            "access_token": "oidc-access",
            "refresh_token": "oidc-refresh",
            "id_token": self.token({"nonce": query["nonce"][0]}),
        }
        token.update(token_overrides or {})
        values = [
            token,
            {"keys": [self.jwk]},
            identity
            if identity is not None
            else {"sub": "app-specific-subject", "nickname": "Demo Alice"},
        ]
        with patch("partner.oidc.remote", side_effect=values):
            return self.http.get(
                "/oidc/callback",
                base_url=ORIGIN,
                query_string={
                    "code": "code",
                    "state": query["state"][0],
                    "iss": self.issuer,
                },
            )

    def test_login_verifies_and_rotates_session_without_merging_demo(self):
        with self.http.session_transaction(base_url=ORIGIN) as sess:
            original_sid = sess.get("sid")
        query = self.start()
        response = self.finish(query)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        with self.http.session_transaction(base_url=ORIGIN) as sess:
            self.assertTrue(sess["user"].startswith("oidc:"))
            self.assertNotEqual(sess["user"], "alice")
            self.assertNotEqual(sess["sid"], original_sid)
            handle = sess["oidc_session"]
            self.assertNotIn("oidc-access", str(dict(sess)))
            self.assertNotIn("oidc-refresh", str(dict(sess)))
        with self.app.app_context(), ledger().transaction() as tx:
            login = ledger().get(tx, "oidc_session", handle)
            self.assertEqual(login["sub"], "app-specific-subject")
            self.assertEqual(ledger().items(tx, "link"), [])
            self.assertEqual(ledger().items(tx, "grant"), [])
        with patch("partner.oidc.remote") as remote:
            replay = self.http.get(
                "/oidc/callback",
                base_url=ORIGIN,
                query_string={
                    "code": "code",
                    "state": query["state"][0],
                    "iss": self.issuer,
                },
            )
            self.assertEqual(replay.status_code, 400)
            remote.assert_not_called()
        self.case.post("/logout", form={"csrf": self.case.csrf()})
        with self.app.app_context(), ledger().transaction() as tx:
            self.assertIsNone(ledger().get(tx, "oidc_session", handle))
        with patch("partner.worker.remote", return_value={}) as remote:
            self.assertEqual(deliver(self.app), 1)
            self.assertEqual(
                remote.call_args.kwargs["client_auth"], ("login-app", "l" * 43)
            )

    def test_rejects_wrong_claims_and_signatures(self):
        cases = [
            {"iss": self.issuer + "/wrong"},
            {"aud": "other"},
            {"aud": ["login-app", "other"]},
            {"azp": "other"},
            {"nonce": "wrong"},
            {"nonce": "한글"},
            {"sub": ""},
            {"exp": int(time.time()) - 60},
            {"iat": int(time.time()) + 120},
            {"exp": int(time.time()) + 1200},
            {"iat": None},
            {"iat": True},
        ]
        for override in cases:
            with self.subTest(override=override), self.assertRaises(ProtocolError):
                validate_id_token(
                    self.token(override),
                    {"keys": [self.jwk]},
                    "nonce",
                    "login-app",
                    self.issuer,
                )
        with self.assertRaises(ProtocolError):
            validate_id_token(
                self.token(), {"keys": []}, "nonce", "login-app", self.issuer
            )
        with self.assertRaises(ProtocolError):
            validate_id_token(
                jwt.encode(
                    {"sub": "sub"},
                    "s" * 32,
                    algorithm="HS256",
                    headers={"kid": "test-key"},
                ),
                {"keys": [self.jwk]},
                "nonce",
                "login-app",
                self.issuer,
            )

    def test_bad_userinfo_revokes_issued_tokens(self):
        response = self.finish(
            self.start(), identity={"sub": "different", "nickname": "Alice"}
        )
        self.assertEqual(response.status_code, 502)
        with self.app.app_context(), ledger().transaction() as tx:
            self.assertEqual(ledger().items(tx, "oidc_session"), [])
            jobs = ledger().items(tx, "outbox")
            self.assertEqual(jobs[0][1]["kind"], "oidc")

    def test_state_is_browser_bound_and_denial_is_one_use(self):
        query = self.start()
        other = self.app.test_client()
        with patch("partner.oidc.remote") as remote:
            response = other.get(
                "/oidc/callback",
                base_url=ORIGIN,
                query_string={
                    "code": "code",
                    "state": query["state"][0],
                    "iss": self.issuer,
                },
            )
            self.assertEqual(response.status_code, 400)
            remote.assert_not_called()
        denied = self.http.get(
            "/oidc/callback",
            base_url=ORIGIN,
            query_string={
                "error": "access_denied",
                "state": query["state"][0],
                "iss": self.issuer,
            },
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.finish(query).status_code, 400)

    def test_expiry_ends_local_session_and_queues_revocation(self):
        self.assertEqual(self.finish(self.start()).status_code, 302)
        with self.http.session_transaction(base_url=ORIGIN) as sess:
            handle = sess["oidc_session"]
        with self.app.app_context(), ledger().transaction() as tx:
            value = ledger().get(tx, "oidc_session", handle)
            value["expires_at"] = 0
            ledger().put(tx, "oidc_session", handle, value, int(time.time()) + 1000)
        self.http.get("/", base_url=ORIGIN)
        with self.http.session_transaction(base_url=ORIGIN) as sess:
            self.assertNotIn("user", sess)
        with self.app.app_context(), ledger().transaction() as tx:
            self.assertEqual(len(ledger().items(tx, "outbox")), 1)

    def test_malformed_upstream_is_a_recoverable_error(self):
        with patch("partner.oidc.remote", return_value=[]):
            response = self.case.post("/oidc/login", form={"csrf": self.case.csrf()})
        self.assertEqual(response.status_code, 502)
        for bad in [{"token_type": []}, {"scope": {}}, {"expires_in": True}]:
            response = self.finish(self.start(), token_overrides=bad)
            self.assertEqual(response.status_code, 502)
