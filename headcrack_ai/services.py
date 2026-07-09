from __future__ import annotations

from dataclasses import dataclass

from .config import HeadcrackConfig
from .explain import explain_card
from .ingest import load_markets_csv, load_markets_json
from .models import BetLeg, Prediction
from .optimizer import build_card
from .persistence import SQLiteStore
from .providers.odds_api import OddsApiClient, normalize_odds_api_events


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

    def fetch_and_store_odds_api(
        self,
        sport_key: str,
        regions: str | None = None,
        markets: str = "h2h,totals,spreads",
    ) -> int:
        if not self.config.odds_api_key:
            raise RuntimeError("ODDS_API_KEY is required for The Odds API ingestion")
        client = OddsApiClient(self.config.odds_api_key, self.config.odds_api_base_url)
        events = client.fetch_odds(
            sport_key=sport_key,
            regions=regions or self.config.default_regions,
            markets=markets,
            odds_format=self.config.default_odds_format,
        )
        market_rows = normalize_odds_api_events(events)
        for market in market_rows:
            self.store.upsert_market(market)
            # Baseline prediction uses the book probability until a real model overwrites it.
            self.store.insert_prediction(
                Prediction(
                    market_id=market.market_id,
                    model_probability=market.odds.implied_probability,
                    model_name="book_baseline",
                    confidence=0.25,
                    features={"source": "the_odds_api_baseline"},
                )
            )
        return len(market_rows)

    def value_board(self, limit: int = 50) -> list[dict]:
        return self.store.value_board(limit=limit)
