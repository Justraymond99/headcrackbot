from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from ..http.retry import retry_http
from ..logging_config import get_logger
from ..models import AmericanOdds, Market, MarketType, Sport, VenueType
from ..probability import decimal_to_american
from ..providers.matcher import attach_canonical_ids, canonical_event_key, canonical_outcome_key

logger = get_logger(__name__)


@dataclass(frozen=True)
class OddsApiClient:
    api_key: str
    base_url: str = "https://api.the-odds-api.com/v4"

    @retry_http()
    def _get_json(self, path: str, params: dict[str, Any]) -> Any:
        query = urllib.parse.urlencode({**params, "apiKey": self.api_key})
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}?{query}"
        logger.debug("Fetching %s", path)
        with urllib.request.urlopen(url, timeout=20) as response:  # nosec B310
            return json.loads(response.read().decode("utf-8"))

    def list_sports(self) -> list[dict[str, Any]]:
        return self._get_json("sports", {})

    def fetch_odds(
        self,
        sport_key: str,
        regions: str = "us",
        markets: str = "h2h,totals,spreads",
        odds_format: str = "american",
    ) -> list[dict[str, Any]]:
        return self._get_json(
            f"sports/{sport_key}/odds",
            {
                "regions": regions,
                "markets": markets,
                "oddsFormat": odds_format,
            },
        )

    def list_events(self, sport_key: str) -> list[dict[str, Any]]:
        """Return upcoming events without consuming odds-market quota."""
        return self._get_json(f"sports/{sport_key}/events", {})

    def fetch_event_odds(
        self,
        sport_key: str,
        event_id: str,
        regions: str = "us",
        markets: str = "player_shots,player_shots_on_target",
        odds_format: str = "american",
    ) -> dict[str, Any]:
        """Fetch event-level markets such as soccer player props."""
        return self._get_json(
            f"sports/{sport_key}/events/{event_id}/odds",
            {
                "regions": regions,
                "markets": markets,
                "oddsFormat": odds_format,
            },
        )


def _market_type_from_key(key: str) -> MarketType:
    if key == "h2h":
        return MarketType.MONEYLINE
    if key == "totals":
        return MarketType.TOTAL_GOALS
    if key == "spreads":
        return MarketType.SPREAD
    if key == "player_shots":
        return MarketType.PLAYER_SHOTS
    if key == "player_shots_on_target":
        return MarketType.PLAYER_SHOTS_ON_TARGET
    if key in {"player_goal_scorer_anytime", "player_first_goal_scorer", "player_last_goal_scorer"}:
        return MarketType.PLAYER_GOAL
    if key == "player_assists":
        return MarketType.PLAYER_ASSIST
    return MarketType.CUSTOM


def _american_price(price: int | float, odds_format: str = "american") -> int:
    normalized_format = odds_format.lower()
    if normalized_format == "american":
        return int(price)
    if normalized_format == "decimal":
        return decimal_to_american(float(price))
    raise ValueError(f"Unsupported Odds API odds format: {odds_format}")


def normalize_odds_api_events(
    events: list[dict[str, Any]],
    sport: Sport = Sport.SOCCER,
    odds_format: str = "american",
    league: str | None = None,
) -> list[Market]:
    markets: list[Market] = []
    for event in events:
        event_id = str(event.get("id"))
        home_team = event.get("home_team")
        away_team = event.get("away_team")
        match_label = f"{home_team} vs {away_team}"
        for bookmaker in event.get("bookmakers", []):
            sportsbook = bookmaker.get("key") or bookmaker.get("title") or "unknown"
            for market_payload in bookmaker.get("markets", []):
                market_key = market_payload.get("key", "custom")
                market_type = _market_type_from_key(market_key)
                for outcome in market_payload.get("outcomes", []):
                    price = outcome.get("price")
                    if price is None:
                        continue
                    outcome_name = outcome.get("name") or "unknown"
                    player = outcome.get("description")
                    point = outcome.get("point")
                    market_id = (
                        f"oddsapi:{event_id}:{sportsbook}:{market_key}:"
                        f"{player or outcome_name}:{outcome_name}:{point}"
                    )
                    label = _friendly_outcome_label(
                        match_label,
                        market_key,
                        outcome_name,
                        point,
                        home_team,
                        away_team,
                        player=player,
                    )
                    team = _team_for_outcome(outcome_name, home_team, away_team, market_type)
                    markets.append(
                        attach_canonical_ids(
                            Market(
                                market_id=market_id,
                                sport=sport,
                                event_id=event_id,
                                label=label,
                                market_type=market_type,
                                sportsbook=sportsbook,
                                odds=AmericanOdds(_american_price(price, odds_format=odds_format)),
                                team=team,
                                opponent=away_team if team == home_team else home_team if team else None,
                                player=player,
                                threshold=float(point) if point is not None else None,
                                metadata={
                                    "source": "the_odds_api",
                                    "home_team": home_team,
                                    "away_team": away_team,
                                    "league": league,
                                    "commence_time": event.get("commence_time"),
                                    "market_key": market_key,
                                    "odds_format": odds_format,
                                    "raw_price": price,
                                    "outcome_name": outcome_name,
                                    "player": player,
                                },
                                venue_type=VenueType.SPORTSBOOK,
                                canonical_event_id=canonical_event_key(home_team, away_team, league),
                                canonical_outcome_id=canonical_outcome_key(
                                    market_type,
                                    team=team,
                                    player=player,
                                    threshold=float(point) if point is not None else None,
                                    outcome=outcome_name,
                                ),
                            )
                        )
                    )
    return markets


def _team_for_outcome(
    outcome_name: str,
    home_team: str | None,
    away_team: str | None,
    market_type: MarketType,
) -> str | None:
    if market_type == MarketType.TOTAL_GOALS:
        return outcome_name  # "Over" / "Under"
    if market_type == MarketType.MONEYLINE:
        if outcome_name == home_team:
            return home_team
        if outcome_name == away_team:
            return away_team
        if outcome_name.lower() == "draw":
            return "Draw"
    if market_type == MarketType.SPREAD:
        return outcome_name
    return None


def _friendly_outcome_label(
    match_label: str,
    market_key: str,
    outcome_name: str,
    point: float | None,
    home_team: str | None,
    away_team: str | None,
    player: str | None = None,
) -> str:
    if market_key == "h2h":
        if outcome_name.lower() == "draw":
            return f"{match_label} — Draw"
        if outcome_name == home_team:
            return f"{match_label} — {home_team} to win"
        if outcome_name == away_team:
            return f"{match_label} — {away_team} to win"
        return f"{match_label} — {outcome_name}"
    if market_key == "totals" and point is not None:
        return f"{match_label} — {outcome_name} {point} goals"
    if market_key == "spreads" and point is not None:
        return f"{match_label} — {outcome_name} {point:+g}"
    if player:
        prop_labels = {
            "player_shots": "shots",
            "player_shots_on_target": "shots on target",
            "player_assists": "assists",
            "player_goal_scorer_anytime": "anytime goal",
            "player_first_goal_scorer": "first goal",
            "player_last_goal_scorer": "last goal",
        }
        prop = prop_labels.get(market_key, market_key.replace("_", " "))
        line = f" {point:g}" if point is not None else ""
        return f"{match_label} — {player} {outcome_name}{line} {prop}"
    if point is not None:
        return f"{match_label} — {outcome_name} {point}"
    return f"{match_label} — {outcome_name}"
