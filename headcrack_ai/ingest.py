from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .models import AmericanOdds, BetLeg, Market, MarketType, Prediction, Sport


def _market_type(value: str) -> MarketType:
    try:
        return MarketType(value)
    except ValueError:
        return MarketType.CUSTOM


def _sport(value: str) -> Sport:
    try:
        return Sport(value)
    except ValueError:
        return Sport.SOCCER


def market_from_dict(row: dict[str, Any]) -> Market:
    return Market(
        market_id=str(row["market_id"]),
        sport=_sport(str(row.get("sport", "soccer"))),
        event_id=str(row["event_id"]),
        label=str(row["label"]),
        market_type=_market_type(str(row.get("market_type", "custom"))),
        sportsbook=str(row.get("sportsbook", "manual")),
        odds=AmericanOdds(int(row["odds"])),
        team=row.get("team") or None,
        opponent=row.get("opponent") or None,
        player=row.get("player") or None,
        threshold=float(row["threshold"]) if row.get("threshold") not in (None, "") else None,
        metadata={k: v for k, v in row.items() if k.startswith("meta_")},
    )


def leg_from_dict(row: dict[str, Any]) -> BetLeg:
    market = market_from_dict(row)
    prediction = Prediction(
        market_id=market.market_id,
        model_probability=float(row.get("model_probability", market.odds.implied_probability)),
        model_name=str(row.get("model_name", "manual")),
        confidence=float(row.get("confidence", 0.5)),
    )
    tags = tuple(
        tag.strip()
        for tag in str(row.get("tags", "")).split("|")
        if tag.strip()
    )
    return BetLeg(market=market, prediction=prediction, tags=tags)


def load_markets_json(path: str | Path) -> list[BetLeg]:
    payload = json.loads(Path(path).read_text())
    if isinstance(payload, dict):
        payload = payload.get("markets", [])
    return [leg_from_dict(row) for row in payload]


def load_markets_csv(path: str | Path) -> list[BetLeg]:
    with Path(path).open(newline="") as f:
        return [leg_from_dict(row) for row in csv.DictReader(f)]


def dump_card_json(card: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(card, indent=2, default=str))


def legs_to_rows(legs: Iterable[BetLeg]) -> list[dict[str, Any]]:
    rows = []
    for leg in legs:
        rows.append(
            {
                "market_id": leg.market.market_id,
                "label": leg.market.label,
                "sport": leg.market.sport.value,
                "event_id": leg.market.event_id,
                "market_type": leg.market.market_type.value,
                "sportsbook": leg.market.sportsbook,
                "odds": leg.market.odds.value,
                "model_probability": round(leg.model_probability, 4),
                "implied_probability": round(leg.implied_probability, 4),
                "edge": round(leg.edge, 4),
                "ev_per_dollar": round(leg.ev_per_dollar, 4),
                "team": leg.market.team,
                "player": leg.market.player,
                "tags": "|".join(leg.tags),
            }
        )
    return rows
