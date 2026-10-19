# SOUND VOLTEX adapter v1

`service: "sdvx"` · `game_schema: "musecat-game/sdvx/v1"` · OAuth scope `sdvx:read`.

This is Musecat's mapping contract, not an official publisher API or a claim that a real provider is connected. Reviewed 2026-10-20. All linked fixtures are synthetic. Publisher rules vary by version/region; retain that context in source labels or custom typed fields, and send only values actually supplied and authorized by the source.

한국어: 이 문서는 뮤즈캣 전적 매핑 규격입니다. 예제는 가상 데이터이며, 실제 제공자 연결이나 공식 API를 의미하지 않습니다. 플레이 시각과 곡·채보를 보존하고 비공개 항목은 전송하지 않습니다.

日本語: Musecat 向けの記録マッピング規格です。例は架空データであり、実プロバイダー接続や公式 API を意味しません。日時・楽曲・譜面を維持し、非公開項目は送信しません。

## Chart identity

Keep NOVICE/ADVANCED/EXHAUST and source additional difficulty identifiers. Preserve mode because battle scoring can differ from ordinary records. IDs must be namespaced by source; a matching title alone is not sufficient to join records. Keep release/region in provider metadata or labeled custom fields when it changes interpretation.

## Summary fields

| Key | Type | Meaning |
| --- | --- | --- |
| `volforce` | `decimal` | Source-provided VOLFORCE, optional. Do not calculate using an assumed version formula. |
| `skill_level` | `string` | Source skill analyzer rank, optional. |

## Recent-play fields

Use `recent_plays.plays` in newest-first RFC3339 order. Each row contains `song`, `chart`, `played_at` and the following optional typed `fields`; this list defines stable meanings, not a requirement to manufacture missing values.

| Key | Type | Meaning |
| --- | --- | --- |
| `score` | `integer` | Source score, separate from grade and clear lamp. |
| `clear_lamp` | `string` | Source completion; for example COMPLETE/EXCESSIVE COMPLETE/ULTIMATE CHAIN/PERFECT ULTIMATE CHAIN. Do not infer from score alone. |
| `grade` | `rank` | Source score grade. |
| `critical` | `integer` | Optional judgement count. |
| `near` | `integer` | Optional judgement count. |
| `error` | `integer` | Optional judgement count. |

Additional metrics use `provider_name.metric` keys and clear localized labels. Never change a standard key's meaning; introduce a new versioned game schema for incompatible meanings. Consumers without a dedicated game screen display the same fields through the generic renderer.

## Example and selection

[Complete JSON](../../examples/records-sdvx.json) · runtime `/record-examples/sdvx` · authenticated `/api/records/sdvx`.

[Common selection, privacy and cache invalidation rules](../record-adapters.md) apply. Withhold an entire recent-play list using `selection: [{"key":"recent_plays","status":"denied"}]` and omit `recent_plays`; do not replace withheld records with empty fictional scores. Individual unavailable metrics may use explicit paths supported by the common contract. An absent optional field alone carries no inferred denial reason.

## Research sources

- [KONAMI current gameplay/results guide](https://p.eagate.573.jp/game/sdvx/vii/howto/play.html)
- [KONAMI judgement/result guide (legacy version)](https://p.eagate.573.jp/game/sdvx/sv/p/booth_howtoplay/qa.html)
- [KONAMI mode-specific scoring example](https://p.eagate.573.jp/game/sdvx/vii/howto/megamix_battle.html)
