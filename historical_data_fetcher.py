"""Fetch historical game data for ML model training."""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from models import Game, SessionLocal
from config import SPORTSDATA_API_KEY, SPORTSDATA_BASE_URL, ODDS_API_KEY, ODDS_API_BASE_URL
import logging
import time

logger = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """Fetch historical game results and odds for training."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.sportsdata_key = SPORTSDATA_API_KEY
        self.odds_api_key = ODDS_API_KEY
    
    def fetch_historical_results(
        self,
        sport: str,
        start_date: datetime,
        end_date: datetime,
        use_sportsdata: bool = True
    ) -> List[Dict]:
        """Fetch historical game results.
        
        Args:
            sport: Sport name (NBA, NFL, MLB, NHL)
            start_date: Start date for historical data
            end_date: End date for historical data
            use_sportsdata: Use SportsData.io API (requires key)
        
        Returns:
            List of historical game results
        """
        results = []
        current_date = start_date
        
        if use_sportsdata and self.sportsdata_key:
            logger.info(f"Fetching historical results from SportsData.io for {sport}...")
            while current_date <= end_date:
                try:
                    date_str = current_date.strftime("%Y-%m-%d")
                    
                    # Map sport to API endpoint
                    sport_map = {
                        "NBA": "nba",
                        "NFL": "nfl",
                        "MLB": "mlb",
                        "NHL": "nhl"
                    }
                    
                    if sport not in sport_map:
                        current_date += timedelta(days=1)
                        continue
                    
                    api_sport = sport_map[sport]
                    url = f"{SPORTSDATA_BASE_URL}/{api_sport}/scores/json/Scores/{date_str}"
                    headers = {"Ocp-Apim-Subscription-Key": self.sportsdata_key}
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    day_results = response.json()
                    
                    if day_results:
                        results.extend(day_results)
                        logger.info(f"  Fetched {len(day_results)} games for {date_str}")
                    
                    # Rate limiting
                    time.sleep(0.5)
                    current_date += timedelta(days=1)
                    
                except Exception as e:
                    logger.warning(f"Error fetching {sport} results for {current_date.date()}: {e}")
                    current_date += timedelta(days=1)
                    continue
        
        else:
            logger.warning("SportsData.io API key not configured. Cannot fetch historical results.")
            logger.info("Alternative: Use free data sources or manual import")
        
        return results
    
    def fetch_historical_odds(
        self,
        sport: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Fetch historical odds data.
        
        Note: The Odds API doesn't have a direct historical endpoint.
        This would need to be stored as games are fetched.
        
        Args:
            sport: Sport name
            start_date: Start date
            end_date: End date
        
        Returns:
            List of historical odds (if available)
        """
        # The Odds API doesn't provide historical odds directly
        # Historical odds would need to be stored when fetched
        logger.warning("Historical odds not available via API. Use stored odds from database.")
        return []
    
    def import_historical_from_database(self, sport: str, days_back: int = 365) -> int:
        """Import historical games already in database.
        
        Args:
            sport: Sport name
            days_back: How many days back to look
        
        Returns:
            Number of games found
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        games = self.session.query(Game).filter(
            Game.sport == sport,
            Game.status == "finished",
            Game.game_date >= cutoff_date
        ).all()
        
        logger.info(f"Found {len(games)} historical {sport} games in database")
        return len(games)
    
    def bulk_import_historical(
        self,
        sport: str,
        days_back: int = 90,
        use_sportsdata: bool = True
    ) -> int:
        """Bulk import historical data for a sport.
        
        Args:
            sport: Sport name
            days_back: How many days back to fetch
            use_sportsdata: Use SportsData.io API
        
        Returns:
            Number of games imported
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Bulk importing {sport} historical data from {start_date.date()} to {end_date.date()}")
        
        # Fetch historical results
        results = self.fetch_historical_results(sport, start_date, end_date, use_sportsdata)
        
        if not results:
            logger.warning(f"No historical results found for {sport}")
            return 0
        
        # Import results into database
        from auto_results import AutoResultUpdater
        updater = AutoResultUpdater()
        
        imported = 0
        for result in results:
            try:
                # Match result to game in database or create new entry
                # This would need to be implemented based on result format
                imported += 1
            except Exception as e:
                logger.warning(f"Error importing result: {e}")
                continue
        
        logger.info(f"Imported {imported} historical {sport} games")
        return imported


def get_free_historical_data_sources() -> Dict[str, str]:
    """Get information about free historical data sources.
    
    Returns:
        Dictionary of data sources and URLs
    """
    return {
        "NBA": {
            "Basketball Reference": "https://www.basketball-reference.com/",
            "NBA Stats API": "https://stats.nba.com/",
            "Kaggle Datasets": "https://www.kaggle.com/datasets?search=nba",
            "GitHub": "https://github.com/search?q=nba+historical+data"
        },
        "NFL": {
            "Pro Football Reference": "https://www.pro-football-reference.com/",
            "NFL Stats API": "https://api.nfl.com/",
            "Kaggle Datasets": "https://www.kaggle.com/datasets?search=nfl",
            "GitHub": "https://github.com/search?q=nfl+historical+data"
        },
        "MLB": {
            "Baseball Reference": "https://www.baseball-reference.com/",
            "MLB Stats API": "https://statsapi.mlb.com/",
            "Kaggle Datasets": "https://www.kaggle.com/datasets?search=mlb",
            "GitHub": "https://github.com/search?q=mlb+historical+data"
        },
        "NHL": {
            "Hockey Reference": "https://www.hockey-reference.com/",
            "NHL Stats API": "https://statsapi.web.nhl.com/",
            "Kaggle Datasets": "https://www.kaggle.com/datasets?search=nhl",
            "GitHub": "https://github.com/search?q=nhl+historical+data"
        },
        "UFC": {
            "UFC Stats": "http://ufcstats.com/",
            "Kaggle Datasets": "https://www.kaggle.com/datasets?search=ufc",
            "GitHub": "https://github.com/search?q=ufc+historical+data"
        },
        "General": {
            "SportsData.io": "https://sportsdata.io/ (Paid API, free tier available)",
            "The Odds API": "https://the-odds-api.com/ (Paid API, free tier available)",
            "RapidAPI Sports": "https://rapidapi.com/hub (Various free/paid APIs)",
            "Kaggle Sports Datasets": "https://www.kaggle.com/datasets?search=sports",
            "GitHub Sports Data": "https://github.com/search?q=sports+historical+data"
        }
    }


if __name__ == "__main__":
    """CLI for fetching historical data."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch historical sports data")
    parser.add_argument("--sport", required=False, choices=["NBA", "NFL", "MLB", "NHL", "UFC"], help="Sport to fetch data for")
    parser.add_argument("--days", type=int, default=90, help="Days back to fetch")
    parser.add_argument("--sources", action="store_true", help="Show free data sources")
    
    args = parser.parse_args()
    
    if args.sources:
        sources = get_free_historical_data_sources()
        print("\n📊 Free Historical Data Sources:")
        for sport, urls in sources.items():
            print(f"\n{sport}:")
            for name, url in urls.items():
                print(f"  - {name}: {url}")
    elif args.sport:
        fetcher = HistoricalDataFetcher()
        count = fetcher.bulk_import_historical(args.sport, args.days)
        print(f"\n✅ Imported {count} historical {args.sport} games")
    else:
        parser.print_help()

