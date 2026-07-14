"""Venue-valid parlay construction.

Sportsbook parlays use lines from ONE sportsbook only. Prediction-market
contracts are never mixed into sportsbook slips.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Iterable

from .models import BetLeg, Parlay, VenueType

# Legacy payout-dollar bands (kept for compatibility with build_parlays / reports).
TARGET_BANDS: dict[str, tuple[float, float]] = {
    "small": (60.0, 200.0),
    "big": (500.0, 2_000.0),
    "nuclear": (1_000.0, 5_000.0),
}

LEG_BANDS: dict[str, tuple[int, int]] = {
    "small": (3, 4),
    "big": (5, 6),
    "nuclear": (7, 10),
}

PRESETS: dict[str, dict] = {
    "balanced": {
        "label": "Balanced",
        "min_events": 2,
        "max_per_event": 2,
        "prefer_players": True,
        "same_game_only": False,
        "props_only": False,
    },
    "cross_game": {
        "label": "Cross-game",
        "min_events": 3,
        "max_per_event": 1,
        "prefer_players": False,
        "same_game_only": False,
        "props_only": False,
    },
    "same_game": {
        "label": "Same-game",
        "min_events": 1,
        "max_per_event": 99,
        "prefer_players": True,
        "same_game_only": True,
        "props_only": False,
    },
    "player_props": {
        "label": "Player props",
        "min_events": 1,
        "max_per_event": 3,
        "prefer_players": True,
        "same_game_only": False,
        "props_only": True,
    },
}

MAX_POOL = 14
MAX_COMBOS_PER_BOOK = 8_000


def _selection_key(leg: BetLeg) -> tuple:
    market = leg.market
    outcome = str(market.metadata.get("outcome_name") or "")
    return (
        market.event_id,
        market.market_type.value,
        (market.team or "").lower(),
        (market.player or "").lower(),
        market.threshold,
        outcome.lower(),
    )


def _market_group(leg: BetLeg) -> tuple:
    market = leg.market
    return (
        market.event_id,
        market.market_type.value,
        market.threshold,
        (market.player or "").lower(),
    )


def _is_sportsbook(leg: BetLeg) -> bool:
    return leg.market.venue_type != VenueType.PREDICTION_MARKET and leg.market.sportsbook.lower() not in {
        "kalshi",
        "polymarket",
    }


def prune_pool(
    legs: Iterable[BetLeg],
    min_edge: float = -0.02,
    cap: int = MAX_POOL,
    *,
    props_only: bool = False,
) -> list[BetLeg]:
    """Best price per selection within the provided set, with player/team balance."""
    best: dict[tuple, BetLeg] = {}
    for leg in legs:
        if leg.edge < min_edge:
            continue
        if props_only and not leg.market.player:
            continue
        key = _selection_key(leg)
        current = best.get(key)
        if current is None or leg.decimal_odds > current.decimal_odds:
            best[key] = leg
    ranked = sorted(best.values(), key=lambda leg: (leg.edge, leg.ev_per_dollar), reverse=True)
    player_props = [leg for leg in ranked if leg.market.player]
    match_markets = [leg for leg in ranked if not leg.market.player]
    if props_only:
        seen: set[str] = set()
        diverse: list[BetLeg] = []
        for leg in player_props:
            name = (leg.market.player or "").lower()
            if name in seen:
                continue
            diverse.append(leg)
            seen.add(name)
            if len(diverse) >= cap:
                break
        if len(diverse) < cap:
            selected = {id(x) for x in diverse}
            diverse.extend(x for x in player_props if id(x) not in selected)
        return diverse[:cap]
    if not player_props or not match_markets:
        return ranked[:cap]
    player_slots = max(2, cap // 2)
    diverse_props: list[BetLeg] = []
    seen_players: set[str] = set()
    for leg in player_props:
        player = (leg.market.player or "").lower()
        if player in seen_players:
            continue
        diverse_props.append(leg)
        seen_players.add(player)
        if len(diverse_props) >= player_slots:
            break
    pool = diverse_props[:player_slots] + match_markets[: cap - player_slots]
    if len(pool) < cap:
        selected = {id(leg) for leg in pool}
        pool.extend(leg for leg in ranked if id(leg) not in selected)
    return sorted(pool[:cap], key=lambda leg: (leg.edge, leg.ev_per_dollar), reverse=True)


def _impossible_scoreline(combo: tuple[BetLeg, ...]) -> bool:
    """Reject obvious contradictions (e.g. home win + away win, over + under same line)."""
    by_event: dict[str, list[BetLeg]] = defaultdict(list)
    for leg in combo:
        by_event[leg.market.event_id].append(leg)
    for event_legs in by_event.values():
        ml_teams = [
            (leg.market.team or "").lower()
            for leg in event_legs
            if leg.market.market_type.value == "moneyline"
        ]
        if len(ml_teams) >= 2 and len(set(ml_teams)) >= 2:
            # Two different moneyline sides on the same event cannot both win.
            return True
        totals = [
            (
                leg.market.threshold,
                str(leg.market.metadata.get("outcome_name") or leg.market.team or "").lower(),
            )
            for leg in event_legs
            if leg.market.market_type.value == "total_goals"
        ]
        for line, side in totals:
            opposite = "under" if "over" in side else "over" if "under" in side else ""
            if opposite and any(l == line and opposite in s for l, s in totals):
                return True
    return False


def _has_conflict(combo: tuple[BetLeg, ...], max_per_event: int) -> bool:
    groups = [_market_group(leg) for leg in combo]
    if len(set(groups)) != len(groups):
        return True
    players = [leg.market.player.lower() for leg in combo if leg.market.player]
    if len(set(players)) != len(players):
        return True
    events = Counter(leg.market.event_id for leg in combo)
    if any(count > max_per_event for count in events.values()):
        return True
    if _impossible_scoreline(combo):
        return True
    return False


def _preset_ok(combo: tuple[BetLeg, ...], preset: str) -> bool:
    cfg = PRESETS[preset]
    events = {leg.market.event_id for leg in combo}
    if cfg["same_game_only"] and len(events) != 1:
        return False
    if len(events) < cfg["min_events"]:
        return False
    if cfg["props_only"] and any(not leg.market.player for leg in combo):
        return False
    if cfg["prefer_players"] and not cfg["props_only"]:
        # Soft requirement already handled by pool; require at least one player when available.
        pass
    return True


def score_correlation(legs: tuple[BetLeg, ...]) -> float:
    if not legs:
        return 0.0
    tags = [set(leg.tags) for leg in legs]
    shared_tags = set.intersection(*tags) if all(tags) else set()
    teams = {leg.market.team for leg in legs if leg.market.team}
    events = {leg.market.event_id for leg in legs}
    score = 0.0
    score += len(shared_tags) * 0.35
    # Same-game is concentration risk for most presets — slight penalty default.
    if len(events) == 1:
        score -= 0.15
    if len(teams) == 1:
        score -= 0.2
    if any("goals" in leg.tags for leg in legs) and any("attacking_volume" in leg.tags for leg in legs):
        score += 0.4
    if any("under" in leg.tags for leg in legs) and any("over" in leg.tags for leg in legs):
        score -= 1.2
    return score


def score_risk(legs: tuple[BetLeg, ...]) -> float:
    low_probability_penalty = sum(max(0.0, 0.45 - leg.model_probability) for leg in legs)
    negative_edge_penalty = sum(abs(min(0.0, leg.edge)) for leg in legs)
    leg_count_penalty = max(0, len(legs) - 3) * 0.45
    longshot_penalty = sum(0.25 for leg in legs if leg.market.odds.value >= 200)
    event_concentration = max(0, Counter(l.market.event_id for l in legs).most_common(1)[0][1] - 1) * 0.35
    return low_probability_penalty + negative_edge_penalty + leg_count_penalty + longshot_penalty + event_concentration


def _rank_key(parlay: Parlay) -> tuple:
    event_count = len({leg.market.event_id for leg in parlay.legs})
    player_count = sum(1 for leg in parlay.legs if leg.market.player)
    market_types = len({leg.market.market_type.value for leg in parlay.legs})
    return (
        parlay.expected_value,
        event_count,
        player_count,
        market_types,
        parlay.adjusted_probability,
        -parlay.risk_score,
    )


def _suggest_for_book(
    book_legs: list[BetLeg],
    *,
    stake: float,
    band: str,
    preset: str,
    count: int,
    min_edge: float,
) -> list[Parlay]:
    cfg = PRESETS[preset]
    lo, hi = LEG_BANDS[band]
    pool = prune_pool(book_legs, min_edge=min_edge, props_only=cfg["props_only"])
    if len(pool) < lo:
        return []
    available_players = sum(1 for leg in pool if leg.market.player)
    desired_players = {"small": 1, "big": 2, "nuclear": 3}.get(band, 1) if cfg["prefer_players"] else 0
    if cfg["props_only"]:
        desired_players = lo
    min_players = min(available_players, desired_players)

    parlays: list[Parlay] = []
    combos_seen = 0
    for size in range(lo, min(hi, len(pool)) + 1):
        for combo in combinations(pool, size):
            combos_seen += 1
            if combos_seen > MAX_COMBOS_PER_BOOK:
                break
            if _has_conflict(combo, cfg["max_per_event"]):
                continue
            if not _preset_ok(combo, preset):
                continue
            if sum(1 for leg in combo if leg.market.player) < min_players:
                continue
            book = combo[0].market.sportsbook
            parlays.append(
                Parlay(
                    legs=combo,
                    stake=stake,
                    target_band=band,
                    correlation_score=score_correlation(combo),
                    risk_score=score_risk(combo),
                    notes=f"Single-venue slip @ {book} ({PRESETS[preset]['label']}). Combined odds estimated.",
                    venue=book,
                    preset=preset,
                    combined_odds_estimated=True,
                )
            )
        if combos_seen > MAX_COMBOS_PER_BOOK:
            break
    parlays.sort(key=_rank_key, reverse=True)
    return parlays[:count]


def suggest_parlays(
    legs: Iterable[BetLeg],
    stake: float = 3.0,
    band: str = "small",
    count: int = 3,
    min_edge: float = -0.02,
    preset: str = "balanced",
) -> list[Parlay]:
    """Auto-suggested single-sportsbook parlays for a leg-count band + preset."""
    if band not in LEG_BANDS:
        raise ValueError(f"Unknown leg band: {band}")
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset: {preset}")

    by_book: dict[str, list[BetLeg]] = defaultdict(list)
    for leg in legs:
        if not _is_sportsbook(leg):
            continue
        by_book[leg.market.sportsbook].append(leg)

    candidates: list[Parlay] = []
    for book_legs in by_book.values():
        candidates.extend(
            _suggest_for_book(
                book_legs,
                stake=stake,
                band=band,
                preset=preset,
                count=count,
                min_edge=min_edge,
            )
        )
    candidates.sort(key=_rank_key, reverse=True)

    # Diversify returned suggestions across venues and events.
    selected: list[Parlay] = []
    used_signatures: set[tuple] = set()
    for parlay in candidates:
        sig = tuple(sorted(_selection_key(leg) for leg in parlay.legs))
        if sig in used_signatures:
            continue
        used_signatures.add(sig)
        selected.append(parlay)
        if len(selected) >= count:
            break
    return selected


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
    sportsbook_legs = [leg for leg in legs if _is_sportsbook(leg)]
    by_book: dict[str, list[BetLeg]] = defaultdict(list)
    for leg in sportsbook_legs:
        by_book[leg.market.sportsbook].append(leg)

    parlays: list[Parlay] = []
    for book, book_legs in by_book.items():
        eligible = prune_pool(book_legs, min_edge=min_edge)
        for size in range(min_legs, max_legs + 1):
            for combo in combinations(eligible, size):
                if _has_conflict(combo, max_per_event=2):
                    continue
                decimal_odds = 1.0
                for leg in combo:
                    decimal_odds *= leg.decimal_odds
                payout = stake * decimal_odds
                if payout < low or payout > high:
                    continue
                parlays.append(
                    Parlay(
                        legs=combo,
                        stake=stake,
                        target_band=target_band,
                        correlation_score=score_correlation(combo),
                        risk_score=score_risk(combo),
                        notes=f"Built by Headcrack AI EV optimizer @ {book}.",
                        venue=book,
                        preset="balanced",
                        combined_odds_estimated=True,
                    )
                )
    return sorted(parlays, key=_rank_key, reverse=True)[:top_n]


def build_card(
    legs: Iterable[BetLeg],
    budget: float = 20.0,
    min_edge: float = -0.02,
) -> dict[str, list[Parlay]]:
    allocation = {"small": 3.0, "big": 4.0, "nuclear": 3.0}
    if budget < 20:
        scale = budget / 20.0
        allocation = {band: max(1.0, stake * scale) for band, stake in allocation.items()}
    legs_tuple = tuple(legs)
    return {
        "small": build_parlays(legs_tuple, allocation["small"], "small", min_edge=min_edge, top_n=5),
        "big": build_parlays(legs_tuple, allocation["big"], "big", min_edge=min_edge, top_n=5),
        "nuclear": build_parlays(legs_tuple, allocation["nuclear"], "nuclear", min_edge=min_edge, top_n=5),
    }
