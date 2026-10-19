"""Musecat joint/v1: authenticated intent, receipt and revocation endpoints."""

import json
import uuid
from datetime import datetime
from urllib.parse import urlencode

from flask import Blueprint, g, current_app, jsonify, redirect, request, session

from .common import (
    MANIFEST,
    SCOPES,
    ProtocolError,
    bearer_key,
    callback,
    challenge,
    ledger,
    musecat_callback,
    now,
    opaque,
    require_csrf,
    revoke_local,
    stamp,
    user,
    valid_challenge,
)
from .oauth import create_grant, issue_code
from .storage import digest

bp = Blueprint("joint", __name__)


def uuid4(value):
    try:
        parsed = uuid.UUID(value)
        return parsed.version == 4 and str(parsed) == value
    except (ValueError, TypeError, AttributeError):
        return False


def consent_url(locale="kr"):
    return (
        current_app.config["MUSECAT_WEB_ORIGIN"]
        + "/"
        + locale
        + "/connect/"
        + current_app.config["PARTNER_ID"]
    )


def start_intent(correlation, return_to, completion=None):
    if (
        not current_app.config["MUSECAT_CLIENT_SECRET"]
        or not current_app.config["PARTNER_TO_MUSECAT_KEY"]
    ):
        raise ProtocolError("musecat_configuration_required", 503)
    if not user():
        session["next"] = "/connect/musecat/start?" + urlencode(
            {
                "correlation_id": correlation,
                "return_to": return_to,
                **({"completion_uri": completion} if completion else {}),
            }
        )
        return redirect("/login")
    handle, verifier = opaque(), opaque()
    with ledger().transaction() as tx:
        if ledger().get(tx, "link", user()):
            raise ProtocolError("disconnect_before_reconnecting", 409)
        if ledger().get(tx, "attempt", correlation):
            raise ProtocolError("invalid_intent", 409)
        session.setdefault("sid", opaque())
        intent = {
            "correlation_id": correlation,
            "user": user(),
            "session": session["sid"],
            "verifier": verifier,
            "challenge": challenge(verifier),
            "expires": now() + 300,
            "consumed": False,
            "completion": completion,
        }
        ledger().put(tx, "intent", digest(handle), intent, intent["expires"] + 86400)
        ledger().put(tx, "attempt", correlation, intent, intent["expires"])
    return redirect(return_to + "?" + urlencode({"intent": handle}))


@bp.post("/connect/joint")
def partner_start():
    require_csrf()
    return start_intent(
        str(uuid.uuid4()), consent_url("kr" if g.locale == "ko" else g.locale)
    )


@bp.get("/connect/musecat/start")
def musecat_start():
    correlation, return_to = (
        request.args.get("correlation_id"),
        request.args.get("return_to"),
    )
    completion = request.args.get("completion_uri")
    locales = [
        locale for locale in ["kr", "en", "ja"] if return_to == consent_url(locale)
    ]
    if (
        not uuid4(correlation)
        or not locales
        or (
            completion
            and completion
            != current_app.config["MUSECAT_WEB_ORIGIN"]
            + "/"
            + locales[0]
            + "/settings/connections"
        )
    ):
        raise ProtocolError("invalid_request")
    return start_intent(correlation, return_to, completion)


def execute(action):
    bearer_key()
    request_id = request.headers.get("X-Request-Id")
    body = request.get_json(silent=True)
    if not uuid4(request_id) or not isinstance(body, dict):
        raise ProtocolError("invalid_request")
    fingerprint = digest(json.dumps(body, sort_keys=True, separators=(",", ":")))
    key = request.path + ":" + request_id
    with ledger().transaction() as tx:
        saved = ledger().get(tx, "idempotency", key)
        if saved:
            if saved["fingerprint"] != fingerprint:
                raise ProtocolError("invalid_request", 409)
            return jsonify(saved["response"])
        response = action(tx, body)
        ledger().put(
            tx,
            "idempotency",
            key,
            {"fingerprint": fingerprint, "response": response},
            now() + 600,
        )
    return jsonify(response)


def read_intent(tx, body):
    handle = body.get("intent")
    if not isinstance(handle, str) or not 43 <= len(handle) <= 512:
        raise ProtocolError("invalid_intent")
    intent = ledger().get(tx, "intent", digest(handle))
    if not intent:
        raise ProtocolError("invalid_intent")
    if intent["expires"] <= now():
        raise ProtocolError("intent_expired", 410)
    if intent["consumed"]:
        raise ProtocolError("intent_consumed", 409)
    return intent


@bp.post("/api/joint/intents/lookup")
def lookup():
    def action(tx, body):
        if body.get("partner_id") != current_app.config["PARTNER_ID"]:
            raise ProtocolError("unauthorized_partner", 401)
        intent = read_intent(tx, body)
        return {
            "correlation_id": intent["correlation_id"],
            "sub": "sample:" + intent["user"],
            "name": "Demo " + intent["user"].title(),
            "services": ["chunithm"],
            "manifest": MANIFEST,
            "code_challenge": intent["challenge"],
            "redirect_uri": callback(),
            "expires_at": stamp(intent["expires"]),
        }

    return execute(action)


@bp.post("/api/joint/receipts")
def receipts():
    def action(tx, body):
        intent = read_intent(tx, body)
        if body.get("manifest") != MANIFEST:
            raise ProtocolError("manifest_unsupported")
        if (
            body.get("correlation_id") != intent["correlation_id"]
            or body.get("redirect_uri") != musecat_callback()
            or not valid_challenge(body.get("code_challenge"))
        ):
            raise ProtocolError("invalid_request")
        for key in ["generation", "musecat_code"]:
            if not isinstance(body.get(key), str) or not 1 <= len(body[key]) <= 4096:
                raise ProtocolError("invalid_request")
        try:
            expires = datetime.fromisoformat(
                body["musecat_code_expires_at"].replace("Z", "+00:00")
            ).timestamp()
            if not now() < expires <= now() + 95:
                raise ValueError()
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ProtocolError("invalid_request") from None
        grant = create_grant(
            tx, intent["user"], SCOPES, intent["correlation_id"], body["generation"]
        )
        partner_code = issue_code(tx, grant, body["code_challenge"])
        intent.update(
            consumed=True,
            generation=body["generation"],
            musecat_code_hash=digest(body["musecat_code"]),
            grant=grant["id"],
        )
        ledger().put(
            tx, "intent", digest(body["intent"]), intent, intent["expires"] + 86400
        )
        ledger().put(tx, "attempt", intent["correlation_id"], intent, intent["expires"])
        # The browser callback exchanges Musecat's code AFTER this 200 response.
        return {
            "partner_code": partner_code,
            "partner_code_expires_at": stamp(now() + 90),
            "scope": " ".join(SCOPES),
        }

    return execute(action)


@bp.post("/api/joint/revocations")
def revocations():
    def action(tx, body):
        if (
            not uuid4(body.get("pair_id"))
            or not isinstance(body.get("generation"), str)
            or not body["generation"]
        ):
            raise ProtocolError("invalid_request")
        return {"status": revoke_local(tx, body["pair_id"], body["generation"])}

    return execute(action)
