from __future__ import annotations

from typing import Any

from ..llm_explain import summarize_card
from ..models import BetLeg, Parlay
from ..optimizer import build_card
from ..plain_language import payout_band_label, value_verdict
from .attribution import explain_pick_rationale, top_pick_rationales


def build_card_brief(
    legs: list[BetLeg],
    card: dict[str, list[Parlay]] | None = None,
    budget: float = 20.0,
    min_edge: float = -0.02,
) -> dict[str, Any]:
    """Structured, grounded facts for UI and LLM narration — no hallucination surface."""
    card = card or build_card(legs, budget=budget, min_edge=min_edge)
    summary = summarize_card(card)

    warnings: list[str] = []
    positive = [leg for leg in legs if leg.edge > 0]
    if not positive:
        warnings.append("No clear value singles on the board — consider passing.")
    if not any(card.get("big")) and not any(card.get("nuclear")):
        warnings.append("No big-payout parlays fit today without forcing longshots.")

    best_single = None
    if positive:
        best = max(positive, key=lambda leg: leg.edge)
        best_single = {
            "label": best.market.label,
            "odds": best.market.odds.value,
            "model_probability": round(best.model_probability, 4),
            "implied_probability": round(best.implied_probability, 4),
            "edge": round(best.edge, 4),
            "ev_per_dollar": round(best.ev_per_dollar, 4),
            "verdict": value_verdict(best.edge),
            "why": explain_pick_rationale(best),
        }

    parlay_ideas = []
    for band, parlays in card.items():
        if not parlays:
            continue
        top = parlays[0]
        parlay_ideas.append(
            {
                "band": payout_band_label(band),
                "stake": round(top.stake, 2),
                "payout": round(top.gross_payout, 2),
                "chance": round(top.adjusted_probability, 4),
                "picks": [leg.market.label for leg in top.legs],
                "story": "same game plan" if top.correlation_score >= 1.0 else "mixed story",
            }
        )

    return {
        "picks_reviewed": len(legs),
        "value_picks": len(positive),
        "best_single": best_single,
        "top_rationales": top_pick_rationales(legs, limit=5),
        "parlay_ideas": parlay_ideas,
        "warnings": warnings,
        "card_summary": summary,
        "safety_footer": "No pick is guaranteed. Bet only what you can afford to lose.",
    }


def format_card_brief(brief: dict[str, Any]) -> str:
    lines = ["# Today's Soccer Brief", ""]
    lines.append(f"Reviewed **{brief['picks_reviewed']}** lines · **{brief['value_picks']}** look like value")

    best = brief.get("best_single")
    if best:
        lines.extend(["", "## Best Bet", f"**{best['label']}** — {best['verdict']}", best["why"]])
    else:
        lines.extend(["", "## Best Bet", "No standout single today."])

    if brief.get("top_rationales"):
        lines.extend(["", "## Why These Picks"])
        for row in brief["top_rationales"]:
            lines.append(f"- **{row['pick']}** ({row['verdict']}) — {row['why']}")

    if brief.get("parlay_ideas"):
        lines.extend(["", "## Parlay Ideas"])
        for idea in brief["parlay_ideas"]:
            lines.append(
                f"- **{idea['band']}**: ${idea['stake']:.0f} → ${idea['payout']:.0f} "
                f"({idea['chance']:.0%} chance) — {', '.join(idea['picks'][:4])}"
            )

    if brief.get("warnings"):
        lines.extend(["", "## Heads Up"])
        lines.extend(f"- {w}" for w in brief["warnings"])

    lines.extend(["", f"*{brief['safety_footer']}*"])
    return "\n".join(lines)
