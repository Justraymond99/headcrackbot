from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..models import BetLeg, MarketType
from ..plain_language import format_american_odds


def _decimal_from_american(odds: int) -> float:
    if odds > 0:
        return 1.0 + odds / 100.0
    return 1.0 + 100.0 / abs(odds)


def find_arbitrage_opportunities(legs: list[BetLeg], min_profit_pct: float = 0.005) -> list[dict[str, Any]]:
    """Cross-book arbs: implied probabilities on mutually exclusive outcomes sum below 100%."""
    by_event: dict[str, list[BetLeg]] = defaultdict(list)
    for leg in legs:
        by_event[leg.market.event_id].append(leg)

    opportunities: list[dict[str, Any]] = []

    for event_id, event_legs in by_event.items():
        opportunities.extend(_two_way_arbs(event_id, event_legs, min_profit_pct))
        opportunities.extend(_three_way_moneyline_arbs(event_id, event_legs, min_profit_pct))

    return sorted(opportunities, key=lambda o: o["profit_pct"], reverse=True)


def _two_way_arbs(event_id: str, legs: list[BetLeg], min_profit_pct: float) -> list[dict[str, Any]]:
    """Over/under and yes/no style two-outcome arbs."""
    # Group key: (market_type, threshold-or-sentinel). BTTS has no line.
    pairs: dict[tuple[str, float | None], dict[str, BetLeg]] = defaultdict(dict)
    for leg in legs:
        market = leg.market
        if market.market_type == MarketType.TOTAL_GOALS:
            if market.threshold is None:
                continue
            group_key: tuple[str, float | None] = (market.market_type.value, market.threshold)
        elif market.market_type == MarketType.BOTH_TEAMS_TO_SCORE:
            group_key = (market.market_type.value, None)
        else:
            continue
        name = (market.team or market.label).lower()
        side = "over" if "over" in name or "yes" in name else "under"
        pairs[group_key][side] = leg

    found: list[dict[str, Any]] = []
    for (mtype, line), sides in pairs.items():
        if "over" not in sides or "under" not in sides:
            continue
        best_over = _best_price_by_side(legs, line, mtype, "over")
        best_under = _best_price_by_side(legs, line, mtype, "under")
        if not best_over or not best_under:
            continue
        inv_sum = 1 / best_over["decimal"] + 1 / best_under["decimal"]
        profit = 1 - inv_sum
        if profit < min_profit_pct:
            continue
        label = f"{mtype} {line}" if line is not None else mtype
        found.append(
            {
                "type": "two_way",
                "event_id": event_id,
                "market": label,
                "profit_pct": round(profit, 4),
                "legs": [best_over, best_under],
                "note": f"Guaranteed {profit:.1%} if sized correctly across books",
            }
        )
    return found


def _best_price_by_side(
    legs: list[BetLeg], line: float | None, mtype: str, side: str
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for leg in legs:
        if leg.market.market_type.value != mtype:
            continue
        if line is not None and leg.market.threshold != line:
            continue
        name = (leg.market.team or leg.market.label).lower()
        is_side = ("over" in name or "yes" in name) if side == "over" else ("under" in name or "no" in name)
        if not is_side:
            continue
        decimal = _decimal_from_american(leg.market.odds.value)
        if best is None or decimal > best["decimal"]:
            best = {
                "pick": leg.market.label,
                "book": leg.market.sportsbook,
                "odds": leg.market.odds.value,
                "decimal": decimal,
            }
    return best


def _three_way_moneyline_arbs(event_id: str, legs: list[BetLeg], min_profit_pct: float) -> list[dict[str, Any]]:
    ml = [leg for leg in legs if leg.market.market_type == MarketType.MONEYLINE]
    if len(ml) < 3:
        return []

    meta = ml[0].market.metadata
    home = meta.get("home_team")
    away = meta.get("away_team")
    if not home or not away:
        return []

    home_legs = [leg for leg in ml if leg.market.team == home]
    away_legs = [leg for leg in ml if leg.market.team == away]
    draw_legs = [leg for leg in ml if (leg.market.team or "").lower() == "draw" or "draw" in leg.market.label.lower()]
    if not home_legs or not away_legs or not draw_legs:
        return []

    best_home = max(home_legs, key=lambda leg: leg.decimal_odds)
    best_away = max(away_legs, key=lambda leg: leg.decimal_odds)
    best_draw = max(draw_legs, key=lambda leg: leg.decimal_odds)

    inv_sum = (
        1 / best_home.decimal_odds
        + 1 / best_away.decimal_odds
        + 1 / best_draw.decimal_odds
    )
    profit = 1 - inv_sum
    if profit < min_profit_pct:
        return []

    return [
        {
            "type": "three_way",
            "event_id": event_id,
            "market": f"{home} vs {away} — 1X2",
            "profit_pct": round(profit, 4),
            "legs": [
                {"pick": best_home.market.label, "book": best_home.market.sportsbook, "odds": best_home.market.odds.value},
                {"pick": best_draw.market.label, "book": best_draw.market.sportsbook, "odds": best_draw.market.odds.value},
                {"pick": best_away.market.label, "book": best_away.market.sportsbook, "odds": best_away.market.odds.value},
            ],
            "note": f"Cross-book 1X2 arb — {profit:.1%} margin before sizing",
        }
    ]


def find_prediction_arbs(
    sportsbook_legs: list[BetLeg],
    prediction_legs: list[BetLeg],
    min_gap: float = 0.03,
) -> list[dict[str, Any]]:
    """Gap between sportsbook implied price and prediction-market (e.g. Kalshi) price."""
    if not prediction_legs:
        return []

    by_team: dict[str, list[BetLeg]] = defaultdict(list)
    for leg in sportsbook_legs:
        if leg.market.team:
            by_team[leg.market.team.lower()].append(leg)

    gaps: list[dict[str, Any]] = []
    for pred in prediction_legs:
        team = (pred.market.team or "").lower()
        label_key = pred.market.label.lower()
        candidates = by_team.get(team, [])
        if not candidates:
            candidates = [leg for leg in sportsbook_legs if team and team in leg.market.label.lower()]
        if not candidates:
            continue
        best_book = max(candidates, key=lambda leg: leg.model_probability - leg.implied_probability)
        gap = pred.implied_probability - best_book.implied_probability
        if abs(gap) < min_gap:
            continue
        gaps.append(
            {
                "pick": best_book.market.label,
                "sportsbook": best_book.market.sportsbook,
                "book_odds": format_american_odds(best_book.market.odds.value),
                "book_implied": round(best_book.implied_probability, 4),
                "prediction_market": pred.market.sportsbook,
                "prediction_label": pred.market.label,
                "prediction_implied": round(pred.implied_probability, 4),
                "gap": round(gap, 4),
                "play": "Buy prediction market / fade sportsbook" if gap < 0 else "Buy sportsbook / fade prediction market",
            }
        )
    return sorted(gaps, key=lambda g: abs(g["gap"]), reverse=True)
