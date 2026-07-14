from __future__ import annotations

from typing import Any

from ..models import BetLeg
from ..plain_language import describe_edge, describe_ev_per_dollar, format_american_odds, format_chance, value_verdict


def find_positive_ev(
    legs: list[BetLeg],
    min_edge: float = 0.0,
    min_ev: float = 0.0,
    limit: int = 50,
) -> list[BetLeg]:
    """Model-backed bets with positive expected value."""
    eligible = [
        leg
        for leg in legs
        if leg.edge >= min_edge and leg.ev_per_dollar >= min_ev
    ]
    return sorted(eligible, key=lambda leg: (leg.ev_per_dollar, leg.edge), reverse=True)[:limit]


def format_ev_row(leg: BetLeg) -> dict[str, Any]:
    return {
        "Pick": leg.market.label,
        "Book": leg.market.sportsbook,
        "Odds": format_american_odds(leg.market.odds.value),
        "Model": format_chance(leg.model_probability),
        "Book implied": format_chance(leg.implied_probability),
        "Edge": f"{leg.edge:+.1%}",
        "EV / $1": f"${leg.ev_per_dollar:+.2f}",
        "Verdict": value_verdict(leg.edge),
        "Why": describe_edge(leg.edge) + " · " + describe_ev_per_dollar(leg.ev_per_dollar),
    }
