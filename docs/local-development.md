# Local development with the real Musecat Preview

The goal is a completed integration with **https://preview.musecat.app**, not merely a successful fixture test. You do not need to clone or install Musecat. New development apps work immediately for their owner and up to ten named testers; general-user production access needs review.

## A / OIDC: localhost, without HTTPS

1. Run `python scripts/init-env.py` and set `PARTNER_ORIGIN=http://localhost:8088` in `.env`. Keep `MUSECAT_ISSUER=https://db-dev.musecat.app` and `MUSECAT_WEB_ORIGIN=https://preview.musecat.app`.
2. Run `docker compose up -d --build` and open **http://localhost:8088**. This sample also supports `http://127.0.0.1:8088`; use one exact origin consistently.
3. Register `/onboarding.json?flow=a` or `/onboarding.json?flow=login` in Developer Center. Replace contact details. Use the exact localhost callback; for OIDC, keep a separate app and its dedicated secret.
4. Issue the app secret, configure `.env`, recreate the containers, and authorize using the Musecat account that owns the app or is in its named tester list.
5. Complete the redirect back to localhost and read the permitted API/profile data. This is a real Preview grant. Local HTTP is allowed only for development callbacks; production callbacks require HTTPS.

Secure cookies remain mandatory for public sample origins. The local HTTP exception does not permit arbitrary public HTTP hosts or weaken Preview's HTTPS/SSRF protections.

## B / Joint: let Preview reach the local provider automatically

Preview must call your OAuth/token/records/Joint endpoints. Its localhost refers to the remote server, not your PC. For these flows, either deploy the provider once at a stable public HTTPS address, or automatically expose the local sample:

```sh
python scripts/init-env.py
python scripts/dev-tunnel.py
```

Install [cloudflared](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/) and Docker Compose first. The command starts a temporary Cloudflare HTTPS endpoint, updates only the sample origin/host (preserving secrets), starts the containers and prints the sample and registration URLs. It does not print credentials, create a Musecat account, approve consent or modify your registered app automatically.

Open the printed HTTPS URL for B/Joint consent. Register its JSON in Developer Center; use `?flow=b` to declare all five synthetic games, or the existing Joint template for CHUNITHM. Enter the partner-issued OAuth credentials. Issue Musecat's records invalidation server key and configure `PARTNER_TO_MUSECAT_KEY`; Joint also needs its two server keys and A secret. Register named testers if someone other than the owner will test. Connect from Preview's external-account settings (B), or use the sample's reciprocal button (Joint).

On successful B connection, verify owner records and the recent-play list. Check a withheld group in the sample; wait for the worker's invalidation delivery and refresh in Musecat. The denied group must disappear while authorized data remains. Development-provider records are intentionally not visible to anonymous visitors. Production approval is required before public-profile publication/general-user rollout.

Keep the tunnel command running. A Quick Tunnel URL changes on restart: update the app's declaration/callbacks, restart the sample and obtain consent again. For regular use, a fixed deployment or named tunnel avoids changing registrations. Temporary HTTPS setup is automated, not a requirement to manage a certificate every development session.

## Validation levels

- `python -m unittest discover -s tests`: reproducible local sample protocol/adapter tests; does not establish a real Preview connection.
- Five [game fixtures and mappings](record-adapters.md): check field meanings and source/privacy conversion.
- Developer Center conformance: real server requests against reachable provider endpoints; missing test fixtures are `action_required`, not success.
- Actual Preview consent, callback, records refresh, withheld-data invalidation and disconnect: end-to-end verification.

한국어: 뮤즈캣 전체 설치 없이 실제 preview와 연결하는 절차입니다. A/OIDC는 localhost HTTP로 연결할 수 있습니다. B/양방향은 `python scripts/dev-tunnel.py`로 HTTPS 접근 주소와 로컬 컨테이너 시작을 자동화하거나 고정 서버를 사용하세요. 로컬 검사와 실제 연결 완료는 구분합니다. 개발 앱은 소유자와 테스트 계정만 사용할 수 있고 일반 공개에는 승인이 필요합니다.

日本語: Musecat 全体をインストールせず実際の Preview と接続します。A/OIDC は localhost HTTP を使えます。B/双方向は `python scripts/dev-tunnel.py` で HTTPS アドレスとローカルコンテナー起動を自動化するか、固定サーバーを使用します。ローカル検査と実接続完了は区別します。開発アプリは所有者とテスターのみ、本番公開には承認が必要です。
