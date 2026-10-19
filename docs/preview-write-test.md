# Preview account-action integration verification

Verified on 2026-10-20 (Australia/Sydney), using the local Docker Compose sample through its HTTPS tunnel and the Preview backend `https://db-dev.musecat.app`. All writes used the existing delegated `account:access` grant; no authentication tokens or role overrides were created.

The development SQLite database was backed up before provisioning a unique synthetic game series, Before/After versions, two public test arcades, a private negative-test arcade, and a seven-day campaign. No real arcade or real game version was used. The campaign expires at 2026-10-26 16:56 UTC.

| Action through `/account-actions` | Actual result |
| --- | --- |
| Edit synthetic arcade directions | HTTP 200; new basic revision returned and read back |
| Submit synthetic minor cabinet fault | HTTP 200; flag persisted and read back |
| Campaign participation without verified visit | HTTP 403; verified visit required |
| Visit with invalid coordinates (0, 0) | HTTP 400; invalid visit location or accuracy |
| Visit at the synthetic fixture coordinates | HTTP 200; verified visit persisted |
| Submit campaign result `updated` after visit | HTTP 200; cabinet changed from Before to After and verified participation read back |
| Read private test arcade through the delegated API | HTTP 404; no arcade data returned |

Normal domain rewards were applied in the development database: +2 XP for editing, +5 for the report, +5 for the verified visit, +1 for campaign participation. The untouched hands-on arcade is reserved for manual testing. Tests deliberately do not bypass location checks or alter user roles. Fixture coordinates are only for synthetic fixtures, never for actual venues.

The sample test suite passes all 50 tests, including CSRF/connection requirements, fixed issuer routing, stable cabinet IDs, typed mutation payloads, concurrency revision forwarding, and upstream errors without automatic mutation retries. README instructions and the UI are available in English, Korean, and Japanese.
