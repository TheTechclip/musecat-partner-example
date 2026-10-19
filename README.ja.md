# Musecat Partner Example

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md)
有効な登録は開発モードで所有者と指定テスター最大10名が直ちに利用できます。一般ユーザー向けの本番公開には運営承認が必要です。認証情報とユーザー同意は両モードで必要です。B 専用登録は5ゲームを宣言し、既存の双方向例は CHUNITHM の manifest を維持します。[ゲーム別規格・最近のプレー・共有項目・キャッシュ無効化](docs/record-adapters.md)。


Musecat Preview と連携する **開発・テスト用サンプル**です。Python + Flask + SQLite、Docker Compose、任意の Caddy HTTPS 構成、MIT ライセンス。`alice` / `bob` の2つのデモアカウントと架空の CHUNITHM 記録を使用します。学習用の例であり、OAuth/OIDC プロバイダーの完全な実装ではありません。

[localhost と実際の Preview 接続手順](docs/local-development.md)

## 確認できるフロー

- **OIDC ログイン:** Musecat でログイン → ID token・UserInfo 検証 → 独立したローカルセッション → 近隣施設の参照。
- **A:** サンプル → Musecat の同意 → プロフィール取得 → refresh token のローテーション → 解除。
- **B:** Musecat → サンプルの同意 → 架空の記録取得 → 公開・非公開 → refresh による復旧。
- **Joint:** どちらから開始しても、Musecat の共同同意画面で一度同意すると両方向の権限を発行します。両側の交換と Musecat の状態確認後にのみ完了とし、不完全な接続は部分連携と表示します。
- 両側からの解除、再連携、接続世代による解除要求の分離、永続 outbox での通知再送。

| 開発環境 | URL |
| --- | --- |
| API / OAuth issuer | `https://db-dev.musecat.app` |
| 開発者センター | <https://preview.musecat.app/ja/developer> |
| 正式な連携仕様 | <https://preview.musecat.app/api/developer/spec> |

この例は権限委譲 scope `account:access` と `/developer/v1/account/*`、`/developer/v1/me` API を使用します。独立した OIDC ログインは別アプリと認証情報で `openid profile arcade:read` を要求し、`account:access` は付与しません。

## 最初に連携の目的を選ぶ

以下の方向は **データへのアクセス方向**であり、開始するサイトとは別です。

| 目的 | 開始位置 | 登録 JSON | サンプルに必要な Musecat 発行シークレット |
| --- | --- | --- | --- |
| Musecat アカウントでログイン | ホーム → **Musecat でログイン** | `/onboarding.json?flow=login` | 別の `MUSECAT_LOGIN_CLIENT_SECRET`、ID は `MUSECAT_LOGIN_CLIENT_ID` |
| サンプルから Musecat プロフィール/API を取得（A のみ） | デモログイン → **Musecat 情報のみ連携** | `/onboarding.json?flow=a` | `MUSECAT_CLIENT_SECRET` |
| Musecat からサンプル記録を取得（B のみ） | Musecat 設定 → 通常の外部アカウント連携 → サンプルの CHUNITHM を選択して接続 | `/onboarding.json?flow=b` | 不要。生成済みパートナー OAuth ID/シークレットを Musecat に設定 |
| 統合同意で双方向連携 | どちらのサービスでも **ワンクリック双方向連携** | `/onboarding.json?flow=joint`（既定） | `MUSECAT_CLIENT_SECRET` と `PARTNER_TO_MUSECAT_KEY`。生成済み OAuth 情報と `MUSECAT_TO_PARTNER_KEY` も Musecat に設定 |

すべてのモードは生成済みのローカルセッション・暗号化・デモ用シークレットを使います。未使用モードのキーは `.env` に残せますが、交換は不要です。アプリ登録と正確なコールバック登録は共通です。**B 専用アプリを登録できます。** `/onboarding.json?flow=b` は `direction_a` 自体を省略します。開発者センターで A を無効にして B を宣言すると、A コールバック・Musecat 発行の A シークレット・Joint キーは不要です。登録済みの全機能アプリなら登録変更なしで三つのフローを個別に試せます。ボタンを切り替えるために三つの JSON を交互に再申請しないでください。承認設定の変更は既存の同意を無効にする場合があります。

A は **片方向 Musecat API 連携**が表示され、公開プロフィールを取得できれば成功です。`account:access` は文書化された一般ユーザーの更新操作も許可し、読み取り専用 scope や OIDC ログインではありません。B は Musecat でアカウント接続と架空記録の取得を確認します。**プロフィール公開は別に有効化**して公開プロフィールを確認してください。サンプルの同意数はトークン交換済みの権限であり、Musecat のキャッシュ・実際の表示状態を保証しません。B のみの解除は Musecat 設定で行います。A のみ解除しても独立した B 権限は残ります。個別の同意二つが自動的に共同連携になることはありません。

Alice のデモを保って別のモードを試すには `bob` を使います。ただし Musecat のアカウント重複連携ルールは適用されます。同じ Musecat アカウントを競合するデモに承認せず、変更時は既存連携を明示的に解除してください。独立した **Musecat でログイン**は以下の手順で実装されています。Alice の登録済み A/B/Joint アプリを編集せず、ログイン用アプリを別に登録してください。設定変更の承認で既存 grant が無効になる場合があります。

### 最初の接続に失敗した場合

| 症状 | 確認・復旧 |
| --- | --- |
| A ボタンが無効 | 登録済み Client Secret を `MUSECAT_CLIENT_SECRET` に設定。双方向キーの交換は不要 |
| Musecat にプロバイダーがない | 開発者センターの登録、登録済み B 宣言、パートナー OAuth 資格情報を確認 |
| `invalid_origin` | 正確な HTTPS `PARTNER_ORIGIN` で開く。トンネル変更後は origin・登録 URL を更新しコンテナーを再作成 |
| `invalid_client`・コールバック拒否 | キーの発行元・方向と登録コールバックの完全一致を確認 |
| `invalid_grant`・state 不一致・期限切れ | 同じブラウザーセッションで開始し直す。コード・コールバックは再利用せず、refresh 消費後は再接続 |
| `records_private`・記録が表示されない | サンプルの公開状態、Musecat の公開スイッチ、キャッシュ・更新制限を確認 |
| HTTP 429 | API の再試行時間を守り、全サンプルの自動反復を避ける |


## 1. ローカル起動

Docker Compose、初期化用の Python 3、公開 HTTPS origin が必要です。Musecat がサンプルサーバーを直接呼び出すため、localhost のみの URL は登録できません。

```sh
git clone https://github.com/TheTechclip/musecat-partner-example.git
cd musecat-partner-example
python3 scripts/init-env.py
```

スクリプトは `.env` にランダムなデモパスワード、セッションキー、暗号化キー、パートナー発行キーを生成し、既存の値は維持します。`.env` は Git と Docker ビルドコンテキストから除外されます。

### 方法 A: ローカル + 一時 HTTPS トンネル

別のターミナルで [Cloudflare Quick Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/) を起動します。

```sh
cloudflared tunnel --url http://127.0.0.1:8088 --no-autoupdate
```

出力された `https://...trycloudflare.com` を `.env` の `PARTNER_ORIGIN` に設定し、`PARTNER_HOST` にはホスト名のみを設定します。末尾の `/` は付けません。

```sh
docker compose up -d --build
docker compose ps
```

ブラウザーでも **HTTPS トンネルの URL** を開いてください。Cookie は Secure です。トンネル URL が変わると issuer と callback も変わるため、アプリの URL を変更して登録更新を受け、再連携してください。Quick Tunnel は一時テスト用です。固定アドレスには named tunnel または固定ドメインを使います。

### 方法 B: 固定ドメイン + Caddy

DNS を実行サーバーに向け、80/443 ポートを公開します。`.env` に `PARTNER_ORIGIN=https://your-domain.example` と `PARTNER_HOST=your-domain.example` を設定します。

```sh
docker compose --profile https up -d --build
```

既存の HTTPS プロキシがあれば、Caddy を使わず `app:8080` に転送できます。

### 表示言語

英語・韓国語・日本語に対応しています。ページ上部で言語を選び **変更** を押してください。初回はブラウザーの言語を使い、該当しなければ英語になります。選択はログイン・ログアウト後も維持されます。ログイン、同意、連携操作、テストツールを翻訳し、プロトコル識別子と JSON エラーコードは共通のままにしています。サンプルから始めた共同同意は選択言語で開き、Musecat から始めた場合は Musecat が指定した言語を維持します。

## 2. Musecat 開発者センターへの登録

Musecat 発行キーがなくてもサンプルは起動します。`.env` の `DEMO_PASSWORD` を使い、`alice` または `bob` でログインします。

1. **アプリ登録 JSON** (`/onboarding.json`) を開きます。実際の URL と生成済み `PARTNER_ID` が含まれます。
2. 開発者センターで選択したフローの JSON を使って登録し、基本情報とその JSON に含まれる方向だけを入力します。`contact_email` を自分の連絡先に変更します。
3. 有効な登録を保存します。運営者の承認なしで直ちに利用できます。
4. 以下の認証情報を交換します。値はサーバー専用です。GitHub Issue、スクリーンショット、フロントエンド JavaScript に載せないでください。

| 認証情報 | 発行元 | 設定先 |
| --- | --- | --- |
| Client ID | Musecat (`PARTNER_ID` と同じ) | サンプル `.env`: `PARTNER_ID` |
| Client Secret | Musecat、発行・再発行時のみ表示 | `.env`: `MUSECAT_CLIENT_SECRET` |
| 独立した OIDC Client ID / Secret | Musecat の別ログインアプリ | `.env`: `MUSECAT_LOGIN_CLIENT_ID` / `MUSECAT_LOGIN_CLIENT_SECRET` |
| パートナー OAuth Client ID / Secret | 初期化スクリプト | Musecat の Direction B credential: `PARTNER_OAUTH_CLIENT_ID` / `PARTNER_OAUTH_CLIENT_SECRET` |
| Musecat → サンプル joint key | 初期化スクリプト | Musecat のパートナー発行 Joint キー: `MUSECAT_TO_PARTNER_KEY` |
| サンプル → Musecat partner key | Musecat、発行時に表示 | `.env`: `PARTNER_TO_MUSECAT_KEY` |

`<origin>` はサンプルの公開 HTTPS origin です。

| 用途 | エンドポイント |
| --- | --- |
| OIDC: サンプルが受け取るログイン callback | `<origin>/oidc/callback` |
| Direction A: サンプルが受け取る callback | `<origin>/oauth/musecat/callback` |
| Direction B: Musecat が受け取る callback | `https://preview.musecat.app/api/user/connections/callback/<PARTNER_ID>` |
| サンプル OAuth | `/oauth/authorize`, `/oauth/token`, `/oauth/userinfo`, `/oauth/revoke` |
| 記録 | `<origin>/api/records/chunithm` |
| Joint base | `<origin>/api/joint` |
| Musecat から開始する際のパートナー入口 | `<origin>/connect/musecat/start` |
| 共同同意画面 | `https://preview.musecat.app/ja/connect/<PARTNER_ID>` (`/kr/`, `/en/` も対応) |

環境変数を変更した後は再作成します。

```sh
docker compose up -d --build --force-recreate
```

再起動時も `DATA_KEY` と `SESSION_SECRET` を維持してください。暗号化キーを失うと保存済みトークンと outbox を読めなくなります。新しい連携を開始する前に現在の連携を解除します。

## 2.1. 独立した Musecat でログイン（OIDC）

1. `python3 scripts/init-env.py` を再実行し、既存の値を維持して不足設定を追加します。`MUSECAT_LOGIN_CLIENT_ID` の既定値は `PARTNER_ID + "_login"` で、ID 長の制限に合わせて先頭部分を短縮します。既存 A/B/Joint アプリと認証情報は変更しません。
2. `/onboarding.json?flow=login` から開発者センターに **別アプリ**を登録します。アプリ ID を `MUSECAT_LOGIN_CLIENT_ID` に合わせ、A と `direction_a.login_enabled: true` を有効にし、正確な `<PARTNER_ORIGIN>/oidc/callback` を登録します。このテンプレートに B・Joint は含まれません。連絡先を実際の情報に変更し、開発登録を保存します。一般公開時に本番審査を申請します。
3. 登録後、そのログインアプリの Client Secret を発行し、`.env` の `MUSECAT_LOGIN_CLIENT_SECRET` に設定します。`docker compose up -d --build --force-recreate` で再作成してください。既存 A/B/Joint アプリのシークレットを流用しません。
4. 正確な公開 HTTPS origin のホームで **Musecat でログイン**を選択します。デモログインは不要です。Musecat でログインし `openid profile arcade:read` に同意すると、検証済み ID に基づくローカルセッションを作成します。既存デモセッションは置き換えますが、保存済み A/B/Joint grant の統合・解除は行いません。
5. ログイン済みホームの近隣施設参照（`POST /oidc/nearby`）を実行します。ソウル中心・半径 5 km 固定の読み取り要求です。端末位置を取得せず、施設の全件一覧を公開しません。このログインでは `account:access` API コンソールやデモ記録操作の権限は得られません。
6. **ログアウト**（`POST /logout`）でローカルアクセスを直ちに終了し、worker が暗号化された永続 outbox でトークン失効を再試行します。Musecat 全体のログアウトや Alice の独立した A/B/Joint grant の解除ではありません。送信完了まで worker を稼働してください。

コールバックでは PKCE S256・セッションに結び付けた state・nonce を使用します。設定済み issuer の JWKS で RS256 ID token の `kid`・署名・issuer・audience・発行時刻・有効期限・nonce を検証し、UserInfo の `sub` も一致する必要があります。ローカル ID は issuer と `sub` のハッシュで、表示名やメールによる `alice`/`bob` への自動統合は行いません。トークンはサーバーに暗号化して保存します。ログインは最大 10 分でトークン期限を超えません。自動 refresh はないため、期限切れ後は再ログインしてください。[実装](partner/oidc.py)・[PyJWT 検証 API](https://pyjwt.readthedocs.io/en/stable/api.html)を参照してください。

### エラー別の復旧

ブラウザー画面では翻訳された原因・次の操作と、従来のエラーコード・HTTP 状態を表示します。`invalid_origin` は正確な HTTPS origin、設定・クライアントエラーは対象アプリと認証情報、state・nonce・トークン検証エラーは新しいログイン、同意拒否は利用者の選択による再試行、回数制限は待機時間を案内します。コールバックや認可コードを再利用しないでください。接続障害時は issuer と到達性を確認して新しいフローを開始します。プロトコル/API は HTML を要求されても JSON を維持し、ブラウザー経路でも `?format=json` で診断できます。既知の OAuth エラーコードと安全な `Retry-After` のみを中継し、トークンや上流の応答本文は公開しません。[復旧処理](partner/recovery.py)を参照してください。

これは実装された手順の説明です。Preview 上の実際の OIDC コールバック成功はデプロイ後に別途記録します。既存の A/B/Joint テスト結果は OIDC の実測結果を保証しません。

## 3. 実際の連携テスト

Musecat の開発用アカウントを使います。2つのデモアカウントは同じパスワードを共有するため、承認されたテスト参加者だけに知らせてください。

1. サンプルにログイン → **通常の OAuth 連携のみ** → Musecat で同意 → プロフィール取得とトークン更新後の取得。
2. 解除後、worker の通知送信を待ち、Musecat 設定でも権限が解除されたことを確認。
3. **ワンクリック双方向連携** → 両アカウントと権限を確認 → 一度同意 → 完了を確認。
4. Musecat の外部連携設定で記録を取得。サンプルは `musecat-records/v1` を返します。
5. サンプル側で非公開にすると Musecat が `records_private` として隠すことを確認。公開に戻した後も再取得は1分に1回までです。
6. Musecat 側の「プロフィールに公開」も有効な場合だけ、匿名プロフィールに記録が表示されることを確認。
7. **デモ access token を失効** → 1分待つ → Musecat で再取得 → 自動 refresh による復旧を確認。
8. サンプルで両側を解除し、Musecat の権限と外部記録連携が両方解除されることを確認。
9. Musecat 設定から双方向連携を開始 → サンプルにログイン → 共同同意 → 完了後 Musecat 設定に戻る。
10. Musecat の共同連携解除を実行し、サンプルでも解除を確認して、新しい世代で再連携。

通常の外部アカウント削除と共同連携解除は異なります。双方向解除の確認には共同連携の操作を使います。通知待ちでもローカルアクセスは直ちに停止し、worker が SQLite outbox から再送します。

検証範囲は [Preview 実測結果](docs/preview-test-results.md) を参照してください。

## 構成と検証

| ファイル | 役割 |
| --- | --- |
| `partner/oauth.py` | パートナー OAuth サーバーと架空の記録 API |
| `partner/client.py` | Musecat OAuth client、トークン交換・更新 |
| `partner/joint.py` | intent 取得、原子的・冪等な receipt、双方向解除の受信 |
| `partner/storage.py` | Fernet 暗号化 SQLite ledger |
| `partner/worker.py` | 永続解除キュー、指数バックオフ、期限切れデータの整理 |
| `partner/oidc.py` | 独立した OIDC ログイン・検証済み ID/セッション・近隣参照・ログアウト失効 |
| `partner/recovery.py` | 多言語ブラウザー復旧・プロトコル JSON エラー維持 |
| `partner/web.py` | デモログイン、公開設定、登録フォーム、トークン失効ツール |
| `partner/i18n.py` | 英語・韓国語・日本語の画面翻訳 |

ローカルテストは Python 3.10 以上、Docker は Python 3.13 を使います。

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -v
docker compose config --quiet
```

テストは PKCE、code・refresh の再利用拒否、scope 分離、非公開記録、不正 callback、CSRF とブラウザー Origin、不正 bearer、receipt の冪等性・原子性、世代分離、セッション変更、outbox 再起動、言語選択を対象とします。CI でもテスト、Compose 検証、Docker ビルドを実行します。

## 実装範囲

- OAuth client は1つ、デモユーザーは2人です。新規登録、メール収集、実際のゲームデータはありません。
- 秘密値は環境変数に置きます。保存するトークン・verifier・receipt 応答は暗号化し、token/intent/code の検索キーは SHA-256 です。暗号化キーと DB を一緒に公開しないでください。
- 有効期間: intent 5分、code 90秒、access token 10分、refresh family 30日。使用済み refresh token の再利用で grant を失効させます。
- Joint 要求には専用 bearer と UUIDv4 の `X-Request-Id` が必要です。同じ要求の結果を10分間保持します。
- Musecat 起点の `completion_uri` は、登録された Web origin の対象言語の連携設定ページに限定します。
- outbox は再起動後も残り、24時間以上再送します。間隔は5秒から最大5分まで増加し、最後の試行から1年間保持します。リモート送信より先にローカルアクセスを停止します。
- HTTP access log は無効です。OAuth callback や intent URL をログ・解析ツールに収集しないでください。
- Joint 受信キーを更新する場合、旧キーを `MUSECAT_TO_PARTNER_PREVIOUS_KEY` に、24時間後の Unix 秒を `PREVIOUS_KEY_EXPIRES_AT` に設定し、現在のキーを変更します。Musecat のパートナー発行キーも更新し、猶予期間後に旧キー設定を空にします。

正式な仕様は上記 Musecat 連携文書を参照してください。依存パッケージ情報: [Flask](https://pypi.org/project/Flask/)、[cryptography](https://pypi.org/project/cryptography/)。

## CHUNITHM 表示用の記録項目

架空の応答には `rating`、`rating_max`、`over_power`、`played_chart_count`、`full_combo_count`、`all_justice_count`、`last_played_at`、`last_synced_at` を含めます。`rank_distribution` セクションは `rank` 列（型 `rank`）と `count` 列（型 `integer`）を提供します。Musecat はこれらの任意キーをレーティング・達成率・ランクの UI に変換できます。`played_chart_count` はプレイ済みの異なる譜面数で、プレイ回数ではありません。不明な値は0で埋めず省略します。通信仕様は引き続き `musecat-records/v1` であり、別の同期 API は作りません。出典には架空のデータであることを明示します。

## 開発者 API の全サンプル

デモログイン後、`/api-examples` の **開発者 API サンプル** を開きます。公式 Developer OpenAPI の **92パス・104操作** と、文書化された全リクエスト形式を掲載します。パラメーター・必要スコープ・編集可能な要求フィールド・生成した応答例・元の応答仕様・環境変数のプレースホルダーを使う curl コマンドを確認できます。スナップショットに認証情報やテストアカウントのデータは含みません。

アカウント API は、現在の暗号化された連携とトークン更新処理を使ってサーバーから呼び出します。ブラウザーには応答だけを返し、access/refresh token は渡しません。エラーの HTTP ステータスと本文も表示し、ファイル送信では仕様の multipart フィールドを使います。変更要求は HTTP メソッドを入力して確認した場合だけ実行し、変更 API 全体を自動実行しません。

OAuth・Musecat セッション用の9操作は参照例です。認可・同意には通常のブラウザーフロー、client 認証にはサーバー認証情報、承認管理には Musecat セッションが必要です。実際の A/B/共同連携は `partner/client.py`、`partner/oauth.py`、`partner/joint.py` に実装しています。OIDC は別途有効にしたアプリが必要で、`account:access` トークンの権限を暗黙に広げません。

**Musecat プロフィールを取得** は既存のアカウント API を組み合わせ、完全なプロフィール（ゲーム・お気に入り・国・SNS・レベル・管理するゲームセンターなどの返却フィールド）、パスポート集計、スタンプの最初のページ、アクティビティ、貢献履歴の最初のページを取得します。続きのページやフィルターは API 画面から実行できます。一般の第三者に公開された情報だけを取得し、公開する架空の記録にはコピーしません。フォームに `format=json` を加えると統合 JSON 応答を取得できます。

```sh
python examples/list_examples.py
python examples/list_examples.py --operation 'GET /developer/v1/account/user/me'
# 確認用の出力です。ファイル全体を一括実行しないでください。
python examples/list_examples.py --all > /tmp/musecat-api-examples.sh
```

`partner/developer-openapi.json` は Backend Core `80568ba0cba2758a8f539207476d2b9e5fd93918` の公式仕様スナップショットで、`/api-examples/openapi.json` でも公開します。デプロイ先の仕様で更新するには以下を実行します。YAML 変換は開発作業で、実行環境の追加依存ではありません。

```sh
.venv/bin/pip install -r requirements-dev.txt
curl --fail --silent --show-error https://db-dev.musecat.app/developer/openapi.yaml -o /tmp/musecat-developer-openapi.yaml
.venv/bin/python scripts/update-api-schema.py /tmp/musecat-developer-openapi.yaml
.venv/bin/python -m unittest discover -v
```

テストでは全操作・形式の網羅、固定 origin への送信、サーバー側のトークン管理、変更確認、HTTP エラー表示、プロフィール集約、取得中の解除を検証します。Musecat の既存検証・役割・公開範囲・GPS 条件・レート制限は引き続き適用されます。

[開発者 API 検証結果](docs/developer-api-test-results.md)

外部アプリのプロフィール取得は一般の第三者と同じ公開設定に従います。非公開のお気に入り・ゲームは除外し、国の表示設定も尊重します。非公開パスポートは取得できず、概要公開では訪問日を除外します。全店舗一覧 API は外部に提供せず、個別取得と周辺検索は利用できます。

解決済みのオンボーディング課題と残る検証は [韓国語のレビュー](docs/onboarding-review.ko.md)に整理しています。

ゲーム・提供元ごとの元データはアダプターで共通形式に変換します。指標の意味や専用画面まで自動統一するものではありません。[アダプター契約と制約](docs/record-adapters.md)と架空の SDVX 変換例を参照してください。
