"""User preferences and filtering for picks."""
from typing import List, Dict, Optional
from datetime import datetime, time as dt_time
from models import Game, SessionLocal
import logging
import os

logger = logging.getLogger(__name__)


class PickPreferences:
    """Handle user preferences for pick filtering and scheduling."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.load_preferences()
    
    def load_preferences(self):
        """Load preferences from environment variables."""
        # Time preferences
        self.send_start_hour = int(os.getenv("PICKS_SEND_START_HOUR", "8"))
        self.send_end_hour = int(os.getenv("PICKS_SEND_END_HOUR", "22"))
        
        # Sport preferences (weights)
        sports_pref = os.getenv("PICKS_SPORT_WEIGHTS", "")
        if sports_pref:
            self.sport_weights = {}
            for item in sports_pref.split(","):
                if ":" in item:
                    sport, weight = item.split(":")
                    self.sport_weights[sport.strip()] = float(weight.strip())
                else:
                    self.sport_weights[item.strip()] = 1.0
        else:
            self.sport_weights = {}  # No weighting
        
        # Confidence filtering
        self.min_confidence_hours = {}
        # Lower confidence required during certain hours
        early_hour_conf = os.getenv("PICKS_EARLY_HOUR_CONFIDENCE", "0.7")
        self.min_confidence_hours["early"] = float(early_hour_conf)
        
        # Bet type preferences
        bet_type_pref = os.getenv("PICKS_BET_TYPE_PREFERENCE", "")
        self.preferred_bet_types = bet_type_pref.split(",") if bet_type_pref else []
        
        # Day of week preferences
        day_pref = os.getenv("PICKS_DAYS", "")
        self.allowed_days = day_pref.split(",") if day_pref else []
    
    def is_within_send_hours(self) -> bool:
        """Check if current time is within allowed send hours."""
        now = datetime.utcnow()
        current_hour = now.hour
        
        if self.send_start_hour <= self.send_end_hour:
            # Normal case (e.g., 8 AM - 10 PM)
            return self.send_start_hour <= current_hour < self.send_end_hour
        else:
            # Wraps around midnight (e.g., 10 PM - 8 AM)
            return current_hour >= self.send_start_hour or current_hour < self.send_end_hour
    
    def get_required_confidence_for_current_hour(self) -> float:
        """Get required confidence based on current hour."""
        current_hour = datetime.utcnow().hour
        
        # Early morning (before 9 AM) or late night (after 10 PM) - higher confidence
        if current_hour < 9 or current_hour >= 22:
            return self.min_confidence_hours.get("early", 0.7)
        
        # Normal hours - default confidence
        return 0.6
    
    def apply_sport_weights(
        self,
        picks: List[Dict]
    ) -> List[Dict]:
        """
        Apply sport weights to picks.
        
        Args:
            picks: List of pick dictionaries
        
        Returns:
            Weighted picks (sorted by weighted score)
        """
        if not self.sport_weights:
            return picks
        
        # Calculate weighted scores
        for pick in picks:
            game = pick.get("game")
            if game and game.sport in self.sport_weights:
                weight = self.sport_weights[game.sport]
                # Multiply confidence and EV by weight
                pick["weighted_confidence"] = pick.get("confidence", 0) * weight
                pick["weighted_ev"] = pick.get("expected_value", 0) * weight
            else:
                pick["weighted_confidence"] = pick.get("confidence", 0)
                pick["weighted_ev"] = pick.get("expected_value", 0)
        
        # Re-sort by weighted score
        picks.sort(
            key=lambda x: (x["weighted_ev"] * 0.6) + (x["weighted_confidence"] * 0.4),
            reverse=True
        )
        
        return picks
    
    def filter_by_bet_type_preferences(
        self,
        picks: List[Dict]
    ) -> List[Dict]:
        """
        Filter picks based on bet type preferences.
        
        Args:
            picks: List of pick dictionaries
        
        Returns:
            Filtered picks
        """
        if not self.preferred_bet_types:
            return picks
        
        filtered = []
        for pick in picks:
            bet_type = pick.get("bet_type", "")
            if bet_type in self.preferred_bet_types:
                filtered.append(pick)
            else:
                # Still include non-preferred, but could prioritize
                filtered.append(pick)
        
        # Sort preferred bet types first
        filtered.sort(
            key=lambda x: (
                0 if x.get("bet_type", "") in self.preferred_bet_types else 1,
                -((x.get("expected_value", 0) * 0.6) + (x.get("confidence", 0) * 0.4))
            )
        )
        
        return filtered
    
    def filter_by_day_preferences(
        self,
        picks: List[Dict]
    ) -> List[Dict]:
        """
        Filter picks based on day of week preferences.
        
        Args:
            picks: List of pick dictionaries
        
        Returns:
            Filtered picks
        """
        if not self.allowed_days:
            return picks
        
        current_day = datetime.utcnow().strftime("%A").lower()
        
        if current_day not in [day.lower() for day in self.allowed_days]:
            # Not an allowed day - filter by removing picks for games today
            filtered = []
            for pick in picks:
                game = pick.get("game")
                if game and game.game_date:
                    game_day = game.game_date.strftime("%A").lower()
                    if game_day == current_day:
                        continue  # Skip games today
                filtered.append(pick)
            return filtered
        
        return picks
    
    def apply_all_preferences(
        self,
        picks: List[Dict]
    ) -> List[Dict]:
        """
        Apply all user preferences to picks.
        
        Args:
            picks: List of pick dictionaries
        
        Returns:
            Filtered and weighted picks
        """
        # Filter by day preferences
        picks = self.filter_by_day_preferences(picks)
        
        # Filter by confidence for current hour
        min_confidence = self.get_required_confidence_for_current_hour()
        picks = [p for p in picks if p.get("confidence", 0) >= min_confidence]
        
        # Apply sport weights
        picks = self.apply_sport_weights(picks)
        
        # Filter by bet type preferences (and prioritize)
        picks = self.filter_by_bet_type_preferences(picks)
        
        return picks
    
    def should_send_picks_now(self):
        """
        Check if picks should be sent now based on preferences.
        
        Returns:
            (should_send, reason)
        """
        # Check time window
        if not self.is_within_send_hours():
            return False, f"Outside send hours ({self.send_start_hour}:00-{self.send_end_hour}:00)"
        
        # Check day preferences
        if self.allowed_days:
            current_day = datetime.utcnow().strftime("%A")
            if current_day not in self.allowed_days:
                return False, f"Not an allowed day ({', '.join(self.allowed_days)})"
        
        return True, "OK"
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

