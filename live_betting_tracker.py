"""Live betting and real-time odds tracking."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, SessionLocal
from data_intake import DataIntake
import logging

logger = logging.getLogger(__name__)


class LiveBettingTracker:
    """Track live games and real-time odds."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.data_intake = DataIntake()
    
    def get_live_games(self) -> List[Game]:
        """Get games currently in progress."""
        return self.session.query(Game).filter_by(status="live").all()
    
    def update_live_odds(self, game: Game):
        """Update odds for a live game."""
        # In real implementation, would fetch from live odds API
        # For now, simulate with small variations
        if game.home_moneyline:
            # Simulate live odds movement
            game.home_moneyline += self._simulate_movement()
            game.away_moneyline = self._calculate_opposite_odds(game.home_moneyline)
        
        game.updated_at = datetime.utcnow()
        self.session.commit()
    
    def _simulate_movement(self) -> float:
        """Simulate live odds movement."""
        import random
        return random.uniform(-10, 10)
    
    def _calculate_opposite_odds(self, odds: float) -> float:
        """Calculate opposite side odds."""
        if odds > 0:
            implied = 100 / (odds + 100)
        else:
            implied = abs(odds) / (abs(odds) + 100)
        
        opposite_implied = 1 - implied
        
        if opposite_implied > 0.5:
            return -100 / (opposite_implied - 1)
        else:
            return (100 / opposite_implied) - 100
    
    def get_live_score(self, game: Game) -> Optional[Dict]:
        """Get live score for a game."""
        # In real implementation, would fetch from live score API
        # For now, return None (would need SportsData.io live scores)
        return None
    
    def check_for_live_opportunities(self) -> List[Dict]:
        """Check for live betting opportunities."""
        live_games = self.get_live_games()
        opportunities = []
        
        for game in live_games:
            # Update odds
            self.update_live_odds(game)
            
            # Check for value (simplified)
            if game.home_moneyline and game.away_moneyline:
                home_implied = self._american_to_implied_prob(game.home_moneyline)
                away_implied = self._american_to_implied_prob(game.away_moneyline)
                
                # If odds shifted significantly, might be opportunity
                if abs(home_implied - 0.5) > 0.1:
                    opportunities.append({
                        "game": game,
                        "type": "live_odds_shift",
                        "message": f"Significant odds movement detected"
                    })
        
        return opportunities
    
    def _american_to_implied_prob(self, american_odds: float) -> float:
        """Convert American odds to implied probability."""
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)
    
    def monitor_game(self, game: Game, callback=None):
        """Monitor a game for live updates."""
        # In real implementation, would set up polling or websocket
        # For now, just update odds periodically
        if game.status == "live":
            self.update_live_odds(game)
            if callback:
                callback(game)
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

