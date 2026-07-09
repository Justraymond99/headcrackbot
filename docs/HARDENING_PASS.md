# Hardening Pass: Persistence and Market Data

This pass wires Headcrack AI into a more production-shaped app structure.

## Added

### Persistence

- SQLite persistence layer
- Schema initialization
- Market upserts
- Prediction inserts
- Odds snapshots
- Bet record storage
- Bet result updates
- Stored value board query

### Configuration

Environment-driven config:

- `HEADCRACK_DATABASE_URL`
- `DATABASE_URL`
- `ODDS_API_KEY`
- `ODDS_API_BASE_URL`
- `ODDS_API_REGIONS`
- `ODDS_API_FORMAT`

### Market data providers

Supported where allowed:

- The Odds API official API adapter
- Manual Kalshi CSV adapter
- Existing manual JSON/CSV ingestion

The Kalshi adapter is manual-first because market access rules and available APIs can change. Use exported or hand-entered market rows unless an official API integration is explicitly allowed.

### Service layer

`HeadcrackAIService` now coordinates:

- manual file ingestion
- persistence
- The Odds API ingestion
- value board reads
- betting card generation

### CLI

New commands:

```bash
python -m headcrack_ai.cli init-db
python -m headcrack_ai.cli ingest --input examples/markets_argentina_egypt.json
python -m headcrack_ai.cli value-board
python -m headcrack_ai.cli fetch-odds --sport-key soccer_fifa_world_cup
```

Existing commands remain:

```bash
python -m headcrack_ai.cli build-card --input examples/markets_argentina_egypt.json --budget 20
python -m headcrack_ai.cli simulate-soccer --home-xg 1.8 --away-xg 0.9
```

### Dashboard

The Streamlit dashboard can now:

- initialize/use SQLite persistence
- save uploaded markets
- show uploaded value board
- show stored value board
- run soccer simulations

## Next steps

- Add SQLAlchemy/Postgres backend behind the same store interface
- Add migrations with Alembic
- Add model calibration reports
- Add historical result importer
- Add official provider clients as terms allow
- Add CI workflow for pytest
