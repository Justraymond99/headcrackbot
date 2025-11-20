# Sports Betting Parlay System

A comprehensive system for analyzing sports betting data, generating optimal parlays, and tracking performance.

## Features

### 1. Data Intake
- Fetches odds, spreads, moneylines, and totals from The Odds API
- Retrieves player stats and injury reports from SportsData.io
- Stores team streaks and advanced statistics
- Supports multiple sports (NBA, NFL, MLB, NHL)

### 2. Research Engine
- Customizable logic with configurable weights
- Expected value calculations
- Confidence scoring system
- Automatic parlay building with correlation analysis
- Diversification optimization

### 3. Output & Dashboard
- Streamlit web dashboard for visualization
- Terminal output with detailed parlay information
- Daily reports with performance metrics
- Export capabilities (Notion, Google Sheets - optional)

### 4. Result Tracker
- Win/Loss tracking per leg and parlay
- Hit rate calculations
- ROI percentage tracking
- Performance trends and graphs
- Daily summary reports

### 5. Control Panel
- Manual parlay selection and locking
- Stake management
- Override capabilities
- Status tracking

### 6. Machine Learning (Optional)
- ML models for probability estimation
- Monte Carlo simulations
- Bayesian probability updates
- Historical data training

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Initialize the database:
```bash
python main.py init
```

## Configuration

Edit `.env` file with your API keys:
- `SPORTSDATA_API_KEY`: Your SportsData.io API key
- `ODDS_API_KEY`: Your The Odds API key
- `DATABASE_URL`: PostgreSQL or SQLite connection string

## Usage

### Command Line Interface

**Initialize database:**
```bash
python main.py init
```

**Fetch latest data:**
```bash
python main.py fetch --sports NBA NFL
```

**Generate parlays:**
```bash
python main.py generate --sports NBA --max 10
```

**View performance:**
```bash
python main.py performance --days 30
```

**Launch dashboard:**
```bash
python main.py dashboard
```

### Web Dashboard

Launch the Streamlit dashboard:
```bash
streamlit run dashboard.py
```

Or use the CLI:
```bash
python main.py dashboard
```

The dashboard provides:
- Real-time parlay generation
- Visual performance analytics
- Manual result entry
- Parlay locking interface
- Settings configuration

## Workflow

1. **Fetch Data**: Pull latest odds and stats
   ```bash
   python main.py fetch
   ```

2. **Generate Parlays**: Create top-value parlay combinations
   ```bash
   python main.py generate --max 10
   ```

3. **Review & Lock**: Use dashboard to review and lock final picks

4. **Update Results**: After games, enter results to track performance

5. **Analyze**: View performance trends and ROI

## Customization

### Adjusting Research Engine Weights

Edit `config.py` or use the dashboard settings to adjust:
- Value weight (expected value importance)
- Confidence weight (confidence score importance)
- Correlation weight (diversification penalty)
- Diversification weight (bonus for more legs)

### Custom Logic

Modify `research_engine.py`:
- `calculate_confidence_score()`: Your confidence calculation
- `estimate_true_probability()`: Your probability model
- `calculate_expected_value()`: EV calculation method

### ML Models

Enhance `ml_models.py`:
- Train models on historical data
- Implement custom simulation methods
- Add Bayesian updates with evidence

## Database Schema

- **games**: Game/matchup information with odds
- **player_stats**: Player statistics and injuries
- **team_stats**: Team performance and streaks
- **legs**: Individual bet legs
- **parlays**: Parlay combinations
- **daily_reports**: Daily performance summaries

## API Integration

### The Odds API
- Free tier: 500 requests/month
- Endpoints: Odds, spreads, totals
- Documentation: https://the-odds-api.com/

### SportsData.io
- Various subscription tiers
- Endpoints: Stats, injuries, standings
- Documentation: https://sportsdata.io/

## Notes

- The system uses mock data when API keys are not configured
- SQLite is used by default (change in `.env` for PostgreSQL)
- All odds are in American format
- Confidence scores range from 0.0 to 1.0

## License

This project is for educational purposes. Please gamble responsibly.

