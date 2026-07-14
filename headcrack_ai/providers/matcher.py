"""Deterministic aliasing for sportsbook ↔ prediction-market outcomes.

Unmatched contracts stay visible but must never be presented as arbitrage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from ..models import BetLeg, Market, MarketType

# Common aliases / nicknames for soccer teams that appear on books vs contracts.
TEAM_ALIASES: dict[str, str] = {
    "france": "france",
    "espana": "spain",
    "españa": "spain",
    "spain": "spain",
    "england": "england",
    "argentina": "argentina",
    "usa": "united states",
    "united states": "united states",
    "usmnt": "united states",
    "korea republic": "south korea",
    "south korea": "south korea",
    "cote divoire": "ivory coast",
    "ivory coast": "ivory coast",
}


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().strip()
    text = text.replace("é", "e").replace("ñ", "n").replace("ö", "o").replace("ü", "u")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return TEAM_ALIASES.get(text, text)


def canonical_event_key(home: str | None, away: str | None, league: str | None = None) -> str:
    sides = sorted([normalize_name(home), normalize_name(away)])
    base = " vs ".join(s for s in sides if s)
    league_key = normalize_name(league) if league else ""
    return f"{league_key}:{base}" if league_key else base


def canonical_outcome_key(
    market_type: MarketType | str,
    *,
    team: str | None = None,
    player: str | None = None,
    threshold: float | None = None,
    outcome: str | None = None,
) -> str:
    mtype = market_type.value if isinstance(market_type, MarketType) else str(market_type)
    parts = [
        mtype,
        normalize_name(player) or normalize_name(team),
        f"{threshold:g}" if threshold is not None else "",
        normalize_name(outcome),
    ]
    return "|".join(p for p in parts if p)


@dataclass(frozen=True)
class MatchResult:
    sportsbook_leg: BetLeg
    prediction_leg: BetLeg
    score: float
    matched: bool


def attach_canonical_ids(market: Market) -> Market:
    """Return a copy of ``market`` with canonical IDs filled when missing."""
    meta = dict(market.metadata or {})
    home = meta.get("home_team") or market.team
    away = meta.get("away_team") or market.opponent
    event_key = market.canonical_event_id or canonical_event_key(
        home, away, meta.get("league")
    )
    outcome = meta.get("outcome_name") or market.team
    outcome_key = market.canonical_outcome_id or canonical_outcome_key(
        market.market_type,
        team=market.team,
        player=market.player,
        threshold=market.threshold,
        outcome=str(outcome) if outcome else None,
    )
    if market.canonical_event_id == event_key and market.canonical_outcome_id == outcome_key:
        return market
    from dataclasses import replace

    return replace(market, canonical_event_id=event_key, canonical_outcome_id=outcome_key)


def match_prediction_to_books(
    prediction_legs: Iterable[BetLeg],
    sportsbook_legs: Iterable[BetLeg],
    min_score: float = 0.72,
) -> list[MatchResult]:
    """Greedy best-match of prediction contracts onto book legs of the same type."""
    books = list(sportsbook_legs)
    results: list[MatchResult] = []
    for pred in prediction_legs:
        best: tuple[float, BetLeg] | None = None
        pred_event = normalize_name(pred.market.canonical_event_id or pred.market.event_id)
        pred_outcome = normalize_name(pred.market.canonical_outcome_id or pred.market.label)
        pred_team = normalize_name(pred.market.team)
        pred_player = normalize_name(pred.market.player)
        for book in books:
            if book.market.market_type != pred.market.market_type and pred.market.market_type != MarketType.CUSTOM:
                # Allow CUSTOM prediction contracts to match moneyline by team.
                if not (pred.market.market_type == MarketType.CUSTOM and book.market.market_type == MarketType.MONEYLINE):
                    continue
            score = 0.0
            book_event = normalize_name(book.market.canonical_event_id or book.market.event_id)
            if pred_event and book_event and (pred_event in book_event or book_event in pred_event):
                score += 0.45
            book_team = normalize_name(book.market.team)
            book_player = normalize_name(book.market.player)
            if pred_team and book_team and pred_team == book_team:
                score += 0.35
            elif pred_team and pred_team in normalize_name(book.market.label):
                score += 0.25
            if pred_player and book_player and pred_player == book_player:
                score += 0.4
            if pred.market.threshold is not None and book.market.threshold is not None:
                if abs(pred.market.threshold - book.market.threshold) < 1e-6:
                    score += 0.15
            book_outcome = normalize_name(book.market.canonical_outcome_id or book.market.label)
            if pred_outcome and book_outcome and (
                pred_outcome == book_outcome or pred_team and pred_team in book_outcome
            ):
                score += 0.1
            if best is None or score > best[0]:
                best = (score, book)
        if best is None:
            continue
        score, book = best
        results.append(
            MatchResult(
                sportsbook_leg=book,
                prediction_leg=pred,
                score=round(score, 3),
                matched=score >= min_score,
            )
        )
    return results
