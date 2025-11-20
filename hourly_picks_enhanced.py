"""Enhanced hourly picks generator with duplicate prevention and better filtering."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Game, SessionLocal
from value_bet_finder import ValueBetFinder
from ai_picks import AIPicks
from sms_service import SMSService
from data_intake import DataIntake
from sent_pick import SentPickTracker
from line_shopper import LineShopper
from diverse_parlay_generator import DiverseParlayGenerator
import logging
import time

logger = logging.getLogger(__name__)


class EnhancedHourlyPicksGenerator:
    """Enhanced hourly picks generator with duplicate prevention and smart filtering."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.value_bet_finder = ValueBetFinder()
        self.ai_picks = AIPicks()
        self.sms_service = SMSService()
        self.data_intake = DataIntake()
        self.pick_tracker = SentPickTracker()
        self.line_shopper = LineShopper()
        self.parlay_generator = DiverseParlayGenerator()
    
    def refresh_odds_data(self, sports: Optional[List[str]] = None, retries: int = 3):
        """Refresh odds data from APIs with retry logic."""
        for attempt in range(retries):
            try:
                logger.info(f"Refreshing odds data (attempt {attempt + 1}/{retries})...")
                if sports is None:
                    sports = ["NBA", "NFL", "MLB", "NHL", "UFC"]
                
                self.data_intake.fetch_all_data(sports, fetch_player_props=False)
                logger.info("Odds data refreshed successfully")
                return True
            except Exception as e:
                logger.warning(f"Error refreshing odds (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Failed to refresh odds after all retries")
                    return False
        return False
    
    def filter_picks_by_game_time(
        self,
        picks: List[Dict],
        min_hours_ahead: int = 1,
        max_hours_ahead: int = 24
    ) -> List[Dict]:
        """
        Filter picks to only include games happening within a time window.
        
        Args:
            picks: List of pick dictionaries
            min_hours_ahead: Minimum hours until game starts
            max_hours_ahead: Maximum hours until game starts
        
        Returns:
            Filtered list of picks
        """
        now = datetime.utcnow()
        min_time = now + timedelta(hours=min_hours_ahead)
        max_time = now + timedelta(hours=max_hours_ahead)
        
        filtered = []
        for pick in picks:
            game = pick.get("game")
            if not game or not game.game_date:
                continue
            
            # Skip games that are too soon or too far away
            if min_time <= game.game_date <= max_time:
                filtered.append(pick)
        
        return filtered
    
    def enhance_pick_with_line_shopping(self, pick: Dict) -> Dict:
        """Add best odds information from line shopping."""
        game = pick.get("game")
        if not game:
            return pick
        
        try:
            comparisons = self.line_shopper.compare_odds(
                game,
                pick.get("bet_type", ""),
                pick.get("selection", "")
            )
            
            if comparisons:
                best_odds = max(comparisons, key=lambda x: x.get("odds", 0))
                pick["best_odds"] = best_odds.get("odds")
                pick["best_book"] = best_odds.get("bookmaker")
                pick["odds_comparisons"] = comparisons
        except Exception as e:
            logger.debug(f"Error line shopping for pick: {e}")
        
        return pick
    
    def generate_hourly_picks(
        self,
        min_ev: float = 0.05,
        min_confidence: float = 0.6,
        max_picks: int = 10,
        sports: Optional[List[str]] = None,
        refresh_odds: bool = True,
        filter_recent: bool = True,
        recent_hours: int = 6,
        min_hours_ahead: int = 1,
        max_hours_ahead: int = 24,
        enable_line_shopping: bool = False
    ) -> List[Dict]:
        """
        Generate hourly picks with enhanced filtering.
        
        Args:
            min_ev: Minimum expected value threshold
            min_confidence: Minimum confidence threshold
            max_picks: Maximum number of picks to return
            sports: List of sports to analyze
            refresh_odds: Whether to refresh odds before generating picks
            filter_recent: Whether to filter out recently sent picks
            recent_hours: Hours to look back for duplicate prevention
            min_hours_ahead: Minimum hours until game starts
            max_hours_ahead: Maximum hours until game starts
            enable_line_shopping: Whether to add line shopping data
        
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
        
        # Filter by time window
        now = datetime.utcnow()
        min_time = now + timedelta(hours=min_hours_ahead)
        max_time = now + timedelta(hours=max_hours_ahead)
        query = query.filter(Game.game_date >= min_time, Game.game_date <= max_time)
        
        games = query.all()
        logger.info(f"Found {len(games)} scheduled games in time window")
        
        if not games:
            logger.warning("No scheduled games found in time window")
            return []
        
        # Get value bets
        value_bets = self.value_bet_finder.find_value_bets(
            min_ev=min_ev,
            min_confidence=min_confidence,
            sports=sports,
            max_results=max_picks * 3  # Get more to filter
        )
        
        # Get AI picks
        ai_picks = self.ai_picks.generate_ai_picks(games, max_picks=max_picks * 3)
        
        # Combine and deduplicate picks
        all_picks = []
        seen_picks = set()
        
        # Add value bets
        for vb in value_bets:
            # For player props, include player_name and prop_type in deduplication key
            game = vb.get("game")
            bet_type = vb.get("bet_type")
            selection = vb.get("selection")
            player_name = vb.get("player_name") or vb.get("leg_data", {}).get("player_name")
            prop_type = vb.get("prop_type") or vb.get("leg_data", {}).get("prop_type")
            prop_value = vb.get("prop_value") or vb.get("leg_data", {}).get("prop_value")
            
            if bet_type == "prop" and player_name:
                # Player prop - use player, prop_type, selection, and prop_value for dedup
                pick_key = (
                    game.id if game else None,
                    bet_type,
                    player_name,
                    prop_type,
                    selection,
                    prop_value
                )
            else:
                # Regular bet
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
        
        # Add AI picks
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
        
        # Filter by game time
        all_picks = self.filter_picks_by_game_time(
            all_picks,
            min_hours_ahead=min_hours_ahead,
            max_hours_ahead=max_hours_ahead
        )
        
        # Filter out recently sent picks
        if filter_recent:
            before_count = len(all_picks)
            all_picks = self.pick_tracker.filter_recent_picks(all_picks, hours=recent_hours)
            filtered_count = before_count - len(all_picks)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} recently sent picks")
        
        # Enhance with line shopping if enabled
        if enable_line_shopping:
            for pick in all_picks:
                self.enhance_pick_with_line_shopping(pick)
        
        # Add potential earnings to picks
        from advanced_pick_features import AdvancedPickFeatures
        features = AdvancedPickFeatures()
        all_picks = features.add_bet_sizing_to_picks(all_picks)
        
        # Sort by combined score (EV + confidence)
        all_picks.sort(
            key=lambda x: (x["expected_value"] * 0.6) + (x["confidence"] * 0.4),
            reverse=True
        )
        
        # Return top picks
        top_picks = all_picks[:max_picks]
        logger.info(f"Generated {len(top_picks)} hourly picks (after filtering)")
        
        return top_picks
    
    def send_diverse_parlays_hourly(
        self,
        sports: Optional[List[str]] = None,
        min_confidence: float = 0.5,
        max_parlays_per_sport: int = 1,
        refresh_odds: bool = True
    ) -> bool:
        """
        Send diverse parlay picks from each sport hourly.
        
        Ensures variety in:
        - Leg counts (2-15 legs)
        - Bet types (moneylines, spreads, totals, props, alternate spreads, team totals, periods)
        - Line amounts (alternate spreads, alternate totals)
        
        Args:
            sports: List of sports to generate parlays for
            min_confidence: Minimum combined confidence for parlays
            max_parlays_per_sport: Maximum parlays to send per sport
            refresh_odds: Whether to refresh odds before generating
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Refresh odds if requested
            if refresh_odds:
                self.refresh_odds_data(sports)
            
            # Get best parlay from each sport
            parlays_by_sport = self.parlay_generator.get_best_parlay_per_sport(
                max_parlays_per_sport=max_parlays_per_sport,
                min_confidence=min_confidence
            )
            
            if not parlays_by_sport:
                logger.warning("No parlays generated for any sport")
                return False
            
            # Filter by requested sports if specified
            if sports:
                parlays_by_sport = {
                    sport: parlays 
                    for sport, parlays in parlays_by_sport.items()
                    if sport in sports
                }
            
            # Send via SMS
            success = self.sms_service.send_parlays_sms(
                parlays_by_sport,
                max_parlays_per_sport=max_parlays_per_sport
            )
            
            if success:
                logger.info(f"✅ Diverse parlays sent for {len(parlays_by_sport)} sports")
            else:
                logger.warning("⚠️ Failed to send diverse parlays")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error sending diverse parlays: {e}", exc_info=True)
            return False
    
    def send_hourly_picks(
        self,
        min_ev: float = 0.05,
        min_confidence: float = 0.6,
        max_picks: int = 5,
        sports: Optional[List[str]] = None,
        refresh_odds: bool = True,
        filter_recent: bool = True,
        recent_hours: int = 6,
        min_hours_ahead: int = 1,
        max_hours_ahead: int = 24
    ) -> bool:
        """
        Generate and send hourly picks via SMS with enhanced features.
        
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
                refresh_odds=refresh_odds,
                filter_recent=filter_recent,
                recent_hours=recent_hours,
                min_hours_ahead=min_hours_ahead,
                max_hours_ahead=max_hours_ahead
            )
            
            if not picks:
                logger.info("No new picks to send")
                # Only send "no picks" message if we haven't sent one recently
                recent_count = self.pick_tracker.get_recent_sent_count(hours=1)
                if recent_count == 0:
                    return self.sms_service.send_sms(
                        "📊 No new picks found. Check back later!"
                    )
                return True
            
            logger.info(f"Sending {len(picks)} picks via SMS...")
            success = self.sms_service.send_picks_sms(picks, max_picks=max_picks)
            
            # Record sent picks
            if success:
                for pick in picks:
                    game = pick.get("game")
                    if game:
                        try:
                            self.pick_tracker.record_sent_pick(
                                game_id=game.id,
                                bet_type=pick.get("bet_type", ""),
                                selection=pick.get("selection", ""),
                                odds=pick.get("odds"),
                                expected_value=pick.get("expected_value"),
                                confidence=pick.get("confidence")
                            )
                        except Exception as e:
                            logger.warning(f"Error recording sent pick: {e}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error sending hourly picks: {e}", exc_info=True)
            error_msg = f"❌ Error generating picks: {str(e)[:100]}"
            self.sms_service.send_sms(error_msg)
            return False
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

