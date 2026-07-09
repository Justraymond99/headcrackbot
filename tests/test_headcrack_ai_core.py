from headcrack_ai.models import AmericanOdds
from headcrack_ai.optimizer import build_card
from headcrack_ai.probability import both_teams_to_score_probability, monte_carlo_soccer_match
from headcrack_ai.ingest import load_markets_json
from headcrack_ai.persistence import SQLiteStore
from headcrack_ai.providers.kalshi_manual import cents_to_american, normalize_kalshi_rows
from headcrack_ai.providers.odds_api import normalize_odds_api_events


def test_american_odds_conversion():
    assert round(AmericanOdds(+100).decimal, 2) == 2.0
    assert round(AmericanOdds(-200).implied_probability, 2) == 0.67


def test_btts_probability_range():
    p = both_teams_to_score_probability(1.8, 0.9)
    assert 0 <= p <= 1


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
