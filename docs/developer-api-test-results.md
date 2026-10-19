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

## Independent one-way flow verification

- All **25 sample tests pass**, including independent A completion/disconnection with no Joint key or reverse grant, independent B consent/records/revocation without a Musecat API secret/link, and three distinct registration templates.
- On the running HTTPS tunnel, an isolated Bob browser session used live Musecat metadata and reached the A authorization redirect with `account:access` and S256. It did not approve a new Musecat grant or complete a new A connection against Preview.
- Over real HTTP against the running sample, a Bob-only B grant completed sample consent, PKCE code exchange, synthetic records retrieval and revocation. This exercised the sample endpoints as the registered Musecat client; it did not create a new B-only connection in Musecat's UI.
- All three `/onboarding.json?flow=a|b|joint` responses have the expected declarations. Korean browser inspection confirmed separate A/B/Joint cards and current grant status. The existing Alice bilateral demonstration was retained.
- Background-free developer onboarding findings and remaining platform constraints are documented in [the review](onboarding-review.ko.md).
