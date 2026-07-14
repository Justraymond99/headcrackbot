from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from functools import reduce
from operator import mul
from pathlib import Path
from typing import Any, Iterable

from .ingest import leg_from_dict
from .models import BetLeg, BetRecord, Parlay, ResultStatus
from .persistence import SQLiteStore


def _coerce_status(value: Any) -> ResultStatus:
    if value in (None, ""):
        return ResultStatus.PENDING
    if isinstance(value, ResultStatus):
        return value
    return ResultStatus(str(value).strip().lower())


def bet_record_from_dict(row: dict[str, Any]) -> BetRecord:
    """Build a :class:`BetRecord` from a lightweight dict.

    ``legs`` reuse the same row schema as market ingestion, so a bet file looks
    like a market file wrapped with staking metadata.
    """
    leg_rows: Iterable[dict[str, Any]] = row.get("legs") or []
    legs = tuple(leg_from_dict(leg_row) for leg_row in leg_rows)
    if not legs:
        raise ValueError(f"Bet {row.get('bet_id')!r} has no legs")

    decimal_odds = row.get("decimal_odds")
    if decimal_odds in (None, ""):
        decimal_odds = reduce(mul, (leg.decimal_odds for leg in legs), 1.0)

    placed_at = row.get("placed_at")
    kwargs: dict[str, Any] = {
        "bet_id": str(row["bet_id"]),
        "legs": legs,
        "stake": float(row["stake"]),
        "decimal_odds": float(decimal_odds),
        "status": _coerce_status(row.get("status")),
        "payout": float(row.get("payout", 0.0) or 0.0),
    }
    if placed_at:
        kwargs["placed_at"] = datetime.fromisoformat(str(placed_at))
    return BetRecord(**kwargs)


def bet_record_from_parlay(bet_id: str, parlay: Parlay, status: ResultStatus = ResultStatus.PENDING) -> BetRecord:
    """Turn an optimizer :class:`Parlay` into a placeable, trackable bet."""
    return BetRecord(
        bet_id=bet_id,
        legs=parlay.legs,
        stake=parlay.stake,
        decimal_odds=parlay.decimal_odds,
        status=status,
    )


def _load_rows(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text())
        if isinstance(payload, dict):
            payload = payload.get("bets") or payload.get("results") or payload.get("markets") or []
        return list(payload)
    if suffix == ".csv":
        with path.open(newline="") as f:
            return list(csv.DictReader(f))
    raise ValueError("Input must be .csv or .json")


def import_bet_records(store: SQLiteStore, path: str | Path) -> list[BetRecord]:
    """Import placed bets, registering their markets/predictions along the way."""
    records = [bet_record_from_dict(row) for row in _load_rows(path)]
    for record in records:
        store.save_legs(list(record.legs))
        store.save_bet_record(record)
    return records


@dataclass(frozen=True)
class ResultsImportSummary:
    market_results_recorded: int
    bets_settled: int


def import_market_results(store: SQLiteStore, path: str | Path) -> ResultsImportSummary:
    """Import real-world market outcomes and auto-settle any now-complete bets.

    A results row is ``{"market_id": ..., "outcome": "won"|"lost"|"void"}``.
    """
    recorded = 0
    for row in _load_rows(path):
        market_id = row.get("market_id") or row.get("id")
        outcome = row.get("outcome") or row.get("result") or row.get("status")
        if not market_id or outcome in (None, ""):
            continue
        store.record_market_result(str(market_id), _coerce_status(outcome))
        recorded += 1
    settled = store.settle_bets_from_market_results()
    return ResultsImportSummary(market_results_recorded=recorded, bets_settled=settled)
