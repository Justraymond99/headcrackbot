"""Notification and alert system."""
from typing import List, Optional, Dict
from datetime import datetime
from models import Notification, Game, Parlay, SessionLocal
import logging

logger = logging.getLogger(__name__)


class NotificationSystem:
    """Handle notifications and alerts."""
    
    def __init__(self, user_id: str = "default"):
        self.session = SessionLocal()
        self.user_id = user_id
    
    def create_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        priority: str = "normal",
        related_game: Optional[Game] = None,
        related_parlay: Optional[Parlay] = None
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=self.user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            related_game_id=related_game.id if related_game else None,
            related_parlay_id=related_parlay.id if related_parlay else None
        )
        self.session.add(notification)
        self.session.commit()
        return notification
    
    def notify_odds_alert(self, game: Game, bet_type: str, selection: str, target_odds: float, current_odds: float):
        """Notify when odds hit target."""
        title = f"Odds Alert: {selection}"
        message = f"{game.sport}: {selection} odds are now {current_odds:.0f} (target: {target_odds:.0f})"
        self.create_notification("odds_alert", title, message, "high", related_game=game)
    
    def notify_line_movement(self, game: Game, bet_type: str, old_odds: float, new_odds: float):
        """Notify on significant line movement."""
        movement = new_odds - old_odds
        title = f"Line Movement: {game.sport}"
        message = f"Line moved {movement:+.0f} points ({old_odds:.0f} → {new_odds:.0f})"
        self.create_notification("line_movement", title, message, "normal", related_game=game)
    
    def notify_parlay_result(self, parlay: Parlay):
        """Notify when parlay result is determined."""
        if parlay.result == "win":
            title = "🎉 Parlay Win!"
            message = f"Your parlay '{parlay.name}' won! Payout: ${parlay.payout:.2f}"
            priority = "high"
        else:
            title = "Parlay Result"
            message = f"Your parlay '{parlay.name}' did not win."
            priority = "normal"
        
        self.create_notification("parlay_result", title, message, priority, related_parlay=parlay)
    
    def notify_game_starting(self, game: Game):
        """Notify when game is about to start."""
        title = f"Game Starting: {game.sport}"
        if game.sport == "UFC":
            message = f"{game.fighter1} vs {game.fighter2} is starting soon!"
        else:
            message = f"{game.away_team} @ {game.home_team} is starting soon!"
        self.create_notification("game_starting", title, message, "normal", related_game=game)
    
    def get_unread_notifications(self, limit: int = 20) -> List[Notification]:
        """Get unread notifications."""
        return self.session.query(Notification).filter_by(
            user_id=self.user_id,
            read=False
        ).order_by(Notification.created_at.desc()).limit(limit).all()
    
    def mark_as_read(self, notification_id: int):
        """Mark notification as read."""
        notification = self.session.query(Notification).filter_by(
            id=notification_id,
            user_id=self.user_id
        ).first()
        if notification:
            notification.read = True
            self.session.commit()
    
    def mark_all_as_read(self):
        """Mark all notifications as read."""
        self.session.query(Notification).filter_by(
            user_id=self.user_id,
            read=False
        ).update({"read": True})
        self.session.commit()
    
    def get_notification_count(self) -> int:
        """Get count of unread notifications."""
        return self.session.query(Notification).filter_by(
            user_id=self.user_id,
            read=False
        ).count()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

