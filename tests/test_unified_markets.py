"""Unified markets: venues, matcher, simulation, single-venue parlays."""

from headcrack_ai.ingest import load_markets_json
from headcrack_ai.models import AmericanOdds, BetLeg, Market, MarketType, Prediction, Sport, VenueType
from headcrack_ai.optimizer import PRESETS, suggest_parlays
from headcrack_ai.persistence import SQLiteStore
from headcrack_ai.providers.kalshi import normalize_kalshi_markets
from headcrack_ai.providers.matcher import (
    canonical_event_key,
    match_prediction_to_books,
    normalize_name,
)
from headcrack_ai.providers.polymarket import normalize_polymarket_events
from headcrack_ai.simulation import simulate_match_from_legs, simulate_parlay


def _leg(
    *,
    event: str,
    book: str,
    team: str,
    odds: int,
    prob: float,
    market_type: MarketType = MarketType.MONEYLINE,
    player: str | None = None,
    threshold: float | None = None,
    outcome: str | None = None,
    home: str = "France",
    away: str = "Spain",
) -> BetLeg:
    market = Market(
        market_id=f"{event}:{book}:{team}:{player}:{odds}:{outcome}",
        sport=Sport.SOCCER,
        event_id=event,
        label=f"{home} vs {away} — {player or team}",
        market_type=market_type,
        sportsbook=book,
        odds=AmericanOdds(odds),
        team=None if player else team,
        player=player,
        threshold=threshold,
        metadata={
            "home_team": home,
            "away_team": away,
            "outcome_name": outcome or team,
            "league": "World Cup",
        },
        venue_type=VenueType.SPORTSBOOK,
    )
    return BetLeg(
        market=market,
        prediction=Prediction(
            market_id=market.market_id,
            model_probability=prob,
            model_name="poisson_soccer_live",
            confidence=0.6,
        ),
    )


def test_normalize_name_aliases():
    assert normalize_name("España") == "spain"
    assert canonical_event_key("France", "Spain", "World Cup").endswith("france vs spain")


def test_kalshi_and_polymarket_normalizers_set_venue():
    kalshi = normalize_kalshi_markets(
        [
            {
                "ticker": "KXWC-FRA",
                "event_ticker": "KXWC",
                "title": "France vs Spain Winner?",
                "yes_ask": 55,
                "yes_bid": 52,
                "volume": 1200,
            }
        ]
    )
    assert kalshi and kalshi[0].venue_type == VenueType.PREDICTION_MARKET
    assert kalshi[0].sportsbook == "kalshi"

    poly = normalize_polymarket_events(
        [
            {
                "id": "evt1",
                "slug": "france-vs-spain",
                "title": "France vs Spain",
                "markets": [
                    {
                        "question": "France vs Spain",
                        "conditionId": "c1",
                        "outcomes": '["France", "Spain"]',
                        "outcomePrices": '["0.58", "0.42"]',
                        "clobTokenIds": '["t1", "t2"]',
                        "liquidityNum": 5000,
                    }
                ],
            }
        ]
    )
    assert len(poly) == 2
    assert poly[0].venue_type == VenueType.PREDICTION_MARKET
    assert poly[0].sportsbook == "polymarket"


def test_provider_fixture_parsing_keeps_binary_no_side_custom():
    kalshi = normalize_kalshi_markets(
        [
            {
                "ticker": "KXWC-SPAIN",
                "event_ticker": "KXWC",
                "title": "France vs Spain Winner?",
                "yes_sub_title": "Spain",
                "yes_ask": 47,
                "yes_bid": 44,
            }
        ]
    )
    assert kalshi[0].team == "Spain"

    poly = normalize_polymarket_events(
        [
            {
                "id": "evt-binary",
                "slug": "will-france-beat-spain",
                "title": "Will France beat Spain?",
                "markets": [
                    {
                        "question": "Will France beat Spain?",
                        "conditionId": "binary-1",
                        "outcomes": '["Yes", "No"]',
                        "outcomePrices": '["0.54", "0.46"]',
                    }
                ],
            }
        ]
    )
    yes, no = poly
    assert yes.team == "France"
    assert yes.market_type == MarketType.MONEYLINE
    assert no.team is None
    assert no.market_type == MarketType.CUSTOM
    assert yes.metadata["away_team"] == "Spain"


def test_matcher_rejects_low_score_false_matches():
    book = _leg(event="wc1", book="fanduel", team="France", odds=-120, prob=0.55)
    pred_market = Market(
        market_id="kalshi:X:yes",
        sport=Sport.SOCCER,
        event_id="unrelated",
        label="Kalshi YES — Weather in Tokyo",
        market_type=MarketType.CUSTOM,
        sportsbook="kalshi",
        odds=AmericanOdds(100),
        team="Tokyo",
        venue_type=VenueType.PREDICTION_MARKET,
        metadata={"home_team": "Tokyo", "away_team": "Osaka"},
    )
    pred = BetLeg(
        market=pred_market,
        prediction=Prediction(
            market_id=pred_market.market_id,
            model_probability=0.5,
            model_name="kalshi_market",
        ),
    )
    matches = match_prediction_to_books([pred], [book], min_score=0.72)
    assert matches
    assert matches[0].matched is False


def test_sqlite_migrates_venue_columns(tmp_path):
    store = SQLiteStore(tmp_path / "mig.sqlite3")
    store.initialize()
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    store.save_legs(legs[:1])
    with store.connect() as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(markets)").fetchall()}
    assert "venue_type" in cols
    assert "canonical_event_id" in cols


def test_single_venue_parlays_and_presets():
    legs = []
    for i in range(8):
        legs.append(_leg(event=f"m{i}", book="fanduel", team=f"Team{i}", odds=-110, prob=0.58))
        legs.append(_leg(event=f"m{i}", book="draftkings", team=f"Team{i}", odds=-105, prob=0.57))
        legs.append(
            _leg(
                event=f"m{i}",
                book="fanduel",
                team="Over",
                odds=-115,
                prob=0.56,
                market_type=MarketType.PLAYER_SHOTS,
                player=f"Player{i}",
                threshold=2.5,
                outcome="Over",
            )
        )
    for preset in PRESETS:
        slips = suggest_parlays(legs, band="small", count=3, preset=preset)
        for slip in slips:
            books = {leg.market.sportsbook for leg in slip.legs}
            assert len(books) == 1
            assert slip.venue in books
            players = [leg.market.player for leg in slip.legs if leg.market.player]
            assert len(players) == len(set(players))


def test_prediction_markets_excluded_from_parlays():
    legs = [_leg(event=f"m{i}", book="fanduel", team=f"T{i}", odds=-110, prob=0.58) for i in range(6)]
    pred = Market(
        market_id="poly:1",
        sport=Sport.SOCCER,
        event_id="m0",
        label="Polymarket France",
        market_type=MarketType.MONEYLINE,
        sportsbook="polymarket",
        odds=AmericanOdds(120),
        team="France",
        venue_type=VenueType.PREDICTION_MARKET,
        metadata={"home_team": "France", "away_team": "Spain", "outcome_name": "France"},
    )
    legs.append(
        BetLeg(
            market=pred,
            prediction=Prediction(market_id="poly:1", model_probability=0.6, model_name="polymarket_market"),
        )
    )
    slips = suggest_parlays(legs, band="small", count=2, preset="cross_game")
    for slip in slips:
        assert all(leg.market.sportsbook != "polymarket" for leg in slip.legs)


def test_simulate_match_and_parlay_joint():
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    match = simulate_match_from_legs(legs, simulations=1500, seed=1)
    assert 0 <= match.home_win <= 1
    assert match.top_scores

    from headcrack_ai.models import Parlay

    slips = suggest_parlays(legs, band="small", count=1, min_edge=-0.5, preset="balanced")
    if slips:
        slip = slips[0]
    else:
        book = legs[0].market.sportsbook
        same = [leg for leg in legs if leg.market.sportsbook == book][:3]
        slip = Parlay(
            legs=tuple(same),
            stake=3.0,
            target_band="small",
            correlation_score=0.0,
            risk_score=1.0,
            venue=book,
        )
    result = simulate_parlay(slip, all_event_legs=legs, simulations=1200, seed=2)
    assert "slip_hit_rate" in result
    assert len(result["legs"]) == len(slip.legs)
    assert 0 <= result["slip_hit_rate"] <= 1


def test_api_unified_board_and_simulations_from_persisted_legs(tmp_path, monkeypatch):
    db = tmp_path / "api.sqlite3"
    monkeypatch.setenv("HEADCRACK_DATABASE_URL", f"sqlite:///{db}")
    from headcrack_ai.settings import get_settings

    get_settings.cache_clear()
    store = SQLiteStore(db)
    store.initialize()
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    store.save_legs(legs)

    from fastapi.testclient import TestClient
    from headcrack_ai.api.app import app

    client = TestClient(app)
    board = client.get("/v1/unified-board").json()
    assert board["counts"]["sportsbook_lines"] == len(legs)
    assert board["sportsbook_lines"]

    event_id = legs[0].market.event_id
    match = client.get(
        "/v1/simulations/match",
        params={"event_id": event_id, "simulations": 300, "seed": 7},
    ).json()
    assert match["simulations"] == 300
    assert "home_win" in match

    parlay = client.get(
        "/v1/simulations/parlay",
        params={"simulations": 300, "min_edge": -0.5, "preset": "same_game"},
    ).json()
    assert "parlay" in parlay
    assert "simulation" in parlay
    get_settings.cache_clear()
