from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..models import BetLeg
from ..plain_language import format_american_odds


def _decimal(odds: int) -> float:
    if odds > 0:
        return 1.0 + odds / 100.0
    return 1.0 + 100.0 / abs(odds)


def _selection_key(leg: BetLeg) -> str:
    market = leg.market
    parts = [
        market.event_id,
        market.market_type.value,
        market.team or "",
        str(market.threshold or ""),
        market.label.split("—")[-1].strip().lower() if "—" in market.label else market.label.lower(),
    ]
    return "|".join(parts)


def build_odds_screen(legs: list[BetLeg]) -> list[dict[str, Any]]:
    """Pivot the same pick across sportsbooks for line shopping."""
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"books": {}, "model_probability": None, "edge_best": None}
    )

    for leg in legs:
        key = _selection_key(leg)
        row = grouped[key]
        row["pick"] = leg.market.label
        row["match"] = _match_label(leg)
        row["market_type"] = leg.market.market_type.value
        row["books"][leg.market.sportsbook] = leg.market.odds.value
        row["model_probability"] = leg.model_probability
        if leg.edge > (row.get("edge_best") or -999):
            row["edge_best"] = leg.edge
            row["best_book"] = leg.market.sportsbook
            row["best_odds"] = leg.market.odds.value

    screen: list[dict[str, Any]] = []
    for row in grouped.values():
        if len(row["books"]) < 2:
            continue
        books = row["books"]
        best_book = max(books, key=lambda b: _decimal(books[b]))
        worst_book = min(books, key=lambda b: _decimal(books[b]))
        # Spread in implied-probability points between best and worst price.
        best_imp = 1.0 / _decimal(books[best_book])
        worst_imp = 1.0 / _decimal(books[worst_book])
        row["spread"] = abs(worst_imp - best_imp)
        row["best_book"] = best_book
        row["best_odds"] = books[best_book]
        screen.append(row)

    return sorted(screen, key=lambda r: (r.get("edge_best") or 0, r["spread"]), reverse=True)


def _match_label(leg: BetLeg) -> str:
    meta = leg.market.metadata
    home = meta.get("home_team", "")
    away = meta.get("away_team", "")
    if home and away:
        return f"{home} vs {away}"
    return leg.market.event_id


def format_odds_screen_rows(screen: list[dict[str, Any]], book_columns: list[str] | None = None) -> list[dict[str, Any]]:
    if not screen:
        return []
    if book_columns is None:
        book_columns = sorted({book for row in screen for book in row["books"]})

    rows: list[dict[str, Any]] = []
    for item in screen:
        row: dict[str, Any] = {
            "Match": item["match"],
            "Pick": item["pick"],
            "Best book": item.get("best_book", ""),
            "Best odds": format_american_odds(int(item.get("best_odds", 0))),
        }
        for book in book_columns:
            odds = item["books"].get(book)
            row[book.title()] = format_american_odds(odds) if odds is not None else "—"
        if item.get("model_probability") is not None:
            row["Model"] = f"{item['model_probability']:.0%}"
        rows.append(row)
    return rows
