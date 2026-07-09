from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .models import BankrollState, BetRecord, BetLeg, ResultStatus


@dataclass(frozen=True)
class StakeRecommendation:
    stake: float
    method: str
    reason: str


def kelly_fraction(probability: float, decimal_odds: float) -> float:
    b = decimal_odds - 1.0
    if b <= 0:
        return 0.0
    q = 1.0 - probability
    return max(0.0, (b * probability - q) / b)


def recommend_stake(
    probability: float,
    decimal_odds: float,
    bankroll: BankrollState,
    method: str = "fractional_kelly",
    fraction: float = 0.25,
) -> StakeRecommendation:
    if method == "flat":
        return StakeRecommendation(bankroll.unit_size, "flat", "Flat unit stake.")

    if method == "fractional_kelly":
        raw_fraction = kelly_fraction(probability, decimal_odds)
        stake = bankroll.current_bankroll * raw_fraction * fraction
        max_stake = bankroll.current_bankroll * bankroll.max_event_risk_pct
        stake = min(stake, max_stake)
        if stake <= 0:
            return StakeRecommendation(0.0, method, "No positive Kelly edge; pass.")
        return StakeRecommendation(round(stake, 2), method, f"{fraction:.0%} Kelly capped by event risk.")

    raise ValueError(f"Unknown staking method: {method}")


def summarize_records(records: Iterable[BetRecord]) -> dict[str, float | int]:
    rows = list(records)
    total_staked = sum(row.stake for row in rows)
    total_profit = sum(row.profit_loss for row in rows)
    settled = [row for row in rows if row.status in {ResultStatus.WON, ResultStatus.LOST}]
    wins = sum(1 for row in settled if row.status == ResultStatus.WON)
    losses = sum(1 for row in settled if row.status == ResultStatus.LOST)
    return {
        "bets": len(rows),
        "settled": len(settled),
        "wins": wins,
        "losses": losses,
        "total_staked": round(total_staked, 2),
        "profit_loss": round(total_profit, 2),
        "roi": round(total_profit / total_staked, 4) if total_staked else 0.0,
        "hit_rate": round(wins / len(settled), 4) if settled else 0.0,
    }


def roi_by_market(records: Iterable[BetRecord]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[BetRecord]] = defaultdict(list)
    for record in records:
        market_types = sorted({leg.market.market_type.value for leg in record.legs})
        key = "+".join(market_types)
        grouped[key].append(record)
    return {key: summarize_records(value) for key, value in grouped.items()}


def max_daily_exposure(bankroll: BankrollState) -> float:
    return round(bankroll.current_bankroll * bankroll.max_daily_risk_pct, 2)
