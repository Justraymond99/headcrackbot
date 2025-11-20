"""Hourly picks generator based on betting odds."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, SessionLocal
from value_bet_finder import ValueBetFinder
from ai_picks import AIPicks
from sms_service import SMSService
from data_intake import DataIntake
import logging

logger = logging.getLogger(__name__)


class HourlyPicksGenerator:
    """Generate and send hourly picks based on betting odds."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.value_bet_finder = ValueBetFinder()
        self.ai_picks = AIPicks()
        self.sms_service = SMSService()
        self.data_intake = DataIntake()
    
    def refresh_odds_data(self, sports: Optional[List[str]] = None):
        """Refresh odds data from APIs."""
        try:
            logger.info("Refreshing odds data...")
            if sports is None:
                sports = ["NBA", "NFL", "MLB", "NHL", "UFC"]
            
            # Use fetch_all_data which handles the sport mapping internally
            self.data_intake.fetch_all_data(sports, fetch_player_props=False)
            logger.info("Odds data refreshed")
        except Exception as e:
            logger.error(f"Error refreshing odds: {e}")
    
    def generate_hourly_picks(
        self,
        min_ev: float = 0.05,
        min_confidence: float = 0.6,
        max_picks: int = 10,
        sports: Optional[List[str]] = None,
        refresh_odds: bool = True
    ) -> List[Dict]:
        """
        Generate hourly picks based on current betting odds.
        
        Args:
            min_ev: Minimum expected value threshold
            min_confidence: Minimum confidence threshold
            max_picks: Maximum number of picks to return
            sports: List of sports to analyze (None = all)
            refresh_odds: Whether to refresh odds before generating picks
        
        Returns:
            List of pick dictionaries
        """
        # Refresh odds if requested
        if refresh_odds:
            self.refresh_odds_data(sports)
        
        # Get scheduled games
        query = self.session.query(Game).filter(Game.status == "scheduled")
        if sports:
            query = query.filter(Game.sport.in_(sports))
        
        # Only get games in the next 24 hours
        tomorrow = datetime.utcnow() + timedelta(days=1)
        query = query.filter(Game.game_date <= tomorrow)
        
        games = query.all()
        logger.info(f"Found {len(games)} scheduled games for analysis")
        
        if not games:
            logger.warning("No scheduled games found")
            return []
        
        # Get value bets
        value_bets = self.value_bet_finder.find_value_bets(
            min_ev=min_ev,
            min_confidence=min_confidence,
            sports=sports,
            max_results=max_picks * 2  # Get more to filter
        )
        
        # Get AI picks
        ai_picks = self.ai_picks.generate_ai_picks(games, max_picks=max_picks * 2)
        
        # Combine and deduplicate picks
        all_picks = []
        seen_picks = set()
        
        # Add value bets
        for vb in value_bets:
            game = vb.get("game")
            bet_type = vb.get("bet_type")
            selection = vb.get("selection")
            player_name = vb.get("player_name") or vb.get("leg_data", {}).get("player_name")
            prop_type = vb.get("prop_type") or vb.get("leg_data", {}).get("prop_type")
            prop_value = vb.get("prop_value") or vb.get("leg_data", {}).get("prop_value")
            
            # For player props, include player_name and prop_type in deduplication key
            if bet_type == "prop" and player_name:
                pick_key = (
                    game.id if game else None,
                    bet_type,
                    player_name,
                    prop_type,
                    selection,
                    prop_value
                )
            else:
                pick_key = (
                    game.id if game else None,
                    bet_type,
                    selection
                )
            
            if pick_key not in seen_picks and pick_key[0] is not None:
                seen_picks.add(pick_key)
                pick_data = {
                    "game": game,
                    "bet_type": bet_type,
                    "selection": selection,
                    "odds": vb.get("odds"),
                    "expected_value": vb.get("expected_value", 0),
                    "confidence": vb.get("confidence_score", 0),
                    "edge_percentage": vb.get("edge_percentage", 0),
                    "reasoning": vb.get("reasoning", ""),
                    "source": "value_bet"
                }
                # Add player prop fields if present
                if player_name:
                    pick_data["player_name"] = player_name
                if prop_type:
                    pick_data["prop_type"] = prop_type
                    pick_data["market_key"] = prop_type
                if prop_value is not None:
                    pick_data["prop_value"] = prop_value
                
                all_picks.append(pick_data)
        
        # Add AI picks (prioritize those not already included)
        for pick in ai_picks:
            game = pick.get("game")
            leg = pick.get("leg", {})
            bet_type = leg.get("bet_type")
            selection = leg.get("selection")
            player_name = leg.get("player_name")
            prop_type = leg.get("prop_type") or leg.get("market_key")
            prop_value = leg.get("prop_value")
            
            # For player props, include player_name and prop_type in deduplication key
            if bet_type == "prop" and player_name:
                pick_key = (
                    game.id if game else None,
                    bet_type,
                    player_name,
                    prop_type,
                    selection,
                    prop_value
                )
            else:
                pick_key = (
                    game.id if game else None,
                    bet_type,
                    selection
                )
            
            if pick_key not in seen_picks and pick_key[0] is not None:
                seen_picks.add(pick_key)
                pick_data = {
                    "game": game,
                    "bet_type": bet_type,
                    "selection": selection,
                    "odds": leg.get("odds", pick.get("odds")),
                    "expected_value": pick.get("expected_value", 0),
                    "confidence": pick.get("confidence", 0),
                    "edge_percentage": pick.get("expected_value", 0) * 100,
                    "reasoning": pick.get("reasoning", ""),
                    "source": "ai_pick"
                }
                # Add player prop fields if present
                if player_name:
                    pick_data["player_name"] = player_name
                if prop_type:
                    pick_data["prop_type"] = prop_type
                    pick_data["market_key"] = prop_type
                if prop_value is not None:
                    pick_data["prop_value"] = prop_value
                
                all_picks.append(pick_data)
        
        # Sort by combined score (EV + confidence)
        all_picks.sort(
            key=lambda x: (x["expected_value"] * 0.6) + (x["confidence"] * 0.4),
            reverse=True
        )
        
        # Return top picks
        top_picks = all_picks[:max_picks]
        logger.info(f"Generated {len(top_picks)} hourly picks")
        
        return top_picks
    
    def send_hourly_picks(
        self,
        min_ev: float = 0.05,
        min_confidence: float = 0.6,
        max_picks: int = 5,
        sports: Optional[List[str]] = None,
        refresh_odds: bool = True
    ) -> bool:
        """
        Generate and send hourly picks via SMS.
        
        Args:
            min_ev: Minimum expected value threshold
            min_confidence: Minimum confidence threshold
            max_picks: Maximum number of picks to send
            sports: List of sports to analyze
            refresh_odds: Whether to refresh odds before generating picks
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            logger.info("Generating hourly picks...")
            picks = self.generate_hourly_picks(
                min_ev=min_ev,
                min_confidence=min_confidence,
                max_picks=max_picks,
                sports=sports,
                refresh_odds=refresh_odds
            )
            
            if not picks:
                logger.info("No picks to send")
                return self.sms_service.send_sms(
                    "📊 No picks found at this time. Check back later!"
                )
            
            logger.info(f"Sending {len(picks)} picks via SMS...")
            return self.sms_service.send_picks_sms(picks, max_picks=max_picks)
        
        except Exception as e:
            logger.error(f"Error sending hourly picks: {e}")
            error_msg = f"❌ Error generating picks: {str(e)}"
            self.sms_service.send_sms(error_msg)
            return False
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

