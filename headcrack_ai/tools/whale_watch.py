from __future__ import annotations

from typing import Any

from ..persistence import SQLiteStore
from ..plain_language import format_american_odds


def detect_whale_activity(
    store: SQLiteStore,
    live_legs: list | None = None,
    min_implied_move: float = 0.02,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Large line moves from stored snapshots — proxy for sharp/whale action."""
    moves = store.line_movements(min_implied_move=min_implied_move, limit=limit)

    if live_legs:
        hot_markets = {leg.market.market_id: leg for leg in live_legs}
        for move in moves:
            leg = hot_markets.get(move["market_id"])
            if leg:
                move["model_probability"] = leg.model_probability
                move["current_edge"] = round(leg.edge, 4)

    return moves


def _implied_from_american(odds: int) -> float:
    if odds > 0:
        return 100.0 / (odds + 100.0)
    if odds < 0:
        return abs(odds) / (abs(odds) + 100.0)
    return 0.0


def format_whale_row(row: dict[str, Any]) -> dict[str, Any]:
    open_odds = int(row.get("open_odds") or 0)
    current_odds = int(row.get("current_odds") or 0)
    move = float(row.get("move") or 0)
    # Steam = implied probability rose (price shortened toward the pick).
    if open_odds and current_odds:
        delta = _implied_from_american(current_odds) - _implied_from_american(open_odds)
        if delta > 0.005:
            direction = "steam"
        elif delta < -0.005:
            direction = "fade"
        else:
            direction = "flat"
    else:
        direction = "flat"
    signal = "Sharp money in" if direction == "steam" and move >= 0.03 else direction
    return {
        "Pick": row.get("label", ""),
        "Book": row.get("sportsbook", ""),
        "Open": format_american_odds(open_odds) if open_odds else "—",
        "Now": format_american_odds(current_odds) if current_odds else "—",
        "Move": f"{move:.1%}",
        "Signal": signal,
        "Snapshots": row.get("snapshots", 0),
    }
