# Headcrack AI V1-V4 Implementation

This branch implements the non-mobile Headcrack AI foundation.

## Included

### V1: Core betting engine

- Domain models for markets, predictions, legs, parlays, bet records, bankroll state
- American odds conversion
- Implied probability
- Expected value
- Soccer Poisson model
- BTTS probability
- Win/draw/loss probability
- Monte Carlo soccer simulation

### V2: Value and parlay layer

- Edge calculation
- EV per dollar
- Target payout bands
- Correlation scoring
- Risk scoring
- Card generation for small, big, and nuclear slips

### V3: Bankroll and tracking layer

- Flat staking
- Fractional Kelly staking
- Daily/event risk limits
- Bet summaries
- ROI by market type

### V4: Product/AI layer

- CLI for card building and simulations
- Streamlit dashboard prototype
- Human-readable explanations for legs and parlays
- Manual JSON/CSV market ingestion
- Sample market card input

## Not Included

- Mobile app
- Direct sportsbook automation
- Automated scraping from restricted sites
- Guaranteed profitable betting logic

## CLI

Build a card:

```bash
python -m headcrack_ai.cli build-card --input examples/markets_argentina_egypt.json --budget 20
```

Run a soccer simulation:

```bash
python -m headcrack_ai.cli simulate-soccer --home-xg 1.8 --away-xg 0.9 --simulations 50000
```

## Dashboard

```bash
streamlit run headcrack_ai/dashboard.py
```

## Market input format

Each JSON row supports:

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

## Next hardening steps

- Add tests for probability, optimizer, bankroll, and ingest modules
- Wire this into the existing app entrypoint
- Add database persistence
- Add API clients where terms allow
- Add real model training pipelines once historical data is available
- Add calibration charts and result imports

## Responsible use

This project is for analytics and decision support. It should always preserve bankroll limits, risk warnings, and result tracking.
