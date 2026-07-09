from __future__ import annotations

import math
import random
from collections import Counter
from functools import lru_cache
from typing import Iterable


def clamp_probability(value: float) -> float:
    return min(0.999, max(0.001, value))


def american_to_decimal(odds: int) -> float:
    if odds > 0:
        return 1.0 + odds / 100.0
    if odds < 0:
        return 1.0 + 100.0 / abs(odds)
    raise ValueError("American odds cannot be zero")


def american_to_implied_probability(odds: int) -> float:
    if odds > 0:
        return 100.0 / (odds + 100.0)
    if odds < 0:
        return abs(odds) / (abs(odds) + 100.0)
    raise ValueError("American odds cannot be zero")


def decimal_to_american(decimal_odds: float) -> int:
    if decimal_odds < 1.0:
        raise ValueError("decimal_odds must be >= 1")
    if decimal_odds >= 2.0:
        return round((decimal_odds - 1.0) * 100)
    return round(-100 / (decimal_odds - 1.0))


def expected_value(probability: float, decimal_odds: float, stake: float = 1.0) -> float:
    probability = clamp_probability(probability)
    profit = stake * (decimal_odds - 1.0)
    return probability * profit - (1.0 - probability) * stake


@lru_cache(maxsize=4096)
def poisson_pmf(k: int, lam: float) -> float:
    if k < 0:
        return 0.0
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def poisson_cdf(k: int, lam: float) -> float:
    return sum(poisson_pmf(i, lam) for i in range(k + 1))


def poisson_over_probability(line: float, lam: float, max_count: int = 15) -> float:
    threshold = math.floor(line) + 1
    return sum(poisson_pmf(k, lam) for k in range(threshold, max_count + 1))


def poisson_under_probability(line: float, lam: float, max_count: int = 15) -> float:
    return 1.0 - poisson_over_probability(line, lam, max_count=max_count)


def both_teams_to_score_probability(home_xg: float, away_xg: float) -> float:
    return (1.0 - poisson_pmf(0, home_xg)) * (1.0 - poisson_pmf(0, away_xg))


def win_draw_loss_probabilities(home_xg: float, away_xg: float, max_goals: int = 12) -> tuple[float, float, float]:
    home_win = draw = away_win = 0.0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_pmf(h, home_xg) * poisson_pmf(a, away_xg)
            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p
    total = home_win + draw + away_win
    return home_win / total, draw / total, away_win / total


def qualify_probability_from_wdl(win: float, draw: float, loss: float, shootout_strength: float = 0.5) -> float:
    # Knockout qualification: win in regulation + draw * shootout/extra-time edge.
    return clamp_probability(win + draw * shootout_strength)


def sample_poisson(lam: float, rng: random.Random) -> int:
    # Knuth sampler, fine for soccer-style low lambdas.
    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= rng.random()
    return k - 1


def monte_carlo_soccer_match(
    home_xg: float,
    away_xg: float,
    simulations: int = 50_000,
    seed: int | None = 42,
) -> dict[str, float | dict[str, int]]:
    rng = random.Random(seed)
    scores: Counter[str] = Counter()
    home_wins = draws = away_wins = btts = over_25 = over_35 = 0

    for _ in range(simulations):
        h = sample_poisson(home_xg, rng)
        a = sample_poisson(away_xg, rng)
        scores[f"{h}-{a}"] += 1
        total = h + a
        if h > a:
            home_wins += 1
        elif h == a:
            draws += 1
        else:
            away_wins += 1
        if h > 0 and a > 0:
            btts += 1
        if total >= 3:
            over_25 += 1
        if total >= 4:
            over_35 += 1

    return {
        "home_win": home_wins / simulations,
        "draw": draws / simulations,
        "away_win": away_wins / simulations,
        "btts": btts / simulations,
        "over_2_5": over_25 / simulations,
        "over_3_5": over_35 / simulations,
        "top_scores": dict(scores.most_common(10)),
    }


def ensemble_probability(probabilities: Iterable[float], weights: Iterable[float] | None = None) -> float:
    probs = list(probabilities)
    if not probs:
        raise ValueError("probabilities cannot be empty")
    if weights is None:
        return clamp_probability(sum(probs) / len(probs))
    w = list(weights)
    if len(w) != len(probs):
        raise ValueError("weights and probabilities must have the same length")
    total_weight = sum(w)
    if total_weight <= 0:
        raise ValueError("weights must sum to a positive number")
    return clamp_probability(sum(p * weight for p, weight in zip(probs, w)) / total_weight)
