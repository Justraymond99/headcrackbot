from __future__ import annotations

from typing import Any

from ..models import BetLeg
from ..probability import monte_carlo_soccer_match
from ..soccer import estimate_match_xg, group_legs_by_match
from ..plain_language import format_chance


def build_match_projections(legs: list[BetLeg], simulations: int = 5000) -> list[dict[str, Any]]:
    """Model-backed match projections with xG and simulated outcomes."""
    grouped = group_legs_by_match(legs)
    projections: list[dict[str, Any]] = []

    for match_name, match_legs in grouped.items():
        home_xg, away_xg, features = estimate_match_xg(match_legs)
        sim = monte_carlo_soccer_match(home_xg, away_xg, simulations=simulations)
        top_picks = sorted(match_legs, key=lambda leg: leg.edge, reverse=True)[:3]

        projections.append(
            {
                "match": match_name,
                "home_team": features.get("home_team", ""),
                "away_team": features.get("away_team", ""),
                "home_xg": round(home_xg, 2),
                "away_xg": round(away_xg, 2),
                "home_win": sim["home_win"],
                "draw": sim["draw"],
                "away_win": sim["away_win"],
                "btts": sim["btts"],
                "over_2_5": sim["over_2_5"],
                "top_scores": dict(list(sim["top_scores"].items())[:5]),
                "top_edges": [
                    {
                        "pick": leg.market.label,
                        "book": leg.market.sportsbook,
                        "edge": round(leg.edge, 4),
                        "model": leg.model_probability,
                    }
                    for leg in top_picks
                ],
                "source": features.get("source", "model"),
            }
        )

    return sorted(projections, key=lambda p: max((e["edge"] for e in p["top_edges"]), default=0), reverse=True)


def format_projection_card(proj: dict[str, Any]) -> str:
    lines = [
        f"### {proj['match']}",
        f"**xG:** {proj['home_team']} {proj['home_xg']} — {proj['away_xg']} {proj['away_team']}",
        f"**Win chances:** Home {format_chance(proj['home_win'])} · "
        f"Draw {format_chance(proj['draw'])} · Away {format_chance(proj['away_win'])}",
        f"**BTTS:** {format_chance(proj['btts'])} · **Over 2.5:** {format_chance(proj['over_2_5'])}",
    ]
    if proj.get("top_edges"):
        lines.append("**Best edges:**")
        for edge in proj["top_edges"]:
            lines.append(f"- {edge['pick']} ({edge['book']}) — {edge['edge']:+.1%} edge")
    return "\n".join(lines)
