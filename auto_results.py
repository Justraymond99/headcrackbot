"""Automatic game result fetching and updating."""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from models import Game, SessionLocal
from result_tracker import ResultTracker
from config import ODDS_API_KEY, SPORTSDATA_API_KEY, SPORTSDATA_BASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoResultUpdater:
    """Automatically fetch and update game results."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.tracker = ResultTracker()
        self.sportsdata_key = SPORTSDATA_API_KEY
        self.odds_api_key = ODDS_API_KEY
    
    def fetch_game_results(self, sport: str, date: Optional[datetime] = None) -> List[Dict]:
        """Fetch completed game results from SportsData.io."""
        if not self.sportsdata_key:
            logger.warning("SportsData API key not configured. Cannot fetch results automatically.")
            return []
        
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        
        try:
            # Different endpoints for different sports
            if sport == "NBA":
                url = f"{SPORTSDATA_BASE_URL}/nba/scores/json/Scores/{date_str}"
            elif sport == "NFL":
                url = f"{SPORTSDATA_BASE_URL}/nfl/scores/json/Scores/{date_str}"
            elif sport == "MLB":
                url = f"{SPORTSDATA_BASE_URL}/mlb/scores/json/Scores/{date_str}"
            elif sport == "NHL":
                url = f"{SPORTSDATA_BASE_URL}/nhl/scores/json/Scores/{date_str}"
            else:
                return []
            
            headers = {"Ocp-Apim-Subscription-Key": self.sportsdata_key}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logger.error(f"Error fetching results for {sport}: {e}")
            return []
    
    def update_results_from_api(self, sport: str, date: Optional[datetime] = None):
        """Update game results from API."""
        results = self.fetch_game_results(sport, date)
        
        if not results:
            logger.info(f"No results found for {sport} on {date}")
            return
        
        updated_count = 0
        for result_data in results:
            try:
                # Match game by teams and date
                home_team = result_data.get("HomeTeam", "")
                away_team = result_data.get("AwayTeam", "")
                game_date = datetime.fromisoformat(result_data.get("DateTime", datetime.now().isoformat()))
                
                # Find game in database
                game = self.session.query(Game).filter(
                    Game.sport == sport,
                    Game.home_team == home_team,
                    Game.away_team == away_team,
                    Game.game_date >= game_date - timedelta(hours=12),
                    Game.game_date <= game_date + timedelta(hours=12)
                ).first()
                
                if game and game.status != "finished":
                    # Get scores
                    home_score = result_data.get("HomeTeamScore") or result_data.get("HomeScore") or 0
                    away_score = result_data.get("AwayTeamScore") or result_data.get("AwayScore") or 0
                    
                    if home_score is not None and away_score is not None:
                        # Update game result
                        self.tracker.update_game_result(game.id, int(home_score), int(away_score))
                        
                        # Update parlay results
                        from models import Parlay, Leg
                        parlays = self.session.query(Parlay).join(Leg).filter(
                            Leg.game_id == game.id
                        ).distinct().all()
                        
                        for parlay in parlays:
                            self.tracker.update_parlay_result(parlay.id)
                        
                        updated_count += 1
                        logger.info(f"Updated result for {sport}: {away_team} @ {home_team} ({away_score}-{home_score})")
            
            except Exception as e:
                logger.error(f"Error updating result: {e}")
                continue
        
        self.session.commit()
        logger.info(f"Updated {updated_count} game results for {sport}")
    
    def update_all_pending_results(self, sports: List[str] = None):
        """Update all pending game results."""
        if sports is None:
            sports = ["NBA", "NFL", "MLB", "NHL", "UFC"]
        
        # Check yesterday and today's games
        for days_ago in [1, 0]:
            date = datetime.now() - timedelta(days=days_ago)
            
            for sport in sports:
                if sport == "UFC":
                    # UFC results would need different handling
                    continue
                
                logger.info(f"Checking results for {sport} on {date.date()}")
                self.update_results_from_api(sport, date)
    
    def update_ufc_results(self):
        """Update UFC fight results (manual or from API if available)."""
        # UFC results typically need manual entry or different API
        # For now, check for finished games that need results
        ufc_games = self.session.query(Game).filter(
            Game.sport == "UFC",
            Game.status == "scheduled",
            Game.game_date < datetime.now() - timedelta(hours=6)  # Games that should be finished
        ).all()
        
        logger.info(f"Found {len(ufc_games)} UFC games that may need results")
        # Would need UFC-specific result fetching here
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

