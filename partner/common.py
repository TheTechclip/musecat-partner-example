import base64
import hmac
import json
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

from flask import current_app, request, session

from .storage import digest

MANIFEST = "musecat-joint/v1"
SCOPES = ["profile", "chunithm:read"]
FAMILY = 30 * 24 * 3600


class ProtocolError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status


def ledger():
    return current_app.extensions["ledger"]


def now():
    return int(time.time())


def opaque():
    return secrets.token_urlsafe(32)


def stamp(value=None):
    return (
        datetime.fromtimestamp(now() if value is None else value, timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def challenge(verifier):
    return (
        base64.urlsafe_b64encode(bytes.fromhex(digest(verifier))).decode().rstrip("=")
    )


def valid_challenge(value):
    return (
        isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{43}", value) is not None
    )


def callback():
    return current_app.config["PARTNER_ORIGIN"] + "/oauth/musecat/callback"


def musecat_callback():
    return (
        current_app.config["MUSECAT_WEB_ORIGIN"]
        + "/api/user/connections/callback/"
        + current_app.config["PARTNER_ID"]
    )


def csrf():
    session.setdefault("csrf", opaque())
    return session["csrf"]


def require_csrf():
    if request.headers.get("Origin") not in (
        None,
        current_app.config["PARTNER_ORIGIN"],
    ):
        raise ProtocolError("invalid_origin", 403)
    if not hmac.compare_digest(
        request.form.get("csrf", ""), session.get("csrf", opaque())
    ):
        raise ProtocolError("invalid_csrf", 403)


def user():
    return session.get("user")


def require_user():
    if not user():
        raise ProtocolError("login_required", 401)
    return user()


def basic_auth():
    auth = request.authorization
    if not auth or auth.type.lower() != "basic":
        raise ProtocolError("invalid_client", 401)
    cid = urllib.parse.unquote_plus(auth.username or "")
    secret = urllib.parse.unquote_plus(auth.password or "")
    if not (
        hmac.compare_digest(cid, current_app.config["PARTNER_OAUTH_CLIENT_ID"])
        and hmac.compare_digest(
            secret, current_app.config["PARTNER_OAUTH_CLIENT_SECRET"]
        )
    ):
        raise ProtocolError("invalid_client", 401)


def bearer_key():
    supplied = request.headers.get("Authorization", "")
    keys = [current_app.config["MUSECAT_TO_PARTNER_KEY"]]
    if current_app.config.get("PREVIOUS_KEY_EXPIRES_AT", 0) > now():
        keys.append(current_app.config.get("MUSECAT_TO_PARTNER_PREVIOUS_KEY", ""))
    if not any(
        key and hmac.compare_digest(supplied.encode(), ("Bearer " + key).encode())
        for key in keys
    ):
        raise ProtocolError("unauthorized_partner", 401)


def token_grant(tx):
    auth = request.headers.get("Authorization", "")
    token = (
        ledger().get(tx, "access", digest(auth[7:]))
        if auth.startswith("Bearer ")
        else None
    )
    grant = ledger().get(tx, "grant", token["grant"]) if token else None
    if not grant or grant.get("revoked"):
        raise ProtocolError("invalid_token", 401)
    return grant


def reject_duplicates(values):
    if any(len(values.getlist(key)) != 1 for key in values):
        raise ProtocolError("invalid_request")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def remote(method, path, body=None, token=None, form=False, joint=False):
    """Only call the configured Musecat issuer; never follow redirects or log bodies."""
    url = current_app.config["MUSECAT_ISSUER"] + path
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if joint:
        key = current_app.config["PARTNER_TO_MUSECAT_KEY"]
        if not key:
            raise ProtocolError("musecat_configuration_required", 503)
        headers.update(Authorization="Bearer " + key)
        headers["X-Request-Id"] = (
            body.pop("_request_id", str(uuid.uuid4())) if body else str(uuid.uuid4())
        )
    data = None
    if body is not None:
        if form:
            cid = current_app.config["PARTNER_ID"]
            secret = current_app.config["MUSECAT_CLIENT_SECRET"]
            if not secret:
                raise ProtocolError("musecat_configuration_required", 503)
            basic = urllib.parse.quote_plus(cid) + ":" + urllib.parse.quote_plus(secret)
            headers["Authorization"] = (
                "Basic " + base64.b64encode(basic.encode()).decode()
            )
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = urllib.parse.urlencode(body).encode()
        else:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
    try:
        with urllib.request.build_opener(NoRedirect).open(
            urllib.request.Request(url, data=data, headers=headers, method=method),
            timeout=10,
        ) as response:
            raw = response.read(262145)
            if len(raw) > 262144:
                raise ProtocolError("musecat_response_too_large", 502)
            return json.loads(raw) if raw else {}
    except (urllib.error.URLError, ValueError):
        raise ProtocolError("musecat_request_failed", 502) from None


def revoke_local(tx, pair_id, generation):
    matches = [
        (gid, g)
        for gid, g in ledger().items(tx, "grant")
        if g.get("pair_id") == pair_id and g.get("generation") == generation
    ]
    if not matches:
        return "unknown_generation"
    active = any(not g.get("revoked") for _, g in matches)
    for gid, grant in matches:
        grant["revoked"] = True
        ledger().put(tx, "grant", gid, grant, grant["expires"])
    for uid, link in ledger().items(tx, "link"):
        if link.get("pair_id") == pair_id and link.get("generation") == generation:
            ledger().delete(tx, "link", uid)
    return "revoked" if active else "already_revoked"
