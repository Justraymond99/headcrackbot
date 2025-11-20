"""Real-time odds monitoring and alerting."""
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from models import Game, SessionLocal
from config import ODDS_API_KEY, ODDS_API_BASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OddsMonitor:
    """Monitor odds changes and trigger alerts."""
    
    def __init__(self, check_interval: int = 300):  # 5 minutes default
        self.check_interval = check_interval
        self.session = SessionLocal()
        self.alert_callbacks: List[Callable] = []
        self.last_odds: Dict[int, Dict] = {}  # game_id -> odds snapshot
    
    def register_alert(self, callback: Callable):
        """Register a callback function for odds alerts."""
        self.alert_callbacks.append(callback)
    
    def check_odds_changes(self, sport: str = "basketball_nba") -> List[Dict]:
        """Check for significant odds changes."""
        if not ODDS_API_KEY:
            logger.warning("Odds API key not configured")
            return []
        
        url = f"{ODDS_API_BASE_URL}/sports/{sport}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            games = response.json()
            
            alerts = []
            for game_data in games:
                game_id = self._get_game_id(game_data)
                current_odds = self._extract_odds(game_data)
                
                if game_id in self.last_odds:
                    changes = self._detect_changes(
                        self.last_odds[game_id],
                        current_odds
                    )
                    
                    if changes:
                        alerts.append({
                            'game': game_data,
                            'changes': changes,
                            'timestamp': datetime.now()
                        })
                        
                        # Trigger callbacks
                        for callback in self.alert_callbacks:
                            try:
                                callback(game_data, changes)
                            except Exception as e:
                                logger.error(f"Alert callback error: {e}")
                
                self.last_odds[game_id] = current_odds
            
            return alerts
        
        except Exception as e:
            logger.error(f"Error checking odds: {e}")
            return []
    
    def _get_game_id(self, game_data: Dict) -> int:
        """Get or create game ID from API data."""
        home = game_data.get("home_team", "")
        away = game_data.get("away_team", "")
        date_str = game_data.get("commence_time", "")
        
        # Try to find existing game
        game = self.session.query(Game).filter_by(
            home_team=home,
            away_team=away
        ).first()
        
        if game:
            return game.id
        
        # Return hash as temporary ID
        return hash(f"{home}_{away}_{date_str}")
    
    def _extract_odds(self, game_data: Dict) -> Dict:
        """Extract odds from API response."""
        odds = {
            'home_ml': None,
            'away_ml': None,
            'spread': None,
            'total': None
        }
        
        bookmakers = game_data.get("bookmakers", [])
        if bookmakers:
            book = bookmakers[0]
            markets = book.get("markets", [])
            
            for market in markets:
                if market["key"] == "h2h":
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        if outcome["name"] == game_data.get("home_team"):
                            odds['home_ml'] = outcome.get("price")
                        elif outcome["name"] == game_data.get("away_team"):
                            odds['away_ml'] = outcome.get("price")
                
                elif market["key"] == "spreads":
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        if outcome["name"] == game_data.get("home_team"):
                            odds['spread'] = outcome.get("point")
                
                elif market["key"] == "totals":
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        if outcome["name"] == "Over":
                            odds['total'] = outcome.get("point")
        
        return odds
    
    def _detect_changes(self, old_odds: Dict, new_odds: Dict, threshold: float = 0.1) -> List[Dict]:
        """Detect significant odds changes (10% threshold)."""
        changes = []
        
        for key in ['home_ml', 'away_ml']:
            if old_odds.get(key) and new_odds.get(key):
                old_val = old_odds[key]
                new_val = new_odds[key]
                
                # Calculate percentage change
                change_pct = abs((new_val - old_val) / old_val) * 100
                
                if change_pct >= threshold * 100:
                    changes.append({
                        'market': key,
                        'old': old_val,
                        'new': new_val,
                        'change_pct': change_pct
                    })
        
        return changes
    
    def start_monitoring(self, sport: str = "basketball_nba", duration: int = 3600):
        """Start continuous monitoring."""
        logger.info(f"Starting odds monitoring for {sport}")
        end_time = datetime.now() + timedelta(seconds=duration)
        
        while datetime.now() < end_time:
            alerts = self.check_odds_changes(sport)
            
            if alerts:
                logger.info(f"Found {len(alerts)} odds changes")
                for alert in alerts:
                    logger.info(f"Alert: {alert['changes']}")
            
            time.sleep(self.check_interval)
        
        logger.info("Monitoring stopped")
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

