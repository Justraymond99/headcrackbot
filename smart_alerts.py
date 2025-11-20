"""Smart alerts system with intelligent notifications."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, Notification, ValueBet, SessionLocal
from notification_system import NotificationSystem
from line_shopper import LineShopper
import logging

logger = logging.getLogger(__name__)


class SmartAlerts:
    """Intelligent alert system."""
    
    def __init__(self, user_id: str = "default"):
        self.session = SessionLocal()
        self.user_id = user_id
        self.notification_system = NotificationSystem(user_id)
        self.line_shopper = LineShopper()
    
    def check_odds_alerts(self, game: Game, target_odds: float, bet_type: str, selection: str):
        """Check if odds hit target and alert."""
        current_odds = self._get_current_odds(game, bet_type, selection)
        
        if current_odds is None:
            return
        
        # Check if odds improved to target
        if bet_type in ["moneyline", "spread", "total"]:
            # For favorites (negative), lower absolute value = better
            # For underdogs (positive), higher = better
            if target_odds < 0 and current_odds < 0:
                if abs(current_odds) <= abs(target_odds):
                    self.notification_system.notify_odds_alert(
                        game, bet_type, selection, target_odds, current_odds
                    )
            elif target_odds > 0 and current_odds > 0:
                if current_odds >= target_odds:
                    self.notification_system.notify_odds_alert(
                        game, bet_type, selection, target_odds, current_odds
                    )
    
    def check_line_movement(self, game: Game, threshold: float = 2.0):
        """Check for significant line movement."""
        # Get previous odds (would need to track history)
        # For now, check if current odds differ significantly from opening
        
        if game.home_moneyline:
            # Simplified: check if odds moved significantly
            # In real implementation, would compare to stored opening odds
            pass
    
    def check_value_bet_alerts(self, min_ev: float = 0.1):
        """Alert on new high-value bets."""
        value_bets = self.session.query(ValueBet).filter_by(
            status="available"
        ).order_by(ValueBet.value_score.desc()).limit(5).all()
        
        for vb in value_bets:
            if vb.expected_value >= min_ev:
                game = vb.game
                title = f"🔥 High Value Bet Found!"
                message = f"{game.sport}: {vb.selection} - {vb.edge_percentage:.1f}% edge, {vb.odds:.0f} odds"
                self.notification_system.create_notification(
                    "value_bet",
                    title,
                    message,
                    "high",
                    related_game=game
                )
    
    def check_best_odds_alerts(self, game: Game, bet_type: str, selection: str):
        """Alert when best odds are available."""
        best = self.line_shopper.find_best_odds(game, bet_type, selection)
        
        if best and best.get("edge_vs_average", 0) > 5:
            title = f"💰 Best Odds Available!"
            message = f"{best['bookmaker']} has best odds: {best['odds']:.0f} (+{best['edge_vs_average']:.0f} vs avg)"
            self.notification_system.create_notification(
                "best_odds",
                title,
                message,
                "normal",
                related_game=game
            )
    
    def check_game_starting_alerts(self, minutes_before: int = 30):
        """Alert when games are about to start."""
        now = datetime.utcnow()
        threshold = now + timedelta(minutes=minutes_before)
        
        games = self.session.query(Game).filter(
            Game.status == "scheduled",
            Game.game_date <= threshold,
            Game.game_date > now
        ).all()
        
        for game in games:
            self.notification_system.notify_game_starting(game)
    
    def _get_current_odds(self, game: Game, bet_type: str, selection: str) -> Optional[float]:
        """Get current odds for a bet."""
        if bet_type == "moneyline":
            if selection == game.home_team or selection == game.fighter1:
                return game.home_moneyline
            elif selection == game.away_team or selection == game.fighter2:
                return game.away_moneyline
        elif bet_type == "spread":
            if "home" in selection.lower() or game.home_team in selection:
                return game.spread_home_odds
            else:
                return game.spread_away_odds
        elif bet_type == "total":
            if "over" in selection.lower():
                return game.over_odds
            else:
                return game.under_odds
        return None
    
    def run_all_checks(self):
        """Run all alert checks."""
        # Check value bets
        self.check_value_bet_alerts()
        
        # Check games starting soon
        self.check_game_starting_alerts()
        
        logger.info("Smart alerts check completed")
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

