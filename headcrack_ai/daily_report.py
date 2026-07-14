from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .calibration import build_calibration_report
from .explain import explain_card, build_card_brief, format_card_brief
from .llm_explain import CardNarrator, explain_brief_narrative
from .models import BetLeg
from .optimizer import build_card
from .persistence import SQLiteStore
from .plain_language import format_american_odds, format_chance, payout_band_label, value_verdict
from .reports import summarize


def _best_single(legs: list[BetLeg]) -> dict[str, Any] | None:
    positive = [leg for leg in legs if leg.edge > 0]
    if not positive:
        return None
    best = max(positive, key=lambda leg: leg.ev_per_dollar)
    return {
        "label": best.market.label,
        "odds": best.market.odds.value,
        "model_probability": round(best.model_probability, 4),
        "implied_probability": round(best.implied_probability, 4),
        "edge": round(best.edge, 4),
        "ev_per_dollar": round(best.ev_per_dollar, 4),
    }


def _no_bet_warnings(legs: list[BetLeg], card: dict[str, list]) -> list[str]:
    warnings: list[str] = []
    empty_bands = [payout_band_label(band) for band, parlays in card.items() if not parlays]
    if empty_bands:
        warnings.append(f"No good parlays found for: {', '.join(empty_bands)}.")
    negative = [leg for leg in legs if leg.edge < 0]
    if negative:
        warnings.append(
            f"{len(negative)} of {len(legs)} picks look overpriced — the sportsbook has the edge there."
        )
    if not any(leg.edge > 0 for leg in legs):
        warnings.append("Nothing looks like a great value bet today. Consider sitting out.")
    return warnings


def generate_daily_report(
    legs: list[BetLeg],
    store: SQLiteStore,
    budget: float = 20.0,
    min_edge: float = -0.02,
    narrator: CardNarrator | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or datetime.now(timezone.utc)
    card = build_card(legs, budget=budget, min_edge=min_edge)
    brief = build_card_brief(legs, card=card, budget=budget, min_edge=min_edge)
    tracking = summarize(store.all_bet_records())
    calibration = build_calibration_report(store)
    return {
        "generated_at": generated_at.isoformat(),
        "legs_considered": len(legs),
        "best_single": brief.get("best_single") or _best_single(legs),
        "card": card,
        "brief": brief,
        "card_markdown": explain_card(card),
        "brief_markdown": format_card_brief(brief),
        "narrative": explain_brief_narrative(brief, narrator=narrator),
        "no_bet_warnings": brief.get("warnings") or _no_bet_warnings(legs, card),
        "tracking_summary": tracking,
        "calibration_summary": {
            "samples": calibration["samples"],
            "brier_score": calibration["brier_score"],
            "expected_calibration_error": calibration["expected_calibration_error"],
        },
    }


def format_daily_report(report: dict[str, Any]) -> str:
    lines = [
        "# Today's Picks — Headcrack AI",
        f"Generated: {report['generated_at']}",
        f"Picks reviewed: {report['legs_considered']}",
        "",
        "## Best Single Bet",
    ]
    best = report["best_single"]
    if best:
        lines.append(
            f"**{best['label']}** at {format_american_odds(best['odds'])} — "
            f"we think {format_chance(best['model_probability'])}, "
            f"book thinks {format_chance(best['implied_probability'])}. "
            f"{value_verdict(best['edge'])}."
        )
    else:
        lines.append("No standout single bet today.")

    lines.extend(["", "## AI Brief", report.get("brief_markdown", "")])
    lines.extend(["", "## Suggested Parlays", report["card_markdown"]])
    lines.extend(["", "## Plain English Summary", report["narrative"]])

    lines.extend(["", "## Heads Up"])
    if report["no_bet_warnings"]:
        lines.extend(f"- {warning}" for warning in report["no_bet_warnings"])
    else:
        lines.append("- Board looks playable today.")

    tracking = report["tracking_summary"]
    pl = tracking["profit_loss"]
    direction = "up" if pl >= 0 else "down"
    lines.extend(
        [
            "",
            "## Your Record So Far",
            f"- {tracking['bets']} bets placed, {tracking['settled']} finished, "
            f"won {tracking['wins']} ({tracking['hit_rate']:.0%}), "
            f"{direction} ${abs(pl):.2f} overall ({tracking['roi']:+.0%} return)",
        ]
    )

    calibration = report["calibration_summary"]
    lines.extend(
        [
            "",
            "## How Trustworthy Are Our Picks?",
            f"- Checked {calibration['samples']} finished picks, "
            f"accuracy score {calibration['brier_score']} "
            f"(lower is better)",
        ]
    )
    return "\n".join(lines)
