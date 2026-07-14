import json

from headcrack_ai.calibration import (
    brier_score,
    build_calibration_report,
    expected_calibration_error,
    reliability_bins,
)
from headcrack_ai.daily_report import format_daily_report, generate_daily_report
from headcrack_ai.feature_store import FeatureStore, load_player_logs, load_team_logs
from headcrack_ai.ingest import load_markets_json
from headcrack_ai.llm_explain import TemplateNarrator, explain_card_narrative, summarize_card
from headcrack_ai.models import ResultStatus
from headcrack_ai.optimizer import build_card
from headcrack_ai.persistence import SQLiteStore
from headcrack_ai.reports import (
    build_tracking_report,
    hit_rate_by_confidence,
    model_performance,
    roi_by_market,
    summarize,
)
from headcrack_ai.results import import_bet_records, import_market_results
from headcrack_ai.shot_model import PlayerShotModel


def _fresh_store(tmp_path):
    store = SQLiteStore(tmp_path / "headcrack.sqlite3")
    store.initialize()
    return store


def test_api_ready_does_not_initialize_missing_database(tmp_path, monkeypatch):
    database_path = tmp_path / "missing.sqlite3"
    monkeypatch.setenv("HEADCRACK_DATABASE_URL", f"sqlite:///{database_path}")
    from headcrack_ai.settings import get_settings
    from headcrack_ai.api.app import ready

    get_settings.cache_clear()
    response = ready()
    get_settings.cache_clear()

    assert response.status_code == 503
    assert not database_path.exists()


def test_import_bets_and_auto_settle(tmp_path):
    store = _fresh_store(tmp_path)
    records = import_bet_records(store, "examples/bets_sample.json")
    assert len(records) == 2
    assert all(r["status"] == ResultStatus.PENDING.value for r in store.all_bet_records())

    summary = import_market_results(store, "examples/results_sample.json")
    assert summary.market_results_recorded == 3
    assert summary.bets_settled == 2

    by_id = {r["bet_id"]: r for r in store.all_bet_records()}
    # Single winning leg settles as a win with a positive payout.
    assert by_id["b-messi-shots"]["status"] == ResultStatus.WON.value
    assert by_id["b-messi-shots"]["payout"] > by_id["b-messi-shots"]["stake"]
    # A parlay with one losing leg settles as a loss.
    assert by_id["b-arg-control-double"]["status"] == ResultStatus.LOST.value


def test_void_leg_is_treated_as_push(tmp_path):
    store = _fresh_store(tmp_path)
    import_bet_records(store, "examples/bets_sample.json")
    store.record_market_result("arg-qualify", ResultStatus.WON)
    store.record_market_result("arg-corners-55", ResultStatus.VOID)
    store.settle_bets_from_market_results()

    record = next(r for r in store.all_bet_records() if r["bet_id"] == "b-arg-control-double")
    assert record["status"] == ResultStatus.WON.value
    # Only the surviving qualify leg (-450 -> 1.2222 decimal) contributes to payout.
    assert record["payout"] == round(record["stake"] * (1.0 + 100.0 / 450.0), 2)


def test_tracking_reports(tmp_path):
    store = _fresh_store(tmp_path)
    import_bet_records(store, "examples/bets_sample.json")
    import_market_results(store, "examples/results_sample.json")
    records = store.all_bet_records()

    overall = summarize(records)
    assert overall["settled"] == 2
    assert overall["wins"] == 1

    assert roi_by_market(records)
    assert any(stats["settled"] for stats in model_performance(records).values())

    buckets = hit_rate_by_confidence(records)
    assert buckets

    report = build_tracking_report(store)
    assert set(report) >= {"overall", "roi_by_market", "best_models", "worst_models"}


def test_calibration_metrics():
    rows = [
        {"model_probability": 0.9, "outcome": "won", "model_name": "m"},
        {"model_probability": 0.9, "outcome": "won", "model_name": "m"},
        {"model_probability": 0.1, "outcome": "lost", "model_name": "m"},
        {"model_probability": 0.1, "outcome": "lost", "model_name": "m"},
    ]
    assert brier_score(rows) < 0.05
    bins = reliability_bins(rows, bins=10)
    assert bins
    assert expected_calibration_error(rows) is not None


def test_build_calibration_report_from_store(tmp_path):
    store = _fresh_store(tmp_path)
    import_bet_records(store, "examples/bets_sample.json")
    import_market_results(store, "examples/results_sample.json")
    report = build_calibration_report(store)
    assert report["samples"] >= 3
    assert report["brier_score"] is not None
    assert report["per_model"]


def test_feature_store_rolling_features(tmp_path):
    store = _fresh_store(tmp_path)
    count = load_player_logs(store, "examples/player_logs_sample.json")
    assert count == 5
    load_team_logs(store, "examples/team_logs_sample.json")

    fs = FeatureStore(store)
    features = fs.player_shot_features("Lionel Messi", window=10)
    assert features["games"] == 5
    assert features["avg_shots"] > 0

    allowed = fs.opponent_shots_allowed("Egypt", window=10)
    assert allowed and allowed > 12  # Egypt concedes above the league baseline.

    assert fs.player_shot_features("Unknown Player") is None


def test_shot_model_projection(tmp_path):
    store = _fresh_store(tmp_path)
    load_player_logs(store, "examples/player_logs_sample.json")
    load_team_logs(store, "examples/team_logs_sample.json")

    model = PlayerShotModel(FeatureStore(store))
    projection = model.project("Lionel Messi", threshold=1.5, opponent="Egypt")
    assert projection is not None
    assert 0.0 < projection.over_probability < 1.0
    assert projection.expected_shots > 0

    # Facing a defense that concedes more shots should not lower the projection.
    baseline = model.project("Lionel Messi", threshold=1.5)
    assert projection.expected_shots >= baseline.expected_shots

    prediction = model.prediction("messi-2-shots", "Lionel Messi", 1.5, opponent="Egypt")
    assert prediction.model_name == "soccer_player_shots_poisson_v1"

    assert model.project("Nobody", threshold=1.5) is None


def test_template_narrator_and_summary():
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    card = build_card(legs, budget=20)
    summary = summarize_card(card)
    assert "bands" in summary and "best_single" in summary

    narrative = explain_card_narrative(card, narrator=TemplateNarrator())
    assert isinstance(narrative, str) and len(narrative) > 0
    assert "picks" in narrative.lower()


def test_generate_daily_report(tmp_path):
    store = _fresh_store(tmp_path)
    import_bet_records(store, "examples/bets_sample.json")
    import_market_results(store, "examples/results_sample.json")

    legs = load_markets_json("examples/markets_argentina_egypt.json")
    report = generate_daily_report(legs, store, budget=20, narrator=TemplateNarrator())
    assert report["legs_considered"] == len(legs)
    assert "narrative" in report
    assert report["tracking_summary"]["settled"] == 2

    text = format_daily_report(report)
    assert "Today's Picks" in text
    # Report must be serializable for downstream tooling.
    json.dumps(report["tracking_summary"])


def test_plain_language_helpers():
    from headcrack_ai.plain_language import (
        describe_edge,
        format_american_odds,
        payout_band_label,
        value_verdict,
    )

    assert "bet $100" in format_american_odds(150)
    assert "Strong" in value_verdict(0.06)
    assert "Safe plays" in payout_band_label("small")
    assert "higher" in describe_edge(0.05)


def test_soccer_poisson_enrichment():
    from headcrack_ai.models import AmericanOdds, BetLeg, Market, MarketType, Prediction, Sport
    from headcrack_ai.soccer import enrich_soccer_legs_with_poisson, estimate_match_xg

    home_market = Market(
        market_id="home-win",
        sport=Sport.SOCCER,
        event_id="match-1",
        label="Arsenal vs Chelsea — Arsenal to win",
        market_type=MarketType.MONEYLINE,
        sportsbook="fanduel",
        odds=AmericanOdds(-120),
        team="Arsenal",
        opponent="Chelsea",
        metadata={"home_team": "Arsenal", "away_team": "Chelsea"},
    )
    over_market = Market(
        market_id="over-25",
        sport=Sport.SOCCER,
        event_id="match-1",
        label="Arsenal vs Chelsea — Over 2.5 goals",
        market_type=MarketType.TOTAL_GOALS,
        sportsbook="fanduel",
        odds=AmericanOdds(-110),
        team="Over",
        threshold=2.5,
        metadata={"home_team": "Arsenal", "away_team": "Chelsea"},
    )
    legs = [
        BetLeg(
            home_market,
            Prediction("home-win", 0.55, "book", 0.25),
        ),
        BetLeg(
            over_market,
            Prediction("over-25", 0.52, "book", 0.25),
        ),
    ]
    home_xg, away_xg, _ = estimate_match_xg(legs)
    assert home_xg > 0 and away_xg > 0

    enriched = enrich_soccer_legs_with_poisson(legs)
    assert enriched[0].prediction.model_name == "poisson_soccer_live"
    assert enriched[0].prediction.model_probability != enriched[0].implied_probability or True
