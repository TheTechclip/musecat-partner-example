# Musecat Partner Example

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md)

A runnable **development and testing sample** for Musecat Preview. Python + Flask + SQLite, Docker Compose, optional Caddy HTTPS, MIT license. Two demo accounts (`alice`, `bob`) use synthetic CHUNITHM records. This is a learning example, not a complete OAuth/OIDC provider.

## Supported flows

- **A:** sample → Musecat consent → profile lookup → refresh-token rotation → disconnect.
- **B:** Musecat → sample consent → synthetic records → public/private visibility → refresh recovery.
- **Joint:** start from either service and grant both directions through one Musecat consent screen. Completion requires both exchanges and confirmation of Musecat's state; incomplete connections remain visibly partial.
- Disconnect from either side, reconnect, isolate revocations by connection generation, and retry notifications through a persistent outbox.

| Development service | URL |
| --- | --- |
| API / OAuth issuer | `https://db-dev.musecat.app` |
| Developer Center | <https://preview.musecat.app/en/developer> |
| Authoritative integration specification | <https://preview.musecat.app/api/developer/spec> |

This example uses the delegation scope `account:access` and calls `/developer/v1/me`. It does not demonstrate the separate sign-in scopes `openid profile arcade:read`.

## 1. Run locally

Requires Docker Compose, Python 3 for initialization, and a public HTTPS origin: Musecat must call this server directly, so a localhost-only URL cannot be registered.

```sh
git clone https://github.com/TheTechclip/musecat-partner-example.git
cd musecat-partner-example
python3 scripts/init-env.py
```

The script generates a random demo password, session secret, encryption key, and partner-issued keys in `.env`, preserving existing values. `.env` is excluded from Git and the Docker build context.

### Option A: local app with a temporary HTTPS tunnel

In a separate terminal, start a [Cloudflare Quick Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/):

```sh
cloudflared tunnel --url http://127.0.0.1:8088 --no-autoupdate
```

Set `PARTNER_ORIGIN` in `.env` to the resulting `https://...trycloudflare.com` origin (no trailing slash), and `PARTNER_HOST` to its hostname only.

```sh
docker compose up -d --build
docker compose ps
```

Open the **HTTPS tunnel URL in your browser**: session cookies are Secure. A changed tunnel URL changes the issuer and callbacks; update the app URLs, obtain approval again, and reconnect. Quick Tunnels are temporary; use a named tunnel or a fixed domain for a stable address.

### Option B: fixed domain with Caddy

Point DNS to your server and expose ports 80/443. Set `PARTNER_ORIGIN=https://your-domain.example` and `PARTNER_HOST=your-domain.example` in `.env`.

```sh
docker compose --profile https up -d --build
```

An existing HTTPS proxy can route to `app:8080` without Caddy.

### Interface language

The sample supports English, Korean, and Japanese. Choose a language at the top and press **Apply**. The browser language is the initial default (English fallback); your selection persists through sign-in and sign-out. Login, consent, connection controls, and test tools are translated. Protocol identifiers and JSON error codes remain unchanged. Partner-initiated joint consent uses the selected language; Musecat-initiated flows retain Musecat's requested language.

## 2. Register in Musecat Developer Center

The sample starts without Musecat-issued keys. Sign in as `alice` or `bob` using `DEMO_PASSWORD` from `.env`.

1. Open **App registration JSON** (`/onboarding.json`), populated with the actual URLs and generated `PARTNER_ID`.
2. Register an app in Developer Center and enter its general information, Direction A, Direction B, and Joint settings from that JSON. Replace `contact_email` with your contact address.
3. Request Musecat operator approval. The sample does not bypass approval.
4. Exchange the credentials below. Keep values server-side; do not publish them in GitHub issues, screenshots, or frontend JavaScript.

| Credential | Issuer | Destination |
| --- | --- | --- |
| Client ID | Musecat, matching `PARTNER_ID` | Sample `.env`: `PARTNER_ID` |
| Client Secret | Musecat, shown only when issued/rotated | `.env`: `MUSECAT_CLIENT_SECRET` |
| Partner OAuth Client ID / Secret | Initialization script | Musecat Direction B credentials: `PARTNER_OAUTH_CLIENT_ID` / `PARTNER_OAUTH_CLIENT_SECRET` |
| Musecat → sample joint key | Initialization script | Musecat's partner-issued Joint key: `MUSECAT_TO_PARTNER_KEY` |
| Sample → Musecat partner key | Musecat, shown when issued | `.env`: `PARTNER_TO_MUSECAT_KEY` |

`<origin>` below means the sample's public HTTPS origin.

| Purpose | Endpoint |
| --- | --- |
| Direction A callback received by sample | `<origin>/oauth/musecat/callback` |
| Direction B callback received by Musecat | `https://preview.musecat.app/api/user/connections/callback/<PARTNER_ID>` |
| Sample OAuth | `/oauth/authorize`, `/oauth/token`, `/oauth/userinfo`, `/oauth/revoke` |
| Records | `<origin>/api/records/chunithm` |
| Joint base | `<origin>/api/joint` |
| Partner entry point when starting in Musecat | `<origin>/connect/musecat/start` |
| Joint consent | `https://preview.musecat.app/en/connect/<PARTNER_ID>` (also `/kr/`, `/ja/`) |

After changing environment variables:

```sh
docker compose up -d --build --force-recreate
```

Preserve `DATA_KEY` and `SESSION_SECRET` across restarts. Losing the encryption key makes stored tokens and outbox entries unreadable. Disconnect an existing connection before starting another.

## 3. Live integration checklist

Use a Musecat development account. Both demo accounts share the demo password; distribute it only to authorized testers.

1. Sign in → **Ordinary OAuth only** → Musecat consent → read profile and refresh the token before reading again.
2. Disconnect; let the worker deliver the notification and confirm the grant is revoked in Musecat settings.
3. Choose **One-click bilateral connection**, verify both accounts and permissions, consent once, and confirm completion.
4. Read records in Musecat's external connection settings. The sample returns `musecat-records/v1`.
5. Make sample records private; Musecat should hide them with `records_private`. After making them public, respect the once-per-minute refresh limit.
6. Anonymous profiles should show records only when Musecat's **Show on profile** setting is also enabled.
7. **Expire demo access tokens**, wait one minute, then refresh records in Musecat; automatic token refresh should restore access.
8. Disconnect both sides from the sample; confirm both the Musecat grant and external record connection are revoked.
9. Start joint connection from Musecat settings → sample login → joint consent → completion → return to Musecat settings.
10. Use Musecat's joint disconnect action, verify the sample disconnects, and reconnect with a new generation.

Deleting an ordinary external connection differs from joint disconnection. Use the joint action to test bilateral revocation. Local access is blocked immediately while the worker retries remote notifications from SQLite.

See [live Preview test results](docs/preview-test-results.md) for the recorded verification scope.

## Structure and verification

| File | Responsibility |
| --- | --- |
| `partner/oauth.py` | Partner OAuth server and synthetic records API |
| `partner/client.py` | Musecat OAuth client, token exchange and refresh |
| `partner/joint.py` | Intent lookup, atomic/idempotent receipts, bilateral revocations |
| `partner/storage.py` | Fernet-encrypted SQLite ledger |
| `partner/worker.py` | Durable revocation queue, exponential backoff, expiry cleanup |
| `partner/web.py` | Demo login, privacy controls, onboarding, token-expiry tool |
| `partner/i18n.py` | English, Korean, and Japanese interface catalog |

Local Python tests require Python 3.10+; Docker uses Python 3.13.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -v
docker compose config --quiet
```

Tests cover PKCE, code/refresh replay rejection, scope isolation, private records, invalid callbacks, CSRF and browser Origin behavior, invalid bearer keys, receipt idempotency/atomicity, connection generations, session changes, outbox restart, and language selection. CI runs tests, Compose validation, and a Docker build.

## Implementation boundaries

- One partner OAuth client and two demo users; no registration, email collection, or real game data.
- Raw secrets live in environment variables. Stored tokens, verifiers, and receipt responses are encrypted; token/intent/code lookup keys use SHA-256. Never publish the encryption key alongside the database.
- Intent lifetime: 5 minutes; code: 90 seconds; access token: 10 minutes; refresh family: 30 days. Refresh-token replay revokes the grant.
- Joint requests require a separate bearer key and UUIDv4 `X-Request-Id`; identical request results are retained for 10 minutes.
- Musecat-initiated `completion_uri` is restricted to the registered web origin's localized connection settings page.
- The durable outbox retries for at least 24 hours, with delays from 5 seconds up to 5 minutes; jobs are retained for one year after the last attempt. Local access is blocked before remote delivery.
- HTTP access logging is disabled. Do not collect OAuth callback or intent URLs in logs or analytics.
- To rotate an inbound Joint key, put the old key in `MUSECAT_TO_PARTNER_PREVIOUS_KEY`, set `PREVIOUS_KEY_EXPIRES_AT` to the Unix timestamp 24 hours ahead, and replace the current key. Update the partner-issued key in Musecat, then clear the previous-key configuration after the grace period.

The Musecat specification above is authoritative. Dependency information: [Flask](https://pypi.org/project/Flask/), [cryptography](https://pypi.org/project/cryptography/).

## CHUNITHM presentation fields

The synthetic response includes `rating`, `rating_max`, `over_power`, `played_chart_count`, `full_combo_count`, `all_justice_count`, `last_played_at`, and `last_synced_at`. The `rank_distribution` section has a `rank` column (type `rank`) and `count` column (type `integer`). Musecat can map these optional keys to its CHUNITHM rating, achievement, and rank UI. `played_chart_count` counts distinct charts; it is not a play count. Unknown values should be omitted, not filled with zero. The transport remains `musecat-records/v1`; these keys do not create another synchronization API. The source remains explicitly synthetic.
