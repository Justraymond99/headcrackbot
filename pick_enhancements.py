"""Additional enhancements for hourly picks system."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, SessionLocal
from sent_pick import SentPick, SentPickTracker
from pick_performance_tracker import PickPerformanceTracker
from ai_picks import AIPicks
from telegram_service import TelegramService
from line_shopper import LineShopper
import logging

logger = logging.getLogger(__name__)

# Try to import WebSocket broadcaster (optional)
try:
    from websocket_server import broadcast_performance_update
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.debug("WebSocket server not available (optional feature)")


class PickEnhancements:
    """Additional features for the picks system."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.telegram_service = TelegramService()
        self.pick_tracker = SentPickTracker()
        self.performance_tracker = PickPerformanceTracker()
        self.ai_picks = AIPicks()
        self.line_shopper = LineShopper()
    
    def send_parlay_suggestions(
        self,
        max_parlays: int = 3,
        min_legs: int = 2,
        max_legs: int = 15
    ) -> bool:
        """
        Send top parlay suggestions via Telegram.
        
        Args:
            max_parlays: Maximum number of parlays to send
            min_legs: Minimum legs per parlay
            max_legs: Maximum legs per parlay
        """
        try:
            # Get scheduled games
            tomorrow = datetime.utcnow() + timedelta(days=1)
            games = self.session.query(Game).filter(
                Game.status == "scheduled",
                Game.game_date <= tomorrow
            ).all()
            
            if not games:
                logger.info("No games found for parlay suggestions")
                return False
            
            # Generate AI parlays
            parlays = self.ai_picks.generate_ai_parlays(games, max_parlays=max_parlays)
            
            if not parlays:
                logger.info("No parlay suggestions generated")
                return False
            
            # Format and send
            message_parts = ["🎯 TOP PARLAY PICKS 🎯\n"]
            
            for i, parlay in enumerate(parlays[:max_parlays], 1):
                if parlay["num_legs"] < min_legs or parlay["num_legs"] > max_legs:
                    continue
                
                message_parts.append(f"\n{i}. {parlay['num_legs']}-Leg Parlay")
                message_parts.append(f"   Odds: {parlay['combined_odds']:.0f}")
                message_parts.append(f"   Confidence: {parlay['combined_confidence']*100:.0f}%")
                
                # Add potential payouts
                if parlay.get('potential_payouts'):
                    payouts = parlay['potential_payouts']
                    message_parts.append("   💰 Potential Payouts:")
                    message_parts.append(f"      $10 → ${payouts.get('stake_10', 0):.2f}")
                    message_parts.append(f"      $25 → ${payouts.get('stake_25', 0):.2f}")
                    message_parts.append(f"      $50 → ${payouts.get('stake_50', 0):.2f}")
                    message_parts.append(f"      $100 → ${payouts.get('stake_100', 0):.2f}")
                elif parlay.get('decimal_odds'):
                    decimal = parlay['decimal_odds']
                    message_parts.append("   💰 Potential Payouts:")
                    message_parts.append(f"      $10 → ${10 * decimal:.2f}")
                    message_parts.append(f"      $25 → ${25 * decimal:.2f}")
                    message_parts.append(f"      $50 → ${50 * decimal:.2f}")
                    message_parts.append(f"      $100 → ${100 * decimal:.2f}")
                
                message_parts.append("   Legs:")
                
                for j, pick in enumerate(parlay["picks"], 1):
                    game = pick.get("game")
                    leg = pick.get("leg", {})
                    
                    if game:
                        if game.sport in ["UFC", "BOXING"]:
                            game_info = f"{game.fighter1} vs {game.fighter2}"
                        else:
                            game_info = f"{game.away_team} @ {game.home_team}"
                    else:
                        game_info = "Unknown"
                    
                    selection = leg.get("selection", "N/A")
                    bet_type = leg.get("bet_type", "unknown")
                    odds = leg.get("odds", 0)
                    odds_str = f"+{int(odds)}" if odds > 0 else str(int(odds))
                    
                    message_parts.append(
                        f"      {j}. {game.sport}: {selection} ({bet_type}) {odds_str}"
                    )
                    message_parts.append(f"         {game_info}")
            
            message = "\n".join(message_parts)
            return self.telegram_service.send_message(message)
        
        except Exception as e:
            logger.error(f"Error sending parlay suggestions: {e}")
            return False
    
    def send_performance_summary(
        self,
        days: int = 7,
        include_sport_breakdown: bool = True
    ) -> bool:
        """
        Send performance summary of sent picks.
        
        Args:
            days: Number of days to summarize
            include_sport_breakdown: Whether to include sport breakdown
        """
        try:
            stats = self.performance_tracker.get_pick_performance_stats(days=days)
            
            if stats["total_picks"] == 0:
                message = f"📊 No picks sent in the last {days} days"
                return self.telegram_service.send_message(message)
            
            message_parts = [f"📊 PERFORMANCE SUMMARY ({days} days)\n"]
            message_parts.append(f"Total Picks: {stats['total_picks']}")
            message_parts.append(f"Resolved: {stats['resolved_picks']}")
            
            if stats["resolved_picks"] > 0:
                message_parts.append(f"Wins: {stats['wins']} | Losses: {stats['losses']}")
                if stats["pushes"] > 0:
                    message_parts.append(f"Pushes: {stats['pushes']}")
                message_parts.append(f"Win Rate: {stats['win_rate']*100:.1f}%")
            
            message_parts.append(f"Avg Confidence: {stats['avg_confidence']*100:.1f}%")
            message_parts.append(f"Avg EV: {stats['avg_ev']*100:.1f}%")
            
            if include_sport_breakdown and stats["resolved_picks"] > 0:
                sport_stats = self.performance_tracker.get_sport_performance(days=days)
                if sport_stats:
                    message_parts.append("\nBy Sport:")
                    for sport, sport_data in sport_stats.items():
                        if sport_data["resolved"] > 0:
                            message_parts.append(
                                f"  {sport}: {sport_data['wins']}-{sport_data['losses']} "
                                f"({sport_data['win_rate']*100:.1f}%)"
                            )
            
            message = "\n".join(message_parts)
            success = self.telegram_service.send_message(message)
            
            # Broadcast via WebSocket if available
            if WEBSOCKET_AVAILABLE:
                try:
                    broadcast_performance_update(stats)
                except Exception as e:
                    logger.debug(f"WebSocket broadcast failed: {e}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error sending performance summary: {e}")
            return False
    
    def check_line_movements_on_sent_picks(
        self,
        hours: int = 6
    ) -> List[Dict]:
        """
        Check for favorable line movements on recently sent picks.
        
        Args:
            hours: Hours to look back for sent picks
        
        Returns:
            List of picks with favorable line movements
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        sent_picks = self.session.query(SentPick).filter(
            SentPick.sent_at >= cutoff_time
        ).all()
        
        favorable_movements = []
        
        for sent_pick in sent_picks:
            game = self.session.query(Game).filter_by(id=sent_pick.game_id).first()
            if not game or game.status != "scheduled":
                continue
            
            # Get current odds
            try:
                comparisons = self.line_shopper.compare_odds(
                    game,
                    sent_pick.bet_type,
                    sent_pick.selection
                )
                
                if comparisons:
                    best_odds = max(comparisons, key=lambda x: x.get("odds", 0))
                    current_best = best_odds.get("odds", 0)
                    
                    # Check if odds improved (higher for positive, lower absolute for negative)
                    if sent_pick.odds:
                        if sent_pick.odds > 0 and current_best > sent_pick.odds:
                            # Positive odds improved
                            improvement = current_best - sent_pick.odds
                            favorable_movements.append({
                                "pick": sent_pick,
                                "game": game,
                                "old_odds": sent_pick.odds,
                                "new_odds": current_best,
                                "improvement": improvement,
                                "best_book": best_odds.get("bookmaker")
                            })
                        elif sent_pick.odds < 0 and current_best < sent_pick.odds:
                            # Negative odds improved (less negative = better)
                            improvement = abs(sent_pick.odds) - abs(current_best)
                            favorable_movements.append({
                                "pick": sent_pick,
                                "game": game,
                                "old_odds": sent_pick.odds,
                                "new_odds": current_best,
                                "improvement": improvement,
                                "best_book": best_odds.get("bookmaker")
                            })
            except Exception as e:
                logger.debug(f"Error checking line movement: {e}")
                continue
        
        return favorable_movements
    
    def send_line_movement_alerts(
        self,
        min_improvement: float = 10.0,
        hours: int = 6
    ) -> bool:
        """
        Send alerts for favorable line movements on sent picks.
        
        Args:
            min_improvement: Minimum odds improvement to alert
            hours: Hours to look back for sent picks
        """
        try:
            movements = self.check_line_movements_on_sent_picks(hours=hours)
            
            # Filter by minimum improvement
            significant_movements = [
                m for m in movements 
                if m["improvement"] >= min_improvement
            ]
            
            if not significant_movements:
                return True  # No movements to report
            
            message_parts = ["📈 FAVORABLE LINE MOVEMENTS 📈\n"]
            
            for movement in significant_movements[:5]:  # Limit to 5
                pick = movement["pick"]
                game = movement["game"]
                
                if game.sport in ["UFC", "BOXING"]:
                    game_info = f"{game.fighter1} vs {game.fighter2}"
                else:
                    game_info = f"{game.away_team} @ {game.home_team}"
                
                old_odds_str = f"+{int(movement['old_odds'])}" if movement['old_odds'] > 0 else str(int(movement['old_odds']))
                new_odds_str = f"+{int(movement['new_odds'])}" if movement['new_odds'] > 0 else str(int(movement['new_odds']))
                
                message_parts.append(f"{game.sport}: {pick.selection}")
                message_parts.append(f"  {game_info}")
                message_parts.append(f"  {old_odds_str} → {new_odds_str} ({movement['best_book']})")
                message_parts.append("")
            
            message = "\n".join(message_parts)
            success = self.telegram_service.send_message(message)
            
            # Broadcast via WebSocket if available
            try:
                from websocket_server import broadcast_line_movement
                for movement in significant_movements:
                    broadcast_line_movement(movement)
            except Exception as e:
                logger.debug(f"WebSocket broadcast failed: {e}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error sending line movement alerts: {e}")
            return False
    
    def send_pick_results_followup(
        self,
        hours: int = 24
    ) -> bool:
        """
        Send results of picks from finished games.
        
        Args:
            hours: Hours to look back for sent picks
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            sent_picks = self.session.query(SentPick).filter(
                SentPick.sent_at >= cutoff_time
            ).all()
            
            # Get finished games
            finished_games = self.session.query(Game).filter(
                Game.status == "finished"
            ).all()
            
            results_to_send = []
            
            for sent_pick in sent_picks:
                game = self.session.query(Game).filter_by(id=sent_pick.game_id).first()
                if not game or game.status != "finished":
                    continue
                
                # Find matching leg
                from models import Leg
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
                    results_to_send.append({
                        "pick": sent_pick,
                        "game": game,
                        "leg": matching_leg
                    })
            
            if not results_to_send:
                return True  # No results to send
            
            # Format message
            message_parts = ["🏁 PICK RESULTS 🏁\n"]
            
            wins = 0
            losses = 0
            
            for result in results_to_send[:10]:  # Limit to 10
                pick = result["pick"]
                game = result["game"]
                leg = result["leg"]
                
                if game.sport in ["UFC", "BOXING"]:
                    game_info = f"{game.fighter1} vs {game.fighter2}"
                else:
                    game_info = f"{game.away_team} @ {game.home_team}"
                
                result_emoji = "✅" if leg.result == "win" else "❌" if leg.result == "loss" else "➖"
                
                if leg.result == "win":
                    wins += 1
                elif leg.result == "loss":
                    losses += 1
                
                message_parts.append(f"{result_emoji} {game.sport}: {pick.selection}")
                message_parts.append(f"   {game_info} - {leg.result.upper()}")
                message_parts.append("")
            
            if len(results_to_send) > 10:
                message_parts.append(f"... and {len(results_to_send) - 10} more")
            
            message_parts.append(f"\nRecord: {wins}W-{losses}L")
            
            message = "\n".join(message_parts)
            return self.telegram_service.send_message(message)
        
        except Exception as e:
            logger.error(f"Error sending pick results: {e}")
            return False
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

