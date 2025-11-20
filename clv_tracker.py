"""Closing Line Value (CLV) tracker."""
from typing import Optional
from datetime import datetime, timedelta
from models import Leg, ClosingLineValue, Game, SessionLocal
import logging

logger = logging.getLogger(__name__)


class CLVTracker:
    """Track Closing Line Value for bets."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def record_opening_odds(self, leg: Leg, odds: float):
        """Record opening odds when bet is placed."""
        clv = self.session.query(ClosingLineValue).filter_by(leg_id=leg.id).first()
        
        if not clv:
            clv = ClosingLineValue(leg_id=leg.id)
            self.session.add(clv)
        
        clv.opening_odds = odds
        clv.your_odds = leg.odds
        self.session.commit()
    
    def update_closing_odds(self, leg: Leg, closing_odds: float):
        """Update with closing line odds."""
        clv = self.session.query(ClosingLineValue).filter_by(leg_id=leg.id).first()
        
        if not clv:
            logger.warning(f"No CLV record for leg {leg.id}")
            return
        
        clv.closing_odds = closing_odds
        
        # Calculate CLV metrics
        if clv.your_odds and closing_odds:
            # CLV percentage: (closing - your) / your
            # Positive = you got better odds than closing (good!)
            clv.clv_percentage = ((closing_odds - clv.your_odds) / abs(clv.your_odds)) * 100
            
            # Did you beat closing line?
            # For favorites (negative odds), lower absolute value = better
            # For underdogs (positive odds), higher = better
            if clv.your_odds < 0 and closing_odds < 0:
                clv.beat_closing_line = abs(clv.your_odds) < abs(closing_odds)
            elif clv.your_odds > 0 and closing_odds > 0:
                clv.beat_closing_line = clv.your_odds > closing_odds
            else:
                clv.beat_closing_line = False
            
            # Sharp indicator (0-1): higher = sharper
            # Based on how much you beat closing by
            if clv.beat_closing_line:
                clv.sharp_indicator = min(1.0, abs(clv.clv_percentage) / 10.0)
            else:
                clv.sharp_indicator = max(0.0, 1.0 - abs(clv.clv_percentage) / 10.0)
            
            # Line movement
            if clv.opening_odds:
                clv.line_movement = closing_odds - clv.opening_odds
                
                # Movement direction
                if clv.your_odds < 0 and closing_odds < 0:
                    # Both favorites - movement toward you = closing more negative
                    clv.movement_direction = "toward_you" if abs(closing_odds) > abs(clv.your_odds) else "away_from_you"
                elif clv.your_odds > 0 and closing_odds > 0:
                    # Both underdogs - movement toward you = closing higher
                    clv.movement_direction = "toward_you" if closing_odds > clv.your_odds else "away_from_you"
                else:
                    clv.movement_direction = "unknown"
        
        self.session.commit()
    
    def get_clv_for_leg(self, leg: Leg) -> Optional[ClosingLineValue]:
        """Get CLV record for a leg."""
        return self.session.query(ClosingLineValue).filter_by(leg_id=leg.id).first()
    
    def get_average_clv(self, days: int = 30) -> float:
        """Get average CLV over time period."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        clv_records = self.session.query(ClosingLineValue).join(Leg).filter(
            ClosingLineValue.created_at >= cutoff,
            ClosingLineValue.closing_odds.isnot(None)
        ).all()
        
        if not clv_records:
            return 0.0
        
        return sum(c.clv_percentage for c in clv_records) / len(clv_records)
    
    def get_sharp_score(self) -> float:
        """Get overall sharp score (0-1)."""
        clv_records = self.session.query(ClosingLineValue).filter(
            ClosingLineValue.sharp_indicator.isnot(None)
        ).all()
        
        if not clv_records:
            return 0.5  # Neutral
        
        return sum(c.sharp_indicator for c in clv_records) / len(clv_records)
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

