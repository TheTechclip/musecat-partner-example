"""Typed account-operation forms; credentials never leave the server."""

import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request

from flask import Blueprint, current_app, render_template, request

from .client import authorized_link, verify_link
from .common import NoRedirect, ProtocolError, require_csrf, require_user

bp = Blueprint("account_actions", __name__)


def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ProtocolError("invalid_path_parameter")
    return value


def number(name, minimum, maximum):
    try:
        value = float(request.form.get(name, ""))
    except ValueError:
        raise ProtocolError("invalid_coordinates") from None
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ProtocolError("invalid_coordinates")
    return value


def call_account(link, method, path, body=None):
    # Paths are supplied by this module, never by the browser.
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer " + link["access"],
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    try:
        response = urllib.request.build_opener(NoRedirect).open(
            urllib.request.Request(
                current_app.config["MUSECAT_ISSUER"] + "/developer/v1/account" + path,
                data=data,
                headers=headers,
                method=method,
            ),
            timeout=15,
        )
    except urllib.error.HTTPError as error:
        response = error
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ProtocolError("musecat_unavailable", 503) from None
    with response:
        raw = response.read(262145)
        if len(raw) > 262144:
            raise ProtocolError("musecat_response_too_large", 502)
        try:
            body = json.loads(raw) if raw else None
        except (ValueError, UnicodeError):
            body = {"error": "invalid_json_response"}
        return {"status": response.code, "body": body, "method": method, "path": path}


def render_actions(values, result=None, arcade=None, campaigns=None, reads=None):
    return render_template(
        "account-actions.html",
        title=None,
        issuer=current_app.config["MUSECAT_ISSUER"],
        values=values,
        result=result,
        arcade=arcade,
        campaigns=campaigns or [],
        reads=reads or [],
    )


@bp.get("/account-actions")
def index():
    require_user()
    # Page rendering does not call Musecat; every authenticated API read is a
    # deliberate CSRF-protected POST, like the existing profile example.
    values = {
        key: request.args.get(key, "")[:128]
        for key in ["arcade", "campaign", "game_id", "lat", "lon"]
    }
    return render_actions(values)


@bp.post("/account-actions")
def run():
    require_csrf()
    uid, link = authorized_link()
    values = request.form.to_dict()
    arcade_id = identifier(values.get("arcade", ""))
    action = values.get("action")
    result = None
    if action not in {"load", "basic", "fault", "visit", "campaign"}:
        raise ProtocolError("invalid_request")
    if action != "load" and values.get("confirm") != action:
        raise ProtocolError("explicit_mutation_confirmation_required")
    if action == "basic":
        body = {"arcade": arcade_id}
        for key, limit in [("name", 200), ("address", 1000), ("direction", 2000)]:
            value = values.get(key, "").strip()
            if len(value) > limit or (key == "name" and not value):
                raise ProtocolError("invalid_form_body")
            body[key] = value
        if values.get("base_basic_id"):
            body["base_basic_id"] = identifier(values["base_basic_id"])
        result = call_account(link, "PUT", "/arcade/basic", body)
    elif action == "fault":
        severity = values.get("disruption")
        message = values.get("message", "").strip()
        if (
            severity not in {"unplayable", "major", "bearable", "minor"}
            or not 1 <= len(message) <= 2000
        ):
            raise ProtocolError("invalid_form_body")
        result = call_account(
            link,
            "POST",
            "/arcade/flag",
            {
                "arcade": arcade_id,
                "game_id": identifier(values.get("game_id", "")),
                "disruption": severity,
                "message": message,
            },
        )
    elif action == "visit":
        result = call_account(
            link,
            "POST",
            "/arcade/visit",
            {
                "arcade": arcade_id,
                "lat": number("lat", -90, 90),
                "lon": number("lon", -180, 180),
                "accuracy": number("accuracy", 0, 150),
            },
        )
    elif action == "campaign":
        outcome = values.get("result")
        if outcome not in {"still_old", "updated"}:
            raise ProtocolError("invalid_form_body")
        result = call_account(
            link,
            "POST",
            "/campaign/check",
            {
                "arcade": arcade_id,
                "campaign": identifier(values.get("campaign", "")),
                "game_id": identifier(values.get("game_id", "")),
                "result": outcome,
                "bypass_location": False,
            },
        )
    query = urllib.parse.urlencode({"id": arcade_id, "expand": "basic,game"})
    detail = call_account(link, "GET", "/arcade?" + query)
    prompts = call_account(
        link, "GET", "/arcade/campaigns?" + urllib.parse.urlencode({"id": arcade_id})
    )
    verify_link(uid, link)
    return render_actions(
        values,
        result=result,
        arcade=detail["body"] if detail["status"] == 200 else None,
        campaigns=prompts["body"].get("items", [])
        if prompts["status"] == 200 and isinstance(prompts["body"], dict)
        else [],
        reads=[detail, prompts],
    )
