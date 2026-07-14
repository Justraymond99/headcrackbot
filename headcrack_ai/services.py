from __future__ import annotations

from dataclasses import dataclass

from .config import HeadcrackConfig
from .explain import explain_card
from .feature_store import FeatureStore
from .ingest import load_markets_csv, load_markets_json
from .logging_config import get_logger
from .models import BetLeg, Market, Prediction, Sport
from .optimizer import build_card
from .persistence import SQLiteStore
from .providers.odds_api import OddsApiClient, normalize_odds_api_events
from .providers.kalshi import KalshiClient, fetch_kalshi_soccer_markets
from .providers.polymarket import PolymarketClient, fetch_polymarket_soccer_markets
from .providers.matcher import match_prediction_to_books
from .shot_model import PlayerShotModel
from .soccer import (
    DEFAULT_SOCCER_MARKETS,
    DEFAULT_SOCCER_SPORT_KEY,
    SOCCER_LEAGUES,
    SOCCER_PLAYER_PROP_MARKETS,
    WORLD_CUP_SPORT_KEY,
    enrich_soccer_legs_with_poisson,
    is_soccer_sport_key,
    league_label,
)
from .warehouse.etl import ingest_odds_legs

# Backward-compatible alias for CLI/dashboard imports
POPULAR_SPORTS = SOCCER_LEAGUES

logger = get_logger(__name__)


@dataclass
class SourceStatus:
    name: str
    status: str  # live | stale | off | err
    detail: str
    count: int = 0


@dataclass
class HeadcrackAIService:
    config: HeadcrackConfig
    store: SQLiteStore

    @classmethod
    def from_env(cls) -> "HeadcrackAIService":
        config = HeadcrackConfig.from_env()
        store = SQLiteStore(config.database_url)
        store.initialize()
        return cls(config=config, store=store)

    def ingest_manual_file(self, path: str) -> list[BetLeg]:
        legs = load_markets_json(path) if path.endswith(".json") else load_markets_csv(path)
        self.store.save_legs(legs)
        return legs

    def build_card_from_file(self, path: str, budget: float = 20.0, min_edge: float = -0.02) -> str:
        legs = self.ingest_manual_file(path)
        card = build_card(legs, budget=budget, min_edge=min_edge)
        return explain_card(card)

    def _odds_client(self) -> OddsApiClient:
        if not self.config.odds_api_key:
            raise RuntimeError(
                "ODDS_API_KEY is not set. Get a free key at https://the-odds-api.com "
                "and set it in your environment or .env file."
            )
        return OddsApiClient(self.config.odds_api_key, self.config.odds_api_base_url)

    def list_available_sports(self) -> list[dict]:
        return self._odds_client().list_sports()

    def list_soccer_leagues(self) -> list[dict]:
        sports = self.list_available_sports()
        keys = {key for key, _ in SOCCER_LEAGUES}
        return [s for s in sports if s.get("key") in keys and s.get("active")]

    def fetch_and_store_odds_api(
        self,
        sport_key: str,
        regions: str | None = None,
        markets: str = DEFAULT_SOCCER_MARKETS,
    ) -> int:
        legs = self.fetch_live_legs(sport_key=sport_key, regions=regions, markets=markets)
        return len(legs)

    def fetch_live_legs(
        self,
        sport_key: str,
        regions: str | None = None,
        markets: str = DEFAULT_SOCCER_MARKETS,
        sportsbook: str | None = None,
        apply_poisson: bool = True,
    ) -> list[BetLeg]:
        """Pull live odds and return soccer legs with Poisson model probabilities."""
        client = self._odds_client()
        events = client.fetch_odds(
            sport_key=sport_key,
            regions=regions or self.config.default_regions,
            markets=markets,
            odds_format=self.config.default_odds_format,
        )
        if not events:
            return []

        league = league_label(sport_key)
        market_rows = normalize_odds_api_events(
            events,
            sport=_sport_from_key(sport_key),
            odds_format=self.config.default_odds_format,
            league=league,
        )
        if sportsbook:
            market_rows = [m for m in market_rows if m.sportsbook == sportsbook]

        legs: list[BetLeg] = []
        for market in market_rows:
            prediction = Prediction(
                market_id=market.market_id,
                model_probability=market.odds.implied_probability,
                model_name="book_baseline",
                confidence=0.25,
                features={"source": "the_odds_api_live", "league": league},
            )
            legs.append(BetLeg(market=market, prediction=prediction, tags=_tags_for_market(market)))

        if apply_poisson and is_soccer_sport_key(sport_key):
            feature_store = FeatureStore(self.store)
            feature_store.initialize()
            shot_model = PlayerShotModel(feature_store)
            legs = enrich_soccer_legs_with_poisson(legs, feature_store, shot_model)

        self.store.save_legs(legs)
        try:
            ingest_odds_legs(legs, sport_key, league)
        except Exception:
            logger.exception("Warehouse ingest failed (non-fatal)")
        return legs

    def fetch_soccer_today(
        self,
        regions: str | None = None,
        markets: str = DEFAULT_SOCCER_MARKETS,
        sportsbook: str | None = None,
        league_keys: list[str] | None = None,
        include_player_props: bool = True,
    ) -> tuple[list[BetLeg], list[str]]:
        """Scan soccer leagues and include available World Cup player props."""
        all_legs: list[BetLeg] = []
        leagues_with_games: list[str] = []
        keys = league_keys or [key for key, _ in SOCCER_LEAGUES]

        for sport_key in keys:
            try:
                legs = self.fetch_live_legs(
                    sport_key=sport_key,
                    regions=regions,
                    markets=markets,
                    sportsbook=sportsbook,
                    apply_poisson=True,
                )
            except Exception:
                logger.exception("Live soccer fetch failed for %s", sport_key)
                continue
            if legs:
                all_legs.extend(legs)
                leagues_with_games.append(league_label(sport_key))

        if include_player_props and WORLD_CUP_SPORT_KEY in keys:
            try:
                props = self.fetch_world_cup_player_props(
                    regions=regions,
                    sportsbook=sportsbook,
                )
            except Exception:
                logger.exception("World Cup player-prop scan failed (non-fatal)")
                props = []
            if props:
                existing_ids = {leg.market.market_id for leg in all_legs}
                all_legs.extend(
                    leg for leg in props if leg.market.market_id not in existing_ids
                )

        return all_legs, leagues_with_games

    def fetch_prediction_markets(self, limit: int = 60) -> tuple[list[BetLeg], list[SourceStatus]]:
        """Public Kalshi + Polymarket reads. Never mixed into sportsbook parlays."""
        if not self.config.enable_prediction_markets:
            return [], [
                SourceStatus("Kalshi", "off", "disabled"),
                SourceStatus("Polymarket", "off", "disabled"),
            ]
        statuses: list[SourceStatus] = []
        markets: list = []
        try:
            kalshi = fetch_kalshi_soccer_markets(
                limit=limit,
                client=KalshiClient(self.config.kalshi_base_url),
            )
            markets.extend(kalshi)
            statuses.append(
                SourceStatus("Kalshi", "live" if kalshi else "off", f"{len(kalshi)} contracts", len(kalshi))
            )
        except Exception as exc:
            logger.exception("Kalshi fetch failed")
            statuses.append(SourceStatus("Kalshi", "err", str(exc)[:80]))

        try:
            poly = fetch_polymarket_soccer_markets(
                limit=limit,
                client=PolymarketClient(
                    gamma_base=self.config.polymarket_gamma_url,
                    clob_base=self.config.polymarket_clob_url,
                ),
            )
            markets.extend(poly)
            statuses.append(
                SourceStatus("Polymarket", "live" if poly else "off", f"{len(poly)} contracts", len(poly))
            )
        except Exception as exc:
            logger.exception("Polymarket fetch failed")
            statuses.append(SourceStatus("Polymarket", "err", str(exc)[:80]))

        legs = [
            BetLeg(
                market=market,
                prediction=Prediction(
                    market_id=market.market_id,
                    model_probability=market.odds.implied_probability,
                    model_name=f"{market.sportsbook}_market",
                    confidence=0.35,
                    features={"source": market.metadata.get("source"), "venue_type": market.venue_type.value},
                ),
                tags=("prediction_market", market.sportsbook),
            )
            for market in markets
        ]
        if legs:
            self.store.save_legs(legs)
        return legs, statuses

    def refresh_all_sources(
        self,
        regions: str | None = None,
        include_player_props: bool = True,
    ) -> dict:
        """Pull sportsbooks + prediction markets and return a board pack."""
        statuses: list[SourceStatus] = []
        sportsbook_legs: list[BetLeg] = []
        try:
            sportsbook_legs, leagues = self.fetch_soccer_today(
                regions=regions,
                include_player_props=include_player_props,
            )
            statuses.append(
                SourceStatus(
                    "Sportsbooks",
                    "live" if sportsbook_legs else "off",
                    f"{len(sportsbook_legs)} lines · {len(leagues)} leagues",
                    len(sportsbook_legs),
                )
            )
        except Exception as exc:
            logger.exception("Sportsbook refresh failed")
            leagues = []
            statuses.append(SourceStatus("Sportsbooks", "err", str(exc)[:80]))

        pred_legs, pred_statuses = self.fetch_prediction_markets()
        statuses.extend(pred_statuses)

        matches = match_prediction_to_books(pred_legs, sportsbook_legs)
        matched = sum(1 for m in matches if m.matched)
        statuses.append(
            SourceStatus(
                "Matcher",
                "live" if matched else "off",
                f"{matched}/{len(matches)} contracts linked",
                matched,
            )
        )
        return {
            "sportsbook_legs": sportsbook_legs,
            "prediction_legs": pred_legs,
            "match_results": matches,
            "leagues": leagues,
            "sources": statuses,
        }

    def fetch_world_cup_player_props(
        self,
        regions: str | None = None,
        markets: str = SOCCER_PLAYER_PROP_MARKETS,
        sportsbook: str | None = None,
        max_events: int = 8,
    ) -> list[BetLeg]:
        """Fetch available World Cup props one event at a time.

        The Odds API does not guarantee World Cup player-prop coverage. An empty
        result means supported US books are not offering these markets through
        the provider; it is not replaced with synthetic odds.
        """
        client = self._odds_client()
        try:
            events = client.list_events(WORLD_CUP_SPORT_KEY)[:max_events]
        except Exception:
            logger.exception("World Cup event feed is unavailable")
            return []
        all_markets: list[Market] = []

        for event in events:
            event_id = str(event.get("id") or "")
            if not event_id:
                continue
            try:
                payload = client.fetch_event_odds(
                    sport_key=WORLD_CUP_SPORT_KEY,
                    event_id=event_id,
                    regions=regions or self.config.default_regions,
                    markets=markets,
                    odds_format=self.config.default_odds_format,
                )
            except Exception:
                logger.exception(
                    "Combined World Cup prop fetch failed for event %s; trying markets individually",
                    event_id,
                )
                payload = self._fetch_prop_markets_individually(
                    client,
                    event_id=event_id,
                    regions=regions or self.config.default_regions,
                    markets=markets,
                )
                if not payload:
                    logger.warning("No player props returned for World Cup event %s", event_id)
                    continue
            all_markets.extend(
                normalize_odds_api_events(
                    [payload],
                    sport=Sport.SOCCER,
                    odds_format=self.config.default_odds_format,
                    league=league_label(WORLD_CUP_SPORT_KEY),
                )
            )

        if sportsbook:
            all_markets = [market for market in all_markets if market.sportsbook == sportsbook]

        legs = [
            BetLeg(
                market=market,
                prediction=Prediction(
                    market_id=market.market_id,
                    model_probability=market.odds.implied_probability,
                    model_name="book_baseline",
                    confidence=0.2,
                    features={
                        "source": "the_odds_api_event_props",
                        "league": league_label(WORLD_CUP_SPORT_KEY),
                    },
                ),
                tags=_tags_for_market(market),
            )
            for market in all_markets
        ]

        if legs:
            feature_store = FeatureStore(self.store)
            feature_store.initialize()
            legs = enrich_soccer_legs_with_poisson(
                legs,
                feature_store=feature_store,
                shot_model=PlayerShotModel(feature_store),
            )
            self.store.save_legs(legs)
            try:
                ingest_odds_legs(
                    legs,
                    WORLD_CUP_SPORT_KEY,
                    league_label(WORLD_CUP_SPORT_KEY),
                )
            except Exception:
                logger.exception("World Cup prop warehouse ingest failed (non-fatal)")
        return legs

    def _fetch_prop_markets_individually(
        self,
        client: OddsApiClient,
        event_id: str,
        regions: str,
        markets: str,
    ) -> dict | None:
        """Fallback when a provider rejects a combined prop-market request."""
        merged: dict | None = None
        books: dict[str, dict] = {}
        for market_key in markets.split(","):
            try:
                payload = client.fetch_event_odds(
                    sport_key=WORLD_CUP_SPORT_KEY,
                    event_id=event_id,
                    regions=regions,
                    markets=market_key,
                    odds_format=self.config.default_odds_format,
                )
            except Exception:
                logger.exception("World Cup prop market %s failed for event %s", market_key, event_id)
                continue
            if merged is None:
                merged = {**payload, "bookmakers": []}
            for bookmaker in payload.get("bookmakers", []):
                key = bookmaker.get("key") or bookmaker.get("title") or "unknown"
                target = books.setdefault(key, {**bookmaker, "markets": []})
                target["markets"].extend(bookmaker.get("markets", []))
        if merged is not None:
            merged["bookmakers"] = list(books.values())
        return merged

    def build_live_card(
        self,
        sport_key: str = DEFAULT_SOCCER_SPORT_KEY,
        budget: float = 20.0,
        min_edge: float = -0.02,
        regions: str | None = None,
        markets: str = DEFAULT_SOCCER_MARKETS,
        sportsbook: str | None = None,
    ) -> tuple[list[BetLeg], str]:
        legs = self.fetch_live_legs(
            sport_key=sport_key,
            regions=regions,
            markets=markets,
            sportsbook=sportsbook,
        )
        card = build_card(legs, budget=budget, min_edge=min_edge)
        return legs, explain_card(card)

    def value_board(self, limit: int = 50) -> list[dict]:
        return self.store.value_board(limit=limit)


def _sport_from_key(sport_key: str) -> Sport:
    """Map Odds API sport keys to Headcrack sport enums (soccer-first today)."""
    if is_soccer_sport_key(sport_key):
        return Sport.SOCCER
    if sport_key.startswith("mma_") or sport_key.startswith("boxing_"):
        return Sport.MMA
    if sport_key.startswith("baseball_"):
        return Sport.MLB
    if sport_key.startswith("basketball_"):
        return Sport.NBA
    if sport_key.startswith("esports_"):
        return Sport.ESPORTS
    if "wrestling" in sport_key or sport_key.startswith("fighting_"):
        return Sport.PRO_WRESTLING
    return Sport.SOCCER


def _tags_for_market(market: Market) -> tuple[str, ...]:
    tags: list[str] = []
    if market.market_type.value in {"moneyline", "qualify", "spread"}:
        tags.append("game_winner")
    if market.market_type.value in {"total_goals", "both_teams_to_score"}:
        tags.append("goals")
    if market.market_type.value.startswith("player_"):
        tags.append("player_prop")
    if market.team:
        tags.append(market.team.lower().replace(" ", "_"))
    return tuple(tags)
