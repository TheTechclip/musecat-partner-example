# NOSTALGIA / ノスタルジア adapter v1

`service: "nostalgia"` · `game_schema: "musecat-game/nostalgia/v1"` · OAuth scope `nostalgia:read`.

This is Musecat's mapping contract, not an official publisher API or a claim that a real provider is connected. Reviewed 2026-10-20. All linked fixtures are synthetic. Publisher rules vary by version/region; retain that context in source labels or custom typed fields, and send only values actually supplied and authorized by the source.

한국어: 이 문서는 뮤즈캣 전적 매핑 규격입니다. 예제는 가상 데이터이며, 실제 제공자 연결이나 공식 API를 의미하지 않습니다. 플레이 시각과 곡·채보를 보존하고 비공개 항목은 전송하지 않습니다.

日本語: Musecat 向けの記録マッピング規格です。例は架空データであり、実プロバイダー接続や公式 API を意味しません。日時・楽曲・譜面を維持し、非公開項目は送信しません。

## Chart identity

chart.mode must distinguish basic and recital. Difficulty remains source Normal/Hard/Expert/Real identity; Real level is not converted to Expert difficulty. Source song/chart IDs are provider-specific. IDs must be namespaced by source; a matching title alone is not sufficient to join records. Keep release/region in provider metadata or labeled custom fields when it changes interpretation.

## Summary fields

| Key | Type | Meaning |
| --- | --- | --- |
| `grade` | `decimal` | Player Grade from source. |
| `rating` | `decimal` | Provider-defined rating; label its origin/version and do not imply an official universal formula. |

## Recent-play fields

Use `recent_plays.plays` in newest-first RFC3339 order. Each row contains `song`, `chart`, `played_at` and the following optional typed `fields`; this list defines stable meanings, not a requirement to manufacture missing values.

| Key | Type | Meaning |
| --- | --- | --- |
| `score` | `integer` | Basic-mode source score. |
| `recital_score` | `decimal` | Recital-mode source score, separate from basic score. |
| `grd` | `decimal` | Source per-chart Grd, optional; do not confuse with total player Grade. |
| `clear_lamp` | `string` | Source completion, optional. |

Additional metrics use `provider_name.metric` keys and clear localized labels. Never change a standard key's meaning; introduce a new versioned game schema for incompatible meanings. Consumers without a dedicated game screen display the same fields through the generic renderer.

## Example and selection

[Complete JSON](../../examples/records-nostalgia.json) · runtime `/record-examples/nostalgia` · authenticated `/api/records/nostalgia`.

[Common selection, privacy and cache invalidation rules](../record-adapters.md) apply. Withhold an entire recent-play list using `selection: [{"key":"recent_plays","status":"denied"}]` and omit `recent_plays`; do not replace withheld records with empty fictional scores. Individual unavailable metrics may use explicit paths supported by the common contract. An absent optional field alone carries no inferred denial reason.

## Research sources

- [KONAMI Grade and certifications](https://p.eagate.573.jp/game/nostalgia/op3/howto/entrance.html)
- [KONAMI basic and recital modes](https://p.eagate.573.jp/game/eacnostalgia/op3/info/howto.html)
- [KONAMI competition separates scoring modes](https://p.eagate.573.jp/game/kac/kac9th/nostalgia/index.html)
- [NosLog sync coverage and recent history](https://noslog.app/en/bookmarklet)
- [NosLog user visibility controls](https://noslog.app/en/privacy)

NosLog documents visibility groups and partial recent-history sync. Its public pages do not establish a Musecat OAuth endpoint or user-selected export API. A real NosLog adapter must obtain that provider contract and apply both its export choices and visibility controls; never scrape private settings or fabricate all-time history from a recent window.

Recent-play artwork uses the optional HTTPS `song.image_url` field. Send the actual song cover URL alongside the title, artist, chart, performance and `played_at` time. Omit unavailable artwork; the UI supplies a fallback. See the [common record contract](../record-adapters.md).
