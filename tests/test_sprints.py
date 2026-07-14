"""Sprint 1-8 integration tests."""

import json
from pathlib import Path

import pytest

from headcrack_ai.backtest.engine import BacktestConfig, run_edge_backtest
from headcrack_ai.ensemble.blender import default_soccer_blend
from headcrack_ai.ensemble.calibrators import Calibrator
from headcrack_ai.features.materialize import materialize_match_features
from headcrack_ai.ingest import load_markets_json
from headcrack_ai.ml.trainers import train_binary_classifier
from headcrack_ai.mlops.evaluate import evaluate_and_maybe_promote
from headcrack_ai.warehouse.models import init_warehouse
from headcrack_ai.warehouse.etl import ingest_player_logs_from_json


def test_sprint9_card_brief_and_attribution():
    from headcrack_ai.explain import build_card_brief, explain_pick_rationale, format_card_brief
    from headcrack_ai.llm_explain import TemplateNarrator, explain_brief_narrative

    legs = load_markets_json("examples/markets_argentina_egypt.json")
    brief = build_card_brief(legs, budget=20)
    assert brief["picks_reviewed"] == len(legs)
    assert "safety_footer" in brief
    assert brief["top_rationales"]
    assert explain_pick_rationale(legs[0])

    text = format_card_brief(brief)
    assert "Today's Soccer Brief" in text
    narrative = explain_brief_narrative(brief, narrator=TemplateNarrator())
    assert "guaranteed" in narrative.lower()


def test_init_warehouse(tmp_path, monkeypatch):
    db = tmp_path / "wh.sqlite3"
    monkeypatch.setenv("HEADCRACK_WAREHOUSE_URL", f"sqlite:///{db}")
    from headcrack_ai.settings import get_settings

    get_settings.cache_clear()
    init_warehouse()
    assert db.exists()


def test_train_and_evaluate_model(tmp_path, monkeypatch):
    reg = str(tmp_path / "registry")
    monkeypatch.setenv("MODEL_REGISTRY_PATH", reg)
    from headcrack_ai.settings import get_settings

    get_settings.cache_clear()
    result = train_binary_classifier(registry_dir=reg)
    assert result.brier_score < 0.5
    report = evaluate_and_maybe_promote()
    assert report.model_name == "soccer_moneyline"


def test_ensemble_blend():
    p = default_soccer_blend(poisson_p=0.62, ml_p=0.58, book_p=0.55)
    assert 0.5 < p < 0.75


def test_calibrator_fit():
    cal = Calibrator("isotonic").fit([0.2, 0.4, 0.6, 0.8], [0, 0, 1, 1])
    assert 0.0 <= cal.calibrate(0.7) <= 1.0


def test_backtest_engine():
    legs = load_markets_json("examples/markets_argentina_egypt.json")
    outcomes = {leg.market.market_id: True for leg in legs[:2]}
    outcomes[legs[2].market.market_id] = False
    result = run_edge_backtest(legs, outcomes, BacktestConfig(min_edge=-0.1, flat_stake=5.0))
    assert result.bets > 0


def test_warehouse_player_ingest(tmp_path, monkeypatch):
    db = tmp_path / "wh.sqlite3"
    monkeypatch.setenv("HEADCRACK_WAREHOUSE_URL", f"sqlite:///{db}")
    from headcrack_ai.settings import get_settings

    get_settings.cache_clear()
    rows = json.loads(Path("examples/player_logs_sample.json").read_text())["logs"]
    count = ingest_player_logs_from_json(rows)
    assert count == 5


def test_api_health():
    from fastapi.testclient import TestClient
    from headcrack_ai.api.app import app

    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
