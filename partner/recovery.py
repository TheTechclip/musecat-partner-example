"""Safe, localized recovery advice; upstream descriptions are never displayed."""

import json

from flask import g, jsonify, make_response, render_template, request

from .common import ProtocolError

# OAuth error codes are bounded here rather than copying untrusted upstream text.
UPSTREAM_CODES = {
    "invalid_request": 400,
    "invalid_client": 401,
    "invalid_grant": 400,
    "invalid_scope": 400,
    "unsupported_grant_type": 400,
    "unauthorized_client": 403,
    "access_denied": 403,
    "consent_denied": 403,
    "invalid_token": 401,
    "insufficient_scope": 403,
    "invalid_origin": 403,
    "redirect_uri_mismatch": 400,
    "callback_mismatch": 400,
    "records_private": 403,
    "intent_expired": 410,
    "intent_consumed": 409,
    "invalid_intent": 409,
    "invalid_receipt": 400,
    "connection_required": 409,
    "connection_changed": 409,
}


def upstream_error(response):
    """Read a small error envelope, preserving only recognized codes and delays."""
    if response.code == 429:
        delay = response.headers.get("Retry-After", "")
        delay = (
            int(delay)
            if delay.isascii() and delay.isdigit() and len(delay) <= 4
            else None
        )
        return ProtocolError(
            "rate_limited", 429, retry_after=delay if delay and delay <= 3600 else None
        )
    if response.code >= 500:
        return ProtocolError("musecat_unavailable", 503)
    try:
        raw = response.read(8193)
        data = json.loads(raw) if len(raw) <= 8192 else None
        code = data.get("error") if isinstance(data, dict) else None
        if isinstance(code, str) and code in UPSTREAM_CODES:
            return ProtocolError(code, UPSTREAM_CODES[code])
    except (ValueError, UnicodeError, OSError):
        pass
    return ProtocolError("musecat_request_failed", 502)


# Each entry supplies a cause and a deliberate next step. Never replay a callback
# or retry a code exchange automatically: authorization codes are single-use.
ADVICE = {
    "origin": {
        "en": (
            "The browser origin does not match this sample's configured HTTPS address.",
            "Open the sample at PARTNER_ORIGIN and sign in again. After changing a tunnel URL, update the server configuration and registered URLs, then restart the sample.",
        ),
        "ko": (
            "브라우저 주소가 예제에 설정한 HTTPS 주소와 일치하지 않습니다.",
            "PARTNER_ORIGIN 주소에서 다시 로그인하세요. 터널 주소가 바뀌었다면 서버 설정과 등록 주소를 함께 수정한 뒤 예제를 재시작하세요.",
        ),
        "ja": (
            "ブラウザーの接続元が設定された HTTPS アドレスと一致しません。",
            "PARTNER_ORIGIN のアドレスでログインし直してください。トンネル URL を変更した場合はサーバー設定と登録 URL を更新し、サンプルを再起動してください。",
        ),
    },
    "client": {
        "en": (
            "The app credentials or server registration are missing, invalid, or not approved.",
            "Check this flow's client ID, secret, approval and allowed scopes in the developer center. Store secrets only on the server; restart the connection after correcting the configuration.",
        ),
        "ko": (
            "앱 인증 정보나 서버 등록이 누락되었거나 유효하지 않거나 승인되지 않았습니다.",
            "개발자 센터에서 이 흐름의 Client ID·시크릿·승인·허용 범위를 확인하세요. 시크릿은 서버에만 보관하고 설정을 수정한 뒤 연결을 새로 시작하세요.",
        ),
        "ja": (
            "アプリの認証情報や登録が不足しているか、無効または未承認です。",
            "開発者センターでこのフローの Client ID・シークレット・承認・許可スコープを確認してください。シークレットはサーバーだけに保存し、修正後に連携を最初から開始してください。",
        ),
    },
    "callback": {
        "en": (
            "The callback address does not match the registered redirect URI.",
            "Compare the full HTTPS callback URL, including its path, with the developer center registration. Correct the configuration and start a new login; do not reopen an old callback.",
        ),
        "ko": (
            "콜백 주소가 등록한 리다이렉트 URI와 일치하지 않습니다.",
            "경로까지 포함한 전체 HTTPS 콜백 주소를 개발자 센터 등록과 비교하세요. 설정을 수정한 뒤 로그인을 새로 시작하고 이전 콜백 주소를 다시 열지 마세요.",
        ),
        "ja": (
            "コールバックが登録済みのリダイレクト URI と一致しません。",
            "パスを含む HTTPS コールバック URL 全体を開発者センターの登録と照合してください。設定修正後に新しいログインを開始し、古いコールバックは開き直さないでください。",
        ),
    },
    "verification": {
        "en": (
            "The login response could not be verified, so no new login was accepted.",
            "Return home and start a fresh login in the same browser. Keep cookies enabled and use the configured HTTPS address. If it repeats, check issuer, callback, server time and signing-key configuration.",
        ),
        "ko": (
            "로그인 응답 검증에 실패하여 새 로그인을 허용하지 않았습니다.",
            "홈으로 돌아가 같은 브라우저에서 로그인을 새로 시작하세요. 쿠키를 허용하고 설정한 HTTPS 주소를 사용하세요. 반복되면 발급자·콜백·서버 시각·서명 키 설정을 확인하세요.",
        ),
        "ja": (
            "ログイン応答を検証できなかったため、新しいログインを受け付けませんでした。",
            "ホームに戻り、同じブラウザーでログインを最初から開始してください。Cookie を有効にし、設定済み HTTPS アドレスを使用してください。繰り返す場合は発行者・コールバック・サーバー時刻・署名鍵設定を確認してください。",
        ),
    },
    "expired": {
        "en": (
            "The authorization code or connection intent expired, was already used, or is no longer valid.",
            "Return home and start the intended connection again. Do not refresh the callback page or reuse its URL. If an existing connection blocks a different mode, disconnect it explicitly first.",
        ),
        "ko": (
            "인증 코드나 연결 요청이 만료되었거나 이미 사용되었거나 유효하지 않습니다.",
            "홈으로 돌아가 원하는 연결을 새로 시작하세요. 콜백 페이지를 새로고침하거나 주소를 재사용하지 마세요. 기존 연결이 다른 모드를 막으면 먼저 직접 연결을 해제하세요.",
        ),
        "ja": (
            "認証コードや連携リクエストが期限切れ、使用済み、または無効です。",
            "ホームに戻り、希望する連携を新しく開始してください。コールバックの再読み込みや URL の再利用は避けてください。既存の連携が別モードを妨げる場合は先に明示的に解除してください。",
        ),
    },
    "denied": {
        "en": (
            "Consent was declined. The requested connection was not completed.",
            "You can leave it disconnected. To connect later, return home and start again, then review the requested permissions before consenting.",
        ),
        "ko": (
            "동의가 거부되어 요청한 연결을 완료하지 않았습니다.",
            "연결하지 않은 채로 두어도 됩니다. 나중에 연결하려면 홈에서 다시 시작한 뒤 요청 권한을 확인하고 동의하세요.",
        ),
        "ja": (
            "同意が拒否されたため、要求された連携は完了していません。",
            "未接続のままでも構いません。後で連携する場合はホームから再開し、要求される権限を確認して同意してください。",
        ),
    },
    "private": {
        "en": (
            "These records are private. A connection does not override visibility settings.",
            "Keep the records private, or deliberately change their visibility in the service's settings and request them again. Profile sharing in Musecat may also require its own public switch.",
        ),
        "ko": (
            "이 전적은 비공개입니다. 연결이 공개 범위 설정을 우회하지는 않습니다.",
            "비공개를 유지하거나 해당 서비스 설정에서 직접 공개 범위를 바꾼 뒤 다시 조회하세요. 뮤즈캣 프로필에 표시하려면 별도의 프로필 공개 설정도 필요할 수 있습니다.",
        ),
        "ja": (
            "この記録は非公開です。連携しても公開範囲の設定は優先されます。",
            "非公開を維持するか、サービスの設定で明示的に公開範囲を変更してから再取得してください。Musecat のプロフィール表示には別途公開設定が必要な場合があります。",
        ),
    },
    "rate": {
        "en": (
            "Too many requests were sent. No automatic retry was performed.",
            "Wait for the indicated delay, or at least one minute if none is given, then retry the action once. If this happened during login or code exchange, start a new login rather than replaying the callback.",
        ),
        "ko": (
            "요청 횟수 제한에 도달했습니다. 자동으로 재시도하지 않았습니다.",
            "표시된 시간만큼, 안내가 없다면 최소 1분 기다린 뒤 한 번 다시 시도하세요. 로그인이나 코드 교환 중 발생했다면 콜백을 재사용하지 말고 로그인을 새로 시작하세요.",
        ),
        "ja": (
            "リクエスト回数の上限に達しました。自動再試行は行っていません。",
            "表示された時間、表示がなければ少なくとも 1 分待ってから一度だけ再試行してください。ログインやコード交換中の場合はコールバックを再利用せず、新しいログインを開始してください。",
        ),
    },
    "reconnect": {
        "en": (
            "The saved connection is missing, changed, revoked, or could not refresh its token.",
            "Return home and check the connection status. If a stale connection remains, disconnect it deliberately, then reconnect and consent again. Do not repeatedly force token refreshes.",
        ),
        "ko": (
            "저장된 연결이 없거나 변경·해제되었거나 토큰 갱신에 실패했습니다.",
            "홈에서 연결 상태를 확인하세요. 이전 연결이 남아 있다면 직접 해제한 뒤 다시 연결하고 동의하세요. 토큰 갱신을 반복해서 강제하지 마세요.",
        ),
        "ja": (
            "保存された連携が存在しない、変更・解除された、またはトークンを更新できませんでした。",
            "ホームで連携状態を確認してください。古い連携が残っている場合は明示的に解除して再連携・再同意してください。トークン更新を繰り返し強制しないでください。",
        ),
    },
    "unavailable": {
        "en": (
            "Musecat could not be reached or returned an invalid response.",
            "Check service availability and the configured issuer. Retry ordinary reads later. If login was interrupted, start a new login after the service recovers; do not replay a code exchange.",
        ),
        "ko": (
            "뮤즈캣에 접속할 수 없거나 유효하지 않은 응답을 받았습니다.",
            "서비스 상태와 발급자 주소 설정을 확인하세요. 일반 조회는 나중에 다시 시도하세요. 로그인이 중단되었다면 복구 후 새로 시작하고 코드 교환을 재사용하지 마세요.",
        ),
        "ja": (
            "Musecat に接続できないか、無効な応答を受信しました。",
            "サービスの稼働状況と発行者アドレス設定を確認してください。通常の参照は後で再試行してください。ログインが中断された場合は復旧後に新しく開始し、コード交換を再実行しないでください。",
        ),
    },
    "login": {
        "en": (
            "A valid local demo session is required.",
            "Return home, open the demo login page, and use the demo credentials configured on this server. Never enter your Musecat password into this example.",
        ),
        "ko": (
            "유효한 로컬 데모 로그인이 필요합니다.",
            "홈에서 데모 로그인 페이지를 열고 이 서버에 설정한 데모 인증 정보를 사용하세요. 이 예제에 뮤즈캣 비밀번호를 입력하지 마세요.",
        ),
        "ja": (
            "有効なローカルデモセッションが必要です。",
            "ホームからデモログインを開き、このサーバーに設定されたデモ認証情報を使用してください。このサンプルに Musecat のパスワードを入力しないでください。",
        ),
    },
    "generic": {
        "en": (
            "The request could not be completed.",
            "Return home and check the selected flow, required parameters and app configuration. Start a fresh flow rather than reusing a callback. If it persists, consult the example documentation using the error code below.",
        ),
        "ko": (
            "요청을 완료하지 못했습니다.",
            "홈에서 선택한 흐름·필수 입력·앱 설정을 확인하세요. 콜백을 재사용하지 말고 흐름을 새로 시작하세요. 반복되면 아래 오류 코드로 예제 문서를 확인하세요.",
        ),
        "ja": (
            "リクエストを完了できませんでした。",
            "ホームで選択したフロー・必須項目・アプリ設定を確認してください。コールバックを再利用せず、新しいフローを開始してください。続く場合は下のエラーコードでサンプルのドキュメントを確認してください。",
        ),
    },
}

GROUPS = {
    "origin": {"invalid_origin"},
    "client": {
        "invalid_client",
        "unauthorized_client",
        "invalid_scope",
        "insufficient_scope",
        "musecat_configuration_required",
        "oidc_configuration_required",
    },
    "callback": {"redirect_uri_mismatch", "callback_mismatch", "invalid_redirect_uri"},
    "verification": {
        "invalid_state",
        "invalid_nonce",
        "invalid_id_token",
        "invalid_jwt",
        "invalid_csrf",
        "invalid_musecat_identity",
        "invalid_musecat_token",
        "invalid_musecat_metadata",
        "invalid_oidc_metadata",
        "invalid_oidc_response",
    },
    "expired": {
        "invalid_grant",
        "intent_expired",
        "intent_consumed",
        "invalid_intent",
        "invalid_receipt",
    },
    "denied": {"access_denied", "consent_denied"},
    "private": {"records_private"},
    "rate": {"rate_limited", "too_many_requests"},
    "reconnect": {
        "invalid_token",
        "connection_required",
        "connection_changed",
        "refresh_failed_reconnect",
        "refresh_in_progress_or_failed_reconnect",
        "disconnect_before_reconnecting",
        "musecat_identity_already_connected",
    },
    "unavailable": {
        "musecat_unavailable",
        "musecat_request_failed",
        "invalid_musecat_response",
        "musecat_response_too_large",
    },
    "login": {"login_required", "invalid_credentials"},
}

LABELS = {
    "en": (
        "Action needed",
        "Cause",
        "Next step",
        "Return home",
        "Error code",
        "Retry after (seconds)",
    ),
    "ko": (
        "확인이 필요합니다",
        "원인",
        "다음 단계",
        "홈으로 돌아가기",
        "오류 코드",
        "재시도 대기 시간 (초)",
    ),
    "ja": (
        "確認が必要です",
        "原因",
        "次の手順",
        "ホームに戻る",
        "エラーコード",
        "再試行までの待機時間（秒）",
    ),
}


def error_response(exc):
    # Protocol endpoints stay machine-readable even when an incorrect client
    # sends Accept: text/html. HTML is opt-in for interactive browser routes.
    protocol = request.path.startswith(("/api/", "/.well-known/")) or request.path in {
        "/oauth/token",
        "/oauth/revoke",
        "/oauth/userinfo",
        "/onboarding.json",
        "/health",
    }
    wants_html = (
        not protocol
        and request.args.get("format") != "json"
        and request.accept_mimetypes["text/html"]
        > request.accept_mimetypes["application/json"]
    )
    if wants_html:
        locale = getattr(g, "locale", "en")
        group = next(
            (key for key, codes in GROUPS.items() if exc.code in codes), "generic"
        )
        response = make_response(
            render_template(
                "error.html",
                title=LABELS[locale][0],
                labels=LABELS[locale],
                advice=ADVICE[group][locale],
                error_code=exc.code,
                retry_after=exc.retry_after,
            ),
            exc.status,
        )
    else:
        response = make_response(jsonify(error=exc.code), exc.status)
    if exc.retry_after:
        response.headers["Retry-After"] = str(exc.retry_after)
    response.vary.add("Accept")
    response.vary.add("Accept-Language")
    return response
