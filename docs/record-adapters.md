# Game record adapter contract

This additive `musecat-records/v1` contract separates common transport, game vocabulary and provider-specific extensions. Existing metric/table-only envelopes remain valid. `service` identifies the game and the connection identifies its provider. `game_schema` identifies optional stable meanings, such as `musecat-game/chunithm/v1`; publisher APIs are not assumed.

## Game mappings and research

| Game | Schema | Mapping and sources | Synthetic fixture |
| --- | --- | --- | --- |
| maimai | `musecat-game/maimai/v1` | [maimai](adapters/maimai.md) | [JSON](../examples/records-maimai.json) |
| CHUNITHM | `musecat-game/chunithm/v1` | [CHUNITHM](adapters/chunithm.md) | [JSON](../examples/records-chunithm.json) |
| SOUND VOLTEX | `musecat-game/sdvx/v1` | [SOUND VOLTEX](adapters/sdvx.md) | [JSON](../examples/records-sdvx.json) |
| beatmania IIDX | `musecat-game/iidx/v1` | [IIDX](adapters/iidx.md) | [JSON](../examples/records-iidx.json) |
| NOSTALGIA | `musecat-game/nostalgia/v1` | [NOSTALGIA / NosLog](adapters/nostalgia.md) | [JSON](../examples/records-nostalgia.json) |

한국어: 공통 규격·게임별 의미·제공자 확장을 구분합니다. 최근 플레이와 전송 항목 제외를 지원하며, 위 게임별 문서에 필드와 조사 출처가 있습니다. 예제는 모두 가상 데이터이고 실제 전적 사이트의 API 구현을 대신하지 않습니다.

日本語: 共通形式・ゲーム別の意味・プロバイダー拡張を分離します。最近のプレーと共有項目の除外に対応し、上記のゲーム別文書に項目と調査元を記載しています。すべて架空データで、実サイトの API 実装を代替しません。

For a real provider using its own OAuth JSON rather than this envelope, see [CHUNITHM Info native adapter setup and feature requests](adapters/chuni-info.md).

## Common envelope

Required: `spec`, `service`, authenticated `sub`, `visibility`, `updated_at`, source attribution, `fields` and `sections`. `sub` must equal the partner OAuth subject; Musecat removes it before storage/profile output. All partner links must be HTTPS. Labels require English and should include Korean/Japanese. Unknown values may be null; absence never means zero. Existing bounds remain 256 KiB, 24 summary fields, four tables, 50 rows/table and eight columns. Generic `percent` is 0–100; maimai's above-100 achievement uses `decimal` with a percentage label.

Optional `recent_plays` contains `plays` (at most 50), optional `total` and HTTPS `more_url`. Each play has RFC3339 `played_at`, `song: {title, id?, artist?}`, `chart: {difficulty, id?, level?, mode?}`, optional stable play `id` and typed `fields` (at most 16). Sort newest first. Do not invent timestamps from sync time or claim a partial history is all-time. `total` counts the authorized history window only. Provider IDs must be namespaced; song titles do not establish cross-provider equivalence.

Additional statistics use namespaced keys such as `my_provider.timing_deviation`, an explicit type and localized label/unit. No arbitrary HTML, script or server-defined executable UI is accepted. CHUNITHM retains its rich dashboard; all valid additional metrics, tables and recent plays have a generic fallback. A new rich game view can consume its versioned vocabulary later. Do not silently change key meaning or convert unlike games' score systems.

## User-selected export and missing data

The provider must apply both the user's export choices and its visibility policy before constructing the response. Musecat must not fetch omitted data through another endpoint. `selection` is an optional array of `{key,status}` where status is `denied`, `no_data` or `unsupported`. Supported paths are `player`, `fields`, `sections`, `recent_plays`, `fields.KEY` and `sections.KEY`.

- A denied/unavailable group has no data. Omit `player` and `recent_plays` entirely; keep fields/sections as empty arrays if their whole group is unavailable.
- A missing named metric/table must be absent from its array; do not attach contradictory values.
- When the provider does not supply a reason, simply omit the optional data. Do not guess that the user denied it.
- When one component of a play is withheld, omit that optional metric. If song/chart/time cannot be shared, withhold the entire recent-play group; this version has no per-play selection paths.
- An empty authorized history may use `plays: []`; that differs from a withheld group.

The sample's authenticated CSRF-protected `/records/selection` lets Alice/Bob withhold groups separately per game; `/record-examples/<game>` always returns public synthetic fixtures, not a user's selected export.

## Immediate cache invalidation

After export/privacy changes, send `POST /partner/v1/records/invalidate` with a Musecat-issued server bearer key and JSON `{ "sub": "partner-subject", "service": "nostalgia" }`. Issue a B-capable app's key with `POST /developer/apps/{id}/records-key`. Store it as `PARTNER_TO_MUSECAT_KEY`; B-only apps do not need an A client secret. For an app also using Joint, the inbound key/rotation is shared; rotating it affects both integrations.

A valid request returns 204 even when no matching connection exists. It invalidates only the authenticated app/provider and subject/service cache; an in-flight older fetch cannot restore the invalidated payload. Public reads use no-store and cannot serve the invalidated data; owner refresh/background fetch obtains the reduced envelope. Musecat publication and partner public visibility must both allow display. Provider privacy cannot be overridden by a Musecat owner checkbox.

The sample queues durable invalidation work and retries delivery with backoff. It rejects selection changes for active grants if no server key is configured. Network failure still means a delivery delay: do not promise instantaneous remote deletion before successful invalidation. Previously downloaded data or screenshots cannot be recalled. The notification must be implemented by real providers; the ordinary 24-hour refresh interval alone is insufficient for prompt privacy changes.

## Development, production and local callbacks

A validated registration starts in development mode immediately, without operator review. Only its owner and up to ten explicitly configured test users can authorize or use it. Manage testers with `PUT /developer/apps/{id}/testers` and `{ "usernames": ["tester_name"] }`; the owner is implicit. Removal also blocks subsequent token use. Other users do not discover development providers, and development records are not published to anonymous profile visitors.

A/OIDC callbacks may use exact HTTP loopback URLs in development: `http://localhost:8088/oauth/musecat/callback` or `/oidc/callback`, including registered IP loopback equivalents. Redirect matching remains exact; arbitrary HTTP hosts and lookalike domains are not allowed. The sample supports `PARTNER_ORIGIN=http://localhost:8088` or `http://127.0.0.1:8088` for local A/OIDC and uses non-Secure cookies only for that local HTTP origin. Public deployments continue using Secure cookies.

The remote Preview backend cannot fetch a developer PC's localhost. B records and Joint require a reachable public HTTPS provider when testing against Preview; a fixed development deployment is an alternative to a temporary tunnel. Do not relax remote SSRF checks or register internal server addresses as partner endpoints.

For general-user production use, save public HTTPS callbacks and request review with `POST /developer/apps/{id}/submit`. Production submission does not interrupt development testing. Operators approve/reject the production request; rejection preserves the development app. An approved production app's changes stay staged until approved, preserving the running configuration. Existing deployed approved apps are backfilled as production so their existing user connections remain valid.

A/OIDC still need their issued client secret, B needs partner OAuth credentials, and Joint needs both directions and its keys. User consent, scopes and administrative suspension apply in both modes. Use separate sample apps for isolated experiments.
