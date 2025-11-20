"""Model and utilities for tracking sent picks."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from datetime import datetime, timedelta
from models import Base, SessionLocal
from typing import Optional


class SentPick(Base):
    """Track picks that have been sent via SMS."""
    __tablename__ = "sent_picks"
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    bet_type = Column(String, nullable=False)
    selection = Column(String, nullable=False)
    odds = Column(Float)
    expected_value = Column(Float)
    confidence = Column(Float)
    
    # Tracking
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    message_id = Column(String)  # Twilio message SID if available
    
    # Prevent duplicates
    __table_args__ = (
        Index('idx_game_bet_selection_sent', 'game_id', 'bet_type', 'selection', 'sent_at'),
    )
    
    def __repr__(self):
        return f"<SentPick(game_id={self.game_id}, {self.bet_type}, {self.selection}, sent_at={self.sent_at})>"


class SentPickTracker:
    """Track and filter sent picks."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def was_pick_sent_recently(
        self,
        game_id: int,
        bet_type: str,
        selection: str,
        hours: int = 6,
        player_name: Optional[str] = None,
        prop_type: Optional[str] = None,
        prop_value: Optional[float] = None
    ) -> bool:
        """
        Check if a pick was sent recently.
        
        Args:
            game_id: Game ID
            bet_type: Bet type (moneyline, spread, prop, etc.)
            selection: Selection (team name, over/under, etc.)
            hours: How many hours back to check
            player_name: Player name (for props)
            prop_type: Prop type (for props)
            prop_value: Prop value (for props)
        
        Returns:
            True if pick was sent within the time window
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = self.session.query(SentPick).filter(
            SentPick.game_id == game_id,
            SentPick.bet_type == bet_type,
            SentPick.selection == selection,
            SentPick.sent_at >= cutoff_time
        )
        
        # For player props, also check player name and prop type/value in the selection
        # Since we store selection as a string like "Over 25.5", we check if it matches
        if bet_type == "prop" and player_name and prop_type:
            # The selection field contains the over/under info, but we also want to check player
            # For now, we'll rely on the selection matching, but could enhance with additional fields
            pass
        
        existing = query.first()
        return existing is not None
    
    def record_sent_pick(
        self,
        game_id: int,
        bet_type: str,
        selection: str,
        odds: Optional[float] = None,
        expected_value: Optional[float] = None,
        confidence: Optional[float] = None,
        message_id: Optional[str] = None
    ) -> SentPick:
        """Record that a pick was sent."""
        sent_pick = SentPick(
            game_id=game_id,
            bet_type=bet_type,
            selection=selection,
            odds=odds,
            expected_value=expected_value,
            confidence=confidence,
            message_id=message_id,
            sent_at=datetime.utcnow()
        )
        self.session.add(sent_pick)
        self.session.commit()
        return sent_pick
    
    def filter_recent_picks(
        self,
        picks: list,
        hours: int = 6
    ) -> list:
        """
        Filter out picks that were sent recently.
        
        Args:
            picks: List of pick dictionaries
            hours: How many hours back to check
        
        Returns:
            Filtered list of picks
        """
        filtered = []
        for pick in picks:
            game = pick.get("game")
            if not game:
                continue
            
            if not self.was_pick_sent_recently(
                game.id,
                pick.get("bet_type", ""),
                pick.get("selection", ""),
                hours=hours,
                player_name=pick.get("player_name"),
                prop_type=pick.get("prop_type"),
                prop_value=pick.get("prop_value")
            ):
                filtered.append(pick)
        
        return filtered
    
    def get_recent_sent_count(self, hours: int = 24) -> int:
        """Get count of picks sent in the last N hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return self.session.query(SentPick).filter(
            SentPick.sent_at >= cutoff_time
        ).count()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

