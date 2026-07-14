"""Sprint 9 — grounded explanations and pick rationales."""

from __future__ import annotations

from ..models import BetLeg, Parlay
from ..plain_language import explain_card_plain, explain_leg_plain, explain_parlay_plain
from .attribution import explain_pick_rationale, top_pick_rationales
from .card_brief import build_card_brief, format_card_brief


def explain_leg(leg: BetLeg) -> str:
    return explain_leg_plain(leg)


def explain_parlay(parlay: Parlay) -> str:
    return explain_parlay_plain(parlay)


def explain_card(card: dict[str, list[Parlay]]) -> str:
    return explain_card_plain(card)


__all__ = [
    "build_card_brief",
    "explain_card",
    "explain_leg",
    "explain_parlay",
    "explain_pick_rationale",
    "format_card_brief",
    "top_pick_rationales",
]
