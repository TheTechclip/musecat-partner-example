import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, jsonify, request

from .common import ProtocolError, csrf
from .storage import Ledger


def create_app(overrides=None):
    app = Flask(__name__)
    names = [
        "PARTNER_ORIGIN",
        "PARTNER_ID",
        "PARTNER_OAUTH_CLIENT_ID",
        "PARTNER_OAUTH_CLIENT_SECRET",
        "MUSECAT_TO_PARTNER_KEY",
        "PARTNER_TO_MUSECAT_KEY",
        "MUSECAT_CLIENT_SECRET",
        "DEMO_PASSWORD",
        "SESSION_SECRET",
        "DATA_KEY",
    ]
    app.config.update({name: os.environ.get(name, "") for name in names})
    app.config.update(
        MUSECAT_ISSUER=os.environ.get(
            "MUSECAT_ISSUER", "https://db-dev.musecat.app"
        ).rstrip("/"),
        MUSECAT_WEB_ORIGIN=os.environ.get(
            "MUSECAT_WEB_ORIGIN", "https://preview.musecat.app"
        ).rstrip("/"),
        DATA_DIR=os.environ.get("DATA_DIR", "/data"),
        MAX_CONTENT_LENGTH=16384,
    )
    app.config.update(overrides or {})
    app.config.setdefault(
        "MUSECAT_TO_PARTNER_PREVIOUS_KEY",
        os.environ.get("MUSECAT_TO_PARTNER_PREVIOUS_KEY", ""),
    )
    app.config.setdefault(
        "PREVIOUS_KEY_EXPIRES_AT", int(os.environ.get("PREVIOUS_KEY_EXPIRES_AT", "0"))
    )
    for name in ["PARTNER_ORIGIN", "MUSECAT_ISSUER", "MUSECAT_WEB_ORIGIN"]:
        parsed = urlsplit(app.config[name])
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(name + " must be an HTTPS origin without a trailing slash")
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,127}", app.config["PARTNER_ID"]):
        raise ValueError("PARTNER_ID is required")
    for name in [
        "SESSION_SECRET",
        "DEMO_PASSWORD",
        "PARTNER_OAUTH_CLIENT_SECRET",
        "MUSECAT_TO_PARTNER_KEY",
    ]:
        if len(app.config[name]) < 32:
            raise ValueError(
                name
                + " must contain at least 32 random characters; run scripts/init-env.py"
            )
    app.config.update(
        SECRET_KEY=app.config["SESSION_SECRET"],
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        TRUSTED_HOSTS=[urlsplit(app.config["PARTNER_ORIGIN"]).hostname, "localhost"],
        SESSION_COOKIE_NAME="sample_session",
    )
    Path(app.config["DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    app.extensions["ledger"] = Ledger(
        str(Path(app.config["DATA_DIR"]) / "sample.db"), app.config["DATA_KEY"]
    )
    app.context_processor(
        lambda: {"csrf": csrf, "origin": app.config["PARTNER_ORIGIN"]}
    )

    @app.errorhandler(ProtocolError)
    def error(exc):
        return jsonify(error=exc.code), exc.status

    @app.after_request
    def headers(response):
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer"
                if request.path == "/oauth/musecat/callback"
                else "same-origin",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'self'; style-src 'self'; frame-ancestors 'none'; form-action 'self' "
                + app.config["MUSECAT_ISSUER"]
                + " "
                + app.config["MUSECAT_WEB_ORIGIN"],
            }
        )
        return response

    from . import oauth, joint, web, client

    app.register_blueprint(oauth.bp)
    app.register_blueprint(joint.bp)
    app.register_blueprint(web.bp)
    app.register_blueprint(client.bp)
    return app
