"""Tests for betting tools suite."""

import time

from headcrack_ai.ingest import load_markets_json
from headcrack_ai.config import HeadcrackConfig
from headcrack_ai.models import AmericanOdds, BetLeg, Market, MarketType, Prediction, Sport
from headcrack_ai.optimizer import prune_pool, suggest_parlays
from headcrack_ai.persistence import SQLiteStore
from headcrack_ai.services import HeadcrackAIService
from headcrack_ai.tools import (
    BettingAssistant,
    build_dfs_entries,
    build_match_projections,
    build_odds_screen,
    find_arbitrage_opportunities,
    find_positive_ev,
)
from headcrack_ai.tools.odds_screen import format_odds_screen_rows


def test_ev_finder_and_odds_screen():
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    ev = find_positive_ev(legs, min_edge=0.0, limit=5)
    assert ev
    assert ev[0].ev_per_dollar >= ev[-1].ev_per_dollar

    screen = build_odds_screen(legs)
    rows = format_odds_screen_rows(screen)
    assert isinstance(rows, list)


def test_projections_and_dfs():
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    projections = build_match_projections(legs)
    assert projections
    assert "home_xg" in projections[0]

    dfs = build_dfs_entries(legs, min_edge=-0.5, max_picks=4)
    assert isinstance(dfs, list)


def test_arbitrage_scan():
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    arbs = find_arbitrage_opportunities(legs, min_profit_pct=0.0)
    assert isinstance(arbs, list)


def test_betting_assistant_template():
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    bot = BettingAssistant()
    reply = bot.answer("What are the best +EV bets?", legs)
    assert "pick" in reply.lower() or "bet" in reply.lower()


def _synthetic_leg(event: str, team: str, book: str, odds: int, prob: float) -> BetLeg:
    market = Market(
        market_id=f"{event}:{book}:{team}:{odds}",
        sport=Sport.SOCCER,
        event_id=event,
        label=f"{event} — {team} to win",
        market_type=MarketType.MONEYLINE,
        sportsbook=book,
        odds=AmericanOdds(odds),
        team=team,
        metadata={"home_team": f"{event}-home", "away_team": f"{event}-away"},
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


def _synthetic_prop(
    event: str,
    player: str,
    outcome: str,
    book: str,
    odds: int,
    prob: float,
) -> BetLeg:
    market = Market(
        market_id=f"{event}:{book}:{player}:{outcome}:{odds}",
        sport=Sport.SOCCER,
        event_id=event,
        label=f"{event} — {player} {outcome} 2.5 shots",
        market_type=MarketType.PLAYER_SHOTS,
        sportsbook=book,
        odds=AmericanOdds(odds),
        player=player,
        threshold=2.5,
        metadata={
            "home_team": f"{event}-home",
            "away_team": f"{event}-away",
            "outcome_name": outcome,
        },
    )
    return BetLeg(
        market=market,
        prediction=Prediction(
            market_id=market.market_id,
            model_probability=prob,
            model_name="player_shot_model",
            confidence=0.6,
        ),
    )


def test_suggest_parlays_bands_and_conflicts():
    legs = []
    for i in range(10):
        for book, odds in [("fanduel", -110 - i * 5), ("draftkings", -105 - i * 5)]:
            legs.append(_synthetic_leg(f"match{i}", f"team{i}", book, odds, 0.60))

    small = suggest_parlays(legs, band="small", count=3)
    assert small and all(3 <= len(p.legs) <= 4 for p in small)
    big = suggest_parlays(legs, band="big", count=3)
    assert big and all(5 <= len(p.legs) <= 6 for p in big)

    for parlay in small + big:
        # Best price only: never two books for the same selection.
        keys = {(l.market.event_id, l.market.team) for l in parlay.legs}
        assert len(keys) == len(parlay.legs)

    # Ranked by EV, best first.
    assert small[0].expected_value >= small[-1].expected_value


def test_suggest_parlays_include_player_props_when_available():
    legs = [
        _synthetic_leg(f"match{i}", f"team{i}", "fanduel", -105, 0.58)
        for i in range(8)
    ]
    for i in range(6):
        legs.append(
            _synthetic_prop(f"match{i}", f"player{i}", "Over", "fanduel", -110, 0.59)
        )
        # Opposite sides remain distinct selections, but cannot coexist on a slip.
        legs.append(
            _synthetic_prop(f"match{i}", f"player{i}", "Under", "draftkings", -105, 0.57)
        )

    pool = prune_pool(legs)
    assert sum(1 for leg in pool if leg.market.player) >= 6

    small = suggest_parlays(legs, band="small", count=3)
    big = suggest_parlays(legs, band="big", count=3)
    assert small and all(sum(bool(leg.market.player) for leg in p.legs) >= 1 for p in small)
    assert big and all(sum(bool(leg.market.player) for leg in p.legs) >= 2 for p in big)
    for parlay in small + big:
        players = [leg.market.player for leg in parlay.legs if leg.market.player]
        assert len(players) == len(set(players))
        prop_groups = [
            (leg.market.event_id, leg.market.player, leg.market.threshold)
            for leg in parlay.legs
            if leg.market.player
        ]
        assert len(prop_groups) == len(set(prop_groups))


def test_suggest_parlays_scales_to_large_board():
    legs = []
    for i in range(60):
        for j, book in enumerate(["fanduel", "draftkings", "betmgm", "caesars", "bovada"]):
            legs.append(_synthetic_leg(f"m{i}", f"t{i}", book, -110 - j, 0.58))
    start = time.perf_counter()
    pool = prune_pool(legs)
    result = suggest_parlays(legs, band="nuclear", count=3)
    elapsed = time.perf_counter() - start
    assert len(pool) <= 14
    assert result
    assert elapsed < 5.0
    # Single-venue: every suggested slip uses one book.
    for slip in result:
        assert len({leg.market.sportsbook for leg in slip.legs}) == 1


def test_line_movements(tmp_path):
    store = SQLiteStore(tmp_path / "t.sqlite3")
    store.initialize()
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    store.save_legs(legs)
    store.save_legs(legs)
    moves = store.line_movements(min_implied_move=0.0, limit=10)
    assert isinstance(moves, list)


def test_world_cup_props_event_fetch(tmp_path, monkeypatch):
    class FakeOddsClient:
        def list_events(self, sport_key):
            assert sport_key == "soccer_fifa_world_cup"
            return [{"id": "wc-1"}]

        def fetch_event_odds(self, **kwargs):
            return {
                "id": kwargs["event_id"],
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
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }

    store = SQLiteStore(tmp_path / "props.sqlite3")
    store.initialize()
    service = HeadcrackAIService(
        config=HeadcrackConfig(database_url=f"sqlite:///{store.path}"),
        store=store,
    )
    monkeypatch.setattr(service, "_odds_client", lambda: FakeOddsClient())
    monkeypatch.setattr("headcrack_ai.services.ingest_odds_legs", lambda *args: None)

    legs = service.fetch_world_cup_player_props(max_events=1)

    assert len(legs) == 1
    assert legs[0].market.player == "Lionel Messi"
    assert legs[0].market.market_type.value == "player_shots"


def test_soccer_scan_merges_world_cup_player_props(tmp_path, monkeypatch):
    store = SQLiteStore(tmp_path / "scan.sqlite3")
    store.initialize()
    service = HeadcrackAIService(
        config=HeadcrackConfig(database_url=f"sqlite:///{store.path}"),
        store=store,
    )
    match_leg = _synthetic_leg("wc-1", "Spain", "fanduel", -105, 0.58)
    prop_leg = _synthetic_prop("wc-1", "Player One", "Over", "fanduel", -110, 0.59)
    monkeypatch.setattr(service, "fetch_live_legs", lambda **kwargs: [match_leg])
    monkeypatch.setattr(service, "fetch_world_cup_player_props", lambda **kwargs: [prop_leg])

    legs, leagues = service.fetch_soccer_today(
        league_keys=["soccer_fifa_world_cup"]
    )

    assert leagues == ["World Cup"]
    assert legs == [match_leg, prop_leg]
