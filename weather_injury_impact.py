"""Weather and injury impact analysis."""
from typing import Dict, Optional, List
from datetime import datetime
from models import Game, PlayerStat, SessionLocal
import logging

logger = logging.getLogger(__name__)


class WeatherInjuryImpact:
    """Analyze weather and injury impacts on games."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def get_injury_impact(self, game: Game) -> Dict:
        """Get injury impact for a game."""
        # Get player stats/injuries for the game
        player_stats = self.session.query(PlayerStat).filter_by(game_id=game.id).all()
        
        if not player_stats:
            return {"impact": "none", "message": "No injury data available"}
        
        # Analyze injuries
        key_injuries = []
        for ps in player_stats:
            if ps.injury_status in ["doubtful", "out"]:
                key_injuries.append({
                    "player": ps.player_name,
                    "team": ps.team,
                    "status": ps.injury_status,
                    "position": ps.position
                })
        
        if not key_injuries:
            return {"impact": "none", "message": "No key injuries"}
        
        # Calculate impact
        home_injuries = [i for i in key_injuries if i["team"] == game.home_team]
        away_injuries = [i for i in key_injuries if i["team"] == game.away_team]
        
        impact_score = 0.0
        if home_injuries:
            impact_score -= len(home_injuries) * 0.05  # 5% per key injury
        if away_injuries:
            impact_score += len(away_injuries) * 0.05
        
        return {
            "impact": "negative" if abs(impact_score) > 0.1 else "minimal",
            "impact_score": impact_score,
            "home_injuries": home_injuries,
            "away_injuries": away_injuries,
            "message": f"{len(home_injuries)} home injuries, {len(away_injuries)} away injuries"
        }
    
    def get_weather_impact(self, game: Game) -> Dict:
        """Get weather impact (for outdoor sports)."""
        outdoor_sports = ["NFL", "MLB"]
        
        if game.sport not in outdoor_sports:
            return {"impact": "none", "message": "Indoor sport"}
        
        # In real implementation, would fetch from weather API
        # For now, return placeholder
        return {
            "impact": "unknown",
            "message": "Weather data not available (would integrate with weather API)",
            "temperature": None,
            "wind": None,
            "precipitation": None
        }
    
    def adjust_probability_for_conditions(self, game: Game, base_prob: float, selection: str) -> float:
        """Adjust probability based on injuries and weather."""
        adjusted = base_prob
        
        # Injury impact
        injury_data = self.get_injury_impact(game)
        if injury_data["impact"] != "none":
            impact = injury_data["impact_score"]
            
            # Adjust based on which team
            if selection == game.home_team or selection == game.fighter1:
                adjusted += impact
            elif selection == game.away_team or selection == game.fighter2:
                adjusted -= impact
        
        # Weather impact (simplified)
        weather_data = self.get_weather_impact(game)
        if weather_data.get("precipitation"):
            # Bad weather typically favors underdogs and unders
            adjusted *= 0.98  # Slight reduction
        
        return max(0.01, min(0.99, adjusted))
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

