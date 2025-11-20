"""Streak tracking system."""
from typing import Optional, Dict
from datetime import datetime
from models import Streak, Parlay, SessionLocal
import logging

logger = logging.getLogger(__name__)


class StreakTracker:
    """Track win/loss streaks."""
    
    def __init__(self, user_id: str = "default"):
        self.session = SessionLocal()
        self.user_id = user_id
    
    def update_streaks(self, parlay: Parlay):
        """Update streaks based on parlay result."""
        if parlay.result not in ["win", "loss"]:
            return
        
        # Get or create streak records
        overall_streak = self._get_or_create_streak(None, None)
        sport_streak = self._get_or_create_streak(parlay.sport, None)
        
        # Update overall streak
        self._update_streak(overall_streak, parlay.result)
        
        # Update sport-specific streak
        if parlay.sport:
            self._update_streak(sport_streak, parlay.result)
        
        self.session.commit()
    
    def _get_or_create_streak(self, sport: Optional[str], bet_type: Optional[str]) -> Streak:
        """Get or create streak record."""
        streak = self.session.query(Streak).filter_by(
            user_id=self.user_id,
            sport=sport,
            bet_type=bet_type
        ).first()
        
        if not streak:
            streak = Streak(
                user_id=self.user_id,
                sport=sport,
                bet_type=bet_type,
                streak_type="win",
                current_streak=0,
                longest_streak=0
            )
            self.session.add(streak)
        
        return streak
    
    def _update_streak(self, streak: Streak, result: str):
        """Update a streak record."""
        if result == streak.streak_type:
            # Continue streak
            streak.current_streak += 1
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
        else:
            # Break streak, start new one
            streak.streak_type = result
            streak.current_streak = 1
            streak.streak_started = datetime.utcnow()
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
        
        streak.last_updated = datetime.utcnow()
    
    def get_current_streak(self, sport: Optional[str] = None) -> Dict:
        """Get current streak info."""
        streak = self._get_or_create_streak(sport, None)
        return {
            "type": streak.streak_type,
            "current": streak.current_streak,
            "longest": streak.longest_streak,
            "started": streak.streak_started
        }
    
    def get_all_streaks(self) -> Dict:
        """Get all streak records."""
        streaks = self.session.query(Streak).filter_by(user_id=self.user_id).all()
        return {
            s.sport or "Overall": {
                "type": s.streak_type,
                "current": s.current_streak,
                "longest": s.longest_streak
            }
            for s in streaks
        }
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

