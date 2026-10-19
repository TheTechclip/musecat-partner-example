import hmac
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    g,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
)

from .common import (
    FAMILY,
    MANIFEST,
    ProtocolError,
    callback,
    ledger,
    now,
    require_csrf,
    require_user,
    user,
    queue_record_invalidation,
)

from .i18n import LANGUAGES
from .record_examples import SERVICES, envelope

bp = Blueprint("web", __name__)


@bp.get("/health")
def health():
    return jsonify(status="ok")


@bp.get("/")
def home():
    with ledger().transaction() as tx:
        link = ledger().get(tx, "link", user()) if user() else None
        private = bool(ledger().get(tx, "private", user())) if user() else False
        pending = len(ledger().items(tx, "outbox"))
        selections = (
            {
                game: (ledger().get(tx, "record_selection", user() + ":" + game) or [])
                for game in SERVICES
            }
            if user()
            else {}
        )
        record_grants = sum(
            1
            for _, grant in ledger().items(tx, "grant")
            if grant["user"] == user() and not grant["revoked"] and grant["exchanged"]
        )
    return render_template(
        "index.html",
        mode="home",
        user=user(),
        link=link,
        private=private,
        pending=pending,
        record_grants=record_grants,
        services=SERVICES,
        selections=selections,
        partner_id=current_app.config["PARTNER_ID"],
        a_ready=bool(current_app.config["MUSECAT_CLIENT_SECRET"]),
        oidc_ready=bool(
            current_app.config.get("MUSECAT_LOGIN_CLIENT_ID")
            and current_app.config.get("MUSECAT_LOGIN_CLIENT_SECRET")
        ),
        oidc_login=getattr(g, "oidc_login", None),
        joint_ready=bool(
            current_app.config["MUSECAT_CLIENT_SECRET"]
            and current_app.config["PARTNER_TO_MUSECAT_KEY"]
        ),
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        require_csrf()
        uid = request.form.get("username", "")
        if uid not in ["alice", "bob"] or not hmac.compare_digest(
            request.form.get("password", ""), current_app.config["DEMO_PASSWORD"]
        ):
            raise ProtocolError("invalid_credentials", 401)
        target = session.get("next", "/")
        from .oidc import end_session

        end_session()
        session.clear()
        from .common import opaque

        session.update(user=uid, sid=opaque(), locale=g.locale)
        return redirect(target)
    return render_template("index.html", mode="login")


@bp.post("/logout")
def logout():
    require_csrf()
    from .oidc import end_session

    end_session()
    session.clear()
    session["locale"] = g.locale
    return redirect("/")


@bp.post("/records/privacy")
def privacy():
    require_csrf()
    uid = require_user()
    with ledger().transaction() as tx:
        queue_record_invalidation(tx, uid, SERVICES)
        if request.form.get("private") == "yes":
            ledger().put(tx, "private", uid, True, now() + FAMILY)
        else:
            ledger().delete(tx, "private", uid)
    return redirect("/")


@bp.get("/onboarding.json")
def onboarding():
    origin = current_app.config["PARTNER_ORIGIN"]
    flow = request.args.get("flow", "joint")
    if flow not in {"a", "b", "joint", "login"}:
        raise ProtocolError("invalid_onboarding_flow")
    form = dict(
        spec="musecat-partner-onboarding/v1",
        partner_id=current_app.config["PARTNER_ID"],
        display_name={
            "ko": "뮤즈캣 연동 예제",
            "en": "Musecat Partner Example",
            "ja": "Musecat 連携サンプル",
        },
        description={
            "ko": "테스트 전적으로 양방향 연결을 검증하는 공개 샘플",
            "en": "Public sample with synthetic records for integration testing",
            "ja": "テスト記録で双方向連携を検証する公開サンプル",
        },
        contact_email="developer@example.com",
        website=origin,
        direction_a={"redirect_uris": [callback()]},
        direction_b={
            "issuer": origin,
            "authorization_url": origin + "/oauth/authorize",
            "token_url": origin + "/oauth/token",
            "userinfo_url": origin + "/oauth/userinfo",
            "revocation_url": origin + "/oauth/revoke",
            "records_url": origin + "/api/records",
            "client_auth_method": "client_secret_basic",
            "identity_scope": "profile",
            "services": [
                {"id": game, "scope": game + ":read"}
                for game in (SERVICES if flow == "b" else ("chunithm",))
            ],
        },
        joint={
            "enabled": True,
            "manifests": [MANIFEST],
            "joint_url": origin + "/api/joint",
            "connect_start_url": origin + "/connect/musecat/start",
            "key_rotation_window_hours": 24,
        },
    )
    if flow != "joint":
        form.pop("joint")
    if flow in {"a", "login"}:
        form.pop("direction_b")
    if flow == "b":
        form.pop("direction_a")
    if flow == "login":
        form["partner_id"] = (
            current_app.config.get("MUSECAT_LOGIN_CLIENT_ID")
            or current_app.config["PARTNER_ID"][:122] + "_login"
        )
        form["direction_a"] = {
            "redirect_uris": [origin + "/oidc/callback"],
            "login_enabled": True,
        }
        form["display_name"] = {
            "en": "Musecat Login Example",
            "ko": "뮤즈캣 로그인 예제",
            "ja": "Musecat ログインサンプル",
        }
    return jsonify(form)


@bp.post("/testing/expire-access")
def expire_access():
    """Demo-only control: provoke Musecat's 401 -> refresh -> retry path."""
    require_csrf()
    uid = require_user()
    with ledger().transaction() as tx:
        for key, token in ledger().items(tx, "access"):
            grant = ledger().get(tx, "grant", token["grant"])
            if grant and grant["user"] == uid:
                ledger().delete(tx, "access", key)
    return redirect("/")


@bp.post("/language")
def language():
    require_csrf()
    selected = request.form.get("locale")
    target = request.form.get("next", "/")
    parsed = urlsplit(target)
    if (
        selected not in LANGUAGES
        or parsed.scheme
        or parsed.netloc
        or parsed.fragment
        or parsed.path not in ("/", "/login", "/oauth/authorize", "/api-examples")
    ):
        raise ProtocolError("invalid_request")
    session["locale"] = selected
    return redirect(target)


@bp.get("/record-examples/<service>")
def record_example(service):
    if service not in SERVICES:
        raise ProtocolError("unsupported_service", 404)
    return jsonify(envelope(service, "synthetic"))


@bp.post("/records/selection")
def record_selection():
    require_csrf()
    uid = require_user()
    service = request.form.get("service", "")
    if service not in SERVICES:
        raise ProtocolError("unsupported_service", 404)
    excluded = request.form.getlist("excluded")
    if len(set(excluded)) != len(excluded) or not set(excluded).issubset(
        {"player", "fields", "sections", "recent_plays"}
    ):
        raise ProtocolError("invalid_request")
    with ledger().transaction() as tx:
        queue_record_invalidation(tx, uid, [service])
        ledger().put(
            tx, "record_selection", uid + ":" + service, excluded, now() + FAMILY
        )
    return redirect("/")
