"""Small server-rendered catalog; protocol identifiers remain language-independent."""

from flask import g, request, session

LANGUAGES = {"en": "English", "ko": "한국어", "ja": "日本語"}
MESSAGES = {
    "title": {
        "en": "Partner integration example",
        "ko": "외부 서비스 연결 예제",
        "ja": "外部サービス連携サンプル",
    },
    "subtitle": {
        "en": "Local Docker Compose ↔ Musecat Preview · All game records are synthetic.",
        "ko": "로컬 Docker Compose ↔ Musecat Preview · 모든 게임 전적은 가상 데이터입니다.",
        "ja": "ローカル Docker Compose ↔ Musecat Preview · ゲーム記録はすべて架空のデータです。",
    },
    "language": {"en": "Language", "ko": "언어", "ja": "言語"},
    "apply": {"en": "Apply", "ko": "변경", "ja": "変更"},
    "demo_login": {
        "en": "Demo account sign-in",
        "ko": "데모 계정 로그인",
        "ja": "デモアカウントでログイン",
    },
    "login_hint": {
        "en": "Use alice or bob with DEMO_PASSWORD from the project's .env file.",
        "ko": "계정은 alice 또는 bob, 비밀번호는 프로젝트의 .env에 설정한 DEMO_PASSWORD입니다.",
        "ja": "alice または bob を選び、プロジェクトの .env に設定した DEMO_PASSWORD を入力してください。",
    },
    "account": {"en": "Account", "ko": "계정", "ja": "アカウント"},
    "password": {"en": "Password", "ko": "비밀번호", "ja": "パスワード"},
    "sign_in": {"en": "Sign in", "ko": "로그인", "ja": "ログイン"},
    "authorize_title": {
        "en": "Connect this demo account to Musecat?",
        "ko": "Musecat에 데모 계정을 연결할까요?",
        "ja": "このデモアカウントを Musecat に連携しますか？",
    },
    "authorize_profile": {
        "en": "Share this sample account's profile with Musecat.",
        "ko": "이 샘플 계정의 프로필을 Musecat에 제공합니다.",
        "ja": "このサンプルアカウントのプロフィールを Musecat に提供します。",
    },
    "authorize_records": {
        "en": "Share this sample account's profile and synthetic CHUNITHM records with Musecat.",
        "ko": "이 샘플 계정의 프로필과 가상 CHUNITHM 전적을 Musecat에 제공합니다.",
        "ja": "このサンプルアカウントのプロフィールと架空の CHUNITHM 記録を Musecat に提供します。",
    },
    "approve": {"en": "Agree and connect", "ko": "동의하고 연결", "ja": "同意して連携"},
    "cancel": {"en": "Cancel", "ko": "취소", "ja": "キャンセル"},
    "get_started": {"en": "Get started", "ko": "시작하기", "ja": "はじめに"},
    "get_started_hint": {
        "en": "Sign in to a demo account to test the integration.",
        "ko": "데모 계정으로 로그인해 연결을 테스트하세요.",
        "ja": "デモアカウントにログインして連携をテストできます。",
    },
    "open_login": {"en": "Demo sign-in", "ko": "데모 로그인", "ja": "デモログイン"},
    "demo_name": {"en": "Demo {name}", "ko": "데모 {name}", "ja": "デモ {name}"},
    "sign_out": {"en": "Sign out", "ko": "로그아웃", "ja": "ログアウト"},
    "partial": {
        "en": "Partially connected · not complete",
        "ko": "부분 연결 · 완료되지 않음",
        "ja": "一部のみ連携済み・未完了",
    },
    "connected": {"en": "Connected", "ko": "연결됨", "ja": "連携済み"},
    "profile": {
        "en": "Read Musecat profile",
        "ko": "뮤즈캣 프로필 조회",
        "ja": "Musecat プロフィールを取得",
    },
    "refresh_profile": {
        "en": "Refresh token and read profile",
        "ko": "토큰 갱신 후 조회",
        "ja": "トークンを更新して取得",
    },
    "disconnect_joint": {
        "en": "Disconnect both sides",
        "ko": "양쪽 연결 해제",
        "ja": "両側の連携を解除",
    },
    "disconnect": {"en": "Disconnect", "ko": "연결 해제", "ja": "連携を解除"},
    "not_connected": {
        "en": "Not connected.",
        "ko": "연결되지 않았습니다.",
        "ja": "連携されていません。",
    },
    "setup_hint": {
        "en": "First get your app approved in Musecat Developer Center, then set the Musecat-issued keys in .env.",
        "ko": "먼저 Musecat 개발자 센터에서 앱을 승인받고 .env의 Musecat 발급 키를 설정하세요.",
        "ja": "先に Musecat 開発者センターでアプリの承認を受け、発行されたキーを .env に設定してください。",
    },
    "connect_joint": {
        "en": "One-click bilateral connection",
        "ko": "원클릭 양방향 연결",
        "ja": "ワンクリック双方向連携",
    },
    "connect_oauth": {
        "en": "Ordinary OAuth only",
        "ko": "일반 OAuth 연결만",
        "ja": "通常の OAuth 連携のみ",
    },
    "pending": {
        "en": "{count} revocation notification(s) pending · local access is already blocked.",
        "ko": "해제 알림 {count}건 전송 대기 중 · 로컬 접근은 이미 차단됐습니다.",
        "ja": "解除通知 {count} 件を送信待ちです。ローカルのアクセスはすでに停止しています。",
    },
    "records": {
        "en": "Sample CHUNITHM records",
        "ko": "샘플 CHUNITHM 전적",
        "ja": "CHUNITHM サンプル記録",
    },
    "rating": {
        "en": "Synthetic rating",
        "ko": "가상 레이팅",
        "ja": "架空のレーティング",
    },
    "plays": {"en": "Synthetic plays", "ko": "가상 플레이", "ja": "架空のプレイ回数"},
    "visibility": {
        "en": "Partner visibility: {visibility}",
        "ko": "파트너 공개 상태: {visibility}",
        "ja": "パートナー側の公開設定: {visibility}",
    },
    "private": {"en": "Private", "ko": "비공개", "ja": "非公開"},
    "public": {"en": "Public", "ko": "공개", "ja": "公開"},
    "make_public": {"en": "Make public", "ko": "공개로 변경", "ja": "公開に変更"},
    "make_private": {"en": "Make private", "ko": "비공개로 변경", "ja": "非公開に変更"},
    "refresh_test": {
        "en": "Token refresh test",
        "ko": "토큰 갱신 테스트",
        "ja": "トークン更新テスト",
    },
    "refresh_hint": {
        "en": "Expire only the record API access tokens issued for this demo account. Refreshing records in Musecat should recover using the refresh token. Record refreshes are limited to once per minute.",
        "ko": "이 데모 계정에 발급한 전적 API access token만 만료시킵니다. 이후 Musecat에서 전적을 새로고침하면 refresh token으로 복구해야 합니다. 전적 새로고침은 분당 1회로 제한됩니다.",
        "ja": "このデモアカウントに発行した記録 API の access token だけを失効させます。Musecat で記録を再取得すると refresh token で復旧するはずです。再取得は1分に1回までです。",
    },
    "expire": {
        "en": "Expire demo access tokens",
        "ko": "데모 access token 만료",
        "ja": "デモ access token を失効",
    },
    "registration": {
        "en": "Registration and testing",
        "ko": "등록과 테스트",
        "ja": "登録とテスト",
    },
    "registration_hint": {
        "en": "Download an onboarding form populated with this server's URLs. Client secrets and server-to-server keys are not included.",
        "ko": "이 서버의 실제 URL을 채운 등록 양식을 제공합니다. Client Secret과 서버 간 키는 이 양식에 포함하지 않습니다.",
        "ja": "このサーバーの URL を入力済みの登録フォームを取得できます。Client Secret やサーバー間認証キーは含まれません。",
    },
    "onboarding": {
        "en": "App registration JSON",
        "ko": "앱 등록 JSON",
        "ja": "アプリ登録 JSON",
    },
    "developer_center": {
        "en": "Musecat Developer Center",
        "ko": "Musecat 개발자 센터",
        "ja": "Musecat 開発者センター",
    },
    "spec": {"en": "Integration specification", "ko": "연동 스펙", "ja": "連携仕様"},
    "start_musecat": {
        "en": "Start from Musecat",
        "ko": "Musecat에서 연결 시작",
        "ja": "Musecat から連携を開始",
    },
}


def init_i18n(app):
    @app.before_request
    def locale():
        saved = session.get("locale")
        g.locale = (
            saved
            if saved in LANGUAGES
            else request.accept_languages.best_match(list(LANGUAGES)) or "en"
        )

    app.context_processor(
        lambda: {
            "t": text,
            "locale": g.locale,
            "languages": LANGUAGES,
            "musecat_locale": "kr" if g.locale == "ko" else g.locale,
        }
    )


def text(key, **values):
    return MESSAGES[key][g.locale].format(**values)
