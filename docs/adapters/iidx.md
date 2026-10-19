# beatmania IIDX adapter v1

`service: "iidx"` · `game_schema: "musecat-game/iidx/v1"` · OAuth scope `iidx:read`.

This is Musecat's mapping contract, not an official publisher API or a claim that a real provider is connected. Reviewed 2026-10-20. All linked fixtures are synthetic. Publisher rules vary by version/region; retain that context in source labels or custom typed fields, and send only values actually supplied and authorized by the source.

한국어: 이 문서는 뮤즈캣 전적 매핑 규격입니다. 예제는 가상 데이터이며, 실제 제공자 연결이나 공식 API를 의미하지 않습니다. 플레이 시각과 곡·채보를 보존하고 비공개 항목은 전송하지 않습니다.

日本語: Musecat 向けの記録マッピング規格です。例は架空データであり、実プロバイダー接続や公式 API を意味しません。日時・楽曲・譜面を維持し、非公開項目は送信しません。

## Chart identity

chart.mode identifies SP/DP, with difficulty separately NORMAL/HYPER/ANOTHER/LEGGENDARIA or source value. Preserve chart note count as an optional custom metric, rather than inventing a universal maximum EX score. IDs must be namespaced by source; a matching title alone is not sufficient to join records. Keep release/region in provider metadata or labeled custom fields when it changes interpretation.

## Summary fields

| Key | Type | Meaning |
| --- | --- | --- |
| `sp_dan` | `string` | Source SP certification. |
| `dp_dan` | `string` | Source DP certification; never combine the two. |

## Recent-play fields

Use `recent_plays.plays` in newest-first RFC3339 order. Each row contains `song`, `chart`, `played_at` and the following optional typed `fields`; this list defines stable meanings, not a requirement to manufacture missing values.

| Key | Type | Meaning |
| --- | --- | --- |
| `ex_score` | `integer` | EX score, distinct from other score systems. |
| `miss_count` | `integer` | Source miss count, absent when unavailable. |
| `clear_lamp` | `string` | Source NO PLAY/FAILED/ASSIST CLEAR/EASY CLEAR/CLEAR/HARD CLEAR/EX HARD CLEAR/FULL COMBO or a newer source value. |
| `dj_level` | `rank` | Source DJ level such as AA/AAA. |
| `pgreat` | `integer` | Optional perfect-great judgement count. |
| `great` | `integer` | Optional great judgement count. |

Additional metrics use `provider_name.metric` keys and clear localized labels. Never change a standard key's meaning; introduce a new versioned game schema for incompatible meanings. Consumers without a dedicated game screen display the same fields through the generic renderer.

## Example and selection

[Complete JSON](../../examples/records-iidx.json) · runtime `/record-examples/iidx` · authenticated `/api/records/iidx`.

[Common selection, privacy and cache invalidation rules](../record-adapters.md) apply. Withhold an entire recent-play list using `selection: [{"key":"recent_plays","status":"denied"}]` and omit `recent_plays`; do not replace withheld records with empty fictional scores. Individual unavailable metrics may use explicit paths supported by the common contract. An absent optional field alone carries no inferred denial reason.

## Research sources

- [KONAMI saved play data: EX score and lamps](https://p.eagate.573.jp/game/2dx/26/howto/epass/play_data.html)
- [KONAMI current result guide](https://p.eagate.573.jp/game/2dx/34/howto/play/game_start.html)
