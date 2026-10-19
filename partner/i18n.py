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
        "en": "Musecat API access is not connected.",
        "ko": "뮤즈캣 API 접근이 연결되지 않았습니다.",
        "ja": "Musecat API アクセスは未連携です。",
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

MESSAGES.update(
    {
        "api_console": {
            "en": "Developer API examples",
            "ko": "개발자 API 예제",
            "ja": "開発者 API サンプル",
        },
        "api_intro": {
            "en": "Every operation in the bundled official OpenAPI is "
            "listed. Tokens stay on this server.",
            "ko": "공식 OpenAPI의 모든 작업을 제공합니다. 토큰은 서버에만 보관합니다.",
            "ja": "同梱の公式 OpenAPI の全操作を掲載しています。トークンはサーバーに保管します。",
        },
        "operation": {"en": "Operation", "ko": "API 작업", "ja": "API 操作"},
        "open": {"en": "Open example", "ko": "예제 열기", "ja": "サンプルを開く"},
        "parameters": {"en": "Parameters", "ko": "파라미터", "ja": "パラメーター"},
        "request_body": {
            "en": "Request body (JSON fields for forms)",
            "ko": "요청 본문 (폼도 JSON 필드로 입력)",
            "ja": "リクエスト本文（フォームも JSON フィールドで入力）",
        },
        "run": {"en": "Execute request", "ko": "요청 실행", "ja": "リクエストを実行"},
        "mutation_notice": {
            "en": "This request changes data. Enter the HTTP method "
            "below to explicitly confirm this one request.",
            "ko": "데이터를 변경하는 요청입니다. 아래에 HTTP 메서드를 입력해야 이번 요청을 실행합니다.",
            "ja": "データを変更する要求です。HTTP メソッドを下に入力して、この1回の実行を確認してください。",
        },
        "reference_only": {
            "en": "Reference example: use the matching OAuth flow or a "
            "first-party Musecat session. This playground does "
            "not substitute credentials.",
            "ko": "참고용 예제: 해당 OAuth 흐름 또는 뮤즈캣 로그인 세션을 사용해야 합니다. 콘솔에서 "
            "다른 인증수단을 대신 사용하지 않습니다.",
            "ja": "参照用サンプルです。対応する OAuth フローまたは Musecat "
            "ログインセッションが必要です。この画面で別の認証に置き換えることはありません。",
        },
        "scopes": {"en": "Required scopes", "ko": "필요 권한", "ja": "必要なスコープ"},
        "responses": {
            "en": "Response contracts",
            "ko": "응답 규격",
            "ja": "レスポンス仕様",
        },
        "api_result": {
            "en": "Actual API response",
            "ko": "실제 API 응답",
            "ja": "実際の API レスポンス",
        },
        "schema": {
            "en": "Official OpenAPI snapshot",
            "ko": "공식 OpenAPI 스냅샷",
            "ja": "公式 OpenAPI スナップショット",
        },
        "back": {"en": "Back to demo", "ko": "데모로 돌아가기", "ja": "デモに戻る"},
        "profile_details": {
            "en": "Connected Musecat profile",
            "ko": "연결한 뮤즈캣 프로필",
            "ja": "連携した Musecat プロフィール",
        },
        "profile_notice": {
            "en": "Read using your existing account:access consent and "
            "Musecat domain permissions. Data is displayed only "
            "in this demo session.",
            "ko": "기존 account:access 동의와 뮤즈캣 도메인 권한으로 조회합니다. 이 데모 "
            "세션에서만 표시합니다.",
            "ja": "既存の account:access 同意と Musecat "
            "の権限で取得します。このデモセッションだけに表示します。",
        },
        "games": {
            "en": "Played games",
            "ko": "플레이하는 게임",
            "ja": "プレイするゲーム",
        },
        "favorites": {
            "en": "Favorite arcades",
            "ko": "즐겨찾는 오락실",
            "ja": "お気に入りのゲームセンター",
        },
        "countries": {"en": "Countries", "ko": "국가", "ja": "国"},
        "passport": {"en": "Passport", "ko": "패스포트", "ja": "パスポート"},
        "stamps": {
            "en": "Passport stamps (first page)",
            "ko": "패스포트 스탬프 (첫 페이지)",
            "ja": "パスポートのスタンプ（最初のページ）",
        },
        "activity": {"en": "Activity", "ko": "활동", "ja": "アクティビティ"},
        "contributions": {
            "en": "Contributions (first page)",
            "ko": "기여 기록 (첫 페이지)",
            "ja": "貢献履歴（最初のページ）",
        },
        "raw_data": {
            "en": "Complete response JSON",
            "ko": "전체 응답 JSON",
            "ja": "完全なレスポンス JSON",
        },
        "no_items": {
            "en": "No items returned",
            "ko": "반환된 항목이 없습니다",
            "ja": "返された項目はありません",
        },
        "profile_account": {
            "en": "Profile and account details",
            "ko": "프로필 및 계정 정보",
            "ja": "プロフィールとアカウント情報",
        },
    }
)

MESSAGES.update(
    {
        "distinct_arcades": {
            "en": "Distinct arcades",
            "ja": "訪問したゲームセンター",
            "ko": "방문한 오락실",
        },
        "distinct_cities": {
            "en": "Visited cities",
            "ja": "訪問した都市",
            "ko": "방문한 도시",
        },
        "distinct_countries": {
            "en": "Visited countries",
            "ja": "訪問した国",
            "ko": "방문한 국가",
        },
        "pagination": {
            "en": "Page {page}/{last} · {total} items. Use API examples "
            "for further pages.",
            "ja": "{page}/{last} ページ・全 {total} 件。続きは API サンプルで取得できます。",
            "ko": "{page}/{last} 페이지 · 총 {total}개. 다음 페이지는 API 예제에서 조회할 수 "
            "있습니다.",
        },
        "total_visits": {
            "en": "Total arcade visits",
            "ja": "総訪問回数",
            "ko": "총 오락실 방문",
        },
        "visit_days": {"en": "Visit days", "ja": "訪問した日数", "ko": "방문한 날"},
    }
)


MESSAGES.update(
    {
        "flow_a_title": {
            "en": "A · Read Musecat data in this sample",
            "ko": "A · 예제에서 뮤즈캣 정보 조회",
            "ja": "A · サンプルで Musecat 情報を取得",
        },
        "flow_a_hint": {
            "en": "Musecat → sample. Grant access to Musecat APIs only. This does not give Musecat access to the sample records.",
            "ko": "뮤즈캣 → 예제. 뮤즈캣 API 접근만 동의합니다. 이 연결만으로 뮤즈캣이 예제 전적을 읽을 수는 없습니다.",
            "ja": "Musecat → サンプル。Musecat API へのアクセスだけに同意します。この連携だけでは Musecat はサンプル記録を取得できません。",
        },
        "connect_oauth": {
            "en": "Connect Musecat data only",
            "ko": "뮤즈캣 정보만 연결",
            "ja": "Musecat 情報のみ連携",
        },
        "a_setup_hint": {
            "en": "Set MUSECAT_CLIENT_SECRET after app approval. Joint keys are not needed for this flow.",
            "ko": "앱 승인 후 MUSECAT_CLIENT_SECRET을 설정하세요. 이 흐름에는 양방향 연결 키가 필요 없습니다.",
            "ja": "アプリ承認後に MUSECAT_CLIENT_SECRET を設定してください。このフローに双方向用キーは不要です。",
        },
        "flow_a_registration": {
            "en": "Registration JSON · Musecat data only",
            "ko": "등록 JSON · 뮤즈캣 정보 조회만",
            "ja": "登録 JSON · Musecat 情報のみ",
        },
        "flow_b_title": {
            "en": "B · Show sample records on Musecat",
            "ko": "B · 뮤즈캣에 예제 전적 표시",
            "ja": "B · Musecat にサンプル記録を表示",
        },
        "flow_b_hint": {
            "en": "Sample → Musecat. In Musecat settings, find {partner} in ordinary external account connections and connect CHUNITHM. Use its regular Connect action, rather than the bilateral section. Enable profile sharing and refresh records there.",
            "ko": "예제 → 뮤즈캣. 뮤즈캣 설정의 일반 외부 계정 연결에서 {partner}의 CHUNITHM을 선택하고 연결하세요. 양방향 연결 영역과 별도입니다. 연결 후 프로필 공개를 켜고 전적을 새로고침하세요.",
            "ja": "サンプル → Musecat。Musecat 設定の通常の外部アカウント連携で {partner} の CHUNITHM を選んで接続します。双方向連携とは別です。接続後、プロフィール公開を有効にして記録を更新してください。",
        },
        "flow_b_start": {
            "en": "Open Musecat account connections",
            "ko": "뮤즈캣 계정 연결 열기",
            "ja": "Musecat アカウント連携を開く",
        },
        "flow_b_registration": {
            "en": "Registration JSON · records, no joint flow",
            "ko": "등록 JSON · 전적 제공, 양방향 제외",
            "ja": "登録 JSON · 記録提供、双方向なし",
        },
        "record_grants": {
            "en": "Active record permissions issued by this sample: {count}",
            "ko": "이 예제에서 발급한 유효한 전적 접근 동의: {count}건",
            "ja": "このサンプルが発行した有効な記録アクセス同意: {count} 件",
        },
        "record_grants_hint": {
            "en": "This counts exchanged, unrevoked partner grants, including bilateral grants. Check Musecat settings for its current connection, cached records and profile sharing. Record permission does not imply reverse API access.",
            "ko": "토큰 교환이 완료되고 해제되지 않은 동의 수이며 양방향 동의도 포함합니다. 뮤즈캣의 실제 연결·전적 캐시·프로필 공개 상태는 뮤즈캣 설정에서 확인하세요. 전적 동의가 역방향 API 접근을 뜻하지는 않습니다.",
            "ja": "トークン交換済みで未解除の同意数で、双方向の同意も含みます。Musecat 側の接続・記録キャッシュ・プロフィール公開状態は Musecat 設定で確認してください。記録の同意は逆方向の API アクセスを意味しません。",
        },
        "flow_joint_hint": {
            "en": "Both directions with one combined consent. Both exchanges must complete. Independent one-way connections do not become a managed bilateral connection automatically.",
            "ko": "한 번의 통합 동의로 양쪽 방향을 연결합니다. 두 토큰 교환이 모두 완료되어야 합니다. 단방향 두 개를 연결해도 자동으로 공동 연결이 되지는 않습니다.",
            "ja": "一度の統合同意で両方向を連携します。両方のトークン交換の完了が必要です。個別の片方向連携を二つ作っても、自動的に管理された双方向連携にはなりません。",
        },
        "joint_registration": {
            "en": "Registration JSON · bilateral",
            "ko": "등록 JSON · 양방향",
            "ja": "登録 JSON · 双方向",
        },
        "change_mode_hint": {
            "en": "Disconnect the current Musecat data connection before starting a different mode. A separate record-only grant is managed in Musecat settings.",
            "ko": "다른 모드를 시작하려면 현재 뮤즈캣 정보 연결을 먼저 해제하세요. 별도의 전적 전용 연결은 뮤즈캣 설정에서 관리합니다.",
            "ja": "別のモードを開始する前に現在の Musecat 情報連携を解除してください。独立した記録専用連携は Musecat 設定で管理します。",
        },
        "oneway_mode": {
            "en": "One-way Musecat API connection",
            "ko": "단방향 뮤즈캣 API 연결",
            "ja": "片方向 Musecat API 連携",
        },
        "joint_mode": {
            "en": "Bilateral connection",
            "ko": "양방향 연결",
            "ja": "双方向連携",
        },
    }
)


MESSAGES.update(
    {
        "oidc_title": {
            "en": "Sign in with Musecat",
            "ko": "뮤즈캣으로 로그인",
            "ja": "Musecat でログイン",
        },
        "oidc_hint": {
            "en": "Standalone OpenID Connect login with read-only profile and arcade scopes. It creates a separate local account identified by issuer + subject; demo accounts and linked grants are not merged.",
            "ko": "읽기 전용 프로필·오락실 권한으로 OpenID Connect 로그인을 시험합니다. issuer와 subject로 별도 로컬 계정을 만들며, 데모 계정이나 기존 연결과 자동 병합하지 않습니다.",
            "ja": "読み取り専用のプロフィール・店舗スコープで OpenID Connect ログインを試します。issuer と subject で別のローカルアカウントを識別し、デモアカウントや既存連携とは自動統合しません。",
        },
        "oidc_account": {
            "en": "Signed in: {name}",
            "ko": "로그인: {name}",
            "ja": "ログイン中: {name}",
        },
        "oidc_expiry": {
            "en": "The example session expires with its access/ID token (at most ten minutes). Sign in again after expiry. Sign-out queues token revocation.",
            "ko": "예제 세션은 access/ID token과 함께 최대 10분 뒤 만료됩니다. 만료 후 다시 로그인하세요. 로그아웃하면 토큰 해제를 전송합니다.",
            "ja": "サンプルのセッションは access/ID token とともに最大10分で失効します。期限後は再ログインしてください。ログアウト時にトークン解除を送信します。",
        },
        "oidc_setup": {
            "en": "Register the login-only JSON as a separate app, enable login, obtain approval and set MUSECAT_LOGIN_CLIENT_ID / MUSECAT_LOGIN_CLIENT_SECRET.",
            "ko": "로그인 전용 JSON으로 별도 앱을 등록하고 로그인 허용·승인을 받은 뒤 MUSECAT_LOGIN_CLIENT_ID / MUSECAT_LOGIN_CLIENT_SECRET을 설정하세요.",
            "ja": "ログイン専用 JSON で別アプリを登録し、ログイン有効化・承認後に MUSECAT_LOGIN_CLIENT_ID / MUSECAT_LOGIN_CLIENT_SECRET を設定してください。",
        },
        "oidc_registration": {
            "en": "Registration JSON · OIDC login only",
            "ko": "등록 JSON · OIDC 로그인 전용",
            "ja": "登録 JSON · OIDC ログイン専用",
        },
        "oidc_nearby": {
            "en": "Read nearby arcades using login permission",
            "ko": "로그인 권한으로 주변 오락실 조회",
            "ja": "ログイン権限で周辺店舗を取得",
        },
        "oidc_location": {
            "en": "Demo query around Seoul City Hall (37.5665, 126.978); the user's location is not requested.",
            "ko": "서울시청 주변(37.5665, 126.978) 예제 조회입니다. 사용자 위치를 요청하지 않습니다。",
            "ja": "ソウル市庁付近（37.5665, 126.978）のデモ検索です。ユーザーの現在地は要求しません。",
        },
    }
)


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
