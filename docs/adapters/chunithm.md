# CHUNITHM adapter v1

`service: "chunithm"` · `game_schema: "musecat-game/chunithm/v1"` · OAuth scope `chunithm:read`.

This is Musecat's mapping contract, not an official publisher API or a claim that a real provider is connected. Reviewed 2026-10-20. All linked fixtures are synthetic. Publisher rules vary by version/region; retain that context in source labels or custom typed fields, and send only values actually supplied and authorized by the source.

한국어: 이 문서는 뮤즈캣 전적 매핑 규격입니다. 예제는 가상 데이터이며, 실제 제공자 연결이나 공식 API를 의미하지 않습니다. 플레이 시각과 곡·채보를 보존하고 비공개 항목은 전송하지 않습니다.

日本語: Musecat 向けの記録マッピング規格です。例は架空データであり、実プロバイダー接続や公式 API を意味しません。日時・楽曲・譜面を維持し、非公開項目は送信しません。

## Chart identity

Preserve difficulty and mode, including special/course/world-end chart identities. Optional existing rich dashboard vocabulary remains backward compatible. IDs must be namespaced by source; a matching title alone is not sufficient to join records. Keep release/region in provider metadata or labeled custom fields when it changes interpretation.

## Summary fields

| Key | Type | Meaning |
| --- | --- | --- |
| `rating` | `decimal` | Current source player rating. |
| `rating_max` | `decimal` | Historical highest source rating, not chart rating. |
| `over_power` | `decimal` | Source OVER POWER. |
| `played_chart_count` | `integer` | Number of played charts, not sessions. |
| `full_combo_count` | `integer` | Number of FC charts. |
| `all_justice_count` | `integer` | Number of AJ charts. |

## Recent-play fields

Use `recent_plays.plays` in newest-first RFC3339 order. Each row contains `song`, `chart`, `played_at` and the following optional typed `fields`; this list defines stable meanings, not a requirement to manufacture missing values.

| Key | Type | Meaning |
| --- | --- | --- |
| `score` | `integer` | Source score (ordinary gameplay); do not clamp to another game’s scale. |
| `clear_lamp` | `string` | Source completion such as FC/AJ/AJC; preserve rank separately. |
| `rank` | `rank` | Source score rank. |
| `justice_critical` | `integer` | Optional source judgement count. |

Additional metrics use `provider_name.metric` keys and clear localized labels. Never change a standard key's meaning; introduce a new versioned game schema for incompatible meanings. Consumers without a dedicated game screen display the same fields through the generic renderer.

## Example and selection

[Complete JSON](../../examples/records-chunithm.json) · runtime `/record-examples/chunithm` · authenticated `/api/records/chunithm`.

[Common selection, privacy and cache invalidation rules](../record-adapters.md) apply. Withhold an entire recent-play list using `selection: [{"key":"recent_plays","status":"denied"}]` and omit `recent_plays`; do not replace withheld records with empty fictional scores. Individual unavailable metrics may use explicit paths supported by the common contract. An absent optional field alone carries no inferred denial reason.

## Research sources

- [SEGA international gameplay/achievement information](https://chunithm.sega.com/play/others.html)
- [SEGA course scoring rules](https://maimai.sega.jp/kop3rd/chunithm/)
