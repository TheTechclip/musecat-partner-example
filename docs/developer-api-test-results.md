# Developer API example verification

Verified on 2026-10-20 against `https://db-dev.musecat.app` and Musecat Preview.

- The updated bundled contract contains **104 operations across 92 paths**, with **112 operation/content-type variants**. Both bulk arcade-list routes are excluded.
- **22 sample tests pass**, including catalog coverage, rejection of removed list examples, server-side bearer use, mutation confirmation, multipart uploads, non-2xx responses, all three UI languages, profile composition and disconnect-during-read handling.
- Generic execution covers 95 resource/public-metadata operations. Nine OAuth/first-party-session operations retain curl/reference examples with their distinct authentication flows.
- Core's full test suite verifies existing tokens cannot call either bulk list route (including HEAD), first-party discovery and external nearby search still work, and delegated profile reads match the public projection even for staff actors. Private passports and visit statistics return 404; summary responses omit visit dates. First-party owner access remains available.
- Backend Full's full test suite passes with the updated Core pin.
- Earlier browser testing confirmed the deployed CHUNITHM presentation renders the public synthetic record envelope. Those earlier owner-profile results do not establish the current privacy policy.

Live testing here is read-only. Changing APIs are covered by generated examples and mocked request tests; they were not automatically exercised against the connected user's real data. Domain permissions, validity checks, location requirements and rate limits remain enforced by Musecat.

No account responses, credentials, tokens or database files are included in this report.


Live verification after the development backend rollout, using the existing encrypted Alice connection (no credentials or account responses recorded):

- `GET` and `HEAD /developer/v1/arcades`: **404**.
- `GET` and `HEAD /developer/v1/account/arcades`: **403**.
- The connected account profile matches an ordinary unauthenticated third-party read for favorites, games, countries, primary country, visit statistics, warp and ownership fields.
- Passport aggregates and stamps match the ordinary public responses for the connected user's current settings (HTTP 200). The private/summary/full matrix is covered by disposable Core fixtures, without changing the real user's privacy settings.
- External nearby discovery returns HTTP 200. The deployed OpenAPI and running sample both exclude the bulk-list operations.
- The quota failure during the first build was resolved by expanding the development instance root from 64GiB to 128GiB. The development DB backup was verified before rollout. No schema migration was required.
