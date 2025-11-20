# Historical Data Sources Guide

## Overview
To train ML models effectively, you need historical game results with scores, odds, and outcomes. Here are the best options:

## 🎯 Recommended Sources

### 1. **SportsData.io** (Paid API - Best Option)
- **URL**: https://sportsdata.io/
- **Free Tier**: Limited requests/month
- **Paid Plans**: Start at ~$10/month
- **What you get**:
  - Historical game scores
  - Player stats
  - Team stats
  - Real-time data
- **Setup**: Add `SPORTSDATA_API_KEY` to your `.env` file

### 2. **The Odds API** (Paid API)
- **URL**: https://the-odds-api.com/
- **Free Tier**: 500 requests/month
- **What you get**:
  - Current odds
  - Historical odds (if stored)
- **Note**: Doesn't provide historical odds directly, but you can store current odds for future historical use

### 3. **RapidAPI Sports** (Free/Paid APIs)
- **URL**: https://rapidapi.com/hub
- **What you get**:
  - Various sports APIs
  - Some free tiers available
- **Your current API**: Already integrated for advantages

## 🆓 Free Data Sources

### NBA
- **Basketball Reference**: https://www.basketball-reference.com/
  - Complete historical data
  - Can be scraped (check ToS)
- **NBA Stats API**: https://stats.nba.com/
  - Official NBA API (unofficial documentation)
  - Free but rate-limited
- **Kaggle**: Search "NBA historical data"
  - Pre-processed datasets
  - CSV downloads

### NFL
- **Pro Football Reference**: https://www.pro-football-reference.com/
  - Complete historical data
- **NFL Stats API**: https://api.nfl.com/
  - Official NFL API
- **Kaggle**: Search "NFL historical data"

### MLB
- **Baseball Reference**: https://www.baseball-reference.com/
  - Complete historical data
- **MLB Stats API**: https://statsapi.mlb.com/
  - Official MLB API (free)
- **Kaggle**: Search "MLB historical data"

### NHL
- **Hockey Reference**: https://www.hockey-reference.com/
  - Complete historical data
- **NHL Stats API**: https://statsapi.web.nhl.com/
  - Official NHL API (free)
- **Kaggle**: Search "NHL historical data"

### UFC
- **UFC Stats**: http://ufcstats.com/
  - Complete fight history
- **Kaggle**: Search "UFC historical data"

## 📥 How to Import Historical Data

### Option 1: Using SportsData.io API (Recommended)
```bash
# Set your API key in .env file
echo "SPORTSDATA_API_KEY=your_key_here" >> .env

# Run the historical data fetcher
python3 historical_data_fetcher.py --sport NBA --days 365
```

### Option 2: Manual CSV Import
1. Download historical data from Kaggle or other sources
2. Format as CSV with columns: date, home_team, away_team, home_score, away_score, sport
3. Create an import script to load into database

### Option 3: Web Scraping
- Use BeautifulSoup or Scrapy to scrape reference sites
- **Important**: Check Terms of Service before scraping
- Consider rate limiting and respectful scraping

## 🚀 Quick Start

### Get Free Data Sources Info
```bash
python3 historical_data_fetcher.py --sources
```

### Fetch Historical Data (if you have SportsData.io key)
```bash
# Fetch last 90 days
python3 historical_data_fetcher.py --sport NBA --days 90

# Fetch last year
python3 historical_data_fetcher.py --sport NFL --days 365
```

### Import from Database
The system will automatically use any finished games in your database as training data.

## 💡 Tips

1. **Start Small**: Begin with 30-90 days of data to test
2. **Build Over Time**: Let the system collect data as games finish
3. **Use Free Sources**: Kaggle has great pre-processed datasets
4. **Combine Sources**: Use free sources for historical, paid APIs for real-time

## 📊 Minimum Data Requirements

- **ML Model Training**: 30+ finished games with results
- **Good Performance**: 100+ games
- **Excellent Performance**: 500+ games

## 🔧 Current Setup

Your system is configured to:
1. ✅ Fetch current odds from The Odds API
2. ✅ Fetch advantages from RapidAPI Sportsbook
3. ⚠️ Fetch results from SportsData.io (needs API key)
4. ✅ Store all data in SQLite database
5. ✅ Use finished games for ML training

## Next Steps

1. **Get a SportsData.io API key** (recommended)
   - Sign up at https://sportsdata.io/
   - Add key to `.env` file
   - Run `python3 historical_data_fetcher.py --sport NBA --days 365`

2. **Or use free Kaggle datasets**
   - Download CSV files
   - Create import script
   - Load into database

3. **Or wait and collect data over time**
   - System will automatically collect data as games finish
   - Takes longer but no cost



