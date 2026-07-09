from __future__ import annotations

import argparse
import json
from pathlib import Path

from .explain import explain_card
from .ingest import load_markets_csv, load_markets_json
from .optimizer import build_card
from .probability import monte_carlo_soccer_match


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


def simulate_soccer_command(args: argparse.Namespace) -> None:
    result = monte_carlo_soccer_match(args.home_xg, args.away_xg, simulations=args.simulations, seed=args.seed)
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser("headcrack-ai")
    sub = parser.add_subparsers(required=True)

    card = sub.add_parser("build-card", help="Build a V1-V4 betting card from manual markets")
    card.add_argument("--input", required=True, help="CSV or JSON market file")
    card.add_argument("--budget", type=float, default=20.0)
    card.add_argument("--min-edge", type=float, default=-0.02)
    card.set_defaults(func=build_card_command)

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
