import os
from dataclasses import replace
from datetime import timedelta

import pytest

from headcrack_ai.config import HeadcrackConfig
from headcrack_ai.models import AmericanOdds
from headcrack_ai.optimizer import build_card
from headcrack_ai.probability import (
    both_teams_to_score_probability,
    monte_carlo_soccer_match,
    poisson_over_probability,
    poisson_under_probability,
)
from headcrack_ai.ingest import load_markets_json
from headcrack_ai.persistence import SQLiteStore
from headcrack_ai.providers.kalshi_manual import cents_to_american, normalize_kalshi_rows
from headcrack_ai.providers.odds_api import normalize_odds_api_events


def test_american_odds_conversion():
    assert round(AmericanOdds(+100).decimal, 2) == 2.0
    assert round(AmericanOdds(-200).implied_probability, 2) == 0.67


def test_config_rejects_non_sqlite_database_url(monkeypatch):
    monkeypatch.setenv("HEADCRACK_DATABASE_URL", "postgres://user:pass@example.com/db")
    monkeypatch.setenv("ODDS_API_KEY", "test-key")
    from headcrack_ai.settings import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValueError):
        HeadcrackConfig.from_env()
    get_settings.cache_clear()


def test_config_accepts_headcrack_sqlite_override(monkeypatch):
    monkeypatch.setenv("HEADCRACK_DATABASE_URL", "sqlite:///tmp/headcrack.sqlite3")
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@example.com/db")
    from headcrack_ai.settings import get_settings

    get_settings.cache_clear()
    assert HeadcrackConfig.from_env().database_url == "sqlite:///tmp/headcrack.sqlite3"
    get_settings.cache_clear()


def test_prediction_markets_default_to_disabled(monkeypatch):
    monkeypatch.delenv("ENABLE_PREDICTION_MARKETS", raising=False)
    from headcrack_ai.settings import Settings

    assert Settings(_env_file=None).enable_prediction_markets is False


def test_btts_probability_range():
    p = both_teams_to_score_probability(1.8, 0.9)
    assert 0 <= p <= 1


def test_poisson_over_probability_includes_upper_tail():
    assert poisson_over_probability(2.5, 20) > 0.99
    assert poisson_under_probability(2.5, 20) < 0.01


def test_dashboard_imports_as_package():
    import headcrack_ai.dashboard as dashboard

    assert callable(dashboard.run_dashboard)


def test_monte_carlo_soccer_match():
    result = monte_carlo_soccer_match(1.8, 0.9, simulations=1000)
    assert 0 <= result["home_win"] <= 1
    assert "top_scores" in result


def test_build_card_from_sample():
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    card = build_card(legs, budget=20)
    assert set(card.keys()) == {"small", "big", "nuclear"}


def test_sqlite_store_round_trip(tmp_path):
    store = SQLiteStore(tmp_path / "headcrack.sqlite3")
    store.initialize()
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    store.save_legs(legs[:2])
    board = store.value_board(limit=10)
    assert len(board) >= 2
    assert "edge" in board[0]


def test_value_board_only_shows_latest_prediction_per_market(tmp_path):
    store = SQLiteStore(tmp_path / "headcrack.sqlite3")
    store.initialize()
    leg = load_markets_json("examples/markets_argentina_egypt.json")[0]
    store.save_leg(leg)
    store.save_leg(leg)
    board = store.value_board(limit=10)
    matching = [row for row in board if row["market_id"] == leg.market.market_id]
    assert len(matching) == 1


def test_save_leg_does_not_duplicate_identical_bet_leg_index_rows(tmp_path):
    store = SQLiteStore(tmp_path / "headcrack.sqlite3")
    store.initialize()
    leg = load_markets_json("examples/markets_argentina_egypt.json")[0]

    store.save_leg(leg)
    store.save_leg(leg)

    with store.connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM bet_legs WHERE market_id = ?",
            (leg.market.market_id,),
        ).fetchone()[0]
    assert count == 1


def test_value_board_selects_latest_prediction_by_timestamp_not_insert_order(tmp_path):
    store = SQLiteStore(tmp_path / "headcrack.sqlite3")
    store.initialize()
    leg = load_markets_json("examples/markets_argentina_egypt.json")[0]
    older_prediction = replace(
        leg.prediction,
        model_probability=0.10,
        created_at=leg.prediction.created_at - timedelta(days=1),
    )
    newer_prediction = replace(
        leg.prediction,
        model_probability=0.90,
        created_at=leg.prediction.created_at,
    )

    store.upsert_market(leg.market)
    store.insert_prediction(newer_prediction)
    store.insert_prediction(older_prediction)

    row = next(row for row in store.value_board(limit=10) if row["market_id"] == leg.market.market_id)
    assert row["model_probability"] == 0.90


def test_kalshi_manual_adapter():
    assert cents_to_american(50) == 100
    markets = normalize_kalshi_rows([
        {
            "ticker": "TEST",
            "event_id": "event",
            "label": "Test market",
            "market_type": "qualify",
            "yes_price_cents": "60",
            "team": "Team A",
        }
    ])
    assert markets[0].sportsbook == "kalshi"
    assert markets[0].market_id == "kalshi:TEST:yes"


def test_odds_api_normalizer():
    events = [
        {
            "id": "event1",
            "home_team": "Home",
            "away_team": "Away",
            "commence_time": "2026-01-01T00:00:00Z",
            "bookmakers": [
                {
                    "key": "fanduel",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Home", "price": -120},
                                {"name": "Away", "price": 110},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    markets = normalize_odds_api_events(events)
    assert len(markets) == 2
    assert markets[0].sportsbook == "fanduel"


def test_odds_api_decimal_prices_are_converted_to_american():
    events = [
        {
            "id": "event1",
            "home_team": "Home",
            "away_team": "Away",
            "bookmakers": [
                {
                    "key": "fanduel",
                    "markets": [
                        {"key": "h2h", "outcomes": [{"name": "Home", "price": 1.91}]}
                    ],
                }
            ],
        }
    ]
    markets = normalize_odds_api_events(events, odds_format="decimal")
    assert markets[0].odds.value == -110
    assert 0.52 <= markets[0].odds.implied_probability <= 0.53


def test_odds_api_player_props_preserve_player_and_market_type():
    events = [
        {
            "id": "world-cup-event",
            "home_team": "Argentina",
            "away_team": "Spain",
            "bookmakers": [
                {
                    "key": "fanduel",
                    "markets": [
                        {
                            "key": "player_shots",
                            "outcomes": [
                                {
                                    "name": "Over",
                                    "description": "Lionel Messi",
                                    "price": -115,
                                    "point": 2.5,
                                },
                                {
                                    "name": "Under",
                                    "description": "Lionel Messi",
                                    "price": -105,
                                    "point": 2.5,
                                },
                            ],
                        }
                    ],
                }
            ],
        }
    ]

    markets = normalize_odds_api_events(events, league="World Cup")

    assert len(markets) == 2
    assert markets[0].market_type.value == "player_shots"
    assert markets[0].player == "Lionel Messi"
    assert markets[0].threshold == 2.5
    assert "Lionel Messi Over 2.5 shots" in markets[0].label
    assert markets[0].metadata["league"] == "World Cup"
