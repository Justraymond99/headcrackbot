# Project Structure

```
tictactoe/
│
├── config.py                 # Configuration and environment variables
├── models.py                 # Database models (SQLAlchemy)
├── data_intake.py           # API integration for fetching odds/stats
├── research_engine.py       # Parlay generation and analysis logic
├── result_tracker.py        # Win/loss tracking and ROI calculations
├── ml_models.py             # ML models and simulations
├── dashboard.py             # Streamlit web dashboard
├── main.py                  # CLI interface
├── example_usage.py         # Example workflow script
│
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
├── README.md               # Main documentation
└── PROJECT_STRUCTURE.md    # This file
```

## Module Descriptions

### Core Modules

**config.py**
- Loads environment variables
- Defines API endpoints
- Sets default configuration values
- Creates necessary directories

**models.py**
- SQLAlchemy database models
- Tables: Game, PlayerStat, TeamStat, Leg, Parlay, DailyReport
- Database initialization functions

**data_intake.py**
- Fetches odds from The Odds API
- Retrieves stats from SportsData.io
- Stores data in database
- Includes mock data fallback

**research_engine.py**
- Analyzes games and calculates expected value
- Generates parlay combinations
- Scores parlays based on custom weights
- Handles correlation and diversification

**result_tracker.py**
- Updates game and leg results
- Calculates parlay outcomes
- Generates performance reports
- Tracks ROI and hit rates

**ml_models.py**
- Machine learning predictors
- Monte Carlo simulations
- Bayesian probability updates
- Feature extraction for models

### Interface Modules

**dashboard.py**
- Streamlit web application
- Interactive parlay generation
- Performance visualization
- Manual result entry
- Settings configuration

**main.py**
- Command-line interface
- Commands: init, fetch, generate, performance, dashboard
- Terminal output formatting

**example_usage.py**
- Demonstrates complete workflow
- Example script for new users

## Data Flow

1. **Data Intake** → Fetches from APIs → Stores in Database
2. **Research Engine** → Reads from Database → Generates Parlays → Saves to Database
3. **Dashboard/CLI** → Displays Parlays → User Locks Selections
4. **Result Tracker** → Updates Results → Calculates Performance → Generates Reports

## Database Schema

```
games
  ├── id, game_id, sport, home_team, away_team
  ├── game_date, status
  └── odds (moneyline, spread, total)

player_stats
  ├── id, game_id, player_name, team
  └── stats, injury_status

team_stats
  ├── id, team, sport
  └── streaks, records, advanced_stats

legs
  ├── id, game_id, parlay_id
  ├── bet_type, selection, odds
  ├── expected_value, confidence_score
  └── result, actual_outcome

parlays
  ├── id, name, sport
  ├── combined_odds, expected_value
  ├── confidence_rating, status
  └── result, payout, stake

daily_reports
  ├── id, report_date
  ├── wins, losses, hit_rate, roi
  └── export_status
```

## Customization Points

1. **Research Engine Weights** (`research_engine.py`)
   - Adjust value, confidence, correlation, diversification weights

2. **Confidence Calculation** (`research_engine.py::calculate_confidence_score`)
   - Implement your custom logic

3. **Probability Estimation** (`research_engine.py::estimate_true_probability`)
   - Integrate ML models or custom formulas

4. **ML Models** (`ml_models.py`)
   - Train on historical data
   - Implement custom simulations

5. **API Integration** (`data_intake.py`)
   - Add more data sources
   - Customize parsing logic

