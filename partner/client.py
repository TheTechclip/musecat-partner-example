"""Direction A: session-bound PKCE and encrypted Musecat credentials."""

import uuid
from urllib.parse import urlencode

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
)

from .common import (
    FAMILY,
    ProtocolError,
    callback,
    challenge,
    ledger,
    now,
    opaque,
    reject_duplicates,
    remote,
    require_csrf,
    require_user,
    revoke_local,
    stamp,
)
from .storage import digest

bp = Blueprint("client", __name__)


def save_link(tx, uid, token, identity, attempt):
    if not isinstance(identity.get("sub"), str) or not identity["sub"]:
        raise ProtocolError("invalid_musecat_identity", 502)
    for other, link in ledger().items(tx, "link"):
        if other != uid and link["sub"] == identity["sub"]:
            raise ProtocolError("musecat_identity_already_connected", 409)
    existing = ledger().get(tx, "link", uid)
    if existing and existing["sub"] != identity["sub"]:
        raise ProtocolError("disconnect_before_reconnecting", 409)
    link = {
        "id": opaque(),
        "sub": identity["sub"],
        "name": identity.get("nickname") or identity.get("username") or "Musecat user",
        "access": token["access_token"],
        "refresh": token["refresh_token"],
        "revocation_token": token["refresh_token"],
        "access_expires": now() + token["expires_in"],
        "expires": now() + FAMILY,
        "pair_id": attempt.get("correlation_id"),
        "generation": attempt.get("generation"),
        "partial": bool(attempt.get("correlation_id")),
    }
    ledger().put(tx, "link", uid, link, link["expires"])
    return link


def validate_token(token):
    if (
        token.get("token_type", "").lower() != "bearer"
        or set(token.get("scope", "").split()) != {"account:access"}
        or not isinstance(token.get("expires_in"), int)
        or token["expires_in"] <= 0
        or not all(
            isinstance(token.get(k), str) and token[k]
            for k in ["access_token", "refresh_token"]
        )
    ):
        raise ProtocolError("invalid_musecat_token", 502)


@bp.post("/connect/musecat")
def connect():
    require_csrf()
    uid = require_user()
    if not current_app.config["MUSECAT_CLIENT_SECRET"]:
        raise ProtocolError("musecat_configuration_required", 503)
    metadata = remote("GET", "/.well-known/oauth-authorization-server")
    issuer = current_app.config["MUSECAT_ISSUER"]
    if (
        metadata.get("issuer") != issuer
        or metadata.get("authorization_endpoint") != issuer + "/oauth/authorize"
    ):
        raise ProtocolError("invalid_musecat_metadata", 502)
    state, verifier = opaque(), opaque()
    session.setdefault("sid", opaque())
    with ledger().transaction() as tx:
        if ledger().get(tx, "link", uid):
            raise ProtocolError("disconnect_before_reconnecting", 409)
        ledger().put(
            tx,
            "oauth_attempt",
            digest(state),
            {"user": uid, "session": session["sid"], "verifier": verifier},
            now() + 300,
        )
    return redirect(
        issuer
        + "/oauth/authorize?"
        + urlencode(
            {
                "client_id": current_app.config["PARTNER_ID"],
                "redirect_uri": callback(),
                "response_type": "code",
                "scope": "account:access",
                "state": state,
                "code_challenge": challenge(verifier),
                "code_challenge_method": "S256",
            }
        )
    )


@bp.get("/oauth/musecat/callback")
def complete():
    reject_duplicates(request.args)
    uid = require_user()
    state, code = request.args.get("state", ""), request.args.get("code", "")
    with ledger().transaction() as tx:
        attempt = ledger().get(tx, "oauth_attempt", digest(state))
        namespace, key = "oauth_attempt", digest(state)
        if not attempt:
            attempt = ledger().get(tx, "attempt", state)
            namespace, key = "attempt", state
        if (
            not attempt
            or attempt["user"] != uid
            or attempt["session"] != session.get("sid")
        ):
            raise ProtocolError("invalid_state")
        if request.args.get("iss") != current_app.config["MUSECAT_ISSUER"] or (
            request.args.get("error") and code
        ):
            raise ProtocolError("invalid_request")
        if not code or request.args.get("error"):
            ledger().delete(tx, namespace, key)
            return redirect("/?result=cancelled")
        if namespace == "attempt" and (
            not attempt.get("consumed")
            or digest(code) != attempt.get("musecat_code_hash")
        ):
            raise ProtocolError("invalid_receipt")
        # Consume before network I/O: never retry an uncertain code exchange.
        ledger().delete(tx, namespace, key)
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
    )
    try:
        validate_token(token)
        identity = remote("GET", "/developer/v1/me", token=token["access_token"])
    except ProtocolError:
        if isinstance(token.get("refresh_token"), str) and token["refresh_token"]:
            with ledger().transaction() as tx:
                queue_revoke(tx, token["refresh_token"])
        raise
    with ledger().transaction() as tx:
        try:
            link = save_link(tx, uid, token, identity, attempt)
        except ProtocolError:
            # Preserve the newly issued token only as a revocation job.
            queue_revoke(tx, token["refresh_token"])
            link = None
    if link is None:
        raise ProtocolError("musecat_identity_already_connected", 409)
    if attempt.get("correlation_id"):
        status = remote(
            "GET", "/partner/v1/joint/" + attempt["correlation_id"], joint=True
        )
        with ledger().transaction() as tx:
            grant = ledger().get(tx, "grant", attempt["grant"])
            connected = (
                status.get("status") == "connected"
                and status.get("generation") == attempt["generation"]
                and status.get("musecat_access") is True
                and status.get("partner_access") is True
                and grant
                and not grant["revoked"]
                and grant["exchanged"]
            )
            link["partial"] = not connected
            ledger().put(tx, "link", uid, link, link["expires"])
        if connected and attempt.get("completion"):
            return redirect(attempt["completion"])
    return redirect("/")


def queue_revoke(tx, token):
    jid = str(uuid.uuid4())
    ledger().put(
        tx,
        "outbox",
        jid,
        {"kind": "oauth", "token": token, "next": now(), "attempts": 0},
        now() + 365 * 86400,
    )


@bp.post("/disconnect")
def disconnect():
    require_csrf()
    uid = require_user()
    with ledger().transaction() as tx:
        link = ledger().get(tx, "link", uid)
        if link:
            if link.get("pair_id"):
                revoke_local(tx, link["pair_id"], link["generation"])
                jid = str(uuid.uuid4())
                ledger().put(
                    tx,
                    "outbox",
                    jid,
                    {
                        "kind": "joint",
                        "body": {
                            "pair_id": link["pair_id"],
                            "generation": link["generation"],
                            "reason": "user",
                            "revoked_at": stamp(),
                        },
                        "next": now(),
                        "attempts": 0,
                    },
                    now() + 365 * 86400,
                )
            else:
                ledger().delete(tx, "link", uid)
                queue_revoke(tx, link.get("revocation_token") or link["refresh"])
    return redirect("/")


def authorized_link(force_refresh=False):
    uid = require_user()
    # Claim the refresh before network I/O; concurrent refresh calls fail closed.
    with ledger().transaction() as tx:
        link = ledger().get(tx, "link", uid)
        if not link or link.get("partial"):
            raise ProtocolError("connection_required", 409)
        if not link["refresh"]:
            raise ProtocolError("refresh_in_progress_or_failed_reconnect", 409)
        if link["access_expires"] <= now() or force_refresh:
            # Remove refresh from usable state before trying: ambiguous network failures require reconnect.
            refresh = link["refresh"]
            link["refresh"] = ""
            ledger().put(tx, "link", uid, link, link["expires"])
    if not link["refresh"]:
        try:
            token = remote(
                "POST",
                "/oauth/token",
                {"grant_type": "refresh_token", "refresh_token": refresh},
                form=True,
            )
            validate_token(token)
        except ProtocolError:
            # Failed/uncertain rotation remains unusable instead of replaying the old refresh token.
            raise ProtocolError("refresh_failed_reconnect", 409) from None
        with ledger().transaction() as tx:
            current = ledger().get(tx, "link", uid)
            changed = not current or current["id"] != link["id"]
            if changed:
                queue_revoke(tx, token["refresh_token"])
            else:
                current.update(
                    access=token["access_token"],
                    refresh=token["refresh_token"],
                    revocation_token=token["refresh_token"],
                    access_expires=now() + token["expires_in"],
                )
                ledger().put(tx, "link", uid, current, current["expires"])
                link = current
        if changed:
            raise ProtocolError("connection_changed", 409)
    return uid, link


def verify_link(uid, link):
    with ledger().transaction() as tx:
        current = ledger().get(tx, "link", uid)
        if not current or current["id"] != link["id"] or current.get("partial"):
            raise ProtocolError("connection_changed", 409)


@bp.post("/musecat/profile")
def profile():
    require_csrf()
    uid, link = authorized_link(request.form.get("refresh") == "yes")
    identity = remote("GET", "/developer/v1/me", token=link["access"])
    if identity.get("sub") != link["sub"]:
        raise ProtocolError("invalid_musecat_identity", 502)
    account = remote("GET", "/developer/v1/account/user/me", token=link["access"])
    if not isinstance(account.get("id"), str) or not account["id"]:
        raise ProtocolError("invalid_musecat_profile", 502)
    # Every read uses the same user-authorized account token and existing domain handlers.
    user_id = account["id"]
    data = {"identity": identity, "profile": account}
    for name, path in {
        "passport": "/user/passport?year=all",
        "stamps": "/user/passport/stamps?year=all&page=1&per_page=24",
        "activity": "/user/activity?"
        + urlencode({"id": user_id, "days": 365, "tz": "UTC"}),
        "contributions": "/user/changelog?"
        + urlencode({"user": user_id, "page": 1, "per_page": 24}),
    }.items():
        try:
            data[name] = {
                "status": "ok",
                "data": remote(
                    "GET", "/developer/v1/account" + path, token=link["access"]
                ),
            }
        except ProtocolError as error:
            data[name] = {"status": "unavailable", "error": error.code}
    verify_link(uid, link)
    if request.form.get("format") == "json":
        return jsonify(data)
    return render_template("profile.html", data=data, profile=account)
