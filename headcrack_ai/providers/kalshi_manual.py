from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ..models import AmericanOdds, Market, MarketType, Sport, VenueType


def cents_to_american(yes_price_cents: float) -> int:
    p = yes_price_cents / 100.0
    if not 0 < p < 1:
        raise ValueError("Kalshi price cents must be between 0 and 100")
    decimal = 1.0 / p
    if decimal >= 2.0:
        return round((decimal - 1.0) * 100)
    return round(-100 / (decimal - 1.0))


def normalize_kalshi_rows(rows: list[dict[str, Any]], sport: Sport = Sport.SOCCER) -> list[Market]:
    markets: list[Market] = []
    for row in rows:
        ticker = str(row.get("ticker") or row.get("market_id"))
        yes_price = float(row.get("yes_price_cents") or row.get("yes_price") or row.get("price"))
        event_id = str(row.get("event_id") or row.get("event_ticker") or ticker)
        label = str(row.get("label") or row.get("title") or ticker)
        market_type_raw = str(row.get("market_type") or "custom")
        try:
            market_type = MarketType(market_type_raw)
        except ValueError:
            market_type = MarketType.CUSTOM
        markets.append(
            Market(
                market_id=f"kalshi:{ticker}:yes",
                sport=sport,
                event_id=event_id,
                label=f"Kalshi YES - {label}",
                market_type=market_type,
                sportsbook="kalshi",
                odds=AmericanOdds(cents_to_american(yes_price)),
                team=row.get("team") or None,
                opponent=row.get("opponent") or None,
                player=row.get("player") or None,
                threshold=float(row["threshold"]) if row.get("threshold") not in (None, "") else None,
                metadata={"source": "kalshi_manual", **row},
                venue_type=VenueType.PREDICTION_MARKET,
            )
        )
    return markets


def load_kalshi_csv(path: str | Path, sport: Sport = Sport.SOCCER) -> list[Market]:
    with Path(path).open(newline="") as f:
        return normalize_kalshi_rows(list(csv.DictReader(f)), sport=sport)
