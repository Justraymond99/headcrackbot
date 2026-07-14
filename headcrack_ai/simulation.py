"""Odds-informed joint simulation for matches and parlays.

Each Monte Carlo run samples one coherent scoreline (and proxy player outcomes)
so same-game legs are graded against the same world. Multi-game slips sample
each event independently.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from .models import BetLeg, MarketType, Parlay
from .probability import (
    sample_poisson,
)
from .soccer import estimate_match_xg, group_legs_by_match


@dataclass(frozen=True)
class MatchSimResult:
    match: str
    home_team: str
    away_team: str
    home_xg: float
    away_xg: float
    simulations: int
    home_win: float
    draw: float
    away_win: float
    btts: float
    over_2_5: float
    over_3_5: float
    expected_home_goals: float
    expected_away_goals: float
    top_scores: dict[str, int]
    source: str
    prediction_market_compare: list[dict[str, Any]]


def de_vig_moneyline(legs: list[BetLeg]) -> dict[str, float]:
    """Return de-vigged implied probs for home/draw/away when available."""
    if not legs:
        return {}
    meta = legs[0].market.metadata
    home = meta.get("home_team")
    away = meta.get("away_team")
    best: dict[str, float] = {}
    for leg in legs:
        if leg.market.market_type != MarketType.MONEYLINE:
            continue
        team = (leg.market.team or "").lower()
        key = None
        if home and leg.market.team == home:
            key = "home"
        elif away and leg.market.team == away:
            key = "away"
        elif team == "draw":
            key = "draw"
        if key is None:
            continue
        # Prefer best (shortest) implied = highest price for consensus floor; use avg later.
        implied = leg.implied_probability
        best[key] = min(best.get(key, 1.0), implied) if key in best else implied
    if len(best) < 2:
        return {}
    total = sum(best.values()) or 1.0
    return {k: v / total for k, v in best.items()}


def calibrate_xg_to_odds(
    home_xg: float,
    away_xg: float,
    consensus: dict[str, float],
) -> tuple[float, float]:
    """Lightly nudge xG so simulated WDL roughly tracks de-vigged book consensus."""
    if not consensus or "home" not in consensus:
        return home_xg, away_xg
    target_home = consensus.get("home", 0.4)
    # Bias share toward consensus without exploding totals.
    total = home_xg + away_xg
    share = 0.55 * (home_xg / total if total else 0.5) + 0.45 * target_home
    share = min(0.78, max(0.22, share))
    return round(total * share, 3), round(total * (1 - share), 3)


def _grade_leg(leg: BetLeg, home_goals: int, away_goals: int, rng: random.Random) -> bool:
    market = leg.market
    meta = market.metadata
    home = meta.get("home_team")
    away = meta.get("away_team")
    name = (str(meta.get("outcome_name") or market.team or "")).lower()
    total = home_goals + away_goals

    if market.market_type == MarketType.MONEYLINE:
        if home and market.team == home:
            return home_goals > away_goals
        if away and market.team == away:
            return away_goals > home_goals
        if name == "draw" or (market.team or "").lower() == "draw":
            return home_goals == away_goals
        return False

    if market.market_type == MarketType.TOTAL_GOALS and market.threshold is not None:
        if "over" in name:
            return total > market.threshold
        if "under" in name:
            return total < market.threshold
        return False

    if market.market_type == MarketType.BOTH_TEAMS_TO_SCORE:
        scored = home_goals > 0 and away_goals > 0
        if "yes" in name or "yes" in market.label.lower():
            return scored
        return not scored

    if market.market_type in {
        MarketType.PLAYER_SHOTS,
        MarketType.PLAYER_SHOTS_ON_TARGET,
        MarketType.PLAYER_GOAL,
        MarketType.PLAYER_ASSIST,
    }:
        # Proxy: sample a player contribution correlated with match xG features.
        base = float(leg.prediction.features.get("expected_shots") or 0)
        if base <= 0:
            # Fallback intensity from model probability / threshold.
            if market.threshold is not None and market.threshold > 0:
                base = max(0.2, leg.model_probability * (market.threshold + 0.5) * 1.4)
            else:
                base = max(0.15, leg.model_probability * 1.2)
        # Mild correlation with scoring: bump when the player's team scores.
        team = (market.team or "").lower()
        if home and team == str(home).lower() and home_goals > 0:
            base *= 1.1
        if away and team == str(away).lower() and away_goals > 0:
            base *= 1.1
        realized = sample_poisson(base, rng)
        if market.market_type == MarketType.PLAYER_GOAL:
            # Approximate anytime goal with independent Poisson shots→goal proxy.
            return realized >= 1 and rng.random() < min(0.85, max(0.05, leg.model_probability))
        if market.threshold is None:
            return realized >= 1
        if "under" in name:
            return realized < market.threshold
        return realized > market.threshold

    # Unsupported markets: grade independently by model probability.
    return rng.random() < leg.model_probability


def simulate_match_from_legs(
    match_legs: list[BetLeg],
    simulations: int = 10_000,
    seed: int | None = 42,
    prediction_legs: list[BetLeg] | None = None,
) -> MatchSimResult:
    home_xg, away_xg, features = estimate_match_xg(match_legs)
    consensus = de_vig_moneyline(match_legs)
    if consensus:
        home_xg, away_xg = calibrate_xg_to_odds(home_xg, away_xg, consensus)
        source = "odds_consensus+poisson"
    else:
        source = str(features.get("source", "poisson"))

    rng = random.Random(seed)
    scores: Counter[str] = Counter()
    home_wins = draws = away_wins = btts = over_25 = over_35 = 0
    sum_h = sum_a = 0
    for _ in range(simulations):
        h = sample_poisson(home_xg, rng)
        a = sample_poisson(away_xg, rng)
        sum_h += h
        sum_a += a
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

    compare: list[dict[str, Any]] = []
    for pred in prediction_legs or []:
        if pred.market.venue_type.value != "prediction_market" and pred.market.sportsbook.lower() not in {
            "kalshi",
            "polymarket",
        }:
            continue
        compare.append(
            {
                "venue": pred.market.sportsbook,
                "label": pred.market.label,
                "implied": round(pred.implied_probability, 4),
                "liquidity": pred.market.liquidity,
                "matched": bool(pred.market.canonical_event_id),
            }
        )

    home = str(features.get("home_team") or "")
    away = str(features.get("away_team") or "")
    match_name = f"{home} vs {away}" if home and away else "Match"
    return MatchSimResult(
        match=match_name,
        home_team=home,
        away_team=away,
        home_xg=home_xg,
        away_xg=away_xg,
        simulations=simulations,
        home_win=home_wins / simulations,
        draw=draws / simulations,
        away_win=away_wins / simulations,
        btts=btts / simulations,
        over_2_5=over_25 / simulations,
        over_3_5=over_35 / simulations,
        expected_home_goals=sum_h / simulations,
        expected_away_goals=sum_a / simulations,
        top_scores=dict(scores.most_common(8)),
        source=source,
        prediction_market_compare=compare[:6],
    )


def simulate_parlay(
    parlay: Parlay,
    all_event_legs: Iterable[BetLeg] | None = None,
    simulations: int = 8_000,
    seed: int | None = 42,
) -> dict[str, Any]:
    """Joint-simulate every leg; same-event legs share one scoreline per run."""
    event_legs_index: dict[str, list[BetLeg]] = defaultdict(list)
    for leg in all_event_legs or []:
        event_legs_index[leg.market.event_id].append(leg)

    # Build xG per event involved in the slip.
    event_xg: dict[str, tuple[float, float]] = {}
    for leg in parlay.legs:
        eid = leg.market.event_id
        if eid in event_xg:
            continue
        pool = event_legs_index.get(eid) or [leg]
        home_xg, away_xg, features = estimate_match_xg(pool)
        consensus = de_vig_moneyline(pool)
        if consensus:
            home_xg, away_xg = calibrate_xg_to_odds(home_xg, away_xg, consensus)
        event_xg[eid] = (home_xg, away_xg)

    rng = random.Random(seed)
    hit_counts = [0] * len(parlay.legs)
    slip_hits = 0
    lose_leg_counter: Counter[int] = Counter()
    win_examples: list[dict[str, int]] = []
    loss_examples: list[dict[str, int]] = []

    for _ in range(simulations):
        scored: dict[str, tuple[int, int]] = {}
        for eid, (hxg, axg) in event_xg.items():
            scored[eid] = (sample_poisson(hxg, rng), sample_poisson(axg, rng))
        results = []
        for idx, leg in enumerate(parlay.legs):
            h, a = scored[leg.market.event_id]
            ok = _grade_leg(leg, h, a, rng)
            results.append(ok)
            if ok:
                hit_counts[idx] += 1
        if all(results):
            slip_hits += 1
            if len(win_examples) < 5:
                win_examples.append({eid: f"{h}-{a}" for eid, (h, a) in scored.items()})
        else:
            for idx, ok in enumerate(results):
                if not ok:
                    lose_leg_counter[idx] += 1
                    break
            if len(loss_examples) < 5:
                loss_examples.append({eid: f"{h}-{a}" for eid, (h, a) in scored.items()})

    slip_p = slip_hits / simulations
    fair_decimal = (1.0 / slip_p) if slip_p > 0 else None
    stake = parlay.stake
    profit = stake * (parlay.decimal_odds - 1.0)
    ev = slip_p * profit - (1.0 - slip_p) * stake

    leg_rows = []
    for idx, leg in enumerate(parlay.legs):
        support = leg.prediction.model_name
        if support == "book_baseline":
            backing = "consensus/book"
        elif "poisson" in support or "shot" in support:
            backing = "model"
        else:
            backing = support
        leg_rows.append(
            {
                "pick": leg.market.label,
                "book": leg.market.sportsbook,
                "hit_rate": round(hit_counts[idx] / simulations, 4),
                "model_prob": round(leg.model_probability, 4),
                "backing": backing,
            }
        )

    common_loss = None
    if lose_leg_counter:
        idx, _ = lose_leg_counter.most_common(1)[0]
        common_loss = parlay.legs[idx].market.label

    return {
        "simulations": simulations,
        "slip_hit_rate": round(slip_p, 4),
        "fair_decimal_odds": round(fair_decimal, 3) if fair_decimal else None,
        "estimated_decimal_odds": round(parlay.decimal_odds, 3),
        "combined_odds_estimated": parlay.combined_odds_estimated,
        "venue": parlay.venue or parlay.sportsbook,
        "stake": stake,
        "expected_value": round(ev, 3),
        "legs": leg_rows,
        "most_common_losing_leg": common_loss,
        "win_scenarios": win_examples,
        "loss_scenarios": loss_examples,
        "event_xg": {eid: {"home_xg": hxg, "away_xg": axg} for eid, (hxg, axg) in event_xg.items()},
    }


def format_match_sim(result: MatchSimResult) -> str:
    lines = [
        f"### {result.match}",
        f"**xG (odds-informed):** {result.home_team} {result.home_xg:.2f} — {result.away_xg:.2f} {result.away_team}",
        f"**Win chances:** Home {result.home_win:.1%} · Draw {result.draw:.1%} · Away {result.away_win:.1%}",
        f"**Expected score:** {result.expected_home_goals:.2f} – {result.expected_away_goals:.2f}",
        f"**BTTS:** {result.btts:.1%} · **Over 2.5:** {result.over_2_5:.1%} · **Over 3.5:** {result.over_3_5:.1%}",
        f"**Source:** {result.source} · {result.simulations:,} sims",
    ]
    if result.top_scores:
        tops = ", ".join(f"{k} ({v})" for k, v in list(result.top_scores.items())[:5])
        lines.append(f"**Top scorelines:** {tops}")
    if result.prediction_market_compare:
        lines.append("**Prediction markets:**")
        for row in result.prediction_market_compare:
            liq = f", liq {row['liquidity']:.0f}" if row.get("liquidity") else ""
            lines.append(f"- {row['venue']}: {row['implied']:.1%}{liq}")
    return "\n".join(lines)


def format_parlay_sim(result: dict[str, Any]) -> str:
    lines = [
        f"### Slip simulation @ {result.get('venue', '?')}",
        f"**Hit rate:** {result['slip_hit_rate']:.1%} over {result['simulations']:,} runs",
        f"**Fair odds:** {result.get('fair_decimal_odds') or '—'} · "
        f"**Book product (est.):** {result.get('estimated_decimal_odds')}",
        f"**EV on ${result['stake']:.0f} stake:** ${result['expected_value']:+.2f}",
    ]
    if result.get("most_common_losing_leg"):
        lines.append(f"**Most common first failure:** {result['most_common_losing_leg']}")
    lines.append("**Per-leg hit rates:**")
    for leg in result.get("legs", []):
        lines.append(
            f"- {leg['pick']} — {leg['hit_rate']:.1%} hit · model {leg['model_prob']:.1%} ({leg['backing']})"
        )
    return "\n".join(lines)


def list_live_matches(legs: list[BetLeg]) -> list[str]:
    return list(group_legs_by_match(legs).keys())
