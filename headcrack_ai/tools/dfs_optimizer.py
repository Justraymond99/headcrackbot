from __future__ import annotations

from typing import Any

from ..models import BetLeg, MarketType
from ..plain_language import format_american_odds, format_chance, value_verdict


PROP_TYPES = {
    MarketType.PLAYER_SHOTS,
    MarketType.PLAYER_SHOTS_ON_TARGET,
    MarketType.PLAYER_GOAL,
    MarketType.PLAYER_ASSIST,
}


def build_dfs_entries(
    legs: list[BetLeg],
    min_edge: float = 0.0,
    max_picks: int = 6,
    max_same_match: int = 3,
) -> list[dict[str, Any]]:
    """Build a correlated DFS / player-prop slip ranked by model EV."""
    props = [
        leg
        for leg in legs
        if (
            leg.market.market_type in PROP_TYPES
            and leg.edge >= min_edge
            and leg.prediction.model_name != "book_baseline"
        )
    ]
    props = sorted(props, key=lambda leg: (leg.ev_per_dollar, leg.edge), reverse=True)
    best_prices: dict[tuple[str, str, str, float | None], BetLeg] = {}
    for leg in props:
        key = (
            leg.market.event_id,
            leg.market.player or "",
            leg.market.market_type.value,
            leg.market.threshold,
        )
        current = best_prices.get(key)
        if current is None or leg.decimal_odds > current.decimal_odds:
            best_prices[key] = leg
    props = list(best_prices.values())
    props.sort(key=lambda leg: (leg.ev_per_dollar, leg.edge), reverse=True)

    slip: list[dict[str, Any]] = []
    match_counts: dict[str, int] = {}

    for leg in props:
        if len(slip) >= max_picks:
            break
        event = leg.market.event_id
        if match_counts.get(event, 0) >= max_same_match:
            continue
        match_counts[event] = match_counts.get(event, 0) + 1
        slip.append(_prop_entry(leg))

    return slip


def _prop_entry(leg: BetLeg) -> dict[str, Any]:
    features = leg.prediction.features or {}
    # Prefer player-stat projections; never fall back to match-level xG.
    projection = features.get("expected_shots")
    if projection is None:
        projection = features.get("expected_assists") or features.get("expected_goals")
    return {
        "pick": leg.market.label,
        "player": leg.market.player,
        "book": leg.market.sportsbook,
        "odds": format_american_odds(leg.market.odds.value),
        "model": format_chance(leg.model_probability),
        "edge": f"{leg.edge:+.1%}",
        "ev": f"${leg.ev_per_dollar:+.2f}/$1",
        "verdict": value_verdict(leg.edge),
        "projection": f"{projection:.1f}" if isinstance(projection, (int, float)) else "—",
        "leg": leg,
    }


def format_dfs_slip(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "No prop edges fit your filters. Loosen min edge or fetch more player props."
    lines = ["**DFS / Prop Optimizer slip**", ""]
    for idx, entry in enumerate(entries, start=1):
        lines.append(
            f"{idx}. **{entry['pick']}** ({entry['book']}, {entry['odds']}) — "
            f"{entry['verdict']}, model {entry['model']}, EV {entry['ev']}"
        )
    lines.append("")
    lines.append("*Stack correlated props from the same match script when possible.*")
    return "\n".join(lines)
