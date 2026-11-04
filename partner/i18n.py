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
        "en": "Connect your service to Musecat using this runnable sample. Game records are synthetic.",
        "ko": "실행 가능한 예제로 내 서비스를 뮤즈캣에 연결해 보세요. 게임 전적은 가상 데이터입니다.",
        "ja": "実行できるサンプルで自分のサービスを Musecat に接続できます。ゲーム記録は架空のデータです。",
    },
    "language": {"en": "Language", "ko": "언어", "ja": "言語"},
    "apply": {"en": "Apply", "ko": "변경", "ja": "変更"},
    "demo_login": {
        "en": "Demo account sign-in",
        "ko": "데모 계정 로그인",
        "ja": "デモアカウントでログイン",
    },
    "login_hint": {
        "en": "For this hosted demo, request test access from its operator. For your own local copy, use alice or bob with the DEMO_PASSWORD generated in your .env. Do not enter your Musecat or Google password here.",
        "ko": "배포된 데모는 운영자에게 테스트 접근을 요청하세요. 직접 실행한 로컬 예제는 alice 또는 bob과 내 .env에 생성된 DEMO_PASSWORD를 사용합니다. 뮤즈캣이나 Google 비밀번호를 입력하지 마세요.",
        "ja": "公開デモは運営者にテスト利用を依頼してください。自分のローカル環境では alice または bob と .env に生成された DEMO_PASSWORD を使います。Musecat や Google のパスワードは入力しないでください。",
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
        "en": "First register your app in Musecat Developer Center, then set the Musecat-issued keys in .env.",
        "ko": "먼저 Musecat 개발자 센터에서 앱을 등록하고 .env의 Musecat 발급 키를 설정하세요.",
        "ja": "先に Musecat 開発者センターでアプリを登録し、発行されたキーを .env に設定してください。",
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
    "developer_center": {
        "en": "Musecat Developer Center",
        "ko": "뮤즈캣 개발자 센터",
        "ja": "Musecat 開発者センター",
    },
    "spec": {"en": "Integration specification", "ko": "연동 스펙", "ja": "連携仕様"},
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
            "en": "Use Musecat APIs in this sample",
            "ko": "예제에서 뮤즈캣 API 사용",
            "ja": "サンプルで Musecat API を利用",
        },
        "flow_a_hint": {
            "en": "Allow this sample to use Musecat APIs on your behalf, including permitted account actions. This does not give Musecat access to the sample records.",
            "ko": "예제가 내 권한으로 뮤즈캣 API를 사용하도록 연결합니다. 허용된 계정 작업을 포함하며, 뮤즈캣에 예제 전적을 제공하지는 않습니다.",
            "ja": "サンプルが自分の権限で Musecat API を利用できるよう接続します。許可されたアカウント操作を含みます。Musecat にサンプル記録を提供するものではありません。",
        },
        "connect_oauth": {
            "en": "Connect Musecat API access",
            "ko": "뮤즈캣 API 접근 연결",
            "ja": "Musecat API アクセスを接続",
        },
        "a_setup_hint": {
            "en": "Set MUSECAT_CLIENT_SECRET after app registration. Joint keys are not needed for this flow.",
            "ko": "앱 등록 후 MUSECAT_CLIENT_SECRET을 설정하세요. 이 흐름에는 양방향 연결 키가 필요 없습니다.",
            "ja": "アプリ登録後に MUSECAT_CLIENT_SECRET を設定してください。このフローに双方向用キーは不要です。",
        },
        "flow_a_registration": {
            "en": "Registration JSON · Musecat data only",
            "ko": "등록 JSON · 뮤즈캣 정보 조회만",
            "ja": "登録 JSON · Musecat 情報のみ",
        },
        "flow_b_title": {
            "en": "Show sample records on Musecat",
            "ko": "뮤즈캣에 예제 전적 표시",
            "ja": "Musecat にサンプル記録を表示",
        },
        "flow_b_hint": {
            "en": "Open Musecat account connections, find Musecat Partner Example, select CHUNITHM and choose Connect. View records there. Profile sharing is a separate choice; this does not grant the example access to Musecat APIs.",
            "ko": "뮤즈캣 계정 연결에서 Musecat Partner Example의 CHUNITHM을 선택하고 연결하세요. 같은 화면에서 전적을 확인할 수 있습니다. 프로필 공개는 별도 선택이며, 이 연결만으로 예제가 뮤즈캣 API에 접근할 수는 없습니다.",
            "ja": "Musecat のアカウント連携で Musecat Partner Example の CHUNITHM を選んで接続し、記録を確認します。プロフィール公開は別の選択です。この連携だけではサンプルは Musecat API にアクセスできません。",
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
            "en": "Register the login-only JSON as a separate app, enable login and set MUSECAT_LOGIN_CLIENT_ID / MUSECAT_LOGIN_CLIENT_SECRET.",
            "ko": "로그인 전용 JSON으로 별도 앱을 등록하고 로그인을 허용한 뒤 MUSECAT_LOGIN_CLIENT_ID / MUSECAT_LOGIN_CLIENT_SECRET을 설정하세요.",
            "ja": "ログイン専用 JSON で別アプリを登録し、ログインを有効化して MUSECAT_LOGIN_CLIENT_ID / MUSECAT_LOGIN_CLIENT_SECRET を設定してください。",
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


MESSAGES.update(
    {
        "profile_image": {
            "en": "Musecat profile image",
            "ko": "뮤즈캣 프로필 이미지",
            "ja": "Musecat プロフィール画像",
        },
        "game_examples": {
            "en": "Game adapters and sharing choices",
            "ko": "게임별 어댑터와 전송 항목",
            "ja": "ゲーム別アダプターと共有項目",
        },
        "synthetic_json": {
            "en": "Synthetic example JSON (all fields)",
            "ko": "합성 예제 JSON (전체 항목)",
            "ja": "架空のサンプル JSON（全項目）",
        },
        "selection_hint": {
            "en": "Checked groups are withheld from authenticated records. JSON example links always contain synthetic fixtures. Changes queue cache invalidation; failed notifications retry in the worker. The existing Joint example requests CHUNITHM only; register the B-only template to try all five games.",
            "ko": "체크한 그룹은 인증된 전적 응답에서 제외됩니다. JSON 링크는 항상 합성 예제입니다. 변경 시 캐시 무효화를 전송하고 실패하면 worker가 재시도합니다. 기존 양방향 예제는 츄니즘만 요청하며, 다섯 게임은 B 전용 등록으로 시험하세요.",
            "ja": "チェックしたグループは認証済み記録から除外します。JSON リンクは常に架空の例です。変更時にキャッシュ無効化を送り、失敗時は worker が再試行します。既存の双方向例は CHUNITHM のみで、5ゲームは B 専用登録で試せます。",
        },
        "exclude_player": {
            "en": "Withhold player information",
            "ko": "플레이어 정보 제외",
            "ja": "プレーヤー情報を除外",
        },
        "exclude_fields": {
            "en": "Withhold summary metrics",
            "ko": "요약 지표 제외",
            "ja": "集計指標を除外",
        },
        "exclude_sections": {
            "en": "Withhold additional tables",
            "ko": "추가 표 제외",
            "ja": "追加の表を除外",
        },
        "exclude_recent_plays": {
            "en": "Withhold recent plays",
            "ko": "최근 플레이 제외",
            "ja": "最近のプレーを除外",
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
            "musecat_locale": {"ko": "kr", "ja": "jp"}.get(g.locale, g.locale),
        }
    )


MESSAGES.update(
    {
        "actions_title": {
            "en": "Try account actions",
            "ko": "계정 권한으로 직접 체험",
            "ja": "アカウント権限で操作を試す",
        },
        "actions_intro": {
            "en": "Edit arcade information, report a faulty machine and participate in campaigns using your connected Musecat account. Requires account:access consent.",
            "ko": "연결한 뮤즈캣 계정으로 오락실 정보를 수정하고 고장 신고와 캠페인 참여를 직접 해보세요. account:access 동의가 필요합니다.",
            "ja": "連携した Musecat アカウントで店舗情報の編集・故障報告・キャンペーン参加を試せます。account:access への同意が必要です。",
        },
        "actions_test_notice": {
            "en": "These buttons write real data to the configured Musecat server. Use designated synthetic test arcades only. Account level, ownership and location rules still apply. Mutations are never retried automatically.",
            "ko": "버튼을 누르면 설정된 뮤즈캣 서버에 실제 데이터가 저장됩니다. 지정된 가상 테스트 오락실만 사용하세요. 계정 레벨·소유권·위치 규칙이 그대로 적용되며 쓰기 요청을 자동 재시도하지 않습니다.",
            "ja": "ボタンは設定先の Musecat に実データを保存します。指定された架空のテスト店舗だけを使用してください。レベル・所有権・位置の規則はそのまま適用され、書き込みは自動再試行しません。",
        },
        "actions_target": {
            "en": "Choose a test arcade",
            "ko": "테스트 오락실 선택",
            "ja": "テスト店舗を選択",
        },
        "actions_arcade_id": {
            "en": "Test arcade ID",
            "ko": "테스트 오락실 ID",
            "ja": "テスト店舗 ID",
        },
        "actions_load": {
            "en": "Load current information",
            "ko": "현재 정보 불러오기",
            "ja": "現在の情報を取得",
        },
        "actions_response": {
            "en": "Actual Musecat response",
            "ko": "실제 뮤즈캣 응답",
            "ja": "Musecat の実際の応答",
        },
        "actions_recovery": {
            "en": "401: reconnect. 403: check your level, consent and same-day visit; supplied coordinates must be within 100 m. 404: check the test ID and public/open state. 409: reload current data and campaign eligibility before submitting again. 429: wait. After a network failure, read the current state before deciding whether to resubmit.",
            "ko": "401: 다시 연결하세요. 403: 레벨·동의·당일 방문을 확인하세요. 제출 좌표는 오락실 100m 이내여야 합니다. 404: 테스트 ID와 공개·영업 상태를 확인하세요. 409: 최신 정보와 캠페인 참여 조건을 다시 조회하세요. 429: 기다리세요. 네트워크 실패 후에는 재전송 전에 현재 상태를 먼저 확인하세요.",
            "ja": "401: 再連携してください。403: レベル・同意・当日の訪問を確認してください。座標は店舗の 100 m 以内である必要があります。404: ID と公開・営業状態を確認してください。409: 最新情報とキャンペーン条件を再取得してください。429: 待ってください。通信失敗後は再送前に現在の状態を確認してください。",
        },
        "actions_saved": {
            "en": "Request completed. Current information was reloaded below.",
            "ko": "요청을 완료했습니다. 아래에 현재 정보를 다시 불러왔습니다.",
            "ja": "リクエストが完了しました。以下に現在の情報を再取得しました。",
        },
        "actions_basic": {
            "en": "Edit basic information",
            "ko": "오락실 기본 정보 수정",
            "ja": "店舗の基本情報を編集",
        },
        "actions_basic_hint": {
            "en": "Only name, address and directions are edited here. Coordinates, aliases and other fields are left unchanged. A stale revision is rejected.",
            "ko": "이 폼은 이름·주소·찾아가는 길만 수정합니다. 좌표·별명 등 다른 필드는 유지하며 오래된 수정본은 거부됩니다.",
            "ja": "このフォームは名前・住所・アクセス案内だけを編集します。座標・別名などは維持し、古いリビジョンによる変更は拒否されます。",
        },
        "actions_name": {"en": "Name", "ko": "이름", "ja": "名前"},
        "actions_address": {"en": "Address", "ko": "주소", "ja": "住所"},
        "actions_direction": {
            "en": "Directions",
            "ko": "찾아가는 길",
            "ja": "アクセス案内",
        },
        "actions_save_basic": {
            "en": "Save arcade information",
            "ko": "오락실 정보 저장",
            "ja": "店舗情報を保存",
        },
        "actions_fault": {
            "en": "Report a fault",
            "ko": "고장 신고",
            "ja": "故障を報告",
        },
        "actions_game": {"en": "Machine", "ko": "게임 기기", "ja": "ゲーム筐体"},
        "actions_choose": {
            "en": "Choose a machine",
            "ko": "기기를 선택하세요",
            "ja": "筐体を選択",
        },
        "actions_severity": {"en": "Severity", "ko": "고장 정도", "ja": "不具合の程度"},
        "actions_minor": {
            "en": "Minor inconvenience",
            "ko": "경미한 불편",
            "ja": "軽微な不便",
        },
        "actions_bearable": {
            "en": "Playable with issues",
            "ko": "플레이 가능하나 불편",
            "ja": "問題はあるがプレイ可能",
        },
        "actions_major": {"en": "Major problem", "ko": "큰 지장", "ja": "大きな支障"},
        "actions_unplayable": {
            "en": "Unplayable",
            "ko": "플레이 불가",
            "ja": "プレイ不可",
        },
        "actions_message": {
            "en": "Describe the fault",
            "ko": "고장 내용",
            "ja": "故障の内容",
        },
        "actions_send_fault": {
            "en": "Submit fault report",
            "ko": "고장 신고 등록",
            "ja": "故障報告を送信",
        },
        "actions_campaign": {
            "en": "Participate in an update campaign",
            "ko": "업데이트 캠페인 참여",
            "ja": "アップデートキャンペーンに参加",
        },
        "actions_campaign_hint": {
            "en": "Load eligible campaign targets, then confirm the observed version. A verified visit on the same local day is required. This example does not bypass location checks.",
            "ko": "참여 가능한 캠페인 대상을 불러온 뒤 확인한 버전을 제출하세요. 오락실 현지 날짜 기준 당일 인증 방문이 필요합니다. 이 예제는 위치 검사를 우회하지 않습니다.",
            "ja": "対象を取得して確認したバージョンを送信します。店舗の現地日付で当日の認証済み訪問が必要です。このサンプルは位置確認を回避しません。",
        },
        "actions_visit": {
            "en": "Verify a test visit first",
            "ko": "테스트 방문 먼저 인증",
            "ja": "先にテスト訪問を認証",
        },
        "actions_visit_hint": {
            "en": "Synthetic fixture coordinates only: entering coordinates records a real test visit and may award XP. Do not enter fabricated coordinates for real arcades. No browser location is requested.",
            "ko": "가상 테스트 오락실의 좌표만 입력하세요. 실제 테스트 방문이 기록되고 경험치가 부여될 수 있습니다. 실제 오락실에 허위 좌표를 제출하지 마세요. 브라우저 위치를 요청하지 않습니다.",
            "ja": "架空のテスト店舗の座標のみ使用してください。テスト訪問が実際に記録され、経験値が付与される場合があります。実店舗の偽の座標を送信しないでください。ブラウザーの位置情報は要求しません。",
        },
        "actions_lat": {"en": "Test latitude", "ko": "테스트 위도", "ja": "テスト緯度"},
        "actions_lon": {
            "en": "Test longitude",
            "ko": "테스트 경도",
            "ja": "テスト経度",
        },
        "actions_accuracy": {
            "en": "Accuracy (meters)",
            "ko": "정확도 (m)",
            "ja": "精度（m）",
        },
        "actions_verify_visit": {
            "en": "Record verified test visit",
            "ko": "테스트 방문 인증 기록",
            "ja": "テスト訪問認証を記録",
        },
        "actions_no_campaigns": {
            "en": "No eligible campaign prompts for this arcade. Check the selected test arcade and active campaign.",
            "ko": "이 오락실에 참여 가능한 캠페인이 없습니다. 테스트 오락실과 활성 캠페인을 확인하세요.",
            "ja": "この店舗の対象キャンペーンはありません。テスト店舗と有効なキャンペーンを確認してください。",
        },
        "actions_campaign_id": {
            "en": "Campaign ID",
            "ko": "캠페인 ID",
            "ja": "キャンペーン ID",
        },
        "actions_game_id": {
            "en": "Stable machine ID",
            "ko": "고정 게임 기기 ID",
            "ja": "固定筐体 ID",
        },
        "actions_result": {
            "en": "Observed version",
            "ko": "확인한 버전",
            "ja": "確認したバージョン",
        },
        "actions_still_old": {
            "en": "Still on the old version",
            "ko": "아직 이전 버전",
            "ja": "まだ旧バージョン",
        },
        "actions_updated": {
            "en": "Updated to the target version",
            "ko": "대상 버전으로 업데이트됨",
            "ja": "対象バージョンに更新済み",
        },
        "actions_submit_campaign": {
            "en": "Submit campaign participation",
            "ko": "캠페인 참여 제출",
            "ja": "キャンペーン参加を送信",
        },
        "actions_read_results": {
            "en": "Current information and API responses",
            "ko": "현재 정보와 API 응답",
            "ja": "現在の情報と API 応答",
        },
    }
)


MESSAGES.update(
    {
        "start_navigation": {"en": "Getting started", "ko": "시작 안내", "ja": "利用ガイド"},
        "prepare_title": {"en": "Connect your own app", "ko": "내 앱 연결하기", "ja": "自分のアプリを接続"},
        "prepare_intro": {
            "en": "Choose what your service needs. Setup instructions and source code are available without a demo account.",
            "ko": "내 서비스에 필요한 기능을 선택하세요. 데모 계정 없이도 준비 절차와 소스를 확인할 수 있습니다.",
            "ja": "自分のサービスに必要な機能を選んでください。デモアカウントなしで手順とソースを確認できます。",
        },
        "goal_login": {"en": "Let users sign in with Musecat", "ko": "뮤즈캣 계정으로 로그인 받기", "ja": "Musecat アカウントでログイン"},
        "goal_a": {"en": "Use Musecat APIs in my service", "ko": "내 서비스에서 뮤즈캣 API 사용하기", "ja": "自分のサービスで Musecat API を利用"},
        "goal_b": {"en": "Provide my service's game records to Musecat", "ko": "뮤즈캣에 내 서비스의 게임 전적 제공하기", "ja": "自分のゲーム記録を Musecat に提供"},
        "goal_joint": {"en": "Connect both services with one consent", "ko": "한 번의 동의로 두 서비스를 양방향 연결하기", "ja": "一度の同意で両サービスを双方向接続"},
        "purpose_login": {
            "en": "OIDC verifies the user's identity with read-only profile and arcade scopes. Register a separate login app; it does not link the demo accounts or grant general account actions.",
            "ko": "OIDC로 사용자 신원을 확인합니다. 읽기 전용 프로필과 오락실 권한을 쓰는 로그인 앱을 별도로 등록하며, 데모 계정을 연결하거나 일반 계정 작업 권한을 부여하지 않습니다.",
            "ja": "OIDC で本人を確認します。読み取り専用のプロフィールと店舗スコープを使うログイン用アプリを別途登録します。デモアカウントの統合や一般アカウント操作の権限は付与しません。",
        },
        "purpose_a": {
            "en": "OAuth account:access lets your service read and act on the consenting Musecat account within its normal permissions. It includes writes; it is broader than login. It does not let Musecat read your game records.",
            "ko": "OAuth account:access는 동의한 사용자의 기존 권한 안에서 뮤즈캣 정보를 읽고 작업을 실행합니다. 쓰기 작업을 포함해 로그인보다 넓은 권한이며, 뮤즈캣에 내 전적을 제공하지는 않습니다.",
            "ja": "OAuth account:access は同意したユーザーの通常権限内で情報の取得と操作を許可します。書き込みを含み、ログインより広い権限です。Musecat に自分の記録を提供するものではありません。",
        },
        "purpose_b": {
            "en": "Musecat calls your OAuth provider and records API. Select the games you provide. This direction gives your service no access to Musecat APIs.",
            "ko": "뮤즈캣이 내 OAuth 서버와 전적 API를 호출합니다. 제공할 게임을 선택하며, 내 서비스에 뮤즈캣 API 접근 권한을 부여하지 않습니다.",
            "ja": "Musecat が自分の OAuth サーバーと記録 API を呼び出します。提供するゲームを選びます。自分のサービスへの Musecat API アクセス権は付与されません。",
        },
        "purpose_joint": {
            "en": "Combine Musecat API access and CHUNITHM record access in one consent. Both token exchanges must finish. Two independent one-way connections do not become a joint connection.",
            "ko": "뮤즈캣 API 접근과 CHUNITHM 전적 제공을 한 동의로 연결합니다. 양쪽 토큰 교환이 모두 끝나야 완료되며, 별도로 만든 단방향 연결 두 개와는 다릅니다.",
            "ja": "Musecat API アクセスと CHUNITHM 記録提供を一度の同意で接続します。両方のトークン交換が必要です。独立した片方向接続を二つ作ることとは異なります。",
        },
        "host_local": {
            "en": "Start locally: HTTP localhost callbacks are allowed for development. Production requires HTTPS.",
            "ko": "개발은 HTTP localhost 콜백으로 시작할 수 있습니다. 운영은 HTTPS가 필요합니다.",
            "ja": "開発は HTTP localhost のコールバックで始められます。本番は HTTPS が必要です。",
        },
        "host_public": {
            "en": "Your server must be reachable from Musecat over public HTTPS. Use the quick-start tunnel command or deploy it at a stable HTTPS address.",
            "ko": "뮤즈캣 서버가 접근할 수 있는 공개 HTTPS 주소가 필요합니다. 빠른 시작의 터널 명령을 쓰거나 고정 HTTPS 서버에 배포하세요.",
            "ja": "Musecat サーバーからアクセスできる公開 HTTPS が必要です。クイックスタートのトンネルコマンド、または固定 HTTPS サーバーを使います。",
        },
        "keys_login": {
            "en": "Save the login app's client ID and secret as MUSECAT_LOGIN_CLIENT_ID and MUSECAT_LOGIN_CLIENT_SECRET in your server's .env.",
            "ko": "로그인 앱에서 발급한 ID와 시크릿을 서버 .env의 MUSECAT_LOGIN_CLIENT_ID와 MUSECAT_LOGIN_CLIENT_SECRET에 설정하세요.",
            "ja": "ログイン用アプリの ID とシークレットをサーバーの .env の MUSECAT_LOGIN_CLIENT_ID と MUSECAT_LOGIN_CLIENT_SECRET に設定します。",
        },
        "keys_a": {
            "en": "Match PARTNER_ID to your registered app and save its Musecat-issued client secret as MUSECAT_CLIENT_SECRET. Joint keys are not needed.",
            "ko": "PARTNER_ID를 등록한 앱 ID와 맞추고, 뮤즈캣에서 발급한 클라이언트 시크릿을 MUSECAT_CLIENT_SECRET에 설정하세요. 양방향 연결 키는 필요 없습니다.",
            "ja": "PARTNER_ID を登録したアプリ ID に合わせ、Musecat 発行のクライアントシークレットを MUSECAT_CLIENT_SECRET に設定します。双方向用キーは不要です。",
        },
        "keys_b": {
            "en": "In Developer Center, configure your server's PARTNER_OAUTH_CLIENT_ID and PARTNER_OAUTH_CLIENT_SECRET. Issue a records invalidation key there and save it as PARTNER_TO_MUSECAT_KEY on your server.",
            "ko": "내 서버의 PARTNER_OAUTH_CLIENT_ID와 PARTNER_OAUTH_CLIENT_SECRET을 개발자 센터에 설정하세요. 센터에서 전적 캐시 무효화 키를 발급해 서버의 PARTNER_TO_MUSECAT_KEY에 저장하세요.",
            "ja": "自分のサーバーの PARTNER_OAUTH_CLIENT_ID と PARTNER_OAUTH_CLIENT_SECRET を開発者センターに設定します。記録キャッシュ無効化キーを発行し、サーバーの PARTNER_TO_MUSECAT_KEY に保存します。",
        },
        "keys_joint": {
            "en": "Configure the OAuth credentials for both directions. Save Musecat's client secret and outbound server key as MUSECAT_CLIENT_SECRET and PARTNER_TO_MUSECAT_KEY. Give Developer Center your provider credentials and MUSECAT_TO_PARTNER_KEY. The quick start shows each exchange.",
            "ko": "양쪽 OAuth 인증 정보를 설정합니다. 뮤즈캣의 클라이언트 시크릿과 서버 키는 MUSECAT_CLIENT_SECRET과 PARTNER_TO_MUSECAT_KEY에 저장하고, 내 서버의 OAuth 인증 정보와 MUSECAT_TO_PARTNER_KEY는 개발자 센터에 설정하세요. 교환 순서는 빠른 시작에서 확인할 수 있습니다.",
            "ja": "両方向の OAuth 認証情報を設定します。Musecat のシークレットとサーバーキーを MUSECAT_CLIENT_SECRET と PARTNER_TO_MUSECAT_KEY に保存し、自分の OAuth 認証情報と MUSECAT_TO_PARTNER_KEY を開発者センターに設定します。順序はクイックスタートで確認できます。",
        },
        "success_login": {"en": "Check: sign in, return to your app, then load nearby arcades.", "ko": "완료 확인: 로그인 후 내 앱으로 돌아와 주변 오락실을 조회합니다.", "ja": "完了確認: ログイン後に自分のアプリへ戻り、近くの店舗を取得します。"},
        "success_a": {"en": "Check: read the Musecat profile, refresh the token and read it again.", "ko": "완료 확인: 뮤즈캣 프로필 조회와 토큰 갱신 후 재조회를 실행합니다.", "ja": "完了確認: Musecat プロフィールを取得し、トークン更新後に再取得します。"},
        "success_b": {"en": "Check: view records in Musecat, change a sharing choice, then refresh and confirm the withheld data disappears.", "ko": "완료 확인: 뮤즈캣에서 전적을 조회하고 제공 항목을 변경한 뒤, 새로고침하면 제외한 정보가 사라지는지 확인합니다.", "ja": "完了確認: Musecat で記録を取得し、提供項目を変更した後、再取得で除外した情報が消えることを確認します。"},
        "success_joint": {"en": "Check: both services show connected, Musecat profile and records load, and disconnecting revokes both sides.", "ko": "완료 확인: 양쪽 연결 완료 후 뮤즈캣 프로필과 전적을 조회하고, 연결 해제 시 양쪽 권한이 해제되는지 확인합니다.", "ja": "完了確認: 両側の接続完了後にプロフィールと記録を取得し、切断すると両側の権限が解除されることを確認します。"},
        "source_code": {"en": "Get the source", "ko": "소스 받기", "ja": "ソースを取得"},
        "local_quickstart": {"en": "Run the quick start", "ko": "빠른 시작 따라 하기", "ja": "クイックスタート"},
        "prepare_run": {"en": "Run your own copy and choose a unique app ID and your server origin. You do not need to install Musecat.", "ko": "예제를 직접 실행하고 고유한 앱 ID와 내 서버 주소를 설정하세요. 뮤즈캣 자체를 설치할 필요는 없습니다.", "ja": "サンプルを自分で起動し、固有のアプリ ID とサーバーの origin を設定します。Musecat 自体のインストールは不要です。"},
        "prepare_json": {"en": "Open your running copy's registration JSON for the selected goal. Replace the contact email; check every URL and exact callback before registration.", "ko": "직접 실행한 예제에서 선택한 목적의 등록 JSON을 여세요. 연락처 이메일을 바꾸고 모든 URL과 정확한 콜백을 확인하세요.", "ja": "自分で起動したサンプルで目的別の登録 JSON を開きます。連絡先メールを変更し、各 URL と正確なコールバックを確認します。"},
        "prepare_register": {"en": "Sign in with your Musecat account and register your app using those values. During development only its owner and up to 10 named testers can authorize it. Add testers separately to the login app if used.", "ko": "내 뮤즈캣 계정으로 앱을 등록하고 JSON의 값을 입력하세요. 개발 중에는 소유자와 지정한 테스터 최대 10명만 동의할 수 있습니다. 로그인 앱을 따로 쓰면 그 앱에도 테스터를 등록하세요.", "ja": "自分の Musecat アカウントでアプリを登録し、JSON の値を入力します。開発中は所有者と指定した最大10人のテスターのみ利用できます。ログイン用アプリにも個別にテスターを登録します。"},
        "prepare_keys": {"en": "Exchange only the credentials required for your selected goal, save secrets on the server and restart your copy. Never put secrets in the registration JSON or browser code.", "ko": "선택한 목적에 필요한 인증 정보만 교환해 서버에 저장하고 예제를 다시 시작하세요. 등록 JSON이나 브라우저 코드에 비밀값을 넣지 마세요.", "ja": "選んだ目的に必要な認証情報だけを交換し、サーバーに保存してサンプルを再起動します。登録 JSON やブラウザーのコードに秘密情報を入れないでください。"},
        "prepare_verify": {"en": "Authorize with the app owner or a named tester, then perform the completion check above. A health check or local unit test alone does not prove a working Musecat connection.", "ko": "소유자 또는 지정 테스터로 동의하고 위의 완료 확인을 실행하세요. 헬스체크나 로컬 테스트 통과만으로 실제 연동이 완료되지는 않습니다.", "ja": "所有者または指定テスターで同意し、上記の完了確認を行います。ヘルスチェックやローカルテストの成功だけでは実接続は証明できません。"},
        "deployed_json": {"en": "View this demo's registration JSON", "ko": "이 데모의 등록 JSON 보기", "ja": "このデモの登録 JSON を見る"},
        "json_boundary": {"en": "The JSON links above describe this hosted demo, which is already registered. Do not register it as your own app unchanged. Generate your app's values from your own running copy.", "ko": "위 JSON은 이미 등록된 이 배포 데모의 설정입니다. 그대로 내 앱으로 등록하지 말고, 직접 실행한 예제에서 내 앱의 값을 생성하세요.", "ja": "上の JSON は登録済みの公開デモの設定です。そのまま自分のアプリとして登録せず、自分で起動したサンプルから値を生成してください。"},
        "try_demo": {"en": "Try the hosted demo", "ko": "배포된 데모 체험하기", "ja": "公開デモを試す"},
        "demo_access": {"en": "This demo uses operator-managed synthetic accounts. Ask its operator for demo access and a Musecat tester invitation for the flow you want. Your Musecat account alone does not grant access. To build your own integration, use the setup guide above instead.", "ko": "이 데모는 운영자가 관리하는 가상 계정을 사용합니다. 운영자에게 데모 접근과 시험할 앱의 뮤즈캣 테스터 초대를 요청하세요. 뮤즈캣 가입만으로 접근 권한이 생기지는 않습니다. 내 서비스 연동은 위 준비 절차를 따르세요.", "ja": "このデモは運営者が管理する架空のアカウントを使います。デモ利用と対象アプリの Musecat テスター招待を運営者に依頼してください。Musecat 登録だけでは利用できません。自分の連携開発は上の手順に従います。"},
        "troubleshoot_title": {"en": "If a connection fails", "ko": "연결이 안 될 때", "ja": "接続できない場合"},
        "troubleshoot_tester": {"en": "Not allowed to authorize: check the app owner/tester list, including the separate login app.", "ko": "동의할 수 없음: 해당 앱의 소유자 또는 지정 테스터인지 확인하세요. 별도 로그인 앱도 확인해야 합니다.", "ja": "同意できない: アプリの所有者・テスター一覧を確認します。別のログイン用アプリも対象です。"},
        "troubleshoot_credentials": {"en": "Disabled action or callback error: check the chosen flow's credentials, exact origin and callback. If a tunnel URL changed, update registration and restart before trying again.", "ko": "비활성 버튼 또는 콜백 오류: 선택한 목적의 인증 정보와 정확한 서버 주소·콜백을 확인하세요. 터널 주소가 바뀌면 등록 정보를 갱신하고 다시 시작하세요.", "ja": "ボタン無効・コールバックエラー: 目的別の認証情報、正確な origin とコールバックを確認します。トンネル URL が変わった場合は登録を更新して再起動します。"},
        "troubleshoot_records": {"en": "Records missing: check connection, selected game and refresh status in Musecat. Records can be visible to their owner while private. Public profiles additionally require both services' sharing settings and production approval for the app.", "ko": "전적이 안 보임: 뮤즈캣의 연결 상태와 선택 게임, 새로고침 결과를 확인하세요. 비공개 전적도 본인은 조회할 수 있습니다. 공개 프로필에는 양쪽 공개 설정과 앱의 운영 승인이 추가로 필요합니다.", "ja": "記録が見えない: Musecat の接続、選択ゲーム、再取得結果を確認します。非公開でも本人は閲覧できます。公開プロフィールには両側の公開設定とアプリの本番承認も必要です。"},
    }
)


def text(key, **values):
    return MESSAGES[key][g.locale].format(**values)
