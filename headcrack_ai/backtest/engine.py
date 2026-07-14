from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..models import BetLeg


@dataclass(frozen=True)
class BacktestBet:
    leg: BetLeg
    stake: float
    won: bool


@dataclass
class BacktestConfig:
    min_edge: float = 0.02
    flat_stake: float = 5.0
    max_bets: int = 500
    vig_penalty: float = 0.02  # extra implied prob drag


@dataclass
class BacktestResult:
    bets: int
    wins: int
    total_staked: float
    profit_loss: float
    roi: float
    hit_rate: float
    max_drawdown: float


def simulate_flat_bets(bets: Iterable[BacktestBet]) -> BacktestResult:
    rows = list(bets)
    if not rows:
        return BacktestResult(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
    staked = sum(b.stake for b in rows)
    pnl = 0.0
    wins = 0
    peak = 0.0
    equity = 0.0
    max_dd = 0.0
    for bet in rows:
        if bet.won:
            profit = bet.stake * (bet.leg.decimal_odds - 1.0)
            pnl += profit
            wins += 1
        else:
            pnl -= bet.stake
        equity += pnl if bet.won else -bet.stake
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return BacktestResult(
        bets=len(rows),
        wins=wins,
        total_staked=round(staked, 2),
        profit_loss=round(pnl, 2),
        roi=round(pnl / staked, 4) if staked else 0.0,
        hit_rate=round(wins / len(rows), 4),
        max_drawdown=round(max_dd, 2),
    )


def run_edge_backtest(legs: list[BetLeg], outcomes: dict[str, bool], config: BacktestConfig | None = None) -> BacktestResult:
    """Backtest singles where model edge exceeds threshold."""
    config = config or BacktestConfig()
    bets: list[BacktestBet] = []
    for leg in legs:
        adj_implied = min(0.99, leg.implied_probability + config.vig_penalty)
        edge = leg.model_probability - adj_implied
        if edge < config.min_edge:
            continue
        won = outcomes.get(leg.market.market_id, False)
        bets.append(BacktestBet(leg=leg, stake=config.flat_stake, won=won))
        if len(bets) >= config.max_bets:
            break
    return simulate_flat_bets(bets)
