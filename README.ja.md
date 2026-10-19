# Musecat Partner Example

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

Musecat Preview と連携する **開発・テスト用サンプル**です。Python + Flask + SQLite、Docker Compose、任意の Caddy HTTPS 構成、MIT ライセンス。`alice` / `bob` の2つのデモアカウントと架空の CHUNITHM 記録を使用します。学習用の例であり、OAuth/OIDC プロバイダーの完全な実装ではありません。

## 確認できるフロー

- **A:** サンプル → Musecat の同意 → プロフィール取得 → refresh token のローテーション → 解除。
- **B:** Musecat → サンプルの同意 → 架空の記録取得 → 公開・非公開 → refresh による復旧。
- **Joint:** どちらから開始しても、Musecat の共同同意画面で一度同意すると両方向の権限を発行します。両側の交換と Musecat の状態確認後にのみ完了とし、不完全な接続は部分連携と表示します。
- 両側からの解除、再連携、接続世代による解除要求の分離、永続 outbox での通知再送。

| 開発環境 | URL |
| --- | --- |
| API / OAuth issuer | `https://db-dev.musecat.app` |
| 開発者センター | <https://preview.musecat.app/ja/developer> |
| 正式な連携仕様 | <https://preview.musecat.app/api/developer/spec> |

この例は権限委譲 scope `account:access` と `/developer/v1/account/*`、`/developer/v1/me` API を使用します。ログイン専用の `openid profile arcade:read` を使う例とは別です。

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

ブラウザーでも **HTTPS トンネルの URL** を開いてください。Cookie は Secure です。トンネル URL が変わると issuer と callback も変わるため、アプリの URL を変更して再承認を受け、再連携してください。Quick Tunnel は一時テスト用です。固定アドレスには named tunnel または固定ドメインを使います。

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
2. 開発者センターでアプリを登録し、JSON の基本情報・Direction A・Direction B・Joint 設定を入力します。`contact_email` を自分の連絡先に変更します。
3. Musecat 運営者に承認を申請します。サンプルで承認を迂回することはありません。
4. 以下の認証情報を交換します。値はサーバー専用です。GitHub Issue、スクリーンショット、フロントエンド JavaScript に載せないでください。

| 認証情報 | 発行元 | 設定先 |
| --- | --- | --- |
| Client ID | Musecat (`PARTNER_ID` と同じ) | サンプル `.env`: `PARTNER_ID` |
| Client Secret | Musecat、発行・再発行時のみ表示 | `.env`: `MUSECAT_CLIENT_SECRET` |
| パートナー OAuth Client ID / Secret | 初期化スクリプト | Musecat の Direction B credential: `PARTNER_OAUTH_CLIENT_ID` / `PARTNER_OAUTH_CLIENT_SECRET` |
| Musecat → サンプル joint key | 初期化スクリプト | Musecat のパートナー発行 Joint キー: `MUSECAT_TO_PARTNER_KEY` |
| サンプル → Musecat partner key | Musecat、発行時に表示 | `.env`: `PARTNER_TO_MUSECAT_KEY` |

`<origin>` はサンプルの公開 HTTPS origin です。

| 用途 | エンドポイント |
| --- | --- |
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

デモログイン後、`/api-examples` の **開発者 API サンプル** を開きます。公式 Developer OpenAPI の **94パス・106操作** と、文書化された全リクエスト形式を掲載します。パラメーター・必要スコープ・編集可能な要求フィールド・生成した応答例・元の応答仕様・環境変数のプレースホルダーを使う curl コマンドを確認できます。スナップショットに認証情報やテストアカウントのデータは含みません。

アカウント API は、現在の暗号化された連携とトークン更新処理を使ってサーバーから呼び出します。ブラウザーには応答だけを返し、access/refresh token は渡しません。エラーの HTTP ステータスと本文も表示し、ファイル送信では仕様の multipart フィールドを使います。変更要求は HTTP メソッドを入力して確認した場合だけ実行し、変更 API 全体を自動実行しません。

OAuth・Musecat セッション用の9操作は参照例です。認可・同意には通常のブラウザーフロー、client 認証にはサーバー認証情報、承認管理には Musecat セッションが必要です。実際の A/B/共同連携は `partner/client.py`、`partner/oauth.py`、`partner/joint.py` に実装しています。OIDC は別途有効にしたアプリが必要で、`account:access` トークンの権限を暗黙に広げません。

**Musecat プロフィールを取得** は既存のアカウント API を組み合わせ、完全なプロフィール（ゲーム・お気に入り・国・SNS・レベル・管理するゲームセンターなどの返却フィールド）、パスポート集計、スタンプの最初のページ、アクティビティ、貢献履歴の最初のページを取得します。続きのページやフィルターは API 画面から実行できます。所有者専用情報は認証済みデモセッションだけに表示し、公開する架空の記録にはコピーしません。フォームに `format=json` を加えると統合 JSON 応答を取得できます。

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
