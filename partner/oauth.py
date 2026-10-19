"""Direction B: a tiny partner OAuth server and synthetic CHUNITHM records."""

import hmac
import re
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
    SCOPES,
    ProtocolError,
    basic_auth,
    challenge,
    ledger,
    musecat_callback,
    now,
    opaque,
    reject_duplicates,
    require_csrf,
    require_user,
    stamp,
    token_grant,
    user,
    valid_challenge,
)
from .storage import digest

bp = Blueprint("oauth", __name__)


def create_grant(tx, uid, scopes, pair_id=None, generation=None):
    gid = str(uuid.uuid4())
    grant = {
        "id": gid,
        "user": uid,
        "scopes": scopes,
        "expires": now() + FAMILY,
        "pair_id": pair_id,
        "generation": generation,
        "revoked": False,
        "exchanged": False,
    }
    ledger().put(tx, "grant", gid, grant, grant["expires"])
    return grant


def issue_code(tx, grant, pkce):
    code = opaque()
    ledger().put(
        tx,
        "code",
        digest(code),
        {"grant": grant["id"], "challenge": pkce, "used": False},
        now() + 90,
    )
    return code


def issue_tokens(tx, grant):
    access, refresh = opaque(), opaque()
    ledger().put(tx, "access", digest(access), {"grant": grant["id"]}, now() + 600)
    ledger().put(
        tx,
        "refresh",
        digest(refresh),
        {"grant": grant["id"], "used": False},
        grant["expires"],
    )
    grant["exchanged"] = True
    ledger().put(tx, "grant", grant["id"], grant, grant["expires"])
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": 600,
        "scope": " ".join(grant["scopes"]),
    }


@bp.get("/.well-known/oauth-authorization-server")
def metadata():
    origin = current_app.config["PARTNER_ORIGIN"]
    return jsonify(
        issuer=origin,
        authorization_endpoint=origin + "/oauth/authorize",
        token_endpoint=origin + "/oauth/token",
        userinfo_endpoint=origin + "/oauth/userinfo",
        revocation_endpoint=origin + "/oauth/revoke",
        response_types_supported=["code"],
        grant_types_supported=["authorization_code", "refresh_token"],
        token_endpoint_auth_methods_supported=["client_secret_basic"],
        code_challenge_methods_supported=["S256"],
        scopes_supported=SCOPES,
    )


@bp.route("/oauth/authorize", methods=["GET", "POST"])
def authorize():
    values = request.form if request.method == "POST" else request.args
    reject_duplicates(values)
    if (
        values.get("client_id") != current_app.config["PARTNER_OAUTH_CLIENT_ID"]
        or values.get("redirect_uri") != musecat_callback()
    ):
        raise ProtocolError("invalid_request")
    scopes = values.get("scope", "").split()
    if (
        values.get("response_type") != "code"
        or values.get("code_challenge_method") != "S256"
        or not valid_challenge(values.get("code_challenge"))
    ):
        raise ProtocolError("invalid_request")
    if (
        "profile" not in scopes
        or not set(scopes).issubset(SCOPES)
        or len(scopes) != len(set(scopes))
    ):
        raise ProtocolError("invalid_scope")
    if not 1 <= len(values.get("state", "")) <= 512:
        raise ProtocolError("invalid_request")
    if not user():
        session["next"] = "/oauth/authorize?" + urlencode(dict(request.args))
        return redirect("/login")
    if request.method == "GET":
        return render_template(
            "index.html", mode="authorize", fields=dict(values), scopes=scopes
        )
    require_csrf()
    params = {"state": values["state"], "iss": current_app.config["PARTNER_ORIGIN"]}
    if values.get("decision") != "approve":
        params["error"] = "access_denied"
    else:
        with ledger().transaction() as tx:
            grant = create_grant(tx, require_user(), scopes)
            params["code"] = issue_code(tx, grant, values["code_challenge"])
    return redirect(musecat_callback() + "?" + urlencode(params))


@bp.post("/oauth/token")
def token():
    basic_auth()
    reject_duplicates(request.form)
    kind = request.form.get("grant_type")
    failure = None
    with ledger().transaction() as tx:
        if kind == "authorization_code":
            entry = ledger().get(tx, "code", digest(request.form.get("code", "")))
            verifier = request.form.get("code_verifier", "")
            if (
                not entry
                or request.form.get("redirect_uri") != musecat_callback()
                or not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", verifier)
                or not hmac.compare_digest(challenge(verifier), entry["challenge"])
            ):
                raise ProtocolError("invalid_grant")
            key, namespace = digest(request.form["code"]), "code"
        elif kind == "refresh_token":
            key, namespace = digest(request.form.get("refresh_token", "")), "refresh"
            entry = ledger().get(tx, namespace, key)
            if not entry:
                raise ProtocolError("invalid_grant")
        else:
            raise ProtocolError("unsupported_grant_type")
        grant = ledger().get(tx, "grant", entry["grant"])
        if not grant or grant["revoked"]:
            raise ProtocolError("invalid_grant")
        if entry["used"]:
            # Commit revocation before returning the replay error.
            grant["revoked"] = True
            ledger().put(tx, "grant", grant["id"], grant, grant["expires"])
            failure = ProtocolError("invalid_grant")
        else:
            entry["used"] = True
            ledger().put(
                tx,
                namespace,
                key,
                entry,
                grant["expires"] if namespace == "refresh" else now() + 90,
            )
            result = issue_tokens(tx, grant)
    if failure:
        raise failure
    return jsonify(result)


@bp.post("/oauth/revoke")
def revoke():
    basic_auth()
    reject_duplicates(request.form)
    hashed = digest(request.form.get("token", ""))
    with ledger().transaction() as tx:
        entry = ledger().get(tx, "access", hashed) or ledger().get(
            tx, "refresh", hashed
        )
        grant = ledger().get(tx, "grant", entry["grant"]) if entry else None
        if grant:
            grant["revoked"] = True
            ledger().put(tx, "grant", grant["id"], grant, grant["expires"])
    return "", 200


@bp.get("/oauth/userinfo")
def userinfo():
    with ledger().transaction() as tx:
        grant = token_grant(tx)
    if "profile" not in grant["scopes"]:
        raise ProtocolError("insufficient_scope", 403)
    return jsonify(
        sub="sample:" + grant["user"],
        iss=current_app.config["PARTNER_ORIGIN"],
        name="Demo " + grant["user"].title(),
        services=["chunithm"],
    )


@bp.get("/api/records/<service>")
def records(service):
    with ledger().transaction() as tx:
        grant = token_grant(tx)
        if service != "chunithm":
            raise ProtocolError("unsupported_service", 404)
        if "chunithm:read" not in grant["scopes"]:
            raise ProtocolError("insufficient_scope", 403)
        if ledger().get(tx, "private", grant["user"]):
            raise ProtocolError("records_private", 403)
    return jsonify(
        spec="musecat-records/v1",
        service=service,
        sub="sample:" + grant["user"],
        visibility="public",
        updated_at=stamp(),
        source={
            "name": "Musecat Partner Example · synthetic data",
            "url": current_app.config["PARTNER_ORIGIN"],
        },
        fields=[
            {
                "key": "rating",
                "label": {
                    "ko": "데모 레이팅",
                    "en": "Demo rating",
                    "ja": "デモレーティング",
                },
                "type": "decimal",
                "value": 16.42,
                "precision": 2,
            },
            {
                "key": "plays",
                "label": {
                    "ko": "데모 플레이 수",
                    "en": "Demo plays",
                    "ja": "デモプレイ回数",
                },
                "type": "integer",
                "value": 123,
            },
        ],
        sections=[],
    )
