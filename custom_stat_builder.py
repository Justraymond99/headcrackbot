"""Custom stat builder for user-defined metrics."""
from typing import List, Dict, Optional
from datetime import datetime
from models import CustomStat, Game, TeamStat, SessionLocal
import logging

logger = logging.getLogger(__name__)


class CustomStatBuilder:
    """Build and calculate custom statistics."""
    
    def __init__(self, user_id: str = "default"):
        self.session = SessionLocal()
        self.user_id = user_id
    
    def create_stat(
        self,
        name: str,
        formula: str,
        description: Optional[str] = None,
        sport: Optional[str] = None,
        stat_type: str = "team"
    ) -> CustomStat:
        """Create a custom stat definition."""
        stat = CustomStat(
            user_id=self.user_id,
            name=name,
            description=description,
            formula=formula,
            sport=sport,
            stat_type=stat_type
        )
        self.session.add(stat)
        self.session.commit()
        return stat
    
    def calculate_stat(self, stat: CustomStat, entity_id: int) -> float:
        """Calculate stat value for an entity."""
        try:
            # Get entity data
            if stat.stat_type == "team":
                team_stat = self.session.query(TeamStat).filter_by(id=entity_id).first()
                if not team_stat:
                    return 0.0
                
                # Build context for formula evaluation
                context = {
                    "offensive_rating": team_stat.offensive_rating or 0,
                    "defensive_rating": team_stat.defensive_rating or 0,
                    "win_streak": team_stat.win_streak or 0,
                    "loss_streak": team_stat.loss_streak or 0,
                    "pace": team_stat.pace or 0
                }
                
                # Evaluate formula (safely)
                result = eval(stat.formula, {"__builtins__": {}}, context)
                return float(result)
            
            elif stat.stat_type == "game":
                game = self.session.query(Game).filter_by(id=entity_id).first()
                if not game:
                    return 0.0
                
                context = {
                    "home_moneyline": game.home_moneyline or 0,
                    "away_moneyline": game.away_moneyline or 0,
                    "spread": game.spread or 0,
                    "total": game.total or 0
                }
                
                result = eval(stat.formula, {"__builtins__": {}}, context)
                return float(result)
            
        except Exception as e:
            logger.error(f"Error calculating stat {stat.name}: {e}")
            return 0.0
    
    def calculate_all(self, stat: CustomStat) -> Dict:
        """Calculate stat for all applicable entities."""
        values = {}
        
        if stat.stat_type == "team":
            teams = self.session.query(TeamStat).filter_by(sport=stat.sport).all() if stat.sport else \
                    self.session.query(TeamStat).all()
            
            for team in teams:
                value = self.calculate_stat(stat, team.id)
                values[team.team] = value
        
        elif stat.stat_type == "game":
            games = self.session.query(Game).filter_by(sport=stat.sport).all() if stat.sport else \
                    self.session.query(Game).all()
            
            for game in games:
                value = self.calculate_stat(stat, game.id)
                values[f"Game_{game.id}"] = value
        
        # Update stat cache
        stat.values = values
        stat.last_calculated = datetime.utcnow()
        self.session.commit()
        
        return values
    
    def get_user_stats(self) -> List[CustomStat]:
        """Get all user's custom stats."""
        return self.session.query(CustomStat).filter_by(user_id=self.user_id).all()
    
    def delete_stat(self, stat_id: int):
        """Delete a custom stat."""
        stat = self.session.query(CustomStat).filter_by(
            id=stat_id,
            user_id=self.user_id
        ).first()
        if stat:
            self.session.delete(stat)
            self.session.commit()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

