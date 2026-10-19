"""Synthetic adapter fixtures; never fetch or infer a real player's records."""

from flask import current_app
from .common import stamp

SERVICES = ("maimai", "chunithm", "sdvx", "iidx", "nostalgia")


def _chunithm(uid):
    return dict(
        spec="musecat-records/v1",
        service="chunithm",
        sub="sample:" + uid,
        visibility="public",
        updated_at=stamp(),
        source={
            "name": "Musecat Partner Example · synthetic data",
            "url": current_app.config["PARTNER_ORIGIN"],
        },
        fields=[
            {
                "key": "rating",
                "label": {
                    "ko": "데모 레이팅",
                    "en": "Demo rating",
                    "ja": "デモレーティング",
                },
                "type": "decimal",
                "value": 16.42,
                "precision": 2,
            },
            *[
                {
                    "key": key,
                    "label": {"en": en, "ko": ko, "ja": ja},
                    "type": kind,
                    "value": value,
                }
                for key, en, ko, ja, kind, value in [
                    (
                        "rating_max",
                        "Demo max rating",
                        "데모 최고 레이팅",
                        "デモ最高レーティング",
                        "decimal",
                        16.58,
                    ),
                    (
                        "over_power",
                        "Demo OVER POWER",
                        "데모 OVER POWER",
                        "デモ OVER POWER",
                        "decimal",
                        12345.67,
                    ),
                    (
                        "played_chart_count",
                        "Demo played charts",
                        "데모 플레이한 보면",
                        "デモプレイ譜面数",
                        "integer",
                        123,
                    ),
                    (
                        "full_combo_count",
                        "Demo FULL COMBO",
                        "데모 FULL COMBO",
                        "デモ FULL COMBO",
                        "integer",
                        80,
                    ),
                    (
                        "all_justice_count",
                        "Demo ALL JUSTICE",
                        "데모 ALL JUSTICE",
                        "デモ ALL JUSTICE",
                        "integer",
                        30,
                    ),
                    (
                        "last_played_at",
                        "Demo last played",
                        "데모 마지막 플레이",
                        "デモ最終プレイ",
                        "datetime",
                        "2026-10-19T01:00:00Z",
                    ),
                    (
                        "last_synced_at",
                        "Demo last synced",
                        "데모 마지막 동기화",
                        "デモ最終同期",
                        "datetime",
                        stamp(),
                    ),
                ]
            ],
        ],
        player={
            "name": "Demo " + uid.title(),
            "title": "Synthetic CHUNITHM records",
            "level": 85,
            "team": "Musecat Demo",
        },
        sections=[
            {
                "key": "rank_distribution",
                "label": {
                    "ko": "가상 랭크 분포",
                    "en": "Synthetic rank distribution",
                    "ja": "架空のランク分布",
                },
                "columns": [
                    {
                        "key": "rank",
                        "label": {"en": "Rank", "ko": "랭크", "ja": "ランク"},
                        "type": "rank",
                    },
                    {
                        "key": "count",
                        "label": {"en": "Charts", "ko": "보면", "ja": "譜面"},
                        "type": "integer",
                    },
                ],
                "rows": [
                    ["SSS+", 30],
                    ["SSS", 28],
                    ["SS+", 25],
                    ["SS", 20],
                    ["S+", 12],
                    ["S", 8],
                ],
            }
        ],
    )


def metric(key, label, value, kind="integer", precision=None):
    result = {
        "key": key,
        "label": {"en": label, "ko": label, "ja": label},
        "type": kind,
        "value": value,
    }
    if precision is not None:
        result["precision"] = precision
    return result


def envelope(service, uid="alice", excluded=()):
    if service not in SERVICES:
        raise ValueError("unsupported service")
    if service == "chunithm":
        result = _chunithm(uid)
        performance = [
            metric("score", "Score", 1009876),
            metric("clear_lamp", "Clear lamp", "AJ", "string"),
        ]
        difficulty, mode = "MASTER", "standard"
    else:
        summaries, performance, difficulty, mode = {
            "maimai": (
                [metric("rating", "DX rating", 15000)],
                [
                    metric("achievement", "Achievement (%)", 100.1234, "decimal", 4),
                    metric("dx_score", "DX score", 2700),
                    metric("combo", "Combo", "FC+", "string"),
                    metric("sync", "Sync", "FDX", "string"),
                ],
                "MASTER",
                "DX",
            ),
            "sdvx": (
                [metric("volforce", "VOLFORCE", 20.125, "decimal", 3)],
                [
                    metric("score", "Score", 9980000),
                    metric("clear_lamp", "Clear lamp", "EXCESSIVE COMPLETE", "string"),
                    metric("grade", "Grade", "S", "string"),
                ],
                "EXHAUST",
                "normal",
            ),
            "iidx": (
                [metric("sp_dan", "SP dan", "CHUDEN", "string")],
                [
                    metric("ex_score", "EX score", 2800),
                    metric("miss_count", "Miss count", 12),
                    metric("clear_lamp", "Clear lamp", "HARD CLEAR", "string"),
                    metric("dj_level", "DJ level", "AA", "string"),
                ],
                "ANOTHER",
                "SP",
            ),
            "nostalgia": (
                [metric("grade", "Grade", 5000.25, "decimal", 2)],
                [
                    metric("score", "Basic score", 990123),
                    metric("grd", "Chart Grd", 150.25, "decimal", 2),
                    metric("clear_lamp", "Clear lamp", "FULL COMBO", "string"),
                ],
                "EXPERT",
                "basic",
            ),
        }[service]
        result = {
            "spec": "musecat-records/v1",
            "service": service,
            "sub": "sample:" + uid,
            "visibility": "public",
            "updated_at": stamp(),
            "source": {
                "name": "Musecat Partner Example · synthetic data",
                "url": current_app.config["PARTNER_ORIGIN"],
            },
            "fields": summaries,
            "sections": [],
            "player": {"name": "Demo " + uid.title()},
        }
    result["game_schema"] = "musecat-game/" + service + "/v1"
    result["recent_plays"] = {
        "plays": [
            {
                "id": "synthetic-" + service + "-1",
                "played_at": "2026-10-19T01:00:00Z",
                "song": {
                    "id": "sample:song-1",
                    "title": "Synthetic song",
                    "artist": "Example artist",
                },
                "chart": {
                    "id": "sample:chart-1",
                    "difficulty": difficulty,
                    "mode": mode,
                },
                "fields": performance,
            }
        ],
        "total": 1,
    }
    result["selection"] = []
    for key in excluded:
        if key in ("player", "recent_plays", "fields", "sections"):
            result.pop(key, None)
            if key in ("fields", "sections"):
                result[key] = []
        elif key.startswith("fields."):
            result["fields"] = [f for f in result["fields"] if f["key"] != key[7:]]
        else:
            raise ValueError("unsupported selection")
        result["selection"].append({"key": key, "status": "denied"})
    return result
