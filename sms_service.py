"""SMS/Text messaging service for sending picks."""
import os
from typing import List, Dict, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """Handle SMS/text messaging via Twilio."""
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER", "")
        self.to_number = os.getenv("USER_PHONE_NUMBER", "")
        
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                self.is_configured = True
            except Exception as e:
                logger.error(f"Error initializing Twilio client: {e}")
                self.is_configured = False
        else:
            logger.warning("Twilio credentials not configured. SMS will be disabled.")
            self.is_configured = False
    
    def send_sms(self, message: str, to_number: Optional[str] = None, retries: int = 3) -> bool:
        """
        Send SMS message with retry logic.
        
        Args:
            message: Message text to send
            to_number: Recipient phone number (defaults to USER_PHONE_NUMBER)
            retries: Number of retry attempts
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("SMS not configured. Message would be:")
            logger.info(f"\n{message}")
            return False
        
        recipient = to_number or self.to_number
        if not recipient:
            logger.error("No recipient phone number configured")
            return False
        
        import time
        for attempt in range(retries):
            try:
                message_obj = self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=recipient
                )
                logger.info(f"SMS sent successfully. SID: {message_obj.sid}")
                return True
            except TwilioException as e:
                error_code = getattr(e, 'code', None)
                # Rate limit error (20429) - wait longer
                if error_code == 20429:
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"Rate limit hit. Waiting {wait_time} seconds before retry...")
                    if attempt < retries - 1:
                        time.sleep(wait_time)
                        continue
                
                logger.error(f"Error sending SMS (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return False
            except Exception as e:
                logger.error(f"Unexpected error sending SMS: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return False
        
        return False
    
    def send_parlays_sms(self, parlays_by_sport: Dict[str, List[Dict]], max_parlays_per_sport: int = 1) -> bool:
        """
        Format and send diverse parlays from each sport as SMS.
        
        Args:
            parlays_by_sport: Dictionary mapping sport to list of parlays
            max_parlays_per_sport: Maximum parlays to show per sport
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not parlays_by_sport:
            message = "📊 No parlay picks found at this time. Check back later!"
            return self.send_sms(message)
        
        # Format message
        message_parts = ["🎯 BEST PARLAYS (Each Sport) 🎯\n"]
        
        sport_emoji = {
            "NBA": "🏀",
            "NFL": "🏈",
            "MLB": "⚾",
            "NHL": "🏒",
            "UFC": "🥊",
            "BOXING": "🥊"
        }
        
        for sport, parlays in parlays_by_sport.items():
            if not parlays:
                continue
            
            emoji = sport_emoji.get(sport, "📊")
            message_parts.append(f"\n{emoji} {sport} {emoji}")
            
            # Send best parlays from this sport
            for i, parlay in enumerate(parlays[:max_parlays_per_sport], 1):
                num_legs = parlay.get("num_legs", 0)
                combined_odds = parlay.get("combined_odds", 0)
                combined_confidence = parlay.get("combined_confidence", 0)
                decimal_odds = parlay.get("decimal_odds", 1)
                bet_types = parlay.get("bet_types", [])
                
                # Format odds
                odds_str = f"+{int(combined_odds)}" if combined_odds > 0 else str(int(combined_odds))
                
                # Format confidence
                conf_pct = int(combined_confidence * 100)
                if conf_pct >= 75:
                    conf_emoji = "🔥"
                elif conf_pct >= 65:
                    conf_emoji = "🟢"
                else:
                    conf_emoji = "🟡"
                
                message_parts.append(f"\n{i}. {num_legs}-Leg Parlay")
                message_parts.append(f"   Odds: {odds_str} | {conf_emoji} {conf_pct}%")
                
                # Show bet types included
                if bet_types:
                    bet_type_str = ", ".join(set(bet_types)[:5])  # Limit display
                    message_parts.append(f"   Types: {bet_type_str}")
                
                # Show potential payouts
                payouts = parlay.get("potential_payouts", {})
                if payouts:
                    message_parts.append("   💰 Payouts:")
                    if payouts.get("stake_10"):
                        message_parts.append(f"      $10 → ${payouts['stake_10']:.2f} (+${payouts['stake_10']-10:.2f})")
                    if payouts.get("stake_25"):
                        message_parts.append(f"      $25 → ${payouts['stake_25']:.2f} (+${payouts['stake_25']-25:.2f})")
                    if payouts.get("stake_50"):
                        message_parts.append(f"      $50 → ${payouts['stake_50']:.2f} (+${payouts['stake_50']-50:.2f})")
                
                # Show legs (condensed)
                legs = parlay.get("legs", parlay.get("picks", []))
                message_parts.append("   Legs:")
                
                for j, leg in enumerate(legs[:5], 1):  # Show first 5 legs
                    game = leg.get("game")
                    selection = leg.get("selection", "N/A")
                    bet_type = leg.get("bet_type", "unknown")
                    odds = leg.get("odds", 0)
                    odds_str_leg = f"+{int(odds)}" if odds > 0 else str(int(odds))
                    
                    # Format game info
                    if game:
                        if game.sport in ["UFC", "BOXING"]:
                            game_info = f"{game.fighter1} vs {game.fighter2}"
                        else:
                            away = game.away_team or "Away"
                            home = game.home_team or "Home"
                            game_info = f"{away} @ {home}"
                    else:
                        game_info = "Unknown"
                    
                    # Condensed leg format
                    message_parts.append(f"      {j}. {selection} ({bet_type}) {odds_str_leg}")
                    message_parts.append(f"         {game_info}")
                
                if len(legs) > 5:
                    message_parts.append(f"      ... +{len(legs) - 5} more legs")
                
                message_parts.append("")  # Spacing
        
        message = "\n".join(message_parts)
        
        # If message is too long, split it
        max_length = 1600  # Twilio SMS limit is 1600 chars, but we'll be safe
        if len(message) > max_length:
            # Split into multiple messages
            parts = message.split("\n\n")  # Split by double newlines
            messages = []
            current_message = ""
            
            for part in parts:
                if len(current_message) + len(part) + 2 > max_length:
                    if current_message:
                        messages.append(current_message.strip())
                    current_message = part
                else:
                    current_message += "\n\n" + part if current_message else part
            
            if current_message:
                messages.append(current_message.strip())
            
            # Send all messages
            all_sent = True
            for i, msg in enumerate(messages, 1):
                if i > 1:
                    msg = f"({i}/{len(messages)})\n\n{msg}"
                if not self.send_sms(msg):
                    all_sent = False
            
            return all_sent
        
        return self.send_sms(message)
    
    def send_picks_sms(self, picks: List[Dict], max_picks: int = 5) -> bool:
        """
        Format and send picks as SMS.
        
        Args:
            picks: List of pick dictionaries
            max_picks: Maximum number of picks to include in message
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not picks:
            message = "📊 No picks found at this time. Check back later!"
            return self.send_sms(message)
        
        # Format message
        message_parts = ["🏀 HOURLY PICKS 🏀\n"]
        
        # Limit picks to avoid message length issues
        picks_to_send = picks[:max_picks]
        
        for i, pick in enumerate(picks_to_send, 1):
            game = pick.get("game")
            bet_type = pick.get("bet_type", "unknown")
            selection = pick.get("selection", "N/A")
            odds = pick.get("odds", 0)
            confidence = pick.get("confidence", 0)
            ev = pick.get("expected_value", 0)
            
            # Player prop specific fields
            player_name = pick.get("player_name")
            prop_type = pick.get("prop_type") or pick.get("market_key", "")
            prop_value = pick.get("prop_value")
            
            # Format game info
            if game:
                if game.sport in ["UFC", "BOXING"]:
                    game_info = f"{game.fighter1} vs {game.fighter2}"
                else:
                    game_info = f"{game.away_team} @ {game.home_team}"
                sport = game.sport
                
                # Add game time if available
                if game.game_date:
                    game_time = game.game_date.strftime("%I:%M %p")
                    game_info += f" ({game_time})"
            else:
                game_info = "Unknown"
                sport = "N/A"
            
            # Format odds (use best odds if available)
            best_odds = pick.get("best_odds", odds)
            odds_str = f"+{int(best_odds)}" if best_odds > 0 else str(int(best_odds))
            if pick.get("best_book") and best_odds != odds:
                odds_str += f" ({pick['best_book']})"
            
            # Format confidence
            conf_pct = int(confidence * 100)
            if conf_pct >= 75:
                conf_emoji = "🔥"
            elif conf_pct >= 65:
                conf_emoji = "🟢"
            else:
                conf_emoji = "🟡"
            
            # Format EV
            ev_pct = f"+{ev*100:.1f}%" if ev > 0 else f"{ev*100:.1f}%"
            
            # Get potential earnings if available
            potential_earnings = pick.get("potential_earnings", {})
            potential_profit = pick.get("potential_profit", {})
            recommended_stake = pick.get("recommended_stake")
            
            # Build pick line - special formatting for player props
            if bet_type == "prop" and player_name:
                # Format player prop nicely
                prop_desc = pick.get("reasoning", "").split(" with")[0] if pick.get("reasoning") else ""
                
                # Get readable prop type name
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
                
                readable_prop = prop_type_names.get(prop_type, prop_type.replace("player_", "").replace("_", " ").title())
                
                if prop_value:
                    # Over/Under prop
                    pick_line = f"\n{i}. {sport}: {player_name} {readable_prop}"
                    pick_line += f"\n   {selection} {prop_value:.1f}"
                else:
                    # Yes/No prop
                    pick_line = f"\n{i}. {sport}: {player_name} {readable_prop}"
                    pick_line += f"\n   {selection}"
                
                pick_line += f"\n   {game_info}"
                pick_line += f"\n   {odds_str} | {conf_emoji} {conf_pct}% | EV: {ev_pct}"
                
                # Add potential earnings
                if potential_earnings:
                    if recommended_stake:
                        rec_payout = potential_earnings.get("recommended", 0)
                        rec_profit = potential_profit.get("recommended", 0)
                        pick_line += f"\n   💰 ${recommended_stake:.0f} → ${rec_payout:.2f} (+${rec_profit:.2f})"
                    else:
                        payout_25 = potential_earnings.get("stake_25", 0)
                        profit_25 = potential_profit.get("stake_25", 0)
                        pick_line += f"\n   💰 $25 → ${payout_25:.2f} (+${profit_25:.2f})"
            else:
                # Regular bet (moneyline, spread, total)
                pick_line = f"\n{i}. {sport}: {selection}"
                pick_line += f"\n   {game_info}"
                pick_line += f"\n   {bet_type.upper()} | {odds_str} | {conf_emoji} {conf_pct}% | EV: {ev_pct}"
                
                # Add potential earnings
                if potential_earnings:
                    if recommended_stake:
                        rec_payout = potential_earnings.get("recommended", 0)
                        rec_profit = potential_profit.get("recommended", 0)
                        pick_line += f"\n   💰 ${recommended_stake:.0f} → ${rec_payout:.2f} (+${rec_profit:.2f})"
                    else:
                        payout_25 = potential_earnings.get("stake_25", 0)
                        profit_25 = potential_profit.get("stake_25", 0)
                        pick_line += f"\n   💰 $25 → ${payout_25:.2f} (+${profit_25:.2f})"
            
            message_parts.append(pick_line)
        
        # Add summary
        if len(picks) > max_picks:
            message_parts.append(f"\n... and {len(picks) - max_picks} more picks available")
        
        message_parts.append("\n📱 Check dashboard for full details")
        
        message = "".join(message_parts)
        
        # Split if message is too long (SMS limit is ~1600 chars, but we'll use 1000 to be safe)
        if len(message) > 1000:
            # Send first part
            first_part = message[:1000] + "\n... (continued)"
            self.send_sms(first_part)
            # Send remaining picks
            remaining_picks = picks[max_picks:]
            if remaining_picks:
                return self.send_picks_sms(remaining_picks, max_picks)
            return True
        
        return self.send_sms(message)

