from __future__ import annotations

from typing import Any

from ..models import BetLeg
from ..plain_language import describe_edge, format_chance, value_verdict


def explain_pick_rationale(leg: BetLeg) -> str:
    """One-line 'why this bet' from model features and game-script tags."""
    parts: list[str] = []
    features: dict[str, Any] = leg.prediction.features or {}

    if leg.edge > 0.02:
        parts.append(describe_edge(leg.edge))
    elif leg.edge <= -0.02:
        parts.append("The book's price looks sharper than our model here.")
    else:
        parts.append("This is priced close to fair.")

    if "home_xg" in features and "away_xg" in features:
        parts.append(
            f"We project about {features['home_xg']:.1f} vs {features['away_xg']:.1f} expected goals."
        )
    elif "expected_shots" in features:
        parts.append(f"Projected {features['expected_shots']:.1f} shots in this spot.")

    tags = list(leg.tags)
    if tags:
        readable = ", ".join(t.replace("_", " ") for t in tags[:3])
        parts.append(f"Game script tags: {readable}.")

    model = leg.prediction.model_name
    if model and model not in {"book_baseline", "live_odds"}:
        parts.append(f"Model: {model.replace('_', ' ')}.")

    return " ".join(parts)


def top_pick_rationales(legs: list[BetLeg], limit: int = 5) -> list[dict[str, str]]:
    ranked = sorted(legs, key=lambda leg: leg.edge, reverse=True)[:limit]
    return [
        {
            "pick": leg.market.label,
            "verdict": value_verdict(leg.edge),
            "our_chance": format_chance(leg.model_probability),
            "book_chance": format_chance(leg.implied_probability),
            "why": explain_pick_rationale(leg),
        }
        for leg in ranked
    ]
