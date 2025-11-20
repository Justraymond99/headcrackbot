"""Advanced features for the picks system."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, SessionLocal
from sent_pick import SentPick
from bankroll_manager import BankrollManager
from pick_performance_tracker import PickPerformanceTracker
from clv_tracker import CLVTracker
from sms_service import SMSService
from value_bet_finder import ValueBetFinder
import logging
import os

logger = logging.getLogger(__name__)


class AdvancedPickFeatures:
    """Advanced features to enhance the picks system."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.bankroll_manager = BankrollManager()
        self.performance_tracker = PickPerformanceTracker()
        self.clv_tracker = CLVTracker()
        self.sms_service = SMSService()
        self.value_bet_finder = ValueBetFinder()
    
    def add_bet_sizing_to_picks(
        self,
        picks: List[Dict]
    ) -> List[Dict]:
        """
        Add recommended bet sizes and potential earnings to picks.
        
        Args:
            picks: List of pick dictionaries
        
        Returns:
            Picks with bet sizing and potential earnings information added
        """
        bankroll = self.bankroll_manager.get_bankroll()
        
        for pick in picks:
            confidence = pick.get("confidence", 0.6)
            ev = pick.get("expected_value", 0)
            odds = pick.get("odds", 0)
            
            # Calculate unit size based on confidence
            unit_size = self.bankroll_manager.calculate_unit_size(confidence=confidence)
            
            # Optional: Use Kelly Criterion for optimal sizing
            use_kelly = os.getenv("USE_KELLY_SIZING", "false").lower() == "true"
            
            if use_kelly and ev > 0:
                # Convert odds to decimal for Kelly
                if odds > 0:
                    true_prob = (odds / (odds + 100)) * (1 + ev)  # Adjust by EV
                else:
                    true_prob = (abs(odds) / (abs(odds) + 100)) * (1 + ev)
                
                try:
                    kelly_stake = self.bankroll_manager.calculate_kelly_stake(
                        parlay_odds=odds,
                        true_probability=true_prob
                    )
                    pick["recommended_stake"] = kelly_stake
                except:
                    pick["recommended_stake"] = unit_size
            else:
                # Simple unit-based sizing
                pick["recommended_stake"] = unit_size
            
            pick["stake_percentage"] = (pick["recommended_stake"] / bankroll.current_balance * 100) if bankroll.current_balance > 0 else 0
            
            # Calculate potential earnings for different stake amounts
            # Convert American odds to decimal
            if odds > 0:
                decimal_odds = (odds / 100) + 1
            else:
                decimal_odds = (100 / abs(odds)) + 1
            
            # Calculate potential payouts
            pick["potential_earnings"] = {
                "stake_10": round(10 * decimal_odds, 2),
                "stake_25": round(25 * decimal_odds, 2),
                "stake_50": round(50 * decimal_odds, 2),
                "stake_100": round(100 * decimal_odds, 2),
                "recommended": round(pick["recommended_stake"] * decimal_odds, 2)
            }
            
            # Calculate profit (payout - stake)
            pick["potential_profit"] = {
                "stake_10": round((10 * decimal_odds) - 10, 2),
                "stake_25": round((25 * decimal_odds) - 25, 2),
                "stake_50": round((50 * decimal_odds) - 50, 2),
                "stake_100": round((100 * decimal_odds) - 100, 2),
                "recommended": round((pick["recommended_stake"] * decimal_odds) - pick["recommended_stake"], 2)
            }
        
        return picks
    
    def validate_picks_still_have_value(
        self,
        picks: List[Dict],
        min_ev_drop: float = 0.02
    ) -> List[Dict]:
        """
        Validate that picks still have value before sending.
        Removes picks where EV has dropped significantly.
        
        Args:
            picks: List of pick dictionaries
            min_ev_drop: Minimum EV drop to filter out pick
        
        Returns:
            Filtered list of picks that still have value
        """
        validated_picks = []
        
        for pick in picks:
            game = pick.get("game")
            if not game:
                continue
            
            original_ev = pick.get("expected_value", 0)
            
            # Re-analyze the pick to get current EV
            try:
                # Get current legs for this game
                legs = self.value_bet_finder.research_engine.analyze_game(game)
                
                # Find matching leg
                matching_leg = None
                for leg in legs:
                    if (leg.get("bet_type") == pick.get("bet_type") and
                        leg.get("selection") == pick.get("selection")):
                        matching_leg = leg
                        break
                
                if matching_leg:
                    current_ev = matching_leg.get("expected_value", 0)
                    ev_change = original_ev - current_ev
                    
                    # If EV dropped significantly, skip this pick
                    if ev_change > min_ev_drop:
                        logger.debug(f"Skipping pick due to EV drop: {ev_change:.3f}")
                        continue
                    
                    # Update with current values
                    pick["current_ev"] = current_ev
                    pick["original_ev"] = original_ev
                else:
                    # Couldn't re-analyze, keep original
                    pass
            
            except Exception as e:
                logger.debug(f"Error validating pick: {e}, keeping original")
            
            validated_picks.append(pick)
        
        return validated_picks
    
    def send_game_start_reminders(
        self,
        hours_before: int = 1
    ) -> bool:
        """
        Send reminders when games for sent picks are starting soon.
        
        Args:
            hours_before: Hours before game start to send reminder
        """
        try:
            now = datetime.utcnow()
            reminder_window_start = now + timedelta(hours=hours_before - 0.5)
            reminder_window_end = now + timedelta(hours=hours_before + 0.5)
            
            # Get sent picks with games starting in the window
            sent_picks = self.session.query(SentPick).filter(
                SentPick.sent_at >= now - timedelta(hours=24)  # Only recent picks
            ).all()
            
            games_to_remind = {}
            
            for sent_pick in sent_picks:
                game = self.session.query(Game).filter_by(id=sent_pick.game_id).first()
                if not game or game.status != "scheduled":
                    continue
                
                if reminder_window_start <= game.game_date <= reminder_window_end:
                    if game.id not in games_to_remind:
                        games_to_remind[game.id] = {
                            "game": game,
                            "picks": []
                        }
                    games_to_remind[game.id]["picks"].append(sent_pick)
            
            if not games_to_remind:
                return True  # No reminders needed
            
            # Format reminder message
            message_parts = [f"⏰ GAME STARTING IN {hours_before} HOUR(S) ⏰\n"]
            
            for game_data in list(games_to_remind.values())[:5]:  # Limit to 5 games
                game = game_data["game"]
                picks = game_data["picks"]
                
                if game.sport in ["UFC", "BOXING"]:
                    game_info = f"{game.fighter1} vs {game.fighter2}"
                else:
                    game_info = f"{game.away_team} @ {game.home_team}"
                
                game_time = game.game_date.strftime("%I:%M %p")
                
                message_parts.append(f"{game.sport}: {game_info}")
                message_parts.append(f"Start: {game_time}")
                message_parts.append(f"Your picks: {len(picks)}")
                for pick in picks[:3]:  # Show up to 3 picks
                    message_parts.append(f"  - {pick.selection} ({pick.bet_type})")
                message_parts.append("")
            
            message = "\n".join(message_parts)
            return self.sms_service.send_sms(message)
        
        except Exception as e:
            logger.error(f"Error sending game reminders: {e}")
            return False
    
    def check_risk_limits_before_sending(
        self,
        picks: List[Dict]
    ) -> List[Dict]:
        """
        Filter picks based on bankroll risk limits.
        Removes picks that would exceed daily/weekly budgets.
        
        Args:
            picks: List of pick dictionaries
        
        Returns:
            Filtered list that fits within risk limits
        """
        bankroll = self.bankroll_manager.get_bankroll()
        status = self.bankroll_manager.get_budget_status()
        
        # Add bet sizing if not present
        picks = self.add_bet_sizing_to_picks(picks)
        
        filtered_picks = []
        total_stake = 0.0
        
        for pick in picks:
            stake = pick.get("recommended_stake", 0)
            
            # Check daily budget
            if bankroll.daily_budget:
                daily_remaining = status.get("daily_remaining", 0)
                if daily_remaining and (total_stake + stake) > daily_remaining:
                    logger.debug(f"Skipping pick due to daily budget limit")
                    continue
            
            # Check weekly budget
            if bankroll.weekly_budget:
                weekly_remaining = status.get("weekly_remaining", 0)
                if weekly_remaining and (total_stake + stake) > weekly_remaining:
                    logger.debug(f"Skipping pick due to weekly budget limit")
                    continue
            
            # Check max bet size
            if bankroll.max_bet_size and stake > bankroll.max_bet_size:
                stake = bankroll.max_bet_size
                pick["recommended_stake"] = stake
            
            total_stake += stake
            filtered_picks.append(pick)
        
        return filtered_picks
    
    def track_closing_line_value(
        self,
        game_id: int
    ):
        """
        Track Closing Line Value for sent picks when game starts.
        
        Args:
            game_id: Game ID to track CLV for
        """
        try:
            game = self.session.query(Game).filter_by(id=game_id).first()
            if not game:
                return
            
            # Get sent picks for this game
            sent_picks = self.session.query(SentPick).filter_by(game_id=game_id).all()
            
            for sent_pick in sent_picks:
                # Get matching leg if it exists
                from models import Leg
                legs = self.session.query(Leg).filter_by(
                    game_id=game_id,
                    bet_type=sent_pick.bet_type
                ).all()
                
                matching_leg = None
                for leg in legs:
                    if leg.selection == sent_pick.selection:
                        matching_leg = leg
                        break
                
                if matching_leg:
                    # Record opening odds (when pick was sent)
                    self.clv_tracker.record_opening_odds(matching_leg, sent_pick.odds)
                    
                    # Try to get closing odds (would need to be fetched at game start)
                    # For now, we'll just record opening odds
                    # In production, you'd fetch closing odds from API at game start
                    pass
        
        except Exception as e:
            logger.error(f"Error tracking CLV: {e}")
    
    def get_pick_explanation(
        self,
        pick: Dict
    ) -> str:
        """
        Generate a detailed explanation for why a pick was selected.
        
        Args:
            pick: Pick dictionary
        
        Returns:
            Explanation string
        """
        game = pick.get("game")
        if not game:
            return "No explanation available"
        
        reasons = []
        
        # Player prop specific explanation
        bet_type = pick.get("bet_type", "")
        if bet_type == "prop" and pick.get("player_name"):
            player_name = pick.get("player_name")
            prop_type = pick.get("prop_type", "")
            reasons.append(f"{player_name} {prop_type} prop")
        
        # EV explanation
        ev = pick.get("expected_value", 0)
        if ev > 0.05:
            reasons.append(f"Strong positive EV: +{ev*100:.1f}%")
        elif ev > 0:
            reasons.append(f"Positive EV: +{ev*100:.1f}%")
        
        # Confidence explanation
        confidence = pick.get("confidence", 0)
        if confidence >= 0.75:
            reasons.append("High confidence model prediction")
        elif confidence >= 0.65:
            reasons.append("Moderate-high confidence")
        
        # Source explanation
        source = pick.get("source", "")
        if source == "value_bet":
            reasons.append("Identified as value bet by scanner")
        elif source == "ai_pick":
            reasons.append("AI-optimized selection")
        
        # Historical performance (if available)
        stats = self.performance_tracker.get_bet_type_performance(days=30)
        if bet_type in stats and stats[bet_type]["resolved"] > 5:
            win_rate = stats[bet_type]["win_rate"]
            if win_rate > 0.6:
                prop_desc = "prop" if bet_type == "prop" else bet_type
                reasons.append(f"Strong {prop_desc} performance ({win_rate*100:.1f}% win rate)")
        
        if not reasons:
            return "Pick based on current odds and model analysis"
        
        return " | ".join(reasons)
    
    def send_detailed_pick_with_explanations(
        self,
        picks: List[Dict],
        include_sizing: bool = True,
        include_explanations: bool = True
    ) -> bool:
        """
        Send picks with detailed information including bet sizing and explanations.
        
        Args:
            picks: List of pick dictionaries
            include_sizing: Whether to include bet sizing recommendations
            include_explanations: Whether to include pick explanations
        """
        if not picks:
            return self.sms_service.send_sms("No picks available")
        
        message_parts = ["🏀 DETAILED PICKS 🏀\n"]
        
        for i, pick in enumerate(picks[:5], 1):  # Limit to 5 for SMS
            game = pick.get("game")
            bet_type = pick.get("bet_type", "unknown")
            selection = pick.get("selection", "N/A")
            odds = pick.get("odds", 0)
            confidence = pick.get("confidence", 0)
            ev = pick.get("expected_value", 0)
            
            # Player prop fields
            player_name = pick.get("player_name")
            prop_type = pick.get("prop_type") or pick.get("market_key", "")
            prop_value = pick.get("prop_value")
            
            # Prop type names mapping
            prop_type_names = {
                "player_points": "Pts",
                "player_rebounds": "Reb",
                "player_assists": "Ast",
                "player_pass_yds": "Pass Yds",
                "player_rush_yds": "Rush Yds",
                "player_reception_yds": "Rec Yds",
                "player_threes": "3PM",
                "player_blocks": "Blk",
                "player_steals": "Stl",
                "batter_home_runs": "HR",
                "batter_hits": "Hits",
                "pitcher_strikeouts": "K",
                "player_goals": "Goals",
                "player_anytime_td": "Anytime TD"
            }
            
            if game:
                if game.sport in ["UFC", "BOXING"]:
                    game_info = f"{game.fighter1} vs {game.fighter2}"
                else:
                    game_info = f"{game.away_team} @ {game.home_team}"
                sport = game.sport
                game_time = game.game_date.strftime("%I:%M %p") if game.game_date else ""
            else:
                game_info = "Unknown"
                sport = "N/A"
                game_time = ""
            
            odds_str = f"+{int(odds)}" if odds > 0 else str(int(odds))
            conf_pct = int(confidence * 100)
            ev_pct = f"+{ev*100:.1f}%" if ev > 0 else f"{ev*100:.1f}%"
            
            # Get potential earnings
            potential_earnings = pick.get("potential_earnings", {})
            potential_profit = pick.get("potential_profit", {})
            recommended_stake = pick.get("recommended_stake")
            
            # Format based on bet type
            if bet_type == "prop" and player_name:
                readable_prop = prop_type_names.get(prop_type, prop_type.replace("player_", "").replace("_", " ").title())
                if prop_value:
                    message_parts.append(f"\n{i}. {sport}: {player_name} {readable_prop}")
                    message_parts.append(f"   {selection} {prop_value:.1f}")
                else:
                    message_parts.append(f"\n{i}. {sport}: {player_name} {readable_prop}")
                    message_parts.append(f"   {selection}")
            else:
                message_parts.append(f"\n{i}. {sport}: {selection}")
            
            message_parts.append(f"   {game_info}")
            if game_time:
                message_parts.append(f"   Starts: {game_time}")
            message_parts.append(f"   {bet_type.upper()} | {odds_str} | {conf_pct}% | EV: {ev_pct}")
            
            # Add potential earnings
            if potential_earnings and recommended_stake:
                rec_payout = potential_earnings.get("recommended", 0)
                rec_profit = potential_profit.get("recommended", 0)
                message_parts.append(f"   💰 ${recommended_stake:.0f} → ${rec_payout:.2f} (+${rec_profit:.2f})")
            elif potential_earnings:
                payout_25 = potential_earnings.get("stake_25", 0)
                profit_25 = potential_profit.get("stake_25", 0)
                message_parts.append(f"   💰 $25 → ${payout_25:.2f} (+${profit_25:.2f})")
            
            if include_sizing and pick.get("recommended_stake"):
                stake = pick["recommended_stake"]
                stake_pct = pick.get("stake_percentage", 0)
                message_parts.append(f"   💰 Recommended: ${stake:.2f} ({stake_pct:.1f}% of bankroll)")
            
            if include_explanations:
                explanation = self.get_pick_explanation(pick)
                # Shorten for SMS
                explanation = explanation[:80] + "..." if len(explanation) > 80 else explanation
                message_parts.append(f"   💡 {explanation}")
        
        message = "\n".join(message_parts)
        return self.sms_service.send_sms(message)
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

