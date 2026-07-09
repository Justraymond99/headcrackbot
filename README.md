# Headcrack AI

Headcrack AI is a sports betting decision-support engine for finding, explaining, and tracking positive expected value opportunities.

The system is built around a simple idea: do not chase random parlays. Convert market prices into implied probabilities, estimate true probabilities with models, compare the two, and build cards only when the legs fit the same game script.

> Educational analytics project. Not financial advice. No model can guarantee profitable betting.

## What It Does

- Ingests manual market files, Kalshi-style exported rows, and allowed official odds feeds
- Converts American and decimal odds into normalized American prices
- Stores markets, predictions, odds snapshots, bet legs, and bet records in SQLite
- Calculates implied probability, model edge, expected value, and EV per dollar
- Runs soccer-focused Poisson and Monte Carlo simulations
- Builds parlay cards by target payout band
- Scores parlays by correlation, risk, adjusted hit probability, and expected value
- Tracks bankroll, bet records, results, ROI, and market performance
- Provides a CLI and Streamlit dashboard for daily workflow

## Current Status

The project now has a production-shaped Headcrack AI foundation:

- Core probability engine
- Soccer simulation engine
- EV parlay optimizer
- SQLite persistence layer
- Official The Odds API adapter
- Manual Kalshi adapter
- Dashboard with persistence-backed value board
- CLI commands for ingestion, odds fetching, card generation, and value-board review
- Regression tests for probability, provider adapters, persistence, config safety, and dashboard imports

## Architecture

```text
headcrack_ai/
├── bankroll.py          # staking, fractional Kelly, ROI summaries
├── cli.py               # command-line workflow
├── config.py            # environment-backed config with SQLite guardrails
├── dashboard.py         # Streamlit dashboard
├── explain.py           # human-readable card and leg explanations
├── ingest.py            # manual JSON/CSV market ingestion
├── models.py            # domain models: markets, predictions, legs, parlays, records
├── optimizer.py         # EV/correlation/risk parlay builder
├── persistence.py       # SQLite schema and store
├── probability.py       # odds conversion, Poisson, Monte Carlo, ensemble utilities
├── services.py          # app/service coordination layer
└── providers/
    ├── kalshi_manual.py # manual/exported Kalshi-style market rows
    └── odds_api.py      # The Odds API adapter and normalizer
```

## Install

```bash
git clone https://github.com/Justraymond99/headcrackbot.git
cd headcrackbot
pip install -r requirements.txt
```

If the repo does not yet include all optional dashboard/test dependencies, install them directly:

```bash
pip install streamlit pandas pytest
```

## Configuration

Headcrack AI currently supports SQLite persistence only.

```bash
export HEADCRACK_DATABASE_URL="sqlite:///headcrack_ai.sqlite3"
export ODDS_API_KEY="your_the_odds_api_key"
export ODDS_API_REGIONS="us"
export ODDS_API_FORMAT="american"
```

Important: non-SQLite `DATABASE_URL` values are rejected until a Postgres backend exists. Use `HEADCRACK_DATABASE_URL` for the app database.

## Quick Start

Initialize local persistence:

```bash
python -m headcrack_ai.cli init-db
```

Ingest a sample market card:

```bash
python -m headcrack_ai.cli ingest --input examples/markets_argentina_egypt.json
```

View the stored value board:

```bash
python -m headcrack_ai.cli value-board
```

Build a betting card from a file:

```bash
python -m headcrack_ai.cli build-card --input examples/markets_argentina_egypt.json --budget 20
```

Run a soccer Monte Carlo simulation:

```bash
python -m headcrack_ai.cli simulate-soccer --home-xg 1.8 --away-xg 0.9 --simulations 50000
```

Fetch odds from The Odds API, where allowed by your API plan and terms:

```bash
python -m headcrack_ai.cli fetch-odds --sport-key soccer_fifa_world_cup
```

Launch the dashboard:

```bash
streamlit run headcrack_ai/dashboard.py
```

## Market Input Format

Manual JSON rows look like this:

```json
{
  "market_id": "messi-2-shots",
  "sport": "soccer",
  "event_id": "arg-egypt-r16",
  "label": "Lionel Messi 2+ shots",
  "market_type": "player_shots",
  "sportsbook": "manual",
  "odds": -180,
  "team": "Argentina",
  "player": "Lionel Messi",
  "threshold": 1.5,
  "model_probability": 0.73,
  "model_name": "manual_player_prop",
  "confidence": 0.68,
  "tags": "argentina_control|attacking_volume"
}
```

Tags matter because the optimizer rewards parlays that tell one coherent story, such as `argentina_control`, `attacking_volume`, `goals`, `pressure`, or `underdog_counter`.

## Core Concepts

### Implied Probability

A sportsbook price is converted into the probability the book is implying.

```text
American -200 -> implied probability ≈ 66.7%
American +150 -> implied probability = 40.0%
```

### Edge

```text
edge = model_probability - implied_probability
```

If the model says an outcome should happen 58% of the time and the market implies 50%, the edge is +8%.

### Expected Value

```text
EV = probability * profit - miss_probability * stake
```

A bet can lose often and still be good if the payout is mispriced. A bet can also feel safe and still be bad if the price is too expensive.

### Correlated Parlays

The optimizer prefers legs that support the same game script.

Good story:

```text
Argentina control + Messi shots + Argentina corners + Over team pressure
```

Bad story:

```text
Favorite clean sheet + underdog goal + unrelated longshot prop
```

## Dashboard

The Streamlit dashboard includes:

- Uploadable market files
- Uploaded value board
- Save-to-SQLite workflow
- Stored value board
- Generated cards by target payout band
- Soccer simulation tab

Run it with:

```bash
streamlit run headcrack_ai/dashboard.py
```

## Persistence

SQLite tables include:

- `markets`
- `predictions`
- `bet_legs`
- `bet_records`
- `odds_snapshots`

The stored value board only shows the latest prediction per market, so repeated imports do not flood the board with stale duplicate edges.

## Provider Support

### The Odds API

The adapter uses official API endpoints and supports American or decimal source prices. Decimal prices are converted before storage so implied probabilities stay correct.

### Kalshi

Kalshi is manual/export-first for now. Use CSV rows containing tickers, labels, YES prices, and market metadata unless an official integration is explicitly added.

## Testing

```bash
pytest tests/test_headcrack_ai_core.py
```

Current test coverage includes:

- odds conversion
- config guardrails
- Poisson upper-tail totals
- Monte Carlo output sanity
- card generation
- SQLite persistence round trip
- latest-prediction value-board de-duping
- Kalshi manual adapter
- The Odds API normalizer
- decimal odds conversion
- dashboard importability

## Roadmap

Next build targets:

- Historical feature store
- Soccer player shot model
- Shot-on-target model
- Cards/corners models
- Model calibration reports
- Real bet-result import workflow
- Postgres store backend
- Automated daily report generation
- LLM-generated card explanations

## Responsible Use

This system is for analytics, education, and decision support. Keep bankroll limits, track every result, and avoid increasing stake size to chase losses.
