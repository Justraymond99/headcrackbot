from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import HeadcrackConfig
from .explain import explain_card
from .ingest import load_markets_csv, load_markets_json
from .optimizer import build_card
from .persistence import SQLiteStore
from .probability import monte_carlo_soccer_match
from .services import HeadcrackAIService


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
    print(json.dumps(rows, indent=2))


def fetch_odds_command(args: argparse.Namespace) -> None:
    service = HeadcrackAIService.from_env()
    count = service.fetch_and_store_odds_api(
        sport_key=args.sport_key,
        regions=args.regions,
        markets=args.markets,
    )
    print(f"Fetched and stored {count} markets from The Odds API")


def simulate_soccer_command(args: argparse.Namespace) -> None:
    result = monte_carlo_soccer_match(args.home_xg, args.away_xg, simulations=args.simulations, seed=args.seed)
    print(json.dumps(result, indent=2))


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

    board = sub.add_parser("value-board", help="Read top stored edges from persistence")
    board.add_argument("--database-url", default="sqlite:///headcrack_ai.sqlite3")
    board.add_argument("--limit", type=int, default=25)
    board.set_defaults(func=value_board_command)

    odds = sub.add_parser("fetch-odds", help="Fetch and store markets from The Odds API")
    odds.add_argument("--sport-key", required=True, help="Example: soccer_fifa_world_cup")
    odds.add_argument("--regions", default=None)
    odds.add_argument("--markets", default="h2h,totals,spreads")
    odds.set_defaults(func=fetch_odds_command)

    sim = sub.add_parser("simulate-soccer", help="Run a soccer Poisson Monte Carlo simulation")
    sim.add_argument("--home-xg", type=float, required=True)
    sim.add_argument("--away-xg", type=float, required=True)
    sim.add_argument("--simulations", type=int, default=50_000)
    sim.add_argument("--seed", type=int, default=42)
    sim.set_defaults(func=simulate_soccer_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
