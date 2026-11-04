# Local development with the real Musecat Preview

The goal is a completed integration with **https://external-app.musecat.app**, not merely a successful fixture test. You do not need to clone or install Musecat. New development apps work immediately for their owner and up to ten named testers; general-user production access needs review.

This preview branch and the hosted [example app](https://example-app.musecat.app) use the same isolated environment: `MUSECAT_ISSUER=https://db-pr-99.musecat.app` and `MUSECAT_WEB_ORIGIN=https://external-app.musecat.app`. Register your app in [this environment's Developer Center](https://external-app.musecat.app/en/developer) and use [its integration specification](https://external-app.musecat.app/api/developer/spec). For your own integration, run your own copy and register its generated ID and URLs, rather than registering the public example's JSON. If switching environments, change both origins to the matching backend/frontend pair, register a new app, and obtain that environment's credentials; do not reuse previous grants or keys.

Use the preview integration branch for the sample described here:

```sh
git clone --branch code/pr99-example-integration https://github.com/TheTechclip/musecat-partner-example.git
cd musecat-partner-example
```

## A / OIDC: localhost, without HTTPS

1. Run `python3 scripts/init-env.py` and set `PARTNER_ORIGIN=http://localhost:8088` in `.env`. Set `MUSECAT_ISSUER=https://db-pr-99.musecat.app` and `MUSECAT_WEB_ORIGIN=https://external-app.musecat.app`.
2. Run `docker compose up -d --build` and open **http://localhost:8088**. This sample also supports `http://127.0.0.1:8088`; use one exact origin consistently.
3. Register `/onboarding.json?flow=a` or `/onboarding.json?flow=login` in Developer Center. Replace contact details. Use the exact localhost callback; for OIDC, keep a separate app and its dedicated secret.
4. Issue the app secret, configure `.env`, recreate the containers, and authorize using the Musecat account that owns the app or is in its named tester list.
5. Complete the redirect back to localhost and read the permitted API/profile data. This is a real Preview grant. Local HTTP is allowed only for development callbacks; production callbacks require HTTPS.

Secure cookies remain mandatory for public sample origins. The local HTTP exception does not permit arbitrary public HTTP hosts or weaken Preview's HTTPS/SSRF protections.

## B / Joint: let Preview reach the local provider automatically

Preview must call your OAuth/token/records/Joint endpoints. Its localhost refers to the remote server, not your PC. For these flows, either deploy the provider once at a stable public HTTPS address, or automatically expose the local sample:

```sh
python3 scripts/init-env.py
python3 scripts/dev-tunnel.py
```

Install [cloudflared](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/) and Docker Compose first. The command starts a temporary Cloudflare HTTPS endpoint, updates only the sample origin/host (preserving secrets), starts the containers and prints the sample and registration URLs. It does not print credentials, create a Musecat account, approve consent or modify your registered app automatically.

Open the printed HTTPS URL for B/Joint consent:

1. Use that server's `/onboarding.json?flow=b` to declare all five synthetic games, or `?flow=joint` for the CHUNITHM Joint example. Copy the selected form's fields into Developer Center and replace the example contact details. The B-only form keeps the required `direction_a` object with empty `redirect_uris` and `login_enabled: false`; no A callback or A secret is needed.
2. Set Direction B's credentials in Developer Center to the sample-generated `PARTNER_OAUTH_CLIENT_ID` and `PARTNER_OAUTH_CLIENT_SECRET`.
3. Issue the **record invalidation server key** in Direction B and set the returned value as `PARTNER_TO_MUSECAT_KEY` in the sample's `.env`. B needs this key to change record visibility or selected fields after connecting. Joint uses the same key; it additionally needs the Musecat-issued `MUSECAT_CLIENT_SECRET` in `.env` and the sample-issued `MUSECAT_TO_PARTNER_KEY` in Developer Center's partner server key field. Do not issue a second independent key for Joint.
4. Recreate the containers with `docker compose up -d --build --force-recreate`. In Developer Center, add the Musecat usernames of testers other than the app owner (up to ten). A separate OIDC app has its own owner/tester access list.
5. Connect from Preview's external-account settings (B), or use the sample's reciprocal button (Joint).

On successful B connection, verify owner records and the recent-play list. Check a withheld group in the sample; wait for the worker's invalidation delivery and refresh in Musecat. The denied group must disappear while authorized data remains. Development-provider records are intentionally not visible to anonymous visitors. Production approval is required before public-profile publication/general-user rollout.

Keep the tunnel command running. A Quick Tunnel URL changes on restart: update the app's declaration/callbacks, restart the sample and obtain consent again. For regular use, a fixed deployment or named tunnel avoids changing registrations. Temporary HTTPS setup is automated, not a requirement to manage a certificate every development session.

## Validation levels

- `python3 -m unittest discover -s tests`: reproducible local sample protocol/adapter tests; does not establish a real Preview connection.
- Five [game fixtures and mappings](record-adapters.md): check field meanings and source/privacy conversion.
- Developer Center conformance: real server requests against reachable provider endpoints; missing test fixtures are `action_required`, not success.
- Actual Preview consent, callback, records refresh, withheld-data invalidation and disconnect: end-to-end verification.

한국어: 뮤즈캣 전체 설치 없이 실제 preview와 연결하는 절차입니다. A/OIDC는 localhost HTTP로 연결할 수 있습니다. B/양방향은 `python3 scripts/dev-tunnel.py`로 HTTPS 접근 주소와 로컬 컨테이너 시작을 자동화하거나 고정 서버를 사용하세요. 로컬 검사와 실제 연결 완료는 구분합니다. 개발 앱은 소유자와 테스트 계정만 사용할 수 있고 일반 공개에는 승인이 필요합니다.

日本語: Musecat 全体をインストールせず実際の Preview と接続します。A/OIDC は localhost HTTP を使えます。B/双方向は `python3 scripts/dev-tunnel.py` で HTTPS アドレスとローカルコンテナー起動を自動化するか、固定サーバーを使用します。ローカル検査と実接続完了は区別します。開発アプリは所有者とテスターのみ、本番公開には承認が必要です。

## Isolated Compose preview deployments

`compose.preview.yaml` runs the same app and outbox worker behind an existing
HTTPS proxy without publishing host ports or starting Caddy. Supply a new
private environment file to `docker compose --env-file /private/runtime.env -f
compose.preview.yaml config --quiet` before deploying. Keep the public
`PARTNER_ORIGIN` HTTPS even when the proxy's internal route uses HTTP to
`app:8080`.

Use a new application-scoped `preview-data` volume and freshly generated local
session, encryption, demo, provider OAuth and inbound Joint keys. Never attach an
existing sample volume to a different issuer or replace its encryption key. Keep
the original `.env` and running/stopped demo deployments intact.

Set `MUSECAT_ISSUER` and `MUSECAT_WEB_ORIGIN` to the matching isolated backend
and frontend. Register the new partner ID and separate OIDC login ID using the
actual test user's normal Developer Center session; do not reuse an old app's
owner, grants or keys. `MUSECAT_CLIENT_SECRET`, `MUSECAT_LOGIN_CLIENT_SECRET` and
`PARTNER_TO_MUSECAT_KEY` remain blank until that registration and key exchange.
Health and onboarding pages can be checked first; working health does not mean
A/OIDC/Joint consent has completed. Keep the worker running for revocation and
record-visibility invalidation tests.

Japanese Musecat callback/consent routes use `/jp/`; the sample UI language
remains `ja`. Exact callback and same-origin completion checks remain required.
