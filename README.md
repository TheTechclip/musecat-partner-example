# Musecat Partner Example

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md)
Validated registration is immediately usable in development by its owner and up to ten named testers. Production access for general users requires operator approval. Configure each enabled direction’s credentials and obtain user consent. The B-only template declares all five games; the existing Joint sample keeps CHUNITHM to preserve its original manifest. [Game mappings, recent plays, selection and invalidation](docs/record-adapters.md).


A runnable **development and testing sample** for Musecat Preview. Python + Flask + SQLite, Docker Compose, optional Caddy HTTPS, MIT license. Two demo accounts (`alice`, `bob`) use synthetic CHUNITHM records. This is a learning example, not a complete OAuth/OIDC provider.

[Localhost and one-command real Preview setup](docs/local-development.md)

## Supported flows

- **OIDC login:** sign in with Musecat, validate the ID token and UserInfo, create a separate local session, and query nearby arcades.
- **A:** sample → Musecat consent → profile lookup → refresh-token rotation → disconnect.
- **B:** Musecat → sample consent → synthetic records → public/private visibility → refresh recovery.
- **Joint:** start from either service and grant both directions through one Musecat consent screen. Completion requires both exchanges and confirmation of Musecat's state; incomplete connections remain visibly partial.
- Disconnect from either side, reconnect, isolate revocations by connection generation, and retry notifications through a persistent outbox.

| Development service | URL |
| --- | --- |
| API / OAuth issuer | `https://db-dev.musecat.app` |
| Developer Center | <https://preview.musecat.app/en/developer> |
| Authoritative integration specification | <https://preview.musecat.app/api/developer/spec> |

This example uses the delegation scope `account:access` and the documented `/developer/v1/account/*` APIs as well as `/developer/v1/me`. The separate OIDC sign-in flow uses `openid profile arcade:read` with its own registered app and credentials; it does not grant `account:access`.

## Choose a connection before configuring keys

“Direction” below describes **data access**, not which website is opened first.

| Goal | Start here | Registration JSON | Musecat-issued secret needed by sample |
| --- | --- | --- | --- |
| Sign in with Musecat | Home → **Sign in with Musecat** | `/onboarding.json?flow=login` | Separate `MUSECAT_LOGIN_CLIENT_SECRET`; ID in `MUSECAT_LOGIN_CLIENT_ID` |
| Sample reads Musecat profile/APIs (A only) | Demo sign-in → **Connect Musecat data only** | `/onboarding.json?flow=a` | `MUSECAT_CLIENT_SECRET` |
| Musecat reads sample CHUNITHM records (B only) | Musecat settings → ordinary external account connection → this sample → select CHUNITHM → connect | `/onboarding.json?flow=b` | None; configure the generated partner OAuth client ID/secret in Musecat |
| Both directions with managed shared consent | **One-click bilateral connection** in either service | `/onboarding.json?flow=joint` (default) | `MUSECAT_CLIENT_SECRET` and `PARTNER_TO_MUSECAT_KEY`; also exchange the generated partner OAuth credentials and `MUSECAT_TO_PARTNER_KEY` |

All modes still use the generated local session/encryption/demo secrets. Generated keys for unused modes may remain in `.env`; you do not need to exchange them. Validated registration and exact callback matching still apply; operator approval is not required for owner/tester development use. B-only registration is supported: `/onboarding.json?flow=b` omits `direction_a` entirely. In Developer Center, disable A and declare B; no A callback, Musecat-issued A secret, or Joint keys are required. Do not register the three templates as successive updates merely to switch demo buttons: an already registered full app can exercise A, B and Joint independently, and registered configuration changes can invalidate grants.

For A, success means the sample displays a **one-way Musecat API connection** and can read the public profile. `account:access` also authorizes documented general-user mutations; this is not a read-only scope or OIDC sign-in. For B, success means Musecat shows the connected account and can fetch synthetic records. Enable **profile sharing** separately, then verify the public profile. Sample-side grant counts show issued/exchanged permission, not Musecat's cached or currently displayed profile. Manage B-only disconnection in Musecat settings. A-only disconnection does not revoke an independent B grant. Two independent grants do not automatically become a managed Joint pair.

Use `bob` to try another mode without disturbing Alice's demonstration. A different sample account does not bypass Musecat's account-binding rules: do not approve the same Musecat account into a conflicting demo binding. Disconnect deliberately before changing bindings. Standalone “Sign in with Musecat” is implemented separately below. Use a separate login app instead of changing Alice’s registered A/B/Joint app, because saving configuration changes can invalidate its existing grants.

### When first connection fails

| Symptom | Check / next action |
| --- | --- |
| Missing/disabled A action | Obtain the registered app's Client Secret and set `MUSECAT_CLIENT_SECRET`; no Joint key exchange is needed |
| Missing provider in Musecat | Confirm saved Direction B declaration and partner OAuth credentials in Developer Center |
| `invalid_origin` | Open the exact HTTPS `PARTNER_ORIGIN`; after a tunnel change update origin, registered URLs and recreate containers |
| `invalid_client` or callback rejection | Check credential issuer/direction and exact registered callback, including locale-independent B callback |
| `invalid_grant`, invalid state, expired flow | Start a fresh flow in the same browser session; do not reuse a callback/code; reconnect if refresh was consumed |
| `records_private` or profile shows nothing | Check sample privacy, Musecat service's profile-sharing switch, cache status and refresh limit |
| HTTP 429 | Respect the endpoint's retry window; do not automatically rerun every API example |


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

Open the **HTTPS tunnel URL in your browser**: session cookies are Secure. A changed tunnel URL changes the issuer and callbacks; update the app URLs, save the updated registration, and reconnect. Quick Tunnels are temporary; use a named tunnel or a fixed domain for a stable address.

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
2. Register an app in Developer Center using the selected flow JSON. Enter general information and only the directions present in that template. Replace `contact_email` with your contact address.
3. Save the validated registration. It activates immediately without operator approval.
4. Exchange the credentials below. Keep values server-side; do not publish them in GitHub issues, screenshots, or frontend JavaScript.

| Credential | Issuer | Destination |
| --- | --- | --- |
| Client ID | Musecat, matching `PARTNER_ID` | Sample `.env`: `PARTNER_ID` |
| Client Secret | Musecat, shown only when issued/rotated | `.env`: `MUSECAT_CLIENT_SECRET` |
| Separate OIDC Client ID / Secret | Separate login app in Musecat | `.env`: `MUSECAT_LOGIN_CLIENT_ID` / `MUSECAT_LOGIN_CLIENT_SECRET` |
| Partner OAuth Client ID / Secret | Initialization script | Musecat Direction B credentials: `PARTNER_OAUTH_CLIENT_ID` / `PARTNER_OAUTH_CLIENT_SECRET` |
| Musecat → sample joint key | Initialization script | Musecat's partner-issued Joint key: `MUSECAT_TO_PARTNER_KEY` |
| Sample → Musecat partner key | Musecat, shown when issued | `.env`: `PARTNER_TO_MUSECAT_KEY` |

`<origin>` below means the sample's public HTTPS origin.

| Purpose | Endpoint |
| --- | --- |
| OIDC login callback received by sample | `<origin>/oidc/callback` |
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

## 2.1. Standalone Sign in with Musecat (OIDC)

1. Run `python3 scripts/init-env.py` again to add missing settings while preserving existing values. The default `MUSECAT_LOGIN_CLIENT_ID` is `PARTNER_ID + "_login"` (the base is truncated to fit the partner ID limit). Keep the existing A/B/Joint app and credentials unchanged.
2. Open `/onboarding.json?flow=login` and register **a separate app** in Developer Center. Its partner ID must equal `MUSECAT_LOGIN_CLIENT_ID`; enable A and `direction_a.login_enabled: true`, and register exactly `<PARTNER_ORIGIN>/oidc/callback`. This template does not declare B or Joint. Replace the example contact details and save the validated registration; no operator review is required for development use.
3. After registration, issue that app's Client Secret, set `MUSECAT_LOGIN_CLIENT_SECRET` in `.env`, and recreate the containers: `docker compose up -d --build --force-recreate`. Never put the A/B/Joint app's secret into this setting.
4. Open the exact public HTTPS origin, then choose **Sign in with Musecat** on the home page. Demo login is not required. Complete Musecat login and consent for `openid profile arcade:read`; the callback returns to a local session derived from the verified identity. An existing local demo session is replaced, but its stored A/B/Joint grants are not merged or disconnected.
5. Use the signed-in home page's nearby-arcade action (`POST /oidc/nearby`). It makes a read-only request centered on Seoul with a fixed 5 km radius; it does not request your device's location or expose an arcade-directory export. This login does not enable the `account:access` API console or demo-account record tools.
6. Choose **Sign out** (`POST /logout`). Local access ends immediately and the worker retries token revocation through the encrypted persistent outbox. This does not sign you out of Musecat globally or disconnect Alice's separate A/B/Joint grants. Keep the worker running to deliver pending revocations.

The callback uses PKCE S256, session-bound state and nonce, and RS256 ID-token verification against the configured issuer's JWKS (`kid`, issuer, audience, issued-at, expiry and nonce). It also requires the UserInfo `sub` to match. Local identity is a hash of issuer plus `sub`, never a nickname/email match or an automatic merge into `alice`/`bob`. Tokens stay encrypted on the server. The local login lasts at most 10 minutes (and no longer than token expiry); there is no silent refresh, so sign in again after expiry. See [the implementation](partner/oidc.py) and [PyJWT's validation API](https://pyjwt.readthedocs.io/en/stable/api.html).

### Error recovery

Interactive browser routes display a translated cause and next action with the stable error code and HTTP status. `invalid_origin` points to the exact HTTPS origin, configuration/client errors to the correct app and credentials, state/nonce/token errors to a fresh login, denied consent to a deliberate retry, and rate limits to the retry delay. Do not replay a callback or authorization code. Unavailable services require checking issuer/reachability before restarting the flow. Protocol/API endpoints remain JSON, including when a client asks for HTML; `?format=json` also preserves JSON for browser-route diagnostics. Known upstream OAuth codes and safe `Retry-After` values can be relayed without exposing tokens or remote response bodies. See [recovery handling](partner/recovery.py).

These instructions describe the implemented flow. A successful live OIDC callback on Preview must be recorded separately after deployment; existing A/B/Joint test results do not prove OIDC login works.

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
| `partner/oidc.py` | Separate OIDC login, verified identity/session, nearby read, logout revocation |
| `partner/recovery.py` | Translated browser recovery with unchanged protocol JSON errors |
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

## Complete Developer API examples

After demo sign-in, open **Developer API examples** at `/api-examples`. The bundled official Developer OpenAPI contains **104 operations across 92 paths**, including all documented request content types. Each entry includes parameters, required scopes, editable request fields, generated response examples, the original response contract, and a curl command with environment-variable placeholders. The snapshot contains no application credentials or test-account data.

Account API calls execute server-side using the current encrypted connection, including refresh rotation. The browser receives the API result, never the access/refresh token. The console displays non-2xx status and error bodies. File upload operations support their documented multipart fields. Changing requests require typing that request's HTTP method before execution; the sample never automatically runs the mutation catalog.

The nine OAuth/first-party-session operations are reference examples rather than generic token-proxy actions: authorization and consent need their normal browser flow, client authentication needs confidential credentials, and authorization management needs a Musecat session. Existing `partner/client.py`, `partner/oauth.py`, and `partner/joint.py` implement the actual A/B/joint flows. OIDC scopes require a separately enabled application; an `account:access` token is not silently upgraded.

**Read Musecat profile** now composes the existing account APIs for the full profile (games, favorites, countries, SNS, level, owned arcades and other returned fields), passport aggregates, the first stamp page, activity, and the first contribution page. Subsequent pages and filters can be exercised in the API console. Connected apps receive the ordinary third-party profile projection: private favorites and games are omitted, country visibility is respected, and private passports are unavailable. Summary passports omit visit dates. Authorized writes retain their documented behavior. Bulk arcade listing is excluded from the external API; individual detail and nearby search remain available. Append form field `format=json` for the combined JSON response.

```sh
python examples/list_examples.py
python examples/list_examples.py --operation 'GET /developer/v1/account/user/me'
# Print all examples for review; do not execute the resulting file as a batch.
python examples/list_examples.py --all > /tmp/musecat-api-examples.sh
```

`partner/developer-openapi.json` is the official contract snapshot from Backend Core revision `80568ba0cba2758a8f539207476d2b9e5fd93918`. It is served at `/api-examples/openapi.json`. To update it from the deployment (YAML conversion is a development task, not a runtime dependency):

```sh
.venv/bin/pip install -r requirements-dev.txt
curl --fail --silent --show-error https://db-dev.musecat.app/developer/openapi.yaml -o /tmp/musecat-developer-openapi.yaml
.venv/bin/python scripts/update-api-schema.py /tmp/musecat-developer-openapi.yaml
.venv/bin/python -m unittest discover -v
```

Tests verify complete operation/media coverage, fixed-origin request routing, server-side token handling, write confirmation, HTTP error display, full-profile composition, and disconnect races. Standard domain validation, roles, visibility, GPS requirements and rate limits still apply on Musecat.

[Developer API verification](docs/developer-api-test-results.md)

A source-based review of resolved onboarding gaps and remaining validation work is available in [Korean](docs/onboarding-review.ko.md).

Different game/provider payloads are normalized by adapters into the common envelope; game-specific meanings and rich screens remain separate. See [record adapter contracts and limits](docs/record-adapters.md) and the synthetic SDVX example.
