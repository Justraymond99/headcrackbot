# Headcrack AI

Headcrack AI is a sports betting decision-support engine for finding, explaining, and tracking positive expected value opportunities.

The system is built around a simple idea: do not chase random parlays. Convert market prices into implied probabilities, estimate true probabilities with models, compare the two, and build cards only when the legs fit the same game script.

> Educational analytics project. Not financial advice. No model can guarantee profitable betting.

## What It Does

- Ingests manual market files, sportsbook odds, and public Kalshi / Polymarket prices
- Converts American and decimal odds into normalized American prices
- Stores markets, predictions, odds snapshots, bet legs, and bet records in SQLite
- Calculates implied probability, model edge, expected value, and EV per dollar
- Runs soccer-focused Poisson and joint Monte Carlo simulations for matches and parlays
- Builds **single-sportsbook** parlay cards by leg-count band and preset (never mixes books)
- Scores parlays by diversity, risk, adjusted hit probability, and expected value
- Tracks bankroll, bet records, results, ROI, and market performance
- Provides a CLI and Streamlit dashboard for daily workflow

## Current Status

The project now has a production-shaped Headcrack AI foundation:

- Core probability engine
- Soccer simulation engine
- EV parlay optimizer
- SQLite persistence layer
- Official The Odds API adapter
- Live public Kalshi + Polymarket adapters (read-only prices, comparison, paper simulation)
- Manual Kalshi CSV fallback
- Dashboard with high-contrast theme, source freshness pills, and game → slip → simulate flow
- Venue-valid single-sportsbook parlays with Balanced / Cross-game / Same-game / Player-props presets
- Odds-informed match and full-slip Monte Carlo (correlated same-game grading)
- CLI commands for ingestion, odds fetching, card generation, and value-board review
- Real bet-result import workflow with automatic parlay settlement
- Tracking reports (ROI by market/sport/sportsbook, hit rate by confidence, best/worst models)
- Model calibration reports (reliability bins, Brier score, log loss, expected calibration error)
- Historical feature store for player and team game logs
- Soccer player shot model driven by the feature store
- Event-level soccer player-prop ingestion (shots, shots on target, goals, assists)
- World Cup player-prop fetch in the dashboard, with an honest no-coverage state
- Odds Screen, +EV Finder, Prop Optimizer, Whale Watch, Arbitrage, and MonsterGPT tools
- Automated daily report generation
- Natural-language card explanations with an optional LLM narrator and offline template fallback
- Regression tests for probability, provider adapters, persistence, config safety, dashboard imports, tracking, calibration, feature store, shot model, and reporting

## Architecture

```text
headcrack_ai/
├── bankroll.py          # staking, fractional Kelly, ROI summaries
├── calibration.py       # reliability bins, Brier score, log loss, ECE
├── cli.py               # command-line workflow
├── config.py            # environment-backed config with SQLite guardrails
├── daily_report.py      # end-to-end daily report generator
├── dashboard.py         # Streamlit dashboard routing
├── dashboard_pages.py   # research, props, EV, odds, and arbitrage pages
├── explain/             # grounded card briefs and pick attribution
├── feature_store.py     # historical player/team game logs and rolling features
├── ingest.py            # manual JSON/CSV market ingestion
├── llm_explain.py       # LLM/template natural-language card narration
├── models.py            # domain models: markets, predictions, legs, parlays, records
├── optimizer.py         # EV/correlation/risk parlay builder
├── persistence.py       # SQLite schema and store
├── probability.py       # odds conversion, Poisson, Monte Carlo, ensemble utilities
├── reports.py           # tracking reports over settled bets
├── results.py           # bet + market-result import and auto-settlement
├── shot_model.py        # soccer player shot Poisson model
├── services.py          # app/service coordination layer
├── tools/               # odds, EV, props, projections, whale watch, arbitrage
└── providers/
    ├── kalshi.py         # public Kalshi market-data adapter
    ├── kalshi_manual.py  # manual/exported Kalshi-style market rows
    ├── matcher.py        # sportsbook ↔ prediction-market identity matching
    ├── odds_api.py       # The Odds API adapter and normalizer
    └── polymarket.py     # public Polymarket Gamma/CLOB adapter
```

## Install

```bash
git clone https://github.com/Justraymond99/headcrackbot.git
cd headcrackbot
pip install -r requirements-headcrack.txt
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

## Venues: sportsbooks vs prediction markets

Headcrack treats **sportsbooks** (FanDuel, BetMGM, DraftKings, …) and **prediction markets** (Kalshi, Polymarket) as different venues.

| Capability | Sportsbooks | Kalshi / Polymarket |
|---|---|---|
| Live public prices | The Odds API | Public REST (no trading keys) |
| Placeable parlays | Single-book slips only | Not mixed into sportsbook parlays |
| Comparison / arb gaps | Cross-book arbs | Vs sportsbooks when matcher links contracts |
| Simulation | Odds-informed match + slip sims | Shown beside sims as optional comparison |
| Real order execution | Not implemented | Not implemented |

`ENABLE_PREDICTION_MARKETS=true` (default) loads public Kalshi and Polymarket soccer-related contracts on **Refresh all**. Unmatched contracts stay visible but are never labeled as arbitrage. CSV upload remains an offline Kalshi fallback.

Paper simulation grades slips against Monte Carlo worlds; it is not filled-order execution.

## World Cup Player Props

Open the dashboard and select **World Cup props** in the global fetch bar. Player
props use The Odds API's event-level endpoint; they cannot be requested from the
regular league odds endpoint.

The same workflow is available from the CLI:

```bash
python -m headcrack_ai.cli fetch-world-cup-props --friendly
```

The provider currently documents soccer prop coverage mainly for major domestic
leagues and US bookmakers, so World Cup availability can be empty. Headcrack
shows that state explicitly and never substitutes synthetic odds. Manual JSON/CSV
prop files remain supported through **Build Card**.

Only props backed by a Headcrack model are eligible for the optimized slip.
Book-only lines still appear in the available-props screen, but are not labeled
as +EV.

## Expansion Order

The domain model reserves sport identifiers for the planned expansion:

1. Soccer (active; World Cup props first)
2. MMA/UFC
3. Baseball
4. Basketball
5. Esports
6. Pro wrestling/WWE

Each sport will receive its own market mapping and projection model before its
lines are allowed into +EV or optimizer results.

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

## Tracking, Models, and Reports

Import bets you placed, then import the real-world market outcomes. Bets settle
automatically once every leg has a recorded result:

```bash
python -m headcrack_ai.cli import-bets --input examples/bets_sample.json
python -m headcrack_ai.cli import-results --input examples/results_sample.json
```

Review performance and model trustworthiness:

```bash
python -m headcrack_ai.cli report
python -m headcrack_ai.cli calibration-report
```

Load historical game logs and project a player shot line from them:

```bash
python -m headcrack_ai.cli load-player-logs --input examples/player_logs_sample.json
python -m headcrack_ai.cli load-team-logs --input examples/team_logs_sample.json
python -m headcrack_ai.cli project-shots --player "Lionel Messi" --threshold 1.5 --opponent Egypt
```

Generate the full daily report (card, narrative, tracking, calibration, no-bet warnings):

```bash
python -m headcrack_ai.cli daily-report --input examples/markets_argentina_egypt.json
```

Get a natural-language explanation of a card. If `OPENAI_API_KEY` is set the LLM
narrator is used, otherwise a deterministic offline template narrates the card:

```bash
python -m headcrack_ai.cli explain-narrative --input examples/markets_argentina_egypt.json
```

### Bet and Result Input Formats

A bet file reuses the market row schema for each leg, wrapped with staking metadata:

```json
{
  "bets": [
    {
      "bet_id": "b-messi-shots",
      "stake": 5.0,
      "legs": [
        {"market_id": "messi-2-shots", "label": "Lionel Messi 2+ shots", "market_type": "player_shots", "odds": -180, "model_probability": 0.73, "confidence": 0.68}
      ]
    }
  ]
}
```

A results file records each market's outcome (`won`, `lost`, or `void`):

```json
{"results": [{"market_id": "messi-2-shots", "outcome": "won"}]}
```

A void leg is treated as a push: it is dropped from the parlay and the payout is
recomputed from the surviving winning legs.

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
- `market_results` (real-world outcomes used for settlement and calibration)
- `player_game_logs` (historical feature store)
- `team_game_logs` (historical feature store)

The stored value board only shows the latest prediction per market, so repeated imports do not flood the board with stale duplicate edges.

## Provider Support

### The Odds API

The adapter uses official API endpoints and supports American or decimal source prices. Decimal prices are converted before storage so implied probabilities stay correct.

### Kalshi

Kalshi is manual/export-first for now. Use CSV rows containing tickers, labels, YES prices, and market metadata unless an official integration is explicitly added.

## Testing

```bash
pytest tests/
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
- bet + market-result import and auto-settlement (including void pushes)
- tracking reports (ROI, hit rate by confidence, model performance)
- calibration metrics (Brier, reliability bins, ECE)
- feature store rolling features
- soccer player shot model projection
- template card narration and daily report generation

## Roadmap

**Locked 9-sprint plan:** [docs/HEADCRACK_AI_SPRINT_PLAN.md](docs/HEADCRACK_AI_SPRINT_PLAN.md)

| Sprint | Goal |
| ------ | ---- |
| 1 | Production hardening (CI, Docker, logging, Alembic, retries) |
| 2 | Historical warehouse & normalized database |
| 3 | Feature engineering pipeline |
| 4 | Classical ML models |
| 5 | Ensemble + calibration |
| 6 | Backtesting engine |
| 7 | MLOps (DVC / MLflow) |
| 8 | Daily automation, reporting, APIs |
| 9 | AI explanation layer |

### Already shipped (pre-Sprint 1 baseline)

- Soccer Poisson engine + live odds enrichment
- EV parlay optimizer + plain-English dashboard
- Bet tracking, calibration reports, daily report
- Historical feature store + player shot model (prototype)

## Responsible Use

This system is for analytics, education, and decision support. Keep bankroll limits, track every result, and avoid increasing stake size to chase losses.
