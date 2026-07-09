from headcrack_ai.models import AmericanOdds
from headcrack_ai.optimizer import build_card
from headcrack_ai.probability import both_teams_to_score_probability, monte_carlo_soccer_match
from headcrack_ai.ingest import load_markets_json


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
