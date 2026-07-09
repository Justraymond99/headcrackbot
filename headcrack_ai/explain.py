from __future__ import annotations

from .models import BetLeg, Parlay


def explain_leg(leg: BetLeg) -> str:
    return (
        f"{leg.market.label}: model {leg.model_probability:.1%}, "
        f"book {leg.implied_probability:.1%}, edge {leg.edge:+.1%}, "
        f"EV ${leg.ev_per_dollar:.2f}/$1."
    )


def explain_parlay(parlay: Parlay) -> str:
    lines = [
        f"${parlay.stake:.2f} -> ${parlay.gross_payout:.2f} ({parlay.target_band})",
        f"Adjusted hit probability: {parlay.adjusted_probability:.1%}",
        f"Expected value: ${parlay.expected_value:.2f}",
        f"Correlation score: {parlay.correlation_score:.2f}; Risk score: {parlay.risk_score:.2f}",
        "Legs:",
    ]
    lines.extend(f"- {explain_leg(leg)}" for leg in parlay.legs)
    if parlay.notes:
        lines.append(f"Notes: {parlay.notes}")
    return "\n".join(lines)


def explain_card(card: dict[str, list[Parlay]]) -> str:
    sections: list[str] = []
    for band, parlays in card.items():
        sections.append(f"## {band.upper()}")
        if not parlays:
            sections.append("No candidates found for this band.")
            continue
        for idx, parlay in enumerate(parlays[:3], start=1):
            sections.append(f"### Candidate {idx}")
            sections.append(explain_parlay(parlay))
    return "\n\n".join(sections)
