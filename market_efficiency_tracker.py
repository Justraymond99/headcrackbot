"""Market efficiency and line movement tracking."""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from models import Game, MarketEfficiency, SessionLocal
import logging

logger = logging.getLogger(__name__)


class MarketEfficiencyTracker:
    """Track market efficiency and line movement."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def track_game(self, game: Game, opening_line: Optional[float] = None):
        """Start tracking a game's market efficiency."""
        efficiency = self.session.query(MarketEfficiency).filter_by(game_id=game.id).first()
        
        if not efficiency:
            efficiency = MarketEfficiency(
                game_id=game.id,
                opening_line=opening_line or game.spread or game.total,
                current_line=opening_line or game.spread or game.total,
                efficiency_score=0.5  # Neutral
            )
            self.session.add(efficiency)
        else:
            if opening_line:
                efficiency.opening_line = opening_line
            efficiency.current_line = game.spread or game.total
        
        self._update_efficiency(efficiency, game)
        self.session.commit()
    
    def update_line(self, game: Game, new_line: float, public_pct: Optional[float] = None):
        """Update line and check for efficiency signals."""
        efficiency = self.session.query(MarketEfficiency).filter_by(game_id=game.id).first()
        
        if not efficiency:
            self.track_game(game, new_line)
            efficiency = self.session.query(MarketEfficiency).filter_by(game_id=game.id).first()
        
        old_line = efficiency.current_line
        efficiency.current_line = new_line
        efficiency.line_movement = new_line - (efficiency.opening_line or new_line)
        
        # Check for reverse line movement
        if public_pct is not None:
            efficiency.public_percentage = public_pct
            # If public is heavy on one side but line moves opposite = sharp money
            if public_pct > 70 and efficiency.line_movement < 0:
                efficiency.reverse_line_movement = True
            elif public_pct < 30 and efficiency.line_movement > 0:
                efficiency.reverse_line_movement = True
            else:
                efficiency.reverse_line_movement = False
        
        # Check for steam moves (rapid line movement)
        if old_line and abs(new_line - old_line) > 2:
            efficiency.steam_move_detected = True
            efficiency.steam_move_time = datetime.utcnow()
        
        self._update_efficiency(efficiency, game)
        efficiency.updated_at = datetime.utcnow()
        self.session.commit()
    
    def update_closing_line(self, game: Game, closing_line: float):
        """Update closing line when game starts."""
        efficiency = self.session.query(MarketEfficiency).filter_by(game_id=game.id).first()
        
        if efficiency:
            efficiency.closing_line = closing_line
            efficiency.line_movement = closing_line - (efficiency.opening_line or closing_line)
            self._update_efficiency(efficiency, game)
            self.session.commit()
    
    def _update_efficiency(self, efficiency: MarketEfficiency, game: Game):
        """Calculate efficiency score."""
        score = 0.5  # Base score
        
        # Reverse line movement = more efficient (sharp money)
        if efficiency.reverse_line_movement:
            score += 0.2
        
        # Steam moves = sharp action
        if efficiency.steam_move_detected:
            score += 0.1
        
        # Large line movement = potential inefficiency
        if efficiency.line_movement and abs(efficiency.line_movement) > 3:
            score -= 0.1
        
        efficiency.efficiency_score = max(0.0, min(1.0, score))
    
    def get_efficiency(self, game: Game) -> Optional[MarketEfficiency]:
        """Get market efficiency for a game."""
        return self.session.query(MarketEfficiency).filter_by(game_id=game.id).first()
    
    def get_inefficient_markets(self, threshold: float = 0.4) -> List[MarketEfficiency]:
        """Find markets with low efficiency (potential value)."""
        return self.session.query(MarketEfficiency).filter(
            MarketEfficiency.efficiency_score < threshold,
            MarketEfficiency.current_line.isnot(None)
        ).all()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

