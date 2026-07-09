# Headcrack AI Roadmap

Headcrack AI is a sports intelligence and betting decision-support platform. The goal is not to guess games randomly. The goal is to combine odds, market prices, statistical models, simulations, and bet tracking to find positive expected value opportunities.

## Core Mission

Build a system that can answer:

- What is the model probability of this outcome?
- What probability is the sportsbook or market implying?
- Is there positive expected value?
- Which bets fit the same game script?
- Which parlays hit the requested payout band without becoming nonsense?
- Which markets are actually profitable over time?

## Product Pillars

### 1. Data Intake

Sources to support:

- Sportsbook odds
- Kalshi prediction markets
- Team statistics
- Player statistics
- Injuries and lineups
- Historical results
- Market movement

Primary storage:

- PostgreSQL for production
- SQLite for local development

Suggested tables:

- games
- teams
- players
- player_game_logs
- team_game_logs
- odds_snapshots
- market_prices
- predictions
- simulations
- bet_legs
- parlays
- bankroll_events
- results

### 2. Probability Engine

Baseline models:

- Implied probability from American odds
- Poisson model for soccer goals
- Both teams to score probability
- Win/draw/loss probability
- Expected value calculation

Next models:

- Dixon-Coles adjustment for soccer scores
- XGBoost or LightGBM for player props
- Bayesian updates from new evidence
- Monte Carlo match simulations
- Ensemble model combining multiple approaches

### 3. Value Finder

Every market should be evaluated as:

```text
edge = model_probability - implied_probability
EV = probability * profit - miss_probability * stake
```

Flag levels:

- Small edge: 2%+
- Strong edge: 5%+
- High conviction: 8%+

### 4. Parlay Optimizer

Inputs:

- Budget
- Target payout band
- Max legs
- Minimum edge
- Sportsbook
- Sport
- Game script

Target payout bands:

- Small: $60-$200
- Big: $500-$2,000
- Nuclear: $1,000-$5,000+

Ranking criteria:

- Expected value
- Correlation score
- Adjusted hit probability
- Payout fit
- Risk score

### 5. Bankroll Management

Strategies to support:

- Flat betting
- Unit betting
- Fractional Kelly
- Risk buckets
- Daily stop loss
- Maximum exposure per match

### 6. Tracking and Feedback Loop

Track every bet:

- Sport
- League
- Market type
- Sportsbook
- Odds
- Stake
- Model probability
- Implied probability
- Edge
- Result
- Profit/loss

Reports:

- ROI by market
- ROI by sport
- ROI by sportsbook
- Hit rate by confidence bucket
- Best and worst models
- Best and worst parlay sizes

## V1 Build Plan

### Milestone 1: Soccer Foundation

- Add soccer-specific market types
- Add odds conversion utilities
- Add Poisson goal model
- Add BTTS probability
- Add win/draw/loss probability
- Add parlay candidate object
- Add payout-band optimizer

### Milestone 2: Real Data Flow

- Normalize FanDuel screenshots or manual market input
- Add Kalshi market input format
- Store odds snapshots
- Add CLI command for building a betting card

### Milestone 3: Daily Card Generator

Given:

```text
budget = 20
targets = [60, 200, 500, 2000]
```

Return:

- 2 small slips
- 2 big slips
- 2 nuclear slips
- best single bet
- best Kalshi position
- no-bet warnings

### Milestone 4: Dashboard

Dashboard sections:

- Today's markets
- Value board
- Parlay builder
- Bankroll tracker
- Results tracker
- Model calibration

## V2 Build Plan

- Add historical soccer player features
- Train player shot model
- Train player shot-on-target model
- Add market movement tracking
- Add Monte Carlo simulator
- Add automated explanations

## V3 Build Plan

- Ensemble model
- Automated odds scraping where allowed
- Live odds movement alerts
- Discord or Telegram bot
- LLM-generated betting card summaries
- Model retraining pipeline

## Guardrails

This project is for education, analytics, and decision support. It should include responsible bankroll limits, risk warnings, and tracking so betting behavior stays controlled and measurable.
