# Developer API and game adapter verification

Verified on 2026-10-20 against **https://preview.musecat.app** and **https://db-dev.musecat.app**, using the runnable local Docker example. All game records in these tests are synthetic; no real NosLog/CHUNITHM Info account integration is implied.

## Deployed implementation

- Core `3f75331593d4`, Full `f0066e1`, Preview `18a9fca092a9`.
- Full's guarded `1792030011_partner_publication` migration preserves previously active approved registrations as production; unapproved legacy apps remain development. Existing Alice A/B/Joint grants remained usable after migration.
- A consistent development database backup passed SQLite integrity verification before rollout.
- Core and Full full suites passed. Web **2703 tests** passed, plus final focused route/UI checks, typecheck, lint/source conventions and i18n. Sample **44 tests** passed; all five JSON fixtures passed the actual Core `ParseEnvelope`.

## Real Preview end-to-end verification

A separate empty-volume provider and dedicated test apps were used. All of the following completed against the deployed servers, not only mocks:

1. B-only app registration activated development immediately; no A callback/secret or operator approval was required. Partner OAuth credentials and an independent records invalidation key were configured.
2. Anonymous/non-tester provider discovery excluded the app. Adding a named tester enabled discovery; removal blocked it again. The owner remained eligible.
3. Actual Preview BFF start → sample consent → PKCE code exchange → Preview callback completed. Musecat fetched and cached **maimai, CHUNITHM, SOUND VOLTEX, IIDX and NOSTALGIA**, including each game's recent song/chart/performance. The authenticated partner subject was stripped from returned payloads.
4. Withholding NOSTALGIA recent plays removed the entire history object. Real authenticated cache invalidation and an immediate owner read returned the reduced envelope with `selection.status: denied`. Other authorized data remained.
5. A development record stayed absent from anonymous profile output even when its owner enabled publication.
6. Production submission, operator rejection preserving development, resubmission and approval succeeded. Reconnecting the production provider and explicitly publishing CHUNITHM made its record visible publicly. Disconnect removed the connection; the temporary provider was then deactivated.
7. A dedicated development OIDC app accepted an exact **HTTP localhost callback** and rejected production submission with that callback. A local HTTP sample completed real Preview consent → localhost callback → RS256/JWKS/issuer/audience/nonce validation → local session → nearby arcade API → logout and token revocation. Scopes were exactly `openid profile arcade:read`.
8. The existing connected Musecat profile returned a public absolute avatar `picture`; an image HEAD request returned 200. The sample permits that configured issuer in its image CSP and displays the URL safely.
9. Browser inspection of the deployed `/kr/p/eric/records/chunithm` tab confirmed the existing rich dashboard and a newly fetched recent-play card with song, chart, timestamp, score and clear lamp.

Both temporary test apps were suspended after verification. Their isolated tunnel/container/volume and secondary credentials were removed. The primary demo and existing user's connections were retained. User-approved two-minute nonrefreshable test authentication stayed inside protected server files; those files and consistent copied DBs were removed. Accounts, passwords and roles were not changed.

## Privacy and API regression checks

The retained Alice connection was checked after rollout using read-only requests:

- `GET`/`HEAD /developer/v1/arcades`: **404**.
- `GET`/`HEAD /developer/v1/account/arcades`: **403**.
- Connected profile favorites, games, countries and visit projections matched ordinary third-party reads.
- Passport aggregates/stamps matched ordinary public responses. Private/summary/full matrices and removal races are covered by disposable backend fixtures, without changing the real user's settings.
- The developer contract and sample exclude both bulk arcade-list aliases.

The API example catalog retains **104 operations / 92 paths / 112 operation-content variants**: 95 generic resource/metadata operations and nine OAuth/session reference operations. Mutating examples require explicit confirmation and were not batch-executed against the connected user's real data.

## Developer experience and limits

[Localhost and actual Preview setup](local-development.md) includes A/OIDC without local HTTPS, plus a one-command optional tunnel for B/Joint. The tunnel command was run against the isolated synthetic provider; it preserved credentials and generated the HTTPS origin automatically. A fixed reachable deployment is also supported. Remote Preview cannot directly call a developer PC's localhost; local unit/schema tests alone are not represented as successful integration.

[Game mappings and research sources](record-adapters.md) define the five optional game vocabularies, recent-play contract, selected-field omission and cache invalidation. They preserve source units and version/mode distinctions; they do not implement arbitrary publisher APIs, calculate undocumented rating formulas or claim cross-provider chart-ID equivalence. A real provider must apply its own user's export/privacy choices and deliver invalidations. Notification delivery can be delayed by network failure; previously downloaded copies cannot be recalled.

No account response bodies, tokens, database files or client secrets are published in this report.
