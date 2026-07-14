from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import replace
from typing import Any

from .feature_store import FeatureStore
from .models import BetLeg, MarketType, Prediction, Sport
from .probability import (
    both_teams_to_score_probability,
    poisson_over_probability,
    poisson_under_probability,
    win_draw_loss_probabilities,
)
from .shot_model import MODEL_NAME as SHOT_MODEL_NAME, PlayerShotModel

# Leagues we scan when you hit "Fetch today's soccer"
SOCCER_LEAGUES: list[tuple[str, str]] = [
    ("soccer_epl", "Premier League"),
    ("soccer_spain_la_liga", "La Liga"),
    ("soccer_germany_bundesliga", "Bundesliga"),
    ("soccer_italy_serie_a", "Serie A"),
    ("soccer_france_ligue_one", "Ligue 1"),
    ("soccer_usa_mls", "MLS"),
    ("soccer_uefa_champs_league", "Champions League"),
    ("soccer_uefa_europa_league", "Europa League"),
    ("soccer_efl_champ", "Championship"),
    ("soccer_fifa_world_cup", "World Cup"),
]

DEFAULT_SOCCER_MARKETS = "h2h,totals"
DEFAULT_SOCCER_SPORT_KEY = "soccer_epl"
WORLD_CUP_SPORT_KEY = "soccer_fifa_world_cup"
SOCCER_PLAYER_PROP_MARKETS = (
    "player_shots,player_shots_on_target,player_goal_scorer_anytime,player_assists"
)
POISSON_MODEL_NAME = "poisson_soccer_live"


def is_soccer_sport_key(sport_key: str) -> bool:
    return sport_key.startswith("soccer_")


def league_label(sport_key: str) -> str:
    for key, label in SOCCER_LEAGUES:
        if key == sport_key:
            return label
    return sport_key.replace("soccer_", "").replace("_", " ").title()


def _solve_total_lambda(line: float, over_probability: float) -> float:
    """Back out a total-goals rate from an over/under line and book probability."""
    target = min(0.95, max(0.05, over_probability))
    low, high = 0.3, 6.0
    for _ in range(40):
        mid = (low + high) / 2.0
        if poisson_over_probability(line, mid) < target:
            low = mid
        else:
            high = mid
    return round((low + high) / 2.0, 3)


def _team_xg_from_feature_store(
    feature_store: FeatureStore | None,
    team: str,
) -> float | None:
    if feature_store is None:
        return None
    stats = feature_store.team_offensive_rate(team)
    return stats


def estimate_match_xg(
    event_legs: list[BetLeg],
    feature_store: FeatureStore | None = None,
) -> tuple[float, float, dict[str, Any]]:
    """Estimate home/away expected goals from book lines and optional team history."""
    if not event_legs:
        return 1.3, 1.1, {"source": "default"}

    meta = event_legs[0].market.metadata
    home = meta.get("home_team") or event_legs[0].market.team
    away = meta.get("away_team") or event_legs[0].market.opponent

    home_win = away_win = None
    over_implied: float | None = None
    over_line: float | None = None

    for leg in event_legs:
        market = leg.market
        name = (market.team or market.label or "").lower()
        if market.market_type == MarketType.MONEYLINE:
            if home and market.team == home:
                home_win = market.odds.implied_probability
            elif away and market.team == away:
                away_win = market.odds.implied_probability
        if market.market_type == MarketType.TOTAL_GOALS and market.threshold is not None:
            if "over" in name or name == "over":
                over_implied = market.odds.implied_probability
                over_line = market.threshold

    features: dict[str, Any] = {"home_team": home, "away_team": away}

    home_hist = _team_xg_from_feature_store(feature_store, home) if home else None
    away_hist = _team_xg_from_feature_store(feature_store, away) if away else None

    if home_hist is not None and away_hist is not None:
        features["source"] = "team_history"
        return home_hist, away_hist, features

    total_lambda = 2.6
    if over_implied is not None and over_line is not None:
        total_lambda = _solve_total_lambda(over_line, over_implied)
        features["source"] = "book_totals"
        features["total_lambda"] = total_lambda
    else:
        features["source"] = "default"

    if home_win and away_win:
        share = home_win / (home_win + away_win)
    else:
        share = 0.52

    if home_hist is not None:
        home_xg = home_hist
        away_xg = max(0.4, total_lambda - home_xg)
    elif away_hist is not None:
        away_xg = away_hist
        home_xg = max(0.4, total_lambda - away_xg)
    else:
        home_xg = total_lambda * share
        away_xg = total_lambda * (1.0 - share)

    features["home_xg"] = round(home_xg, 3)
    features["away_xg"] = round(away_xg, 3)
    return home_xg, away_xg, features


def _model_probability_for_leg(leg: BetLeg, home_xg: float, away_xg: float) -> float | None:
    market = leg.market
    home = market.metadata.get("home_team")
    away = market.metadata.get("away_team")
    name = (market.team or "").lower()
    wdl = win_draw_loss_probabilities(home_xg, away_xg)
    total_lambda = home_xg + away_xg

    if market.market_type == MarketType.MONEYLINE:
        if home and market.team == home:
            return wdl[0]
        if away and market.team == away:
            return wdl[2]
        if name == "draw":
            return wdl[1]

    if market.market_type == MarketType.TOTAL_GOALS and market.threshold is not None:
        if "over" in name or name == "over":
            return poisson_over_probability(market.threshold, total_lambda)
        if "under" in name or name == "under":
            return poisson_under_probability(market.threshold, total_lambda)

    if market.market_type == MarketType.BOTH_TEAMS_TO_SCORE:
        btts = both_teams_to_score_probability(home_xg, away_xg)
        if "yes" in market.label.lower() or name == "yes":
            return btts
        return 1.0 - btts

    return None


def enrich_soccer_legs_with_poisson(
    legs: list[BetLeg],
    feature_store: FeatureStore | None = None,
    shot_model: PlayerShotModel | None = None,
) -> list[BetLeg]:
    """Replace book-copy predictions with Poisson / shot-model probabilities."""
    by_event: dict[str, list[BetLeg]] = defaultdict(list)
    for leg in legs:
        if leg.market.sport != Sport.SOCCER:
            continue
        by_event[leg.market.event_id].append(leg)

    enriched: list[BetLeg] = []
    for event_legs in by_event.values():
        home_xg, away_xg, xg_features = estimate_match_xg(event_legs, feature_store)
        for leg in event_legs:
            model_p = _model_probability_for_leg(leg, home_xg, away_xg)
            model_name = POISSON_MODEL_NAME
            confidence = 0.55
            features: dict[str, Any] = {**xg_features, "market_type": leg.market.market_type.value}

            if model_p is None and leg.market.player and shot_model and leg.market.threshold is not None:
                projection = shot_model.project(
                    leg.market.player,
                    leg.market.threshold,
                    opponent=leg.market.opponent,
                )
                if projection:
                    model_p = projection.over_probability
                    model_name = SHOT_MODEL_NAME
                    confidence = projection.confidence
                    features = projection.features

            if model_p is None:
                enriched.append(leg)
                continue

            prediction = replace(
                leg.prediction,
                model_probability=round(model_p, 4),
                model_name=model_name,
                confidence=confidence,
                features=features,
            )
            enriched.append(replace(leg, prediction=prediction, tags=_soccer_tags(leg, home_xg, away_xg)))

    non_soccer = [leg for leg in legs if leg.market.sport != Sport.SOCCER]
    return non_soccer + enriched


def _soccer_tags(leg: BetLeg, home_xg: float, away_xg: float) -> tuple[str, ...]:
    tags = set(leg.tags)
    if leg.market.market_type == MarketType.TOTAL_GOALS:
        tags.add("goals")
    if leg.market.market_type == MarketType.BOTH_TEAMS_TO_SCORE:
        tags.add("goals")
    if leg.market.market_type == MarketType.PLAYER_SHOTS:
        tags.add("attacking_volume")
    if home_xg + away_xg >= 2.8:
        tags.add("over")
    if leg.market.team:
        tags.add(leg.market.team.lower().replace(" ", "_"))
    return tuple(sorted(tags))


def group_legs_by_match(legs: list[BetLeg]) -> dict[str, list[BetLeg]]:
    grouped: dict[str, list[BetLeg]] = defaultdict(list)
    for leg in legs:
        meta = leg.market.metadata
        home = meta.get("home_team", "?")
        away = meta.get("away_team", "?")
        league = meta.get("league", "")
        key = f"{home} vs {away}" + (f" ({league})" if league else "")
        grouped[key].append(leg)
    return dict(sorted(grouped.items()))
