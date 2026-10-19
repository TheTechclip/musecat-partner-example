# Developer API example verification

Verified on 2026-10-20 against `https://db-dev.musecat.app` and Musecat Preview.

- The deployed `/developer/openapi.yaml` operation set matches the bundled snapshot: **106/106 operations, 94 paths**.
- Every operation and documented request content type renders: **114 operation/content-type variants**.
- **21 sample tests pass**, covering the original OAuth/joint flows plus complete catalog coverage, server-side bearer use, explicit mutation confirmation, multipart uploads, non-2xx responses, all three UI languages, full-profile composition and disconnect-during-read handling.
- The actual connected demo session successfully reads `/developer/v1/me`, `/developer/v1/account/user/me`, passport aggregates, passport stamps, activity and contribution history. Games, favorites and countries are returned by the existing account profile contract.
- Browser execution of `GET /developer/v1/account/user/me` through the API console returns HTTP 200 and includes games, favorites and countries. Access and refresh tokens remain server-side.
- The existing CHUNITHM branch presentation is deployed to Preview and displays the public synthetic record envelope: rating/peak, OVER POWER, FC/AJ and rank distribution, with source attribution.
- Generic execution is available for 97 resource/public-metadata operations. Nine OAuth/first-party-session operations have curl/reference examples and retain their distinct authentication flows; the console does not substitute the account token for confidential-client or first-party session credentials.

Live testing here is read-only. Changing APIs are covered by generated examples and mocked request tests; they were not automatically exercised against the connected user's real data. Domain permissions, validity checks, location requirements and rate limits remain enforced by Musecat.

No account responses, credentials, tokens or database files are included in this report.
