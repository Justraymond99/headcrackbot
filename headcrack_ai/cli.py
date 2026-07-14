from __future__ import annotations

import argparse
import json
from pathlib import Path

from .calibration import build_calibration_report, format_calibration_report
from .config import HeadcrackConfig
from .daily_report import format_daily_report, generate_daily_report
from .explain import explain_card
from .feature_store import FeatureStore, load_player_logs, load_team_logs
from .ingest import load_markets_csv, load_markets_json
from .llm_explain import explain_card_narrative
from .optimizer import build_card
from .persistence import SQLiteStore
from .probability import monte_carlo_soccer_match
from .reports import build_tracking_report, format_tracking_report
from .plain_language import leg_to_friendly_row, value_board_to_friendly_rows
from .results import import_bet_records, import_market_results
from .services import POPULAR_SPORTS, HeadcrackAIService
from .soccer import (
    DEFAULT_SOCCER_MARKETS,
    DEFAULT_SOCCER_SPORT_KEY,
    SOCCER_LEAGUES,
    SOCCER_PLAYER_PROP_MARKETS,
)
from .shot_model import PlayerShotModel


def _load_legs(path: str):
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return load_markets_csv(path)
    if suffix == ".json":
        return load_markets_json(path)
    raise ValueError("Input must be .csv or .json")


def build_card_command(args: argparse.Namespace) -> None:
    legs = _load_legs(args.input)
    card = build_card(legs, budget=args.budget, min_edge=args.min_edge)
    print(explain_card(card))


def init_db_command(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.database_url)
    store.initialize()
    print(f"Initialized database at {store.path}")


def ingest_command(args: argparse.Namespace) -> None:
    service = HeadcrackAIService(HeadcrackConfig.from_env(), SQLiteStore(args.database_url))
    service.store.initialize()
    legs = service.ingest_manual_file(args.input)
    print(f"Ingested {len(legs)} manual legs into {service.store.path}")


def value_board_command(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.database_url)
    store.initialize()
    rows = store.value_board(limit=args.limit)
    if args.friendly:
        print(json.dumps(value_board_to_friendly_rows(rows), indent=2))
    else:
        print(json.dumps(rows, indent=2))


def fetch_odds_command(args: argparse.Namespace) -> None:
    service = HeadcrackAIService.from_env()
    legs = service.fetch_live_legs(
        sport_key=args.sport_key,
        regions=args.regions,
        markets=args.markets,
        sportsbook=args.sportsbook,
    )
    print(f"Fetched {len(legs)} soccer lines ({len({leg.market.event_id for leg in legs})} matches).")
    if args.friendly and legs:
        print(json.dumps([leg_to_friendly_row(leg) for leg in legs[: args.limit]], indent=2))


def fetch_soccer_command(args: argparse.Namespace) -> None:
    service = HeadcrackAIService.from_env()
    legs, active = service.fetch_soccer_today(
        regions=args.regions,
        markets=args.markets,
        sportsbook=args.sportsbook,
    )
    if not legs:
        print("No soccer matches on the board right now.")
        return
    print(f"Found matches in: {', '.join(active)}")
    print(f"Total: {len(legs)} lines across {len({leg.market.event_id for leg in legs})} matches.")
    if args.friendly:
        top = sorted(legs, key=lambda leg: leg.edge, reverse=True)[: args.limit]
        print(json.dumps([leg_to_friendly_row(leg) for leg in top], indent=2))


def fetch_world_cup_props_command(args: argparse.Namespace) -> None:
    service = HeadcrackAIService.from_env()
    legs = service.fetch_world_cup_player_props(
        regions=args.regions,
        markets=args.markets,
        sportsbook=args.sportsbook,
        max_events=args.max_events,
    )
    if not legs:
        print("No World Cup player props were returned by supported sportsbooks.")
        return
    print(
        f"Fetched {len(legs)} World Cup prop lines across "
        f"{len({leg.market.event_id for leg in legs})} matches."
    )
    if args.friendly:
        print(
            json.dumps(
                [leg_to_friendly_row(leg) for leg in legs[: args.limit]],
                indent=2,
            )
        )


def list_sports_command(args: argparse.Namespace) -> None:
    if args.popular or args.soccer:
        print("Soccer leagues (use the key with fetch-odds):")
        for key, label in SOCCER_LEAGUES:
            print(f"  {key:40s}  {label}")
        return
    service = HeadcrackAIService.from_env()
    sports = service.list_soccer_leagues()
    print(f"{len(sports)} active soccer leagues on your API plan:")
    for sport in sports:
        print(f"  {sport.get('key', ''):40s}  {sport.get('title', '')}")


def live_card_command(args: argparse.Namespace) -> None:
    service = HeadcrackAIService.from_env()
    _, card_text = service.build_live_card(
        sport_key=args.sport_key,
        budget=args.budget,
        min_edge=args.min_edge,
        regions=args.regions,
        markets=args.markets,
        sportsbook=args.sportsbook,
    )
    print(card_text)


def simulate_soccer_command(args: argparse.Namespace) -> None:
    result = monte_carlo_soccer_match(args.home_xg, args.away_xg, simulations=args.simulations, seed=args.seed)
    print(json.dumps(result, indent=2))


def import_bets_command(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.database_url)
    store.initialize()
    records = import_bet_records(store, args.input)
    print(f"Imported {len(records)} bet records into {store.path}")


def import_results_command(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.database_url)
    store.initialize()
    summary = import_market_results(store, args.input)
    print(
        f"Recorded {summary.market_results_recorded} market results; "
        f"auto-settled {summary.bets_settled} bets."
    )


def report_command(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.database_url)
    store.initialize()
    report = build_tracking_report(store)
    print(json.dumps(report, indent=2) if args.json else format_tracking_report(report))


def calibration_command(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.database_url)
    store.initialize()
    report = build_calibration_report(store, bins=args.bins)
    print(json.dumps(report, indent=2) if args.json else format_calibration_report(report))


def load_player_logs_command(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.database_url)
    store.initialize()
    count = load_player_logs(store, args.input)
    print(f"Loaded {count} player game logs into {store.path}")


def load_team_logs_command(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.database_url)
    store.initialize()
    count = load_team_logs(store, args.input)
    print(f"Loaded {count} team game logs into {store.path}")


def project_shots_command(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.database_url)
    store.initialize()
    feature_store = FeatureStore(store)
    feature_store.initialize()
    model = PlayerShotModel(feature_store, window=args.window)
    projection = model.project(args.player, args.threshold, opponent=args.opponent)
    if projection is None:
        print(f"No historical shot data for {args.player!r}. Load player logs first.")
        return
    print(
        json.dumps(
            {
                "player": projection.player,
                "threshold": projection.threshold,
                "expected_shots": projection.expected_shots,
                "over_probability": projection.over_probability,
                "confidence": projection.confidence,
                "features": projection.features,
            },
            indent=2,
        )
    )


def daily_report_command(args: argparse.Namespace) -> None:
    store = SQLiteStore(args.database_url)
    store.initialize()
    legs = _load_legs(args.input)
    report = generate_daily_report(legs, store, budget=args.budget, min_edge=args.min_edge)
    print(json.dumps(report["card"], indent=2, default=str) if args.json else format_daily_report(report))


def explain_narrative_command(args: argparse.Namespace) -> None:
    legs = _load_legs(args.input)
    card = build_card(legs, budget=args.budget, min_edge=args.min_edge)
    print(explain_card_narrative(card))


def init_warehouse_command(args: argparse.Namespace) -> None:
    from headcrack_ai.warehouse.models import init_warehouse

    init_warehouse()
    print("Warehouse schema initialized.")


def train_model_command(args: argparse.Namespace) -> None:
    from headcrack_ai.ml.trainers import train_binary_classifier

    result = train_binary_classifier(model_name=args.model_name, model_version=args.version)
    print(
        f"Trained {result.model_name} {result.model_version} — "
        f"Brier {result.brier_score:.4f}, saved to {result.artifact_path}"
    )


def evaluate_model_command(args: argparse.Namespace) -> None:
    from headcrack_ai.mlops.evaluate import evaluate_and_maybe_promote

    report = evaluate_and_maybe_promote(
        model_name=args.model_name, model_version=args.version, max_brier=args.max_brier
    )
    print(json.dumps(report.__dict__, indent=2))


def backtest_command(args: argparse.Namespace) -> None:
    from headcrack_ai.backtest.engine import BacktestConfig, run_edge_backtest

    legs = _load_legs(args.input)
    outcomes = {row["market_id"]: row.get("outcome") == "won" for row in json.loads(Path(args.results).read_text()).get("results", [])}
    result = run_edge_backtest(legs, outcomes, BacktestConfig(min_edge=args.min_edge, flat_stake=args.stake))
    print(json.dumps(result.__dict__, indent=2))


def build_features_command(args: argparse.Namespace) -> None:
    from headcrack_ai.features.materialize import materialize_match_features

    payload = materialize_match_features(args.match_id, window=args.window)
    print(json.dumps(payload, indent=2))


def daily_soccer_job_command(args: argparse.Namespace) -> None:
    from headcrack_ai.jobs.daily_soccer import run_daily_soccer

    result = run_daily_soccer(budget=args.budget, output_dir=args.output_dir, markets_file=args.input)
    print(json.dumps(result.__dict__, indent=2))


def serve_api_command(args: argparse.Namespace) -> None:
    from headcrack_ai.api.app import main as api_main

    api_main()


def serve_telegram_command(args: argparse.Namespace) -> None:
    from headcrack_ai.telegram_bot import main as telegram_main

    telegram_main()


def main() -> None:
    parser = argparse.ArgumentParser("headcrack-ai")
    sub = parser.add_subparsers(required=True)

    card = sub.add_parser("build-card", help="Build a betting card from manual markets")
    card.add_argument("--input", required=True, help="CSV or JSON market file")
    card.add_argument("--budget", type=float, default=20.0)
    card.add_argument("--min-edge", type=float, default=-0.02)
    card.set_defaults(func=build_card_command)

    init_db = sub.add_parser("init-db", help="Initialize SQLite persistence")
    init_db.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    init_db.set_defaults(func=init_db_command)

    ingest = sub.add_parser("ingest", help="Ingest manual JSON/CSV markets into persistence")
    ingest.add_argument("--input", required=True)
    ingest.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    ingest.set_defaults(func=ingest_command)

    board = sub.add_parser("value-board", help="Read top stored picks from persistence")
    board.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    board.add_argument("--limit", type=int, default=25)
    board.add_argument("--friendly", action="store_true", help="Plain-English output")
    board.set_defaults(func=value_board_command)

    odds = sub.add_parser("fetch-odds", help="Fetch live soccer odds for one league")
    odds.add_argument("--sport-key", default=DEFAULT_SOCCER_SPORT_KEY, help="Default: soccer_epl")
    odds.add_argument("--regions", default=None)
    odds.add_argument("--markets", default=DEFAULT_SOCCER_MARKETS)
    odds.add_argument("--sportsbook", default=None, help="e.g. fanduel, draftkings")
    odds.add_argument("--friendly", action="store_true", help="Show plain-English lines")
    odds.add_argument("--limit", type=int, default=25)
    odds.set_defaults(func=fetch_odds_command)

    soccer = sub.add_parser("fetch-soccer", help="Scan all soccer leagues for today's matches")
    soccer.add_argument("--regions", default=None)
    soccer.add_argument("--markets", default=DEFAULT_SOCCER_MARKETS)
    soccer.add_argument("--sportsbook", default=None)
    soccer.add_argument("--friendly", action="store_true")
    soccer.add_argument("--limit", type=int, default=15)
    soccer.set_defaults(func=fetch_soccer_command)

    world_cup_props = sub.add_parser(
        "fetch-world-cup-props",
        help="Fetch event-level World Cup player props when books offer them",
    )
    world_cup_props.add_argument("--regions", default=None)
    world_cup_props.add_argument("--markets", default=SOCCER_PLAYER_PROP_MARKETS)
    world_cup_props.add_argument("--sportsbook", default=None)
    world_cup_props.add_argument("--max-events", type=int, default=8)
    world_cup_props.add_argument("--friendly", action="store_true")
    world_cup_props.add_argument("--limit", type=int, default=25)
    world_cup_props.set_defaults(func=fetch_world_cup_props_command)

    sports = sub.add_parser("list-sports", help="List soccer leagues available from The Odds API")
    sports.add_argument("--popular", action="store_true", help="Show our league list")
    sports.add_argument("--soccer", action="store_true", help="Alias for --popular")
    sports.set_defaults(func=list_sports_command)

    live = sub.add_parser("live-card", help="Fetch live soccer odds and build a card")
    live.add_argument("--sport-key", default=DEFAULT_SOCCER_SPORT_KEY)
    live.add_argument("--budget", type=float, default=20.0)
    live.add_argument("--min-edge", type=float, default=-0.02)
    live.add_argument("--regions", default=None)
    live.add_argument("--markets", default=DEFAULT_SOCCER_MARKETS)
    live.add_argument("--sportsbook", default=None)
    live.set_defaults(func=live_card_command)

    sim = sub.add_parser("simulate-soccer", help="Run a soccer Poisson Monte Carlo simulation")
    sim.add_argument("--home-xg", type=float, required=True)
    sim.add_argument("--away-xg", type=float, required=True)
    sim.add_argument("--simulations", type=int, default=50_000)
    sim.add_argument("--seed", type=int, default=42)
    sim.set_defaults(func=simulate_soccer_command)

    import_bets = sub.add_parser("import-bets", help="Import placed bet records from JSON/CSV")
    import_bets.add_argument("--input", required=True)
    import_bets.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    import_bets.set_defaults(func=import_bets_command)

    import_results = sub.add_parser(
        "import-results", help="Import market outcomes and auto-settle bets"
    )
    import_results.add_argument("--input", required=True)
    import_results.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    import_results.set_defaults(func=import_results_command)

    report = sub.add_parser("report", help="Tracking report: ROI, hit rate, best/worst models")
    report.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    report.add_argument("--json", action="store_true", help="Emit raw JSON instead of text")
    report.set_defaults(func=report_command)

    calibration = sub.add_parser("calibration-report", help="Model calibration report")
    calibration.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    calibration.add_argument("--bins", type=int, default=10)
    calibration.add_argument("--json", action="store_true")
    calibration.set_defaults(func=calibration_command)

    player_logs = sub.add_parser("load-player-logs", help="Load historical player game logs")
    player_logs.add_argument("--input", required=True)
    player_logs.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    player_logs.set_defaults(func=load_player_logs_command)

    team_logs = sub.add_parser("load-team-logs", help="Load historical team game logs")
    team_logs.add_argument("--input", required=True)
    team_logs.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    team_logs.set_defaults(func=load_team_logs_command)

    shots = sub.add_parser("project-shots", help="Project a player's shot line from history")
    shots.add_argument("--player", required=True)
    shots.add_argument("--threshold", type=float, required=True, help="Shots line, e.g. 1.5 for 2+")
    shots.add_argument("--opponent", default=None)
    shots.add_argument("--window", type=int, default=10)
    shots.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    shots.set_defaults(func=project_shots_command)

    daily = sub.add_parser("daily-report", help="Generate the full daily report")
    daily.add_argument("--input", required=True, help="CSV or JSON market file")
    daily.add_argument("--budget", type=float, default=20.0)
    daily.add_argument("--min-edge", type=float, default=-0.02)
    daily.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    daily.add_argument("--json", action="store_true")
    daily.set_defaults(func=daily_report_command)

    narrative = sub.add_parser("explain-narrative", help="Natural-language card explanation")
    narrative.add_argument("--input", required=True)
    narrative.add_argument("--budget", type=float, default=20.0)
    narrative.add_argument("--min-edge", type=float, default=-0.02)
    narrative.set_defaults(func=explain_narrative_command)

    wh = sub.add_parser("init-warehouse", help="Initialize SQLAlchemy warehouse schema")
    wh.set_defaults(func=init_warehouse_command)

    train = sub.add_parser("train-model", help="Train soccer ML classifier (Sprint 4)")
    train.add_argument("--model-name", default="soccer_moneyline")
    train.add_argument("--version", default="v1")
    train.set_defaults(func=train_model_command)

    evalm = sub.add_parser("evaluate-model", help="Evaluate and promote model (Sprint 7)")
    evalm.add_argument("--model-name", default="soccer_moneyline")
    evalm.add_argument("--version", default="v1")
    evalm.add_argument("--max-brier", type=float, default=0.28)
    evalm.set_defaults(func=evaluate_model_command)

    bt = sub.add_parser("backtest", help="Run edge backtest on historical picks")
    bt.add_argument("--input", required=True)
    bt.add_argument("--results", required=True, help="results JSON file")
    bt.add_argument("--min-edge", type=float, default=0.02)
    bt.add_argument("--stake", type=float, default=5.0)
    bt.set_defaults(func=backtest_command)

    feats = sub.add_parser("build-features", help="Materialize features for a match")
    feats.add_argument("--match-id", required=True)
    feats.add_argument("--window", type=int, default=5)
    feats.set_defaults(func=build_features_command)

    job = sub.add_parser("daily-soccer", help="Run full daily soccer automation job")
    job.add_argument("--budget", type=float, default=20.0)
    job.add_argument("--output-dir", default="reports")
    job.add_argument("--input", default=None, help="Markets file — skips live fetch when set")
    job.set_defaults(func=daily_soccer_job_command)

    api = sub.add_parser("serve-api", help="Start FastAPI server")
    api.set_defaults(func=serve_api_command)

    telegram = sub.add_parser("serve-telegram", help="Start the interactive Telegram bot")
    telegram.set_defaults(func=serve_telegram_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
