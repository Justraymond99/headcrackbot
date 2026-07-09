from __future__ import annotations

from itertools import combinations
from typing import Iterable

from .models import BetLeg, Parlay

TARGET_BANDS: dict[str, tuple[float, float]] = {
    "small": (60.0, 200.0),
    "big": (500.0, 2_000.0),
    "nuclear": (1_000.0, 5_000.0),
}


def score_correlation(legs: tuple[BetLeg, ...]) -> float:
    if not legs:
        return 0.0
    tags = [set(leg.tags) for leg in legs]
    shared_tags = set.intersection(*tags) if all(tags) else set()
    teams = {leg.market.team for leg in legs if leg.market.team}
    events = {leg.market.event_id for leg in legs}

    score = 0.0
    score += len(shared_tags) * 0.55
    if len(events) == 1:
        score += 0.7
    if len(teams) == 1:
        score += 0.8
    if any("goals" in leg.tags for leg in legs) and any("attacking_volume" in leg.tags for leg in legs):
        score += 0.6
    if any("underdog_goal" in leg.tags for leg in legs) and any("favorite_clean_sheet" in leg.tags for leg in legs):
        score -= 1.25
    if any("under" in leg.tags for leg in legs) and any("over" in leg.tags for leg in legs):
        score -= 1.0
    return score


def score_risk(legs: tuple[BetLeg, ...]) -> float:
    # Risk increases with leg count, low model probabilities, and negative edges.
    low_probability_penalty = sum(max(0.0, 0.45 - leg.model_probability) for leg in legs)
    negative_edge_penalty = sum(abs(min(0.0, leg.edge)) for leg in legs)
    leg_count_penalty = max(0, len(legs) - 3) * 0.45
    longshot_penalty = sum(0.25 for leg in legs if leg.market.odds.value >= 200)
    return low_probability_penalty + negative_edge_penalty + leg_count_penalty + longshot_penalty


def build_parlays(
    legs: Iterable[BetLeg],
    stake: float,
    target_band: str,
    min_edge: float = 0.0,
    min_legs: int = 2,
    max_legs: int = 6,
    top_n: int = 20,
) -> list[Parlay]:
    if target_band not in TARGET_BANDS:
        raise ValueError(f"Unknown target band: {target_band}")
    low, high = TARGET_BANDS[target_band]
    eligible = [leg for leg in legs if leg.edge >= min_edge]
    parlays: list[Parlay] = []

    for size in range(min_legs, max_legs + 1):
        for combo in combinations(eligible, size):
            decimal_odds = 1.0
            for leg in combo:
                decimal_odds *= leg.decimal_odds
            payout = stake * decimal_odds
            if payout < low or payout > high:
                continue
            corr = score_correlation(combo)
            risk = score_risk(combo)
            parlays.append(
                Parlay(
                    legs=combo,
                    stake=stake,
                    target_band=target_band,
                    correlation_score=corr,
                    risk_score=risk,
                    notes="Built by Headcrack AI EV optimizer.",
                )
            )

    return sorted(
        parlays,
        key=lambda parlay: (
            parlay.expected_value,
            parlay.adjusted_probability,
            parlay.correlation_score,
            -parlay.risk_score,
        ),
        reverse=True,
    )[:top_n]


def build_card(
    legs: Iterable[BetLeg],
    budget: float = 20.0,
    min_edge: float = -0.02,
) -> dict[str, list[Parlay]]:
    # Ladder strategy: several realistic slips plus big payout shots.
    allocation = {
        "small": 3.0,
        "big": 4.0,
        "nuclear": 3.0,
    }
    if budget < 20:
        scale = budget / 20.0
        allocation = {band: max(1.0, stake * scale) for band, stake in allocation.items()}

    legs_tuple = tuple(legs)
    return {
        "small": build_parlays(legs_tuple, allocation["small"], "small", min_edge=min_edge, top_n=5),
        "big": build_parlays(legs_tuple, allocation["big"], "big", min_edge=min_edge, top_n=5),
        "nuclear": build_parlays(legs_tuple, allocation["nuclear"], "nuclear", min_edge=min_edge, top_n=5),
    }
