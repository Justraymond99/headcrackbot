from __future__ import annotations

from typing import Any, Iterable

from .models import BetLeg, Parlay
from .probability import american_to_implied_probability

PAYOUT_BAND_LABELS = {
    "small": "Safe plays ($60–$200 payout)",
    "big": "Big swings ($500–$2,000 payout)",
    "nuclear": "Moon shots ($1,000+ payout)",
}

MARKET_TYPE_LABELS = {
    "moneyline": "Who wins",
    "qualify": "Who advances",
    "spread": "Point spread",
    "total_goals": "Total goals",
    "team_total": "Team total",
    "both_teams_to_score": "Both teams score",
    "corners": "Corner kicks",
    "cards": "Cards",
    "player_goal": "Player goal",
    "player_assist": "Player assist",
    "player_shots": "Player shots",
    "player_shots_on_target": "Shots on target",
    "custom": "Special bet",
}


def format_american_odds(odds: int) -> str:
    if odds > 0:
        return f"+{odds} (bet $100 to win ${odds})"
    return f"{odds} (bet ${abs(odds)} to win $100)"


def format_chance(probability: float) -> str:
    return f"{probability:.0%} chance"


def describe_edge(edge: float) -> str:
    points = abs(edge) * 100
    if edge >= 0.05:
        return f"Strong value — we're about {points:.0f} points higher than the book"
    if edge >= 0.02:
        return f"Good value — we're about {points:.0f} points higher than the book"
    if edge > 0:
        return f"Slight edge — we're a little higher than the book"
    if edge > -0.02:
        return "Roughly fair — close to what the book thinks"
    return f"Bad price — the book looks better by about {points:.0f} points"


def describe_ev_per_dollar(ev: float) -> str:
    if ev > 0.10:
        return f"On average you'd make about ${ev:.2f} per $1 bet over time"
    if ev > 0:
        return f"Slightly profitable on paper — about ${ev:.2f} per $1"
    if ev > -0.05:
        return "Basically break-even — not much edge either way"
    return f"Likely a losing bet long-term — about ${abs(ev):.2f} lost per $1"


def chance_in_plain_english(probability: float) -> str:
    if probability >= 0.75:
        return "very likely"
    if probability >= 0.55:
        return "more likely than not"
    if probability >= 0.40:
        return "a coin flip leaning yes"
    if probability >= 0.20:
        return "unlikely but live"
    return "a long shot"


def parlay_chance_in_words(probability: float) -> str:
    if probability <= 0:
        return "almost no chance"
    one_in = max(1, round(1 / probability))
    if one_in == 1:
        return "looks likely"
    if one_in <= 3:
        return f"roughly 1 in {one_in}"
    if one_in <= 10:
        return f"about 1 in {one_in} — doable but not easy"
    return f"about 1 in {one_in} — tough parlay"


def payout_band_label(band: str) -> str:
    return PAYOUT_BAND_LABELS.get(band, band.replace("_", " ").title())


def market_type_label(market_type: str) -> str:
    return MARKET_TYPE_LABELS.get(market_type, market_type.replace("_", " ").title())


def value_verdict(edge: float) -> str:
    if edge >= 0.05:
        return "🔥 Strong pick"
    if edge >= 0.02:
        return "✅ Good value"
    if edge > 0:
        return "👍 Slight edge"
    if edge > -0.02:
        return "➖ Fair price"
    return "⚠️ Skip — book has the edge"


def explain_leg_plain(leg: BetLeg) -> str:
    return (
        f"**{leg.market.label}** ({format_american_odds(leg.market.odds.value)})\n"
        f"- We think: {format_chance(leg.model_probability)} ({chance_in_plain_english(leg.model_probability)})\n"
        f"- Book thinks: {format_chance(leg.implied_probability)}\n"
        f"- Our take: {value_verdict(leg.edge)} — {describe_edge(leg.edge)}"
    )


def explain_parlay_plain(parlay: Parlay) -> str:
    profit = parlay.gross_payout - parlay.stake
    lines = [
        f"**Bet ${parlay.stake:.2f} → could pay ${parlay.gross_payout:.2f}** "
        f"(profit ${profit:.2f}) — {payout_band_label(parlay.target_band)}",
        f"- Chance to hit: {format_chance(parlay.adjusted_probability)} "
        f"({parlay_chance_in_words(parlay.adjusted_probability)})",
    ]
    if parlay.expected_value > 0:
        lines.append(f"- Long-run outlook: {describe_ev_per_dollar(parlay.expected_value / parlay.stake)}")
    else:
        lines.append("- Long-run outlook: this is more for fun than value")

    if parlay.correlation_score >= 1.0:
        lines.append("- Story check: ✅ picks fit the same game plan")
    elif parlay.correlation_score <= 0:
        lines.append("- Story check: ⚠️ picks don't really match — risky combo")
    if parlay.risk_score >= 1.5:
        lines.append("- Risk: 🎲 longshot — keep the stake small")

    lines.append("")
    lines.append("**Picks on this slip:**")
    for leg in parlay.legs:
        lines.append(f"- {leg.market.label} ({format_american_odds(leg.market.odds.value)})")
    return "\n".join(lines)


def explain_card_plain(card: dict[str, list[Parlay]]) -> str:
    sections: list[str] = []
    for band, parlays in card.items():
        sections.append(f"## {payout_band_label(band)}")
        if not parlays:
            sections.append("Nothing fit this payout range today. That's okay — passing is smart.")
            continue
        for idx, parlay in enumerate(parlays[:3], start=1):
            sections.append(f"### Option {idx}")
            sections.append(explain_parlay_plain(parlay))
    return "\n\n".join(sections)


def leg_to_friendly_row(leg: BetLeg) -> dict[str, Any]:
    return {
        "Pick": leg.market.label,
        "Sportsbook": leg.market.sportsbook,
        "Odds": format_american_odds(leg.market.odds.value),
        "We think": format_chance(leg.model_probability),
        "Book thinks": format_chance(leg.implied_probability),
        "Our take": value_verdict(leg.edge),
        "Why": describe_edge(leg.edge),
    }


def value_board_to_friendly_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    friendly: list[dict[str, Any]] = []
    for row in rows:
        edge = float(row.get("edge", 0))
        odds = int(row["odds"])
        book_chance = american_to_implied_probability(odds)
        friendly.append(
            {
                "Pick": row.get("label", ""),
                "Type": market_type_label(str(row.get("market_type", "custom"))),
                "Sportsbook": row.get("sportsbook", ""),
                "Odds": format_american_odds(odds),
                "We think": format_chance(float(row["model_probability"])),
                "Book thinks": format_chance(book_chance),
                "Our take": value_verdict(edge),
                "Why": describe_edge(edge),
            }
        )
    return friendly


def simulation_to_friendly(result: dict[str, Any]) -> dict[str, str]:
    return {
        "Home win": format_chance(float(result["home_win"])),
        "Draw": format_chance(float(result["draw"])),
        "Away win": format_chance(float(result["away_win"])),
        "Both teams score": format_chance(float(result["btts"])),
        "Over 2.5 goals": format_chance(float(result["over_2_5"])),
        "Over 3.5 goals": format_chance(float(result["over_3_5"])),
    }
