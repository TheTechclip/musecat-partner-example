"""Standalone OIDC login: a separate client, verified identity, server-held tokens."""

import hmac
import urllib.parse

import jwt
from flask import Blueprint, current_app, g, redirect, render_template, request, session

from .common import (
    FAMILY,
    ProtocolError,
    challenge,
    ledger,
    now,
    opaque,
    reject_duplicates,
    remote,
    require_csrf,
)
from .storage import digest

bp = Blueprint("oidc", __name__)
SCOPES = "openid profile arcade:read"


def credentials():
    cid = current_app.config.get("MUSECAT_LOGIN_CLIENT_ID", "")
    secret = current_app.config.get("MUSECAT_LOGIN_CLIENT_SECRET", "")
    if not cid or not secret:
        raise ProtocolError("oidc_configuration_required", 503)
    return cid, secret


def callback():
    return current_app.config["PARTNER_ORIGIN"] + "/oidc/callback"


def validate_id_token(token, jwks, nonce, client_id, issuer):
    try:
        if not isinstance(token, str) or len(token) > 16384:
            raise ValueError("invalid token size")
        header = jwt.get_unverified_header(token)
        if (
            header.get("alg") != "RS256"
            or not isinstance(header.get("kid"), str)
            or header.get("crit")
        ):
            raise ValueError("unsupported header")
        keys = [key for key in jwks["keys"] if key.get("kid") == header["kid"]]
        if (
            len(keys) != 1
            or keys[0].get("kty") != "RSA"
            or keys[0].get("use", "sig") != "sig"
            or keys[0].get("alg", "RS256") != "RS256"
        ):
            raise ValueError("unsupported key")
        key = jwt.PyJWK.from_dict(keys[0], algorithm="RS256").key
        if key.key_size < 2048:
            raise ValueError("weak key")
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=issuer,
            options={
                "require": ["iss", "aud", "sub", "iat", "exp", "nonce"],
                "strict_aud": True,
            },
            leeway=30,
        )
        if (
            not isinstance(claims["sub"], str)
            or not claims["sub"]
            or len(claims["sub"]) > 512
        ):
            raise ValueError("invalid subject")
        if (
            any(type(claims[k]) is not int for k in ["iat", "exp"])
            or not 0 < claims["exp"] - claims["iat"] <= 600
        ):
            raise ValueError("invalid lifetime")
        if claims.get("azp", client_id) != client_id:
            raise ValueError("invalid authorized party")
    except (jwt.PyJWTError, ValueError, TypeError, KeyError, AttributeError):
        raise ProtocolError("invalid_id_token", 400) from None
    if (
        not isinstance(claims["nonce"], str)
        or not claims["nonce"].isascii()
        or not hmac.compare_digest(claims["nonce"], nonce)
    ):
        raise ProtocolError("invalid_nonce", 400)
    return claims


def end_session():
    handle = session.pop("oidc_session", None)
    if not handle:
        return
    with ledger().transaction() as tx:
        login = ledger().get(tx, "oidc_session", handle)
        if login:
            ledger().put(
                tx,
                "outbox",
                "oidc-" + digest(handle),
                {
                    "kind": "oidc",
                    "client_id": login["client_id"],
                    "token": login["revocation_token"],
                    "next": now(),
                    "attempts": 0,
                },
                now() + FAMILY,
            )
            ledger().delete(tx, "oidc_session", handle)
    if str(session.get("user", "")).startswith("oidc:"):
        session.pop("user", None)


@bp.before_app_request
def load_session():
    g.oidc_login = None
    handle = session.get("oidc_session")
    if not handle:
        return
    with ledger().transaction() as tx:
        login = ledger().get(tx, "oidc_session", handle)
    if (
        not login
        or login["expires_at"] <= now()
        or login["uid"] != session.get("user")
        or login["client_id"] != current_app.config.get("MUSECAT_LOGIN_CLIENT_ID")
    ):
        end_session()
        return
    g.oidc_login = login


@bp.post("/oidc/login")
def start():
    require_csrf()
    client_id, _ = credentials()
    issuer = current_app.config["MUSECAT_ISSUER"]
    discovery = remote("GET", "/.well-known/openid-configuration")
    expected = {
        "issuer": issuer,
        "authorization_endpoint": issuer + "/oauth/authorize",
        "token_endpoint": issuer + "/oauth/token",
        "userinfo_endpoint": issuer + "/oauth/userinfo",
        "jwks_uri": issuer + "/oauth/jwks",
    }
    if not isinstance(discovery, dict) or any(
        discovery.get(k) != value for k, value in expected.items()
    ):
        raise ProtocolError("invalid_oidc_metadata", 502)
    state, verifier, nonce = opaque(), opaque(), opaque()
    session.setdefault("sid", opaque())
    with ledger().transaction() as tx:
        ledger().put(
            tx,
            "oidc_attempt",
            digest(state),
            {
                "session": session["sid"],
                "verifier": verifier,
                "nonce": nonce,
                "client_id": client_id,
            },
            now() + 300,
        )
    return redirect(
        discovery["authorization_endpoint"]
        + "?"
        + urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": callback(),
                "scope": SCOPES,
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge(verifier),
                "code_challenge_method": "S256",
            }
        )
    )


@bp.get("/oidc/callback")
def complete():
    reject_duplicates(request.args)
    state = request.args.get("state", "")
    with ledger().transaction() as tx:
        attempt = ledger().get(tx, "oidc_attempt", digest(state))
        if not attempt or attempt["session"] != session.get("sid"):
            raise ProtocolError("invalid_state")
        # A callback, including denial, is one-use; network ambiguity requires a new flow.
        ledger().delete(tx, "oidc_attempt", digest(state))
    client_id, secret = credentials()
    if (
        attempt["client_id"] != client_id
        or request.args.get("iss") != current_app.config["MUSECAT_ISSUER"]
    ):
        raise ProtocolError("invalid_request")
    if request.args.get("error"):
        if request.args.get("code"):
            raise ProtocolError("invalid_request")
        raise ProtocolError("access_denied", 403)
    code = request.args.get("code", "")
    if not code or len(code) > 512:
        raise ProtocolError("invalid_request")
    token = remote(
        "POST",
        "/oauth/token",
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": callback(),
            "code_verifier": attempt["verifier"],
        },
        form=True,
        client_auth=(client_id, secret),
    )
    if not isinstance(token, dict):
        raise ProtocolError("invalid_musecat_token", 502)
    refresh, access = token.get("refresh_token"), token.get("access_token")
    valid_refresh = isinstance(refresh, str) and 0 < len(refresh) <= 512
    valid_access = isinstance(access, str) and 0 < len(access) <= 512
    revocation_token = refresh if valid_refresh else access if valid_access else None
    try:
        if (
            not isinstance(token.get("token_type"), str)
            or token["token_type"].lower() != "bearer"
            or not isinstance(token.get("scope"), str)
            or set(token.get("scope", "").split()) != set(SCOPES.split())
            or type(token.get("expires_in")) is not int
            or not 0 < token["expires_in"] <= 600
            or not isinstance(token.get("access_token"), str)
            or not valid_access
            or (refresh is not None and not valid_refresh)
        ):
            raise ProtocolError("invalid_musecat_token", 502)
        claims = validate_id_token(
            token.get("id_token", ""),
            remote("GET", "/oauth/jwks"),
            attempt["nonce"],
            client_id,
            current_app.config["MUSECAT_ISSUER"],
        )
        identity = remote("GET", "/oauth/userinfo", token=token["access_token"])
        if not isinstance(identity, dict) or identity.get("sub") != claims["sub"]:
            raise ProtocolError("invalid_musecat_identity", 502)
    except ProtocolError:
        if isinstance(revocation_token, str) and revocation_token:
            with ledger().transaction() as tx:
                ledger().put(
                    tx,
                    "outbox",
                    "oidc-" + opaque(),
                    {
                        "kind": "oidc",
                        "client_id": client_id,
                        "token": revocation_token,
                        "next": now(),
                        "attempts": 0,
                    },
                    now() + FAMILY,
                )
        raise
    name = (
        identity.get("nickname") or identity.get("preferred_username") or "Musecat user"
    )
    if not isinstance(name, str) or len(name) > 128:
        name = "Musecat user"
    end_session()
    locale = session.get("locale")
    session.clear()
    handle = opaque()
    uid = "oidc:" + digest(
        current_app.config["MUSECAT_ISSUER"] + "\x00" + claims["sub"]
    )
    with ledger().transaction() as tx:
        ledger().put(
            tx,
            "oidc_session",
            handle,
            {
                "uid": uid,
                "client_id": client_id,
                "sub": claims["sub"],
                "name": identity.get("nickname")
                or identity.get("preferred_username")
                or "Musecat user",
                "access": token["access_token"],
                "revocation_token": revocation_token,
                "expires_at": min(now() + token["expires_in"], claims["exp"]),
            },
            now() + FAMILY,
        )
    session.update(user=uid, oidc_session=handle, sid=opaque())
    if locale:
        session["locale"] = locale
    return redirect("/")


@bp.post("/oidc/nearby")
def nearby():
    require_csrf()
    if not g.oidc_login:
        raise ProtocolError("login_required", 401)
    # An explicit demo location; this does not request or infer the user's position.
    data = remote(
        "GET",
        "/developer/v1/arcades/nearby?lat=37.5665&lon=126.978&distance_limit=5",
        token=g.oidc_login["access"],
    )
    return render_template("oidc-nearby.html", data=data)
