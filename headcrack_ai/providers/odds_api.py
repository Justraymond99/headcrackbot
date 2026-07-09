from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from ..models import AmericanOdds, Market, MarketType, Sport
from ..probability import decimal_to_american


@dataclass(frozen=True)
class OddsApiClient:
    api_key: str
    base_url: str = "https://api.the-odds-api.com/v4"

    def _get_json(self, path: str, params: dict[str, Any]) -> Any:
        query = urllib.parse.urlencode({**params, "apiKey": self.api_key})
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}?{query}"
        with urllib.request.urlopen(url, timeout=20) as response:  # nosec B310 - user-configured official API URL
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


def _market_type_from_key(key: str) -> MarketType:
    if key == "h2h":
        return MarketType.MONEYLINE
    if key == "totals":
        return MarketType.TOTAL_GOALS
    if key == "spreads":
        return MarketType.SPREAD
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
) -> list[Market]:
    markets: list[Market] = []
    for event in events:
        event_id = str(event.get("id"))
        home_team = event.get("home_team")
        away_team = event.get("away_team")
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
                    point = outcome.get("point")
                    market_id = f"oddsapi:{event_id}:{sportsbook}:{market_key}:{outcome_name}:{point}"
                    label = f"{home_team} vs {away_team} - {outcome_name}"
                    if point is not None:
                        label += f" {point}"
                    markets.append(
                        Market(
                            market_id=market_id,
                            sport=sport,
                            event_id=event_id,
                            label=label,
                            market_type=market_type,
                            sportsbook=sportsbook,
                            odds=AmericanOdds(_american_price(price, odds_format=odds_format)),
                            team=outcome_name if market_type in {MarketType.MONEYLINE, MarketType.SPREAD} else None,
                            opponent=away_team if outcome_name == home_team else home_team,
                            threshold=float(point) if point is not None else None,
                            metadata={
                                "source": "the_odds_api",
                                "home_team": home_team,
                                "away_team": away_team,
                                "commence_time": event.get("commence_time"),
                                "market_key": market_key,
                                "odds_format": odds_format,
                                "raw_price": price,
                            },
                        )
                    )
    return markets
