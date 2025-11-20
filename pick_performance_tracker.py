"""Track performance of sent picks."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, Leg, SessionLocal
from sent_pick import SentPick
from result_tracker import ResultTracker
import logging

logger = logging.getLogger(__name__)


class PickPerformanceTracker:
    """Track and analyze performance of sent picks."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.result_tracker = ResultTracker()
    
    def update_sent_pick_results(self, game_id: int):
        """Update results for all sent picks for a finished game."""
        # Get all sent picks for this game
        sent_picks = self.session.query(SentPick).filter_by(game_id=game_id).all()
        
        if not sent_picks:
            return
        
        # Get game result
        game = self.session.query(Game).filter_by(id=game_id).first()
        if not game or game.status != "finished":
            return
        
        # Get legs to determine outcomes
        legs = self.session.query(Leg).filter_by(game_id=game_id).all()
        
        # Match sent picks to legs and update
        for sent_pick in sent_picks:
            # Find matching leg
            matching_leg = None
            for leg in legs:
                if (leg.bet_type == sent_pick.bet_type and 
                    leg.selection == sent_pick.selection):
                    matching_leg = leg
                    break
            
            if matching_leg and matching_leg.result != "pending":
                # Update sent pick with result (we'll add result column)
                # For now, we'll track via legs
                pass
        
        self.session.commit()
    
    def get_pick_performance_stats(
        self,
        days: int = 7
    ) -> Dict:
        """
        Get performance statistics for sent picks.
        
        Args:
            days: Number of days to look back
        
        Returns:
            Dictionary with performance stats
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all sent picks in time period
        sent_picks = self.session.query(SentPick).filter(
            SentPick.sent_at >= cutoff_date
        ).all()
        
        if not sent_picks:
            return {
                "total_picks": 0,
                "resolved_picks": 0,
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "win_rate": 0.0,
                "avg_confidence": 0.0,
                "avg_ev": 0.0
            }
        
        # Match with leg results
        wins = 0
        losses = 0
        pushes = 0
        resolved_count = 0
        total_confidence = 0.0
        total_ev = 0.0
        
        for sent_pick in sent_picks:
            game = self.session.query(Game).filter_by(id=sent_pick.game_id).first()
            if not game:
                continue
            
            # Find matching leg
            legs = self.session.query(Leg).filter_by(
                game_id=sent_pick.game_id,
                bet_type=sent_pick.bet_type
            ).all()
            
            matching_leg = None
            for leg in legs:
                if leg.selection == sent_pick.selection:
                    matching_leg = leg
                    break
            
            if matching_leg and matching_leg.result != "pending":
                resolved_count += 1
                if matching_leg.result == "win":
                    wins += 1
                elif matching_leg.result == "loss":
                    losses += 1
                elif matching_leg.result == "push":
                    pushes += 1
            
            if sent_pick.confidence:
                total_confidence += sent_pick.confidence
            if sent_pick.expected_value:
                total_ev += sent_pick.expected_value
        
        win_rate = wins / resolved_count if resolved_count > 0 else 0.0
        avg_confidence = total_confidence / len(sent_picks) if sent_picks else 0.0
        avg_ev = total_ev / len(sent_picks) if sent_picks else 0.0
        
        return {
            "total_picks": len(sent_picks),
            "resolved_picks": resolved_count,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "win_rate": win_rate,
            "avg_confidence": avg_confidence,
            "avg_ev": avg_ev,
            "days": days
        }
    
    def get_sport_performance(self, days: int = 7) -> Dict[str, Dict]:
        """Get performance stats broken down by sport."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        sent_picks = self.session.query(SentPick).filter(
            SentPick.sent_at >= cutoff_date
        ).all()
        
        sport_stats = {}
        
        for sent_pick in sent_picks:
            game = self.session.query(Game).filter_by(id=sent_pick.game_id).first()
            if not game:
                continue
            
            sport = game.sport
            if sport not in sport_stats:
                sport_stats[sport] = {
                    "total": 0,
                    "wins": 0,
                    "losses": 0,
                    "pushes": 0,
                    "resolved": 0
                }
            
            sport_stats[sport]["total"] += 1
            
            # Find matching leg
            legs = self.session.query(Leg).filter_by(
                game_id=sent_pick.game_id,
                bet_type=sent_pick.bet_type
            ).all()
            
            matching_leg = None
            for leg in legs:
                if leg.selection == sent_pick.selection:
                    matching_leg = leg
                    break
            
            if matching_leg and matching_leg.result != "pending":
                sport_stats[sport]["resolved"] += 1
                if matching_leg.result == "win":
                    sport_stats[sport]["wins"] += 1
                elif matching_leg.result == "loss":
                    sport_stats[sport]["losses"] += 1
                elif matching_leg.result == "push":
                    sport_stats[sport]["pushes"] += 1
        
        # Calculate win rates
        for sport in sport_stats:
            stats = sport_stats[sport]
            stats["win_rate"] = (
                stats["wins"] / stats["resolved"] 
                if stats["resolved"] > 0 else 0.0
            )
        
        return sport_stats
    
    def get_bet_type_performance(self, days: int = 7) -> Dict[str, Dict]:
        """Get performance stats broken down by bet type."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        sent_picks = self.session.query(SentPick).filter(
            SentPick.sent_at >= cutoff_date
        ).all()
        
        bet_type_stats = {}
        
        for sent_pick in sent_picks:
            bet_type = sent_pick.bet_type
            if bet_type not in bet_type_stats:
                bet_type_stats[bet_type] = {
                    "total": 0,
                    "wins": 0,
                    "losses": 0,
                    "pushes": 0,
                    "resolved": 0
                }
            
            bet_type_stats[bet_type]["total"] += 1
            
            # Find matching leg
            legs = self.session.query(Leg).filter_by(
                game_id=sent_pick.game_id,
                bet_type=sent_pick.bet_type
            ).all()
            
            matching_leg = None
            for leg in legs:
                if leg.selection == sent_pick.selection:
                    matching_leg = leg
                    break
            
            if matching_leg and matching_leg.result != "pending":
                bet_type_stats[bet_type]["resolved"] += 1
                if matching_leg.result == "win":
                    bet_type_stats[bet_type]["wins"] += 1
                elif matching_leg.result == "loss":
                    bet_type_stats[bet_type]["losses"] += 1
                elif matching_leg.result == "push":
                    bet_type_stats[bet_type]["pushes"] += 1
        
        # Calculate win rates
        for bet_type in bet_type_stats:
            stats = bet_type_stats[bet_type]
            stats["win_rate"] = (
                stats["wins"] / stats["resolved"] 
                if stats["resolved"] > 0 else 0.0
            )
        
        return bet_type_stats
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

