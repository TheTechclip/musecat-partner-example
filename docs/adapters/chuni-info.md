# CHUNITHM Info → Musecat

This guide connects a real [CHUNITHM Info](https://chuni.info/developers/docs) account to Musecat Preview. It is separate from the sample's synthetic CHUNITHM records. The upstream contract below is based on the CHUNITHM Info developer documentation supplied on 2026-10-20; obtain account consent and request only enabled scopes.

## Register Musecat at CHUNITHM Info

Use your existing **Musecat** app in CHUNITHM Info's developer portal. You do not need to create another app with the same purpose.

| Setting | Value |
| --- | --- |
| Redirect URI | `https://preview.musecat.app/api/user/connections/callback/chuniinfo` |
| Scopes | `profile rating stats scores` |
| Client ID | The ID issued by CHUNITHM Info for your Musecat app |
| Client Secret | The secret issued by CHUNITHM Info; enter it only in Musecat's protected server credential settings |

In CHUNITHM Info development mode, only its app's team members can authorize. Add the person testing the connection to that team. Public use needs CHUNITHM Info's own production approval.

The callback is an authentication return address, not a records endpoint. Do not paste a client secret into a URL, this repository, a browser script, or an issue.

## Configure the provider in Musecat

Register a provider with ID `chuniinfo`, enable the direction that supplies game records to Musecat (B), and select the `chunithm` service. Use these upstream values:

| Provider setting | Value |
| --- | --- |
| Issuer / origin | `https://chuni.info` |
| Authorization URL | `https://chuni.info/oauth2/authorize` |
| Token URL | `https://chuni.info/api/v1/oauth2/token` |
| User information URL | `https://chuni.info/api/v1/oauth2/@me` |
| Records URL | `https://chuni.info/api/v1/oauth2/@me` |
| Revoke URL | `https://chuni.info/api/v1/oauth2/token/revoke` |
| Identity scope in the registration form | `profile` |
| Service scope in the registration form | `rating` |
| Effective scopes requested by the pinned native adapter | `profile rating stats scores` |
| OAuth client authentication | HTTP Basic (`client_secret_basic`) |

These values require Musecat's dedicated CHUNITHM Info native adapter. The upstream `@me` response is not a `musecat-records/v1` envelope: do not claim that CHUNITHM Info has a `/musecat-records` endpoint or use these URLs for an arbitrary generic provider. Native conversion must be enabled only for the fixed trusted CHUNITHM Info configuration.

The native adapter requests all four official scopes for the CHUNITHM service; do not put a space-separated scope list into the form’s single service-scope field.

The adapter uses the top-level `id` as the stable account subject. It converts the authorized nested `profile`, `rating`, `stats`, and `scores` objects into the [CHUNITHM mapping](chunithm.md). Missing or unconsented data must remain absent; it must not become a zero score or a fabricated recent play. `scores.best30` is a best-record list, not a recent-play history.

After saving the provider and protected credentials, connect from Musecat's **Settings → External account connections**, consent at CHUNITHM Info, then inspect the fetched records. Publication also depends on Musecat's app environment and profile visibility settings: development app records are not anonymously published. An ordinary third-party developer does not need to install Musecat or know its internal storage model.

## Token and webhook behavior

CHUNITHM Info documents authorization code flow with optional PKCE S256, single-use codes valid for five minutes, access tokens valid for 24 hours, and refresh tokens valid for 90 days. Refresh rotates the token pair; replaying an old refresh token revokes the user's grant. The adapter must persist the replacement pair atomically and avoid competing refresh requests. Revoke uses `POST /api/v1/oauth2/token/revoke`, HTTP Basic client authentication and a form `token` value.

CHUNITHM Info documents webhook events `user.synced`, `grant.revoked`, and `ping`. Verify `X-Chuni-Signature` as `sha256=HMAC_SHA256(webhook_secret, timestamp + "." + raw_body)`, using `X-Chuni-Timestamp` and rejecting timestamps older than five minutes. Verify the expected app and subject before changing a connection; handle retries idempotently. `user.synced` can trigger a refetch and `grant.revoked` can invalidate the matching connection. It retries failures after 10 and 60 seconds.

Do not configure an invented Musecat webhook address: enable webhooks only after a deployed, signature-verifying receiver and its secret are available. Token revocation and signed webhooks are different protocols from Musecat Joint receipts/revocations.

## Request to CHUNITHM Info: recent plays

The supplied API documentation exposes profile, rating, aggregate statistics and best 30. `last_play_at` and the webhook's `new_plays` count do not provide individual play history. Ask CHUNITHM Info for an authorized recent-plays endpoint or a documented extension of `@me` with:

- A dedicated scope (or a clearly documented existing scope), user-selected export rules, and omission of unconsented data.
- A stable play ID and real RFC3339 `played_at` including timezone for each play, newest first. Sync time must not substitute for play time.
- Song ID/title (artist optional), chart ID/difficulty, and level/mode/version/region where available. IDs must be stable and source-specific.
- Actual score, score rank, clear/FC/AJ/AJC status and available judgement counts; mark optional unavailable fields rather than inventing values.
- At least the latest 50 authorized plays, or documented cursor pagination, ordering, retention window and rate limits. Document corrections/deletions and how clients deduplicate updates.
- Sync/export/privacy change notifications so a cached history can be refreshed or invalidated promptly. A notification count alone is insufficient.

Musecat already supports at most 50 entries in `recent_plays.plays` with song/chart/time and optional typed performance fields. The native adapter can map the upstream extension when its real schema is agreed. Until then, the profile must not present best 30 as recent plays.

## Request to CHUNITHM Info: one-consent bilateral connection

Ordinary OAuth enables Musecat to read CHUNITHM Info data. One-consent bilateral connection additionally needs CHUNITHM Info to register its client in Musecat and implement the **`musecat-joint/v1`** contract. It cannot be enabled by changing scopes alone.

The sample's working implementation is [partner/joint.py](../../partner/joint.py); use the current Musecat integration specification for authoritative validation rules. Its concrete endpoint layout is:

| Declaration / endpoint | Purpose |
| --- | --- |
| `connect_start_url` → `/connect/musecat/start` | Browser entry, validates correlation ID and permitted return/completion URLs, creates a short-lived session-bound intent |
| `joint_url` → `/api/joint` | Base URL for server calls, declares `musecat-joint/v1` |
| `POST /api/joint/intents/lookup` | Resolves an opaque intent to verified subject, requested services, correlation ID, PKCE challenge, redirect URI and expiry |
| `POST /api/joint/receipts` | Atomically consumes the intent and returns a short-lived partner authorization code after validating Musecat's receipt |
| `POST /api/joint/revocations` | Applies a bilateral disconnect scoped to `pair_id` and connection `generation` |

These paths are the sample's layout, not existing CHUNITHM Info endpoints. Both servers must authenticate server calls with separate directional bearer keys, use `X-Request-Id` UUIDs with idempotent retries, bind intent/code/subject/session/PKCE, reject expired or replayed intents/codes, and keep receipts atomic. A delayed revocation for an older generation must not disconnect a newer connection. Use a persistent retry outbox for bilateral disconnects, and show completion only after both directions are verified.

CHUNITHM Info would also exchange the Musecat code at Musecat's token endpoint and confirm joint status with `GET /partner/v1/joint/{correlation_id}`. Its current standard `grant.revoked` webhook does not by itself implement this shared pair/generation protocol.

Suggested request to send their team:

> 뮤즈캣에서 OAuth로 프로필·레이팅·통계·베스트 30을 읽는 연동을 준비 중입니다. 최근 플레이는 건수 대신 곡·채보·실제 플레이 시각·점수·성과와 안정적인 플레이 ID가 포함된 최신순 이력 API가 필요합니다(최신 50건 또는 커서 페이지네이션, 동의 스코프·전송 항목 선택·변경 알림 포함). 원클릭 양방향 연결은 별도로 `musecat-joint/v1`의 intent 조회·receipt·세대별 연결 해제와 양쪽 서버 인증을 지원할 수 있는지 협의하고 싶습니다. 기존 OAuth API만으로 최근 플레이나 공동 연결이 지원된다고 가정하지 않겠습니다.
