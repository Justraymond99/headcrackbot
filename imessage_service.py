"""iMessage notification service for Mac users (no registration needed!)."""
import subprocess
import json
import logging
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)


class iMessageService:
    """Handle iMessage notifications via AppleScript (Mac only, no registration!)."""
    
    def __init__(self):
        self.to_number = os.getenv("USER_PHONE_NUMBER", "").replace("+", "")  # Remove + for iMessage
        self.is_configured = bool(self.to_number)
        
        if not self.is_configured:
            logger.warning("Phone number not configured. iMessage will be disabled.")
            logger.info("Set USER_PHONE_NUMBER in .env (e.g., +19294715507)")
        else:
            # Test if Messages app is available (Mac only)
            try:
                result = subprocess.run(
                    ["osascript", "-e", "tell application \"Messages\" to get name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    logger.warning("Messages app not available. Make sure you're on macOS.")
                    self.is_configured = False
                else:
                    logger.info("✅ iMessage service configured (no registration needed!)")
            except Exception as e:
                logger.warning(f"Could not verify Messages app: {e}")
                self.is_configured = False
    
    def _send_imessage_applecript(self, message: str, recipient: str) -> bool:
        """
        Send iMessage using AppleScript.
        
        Args:
            message: Message text to send
            recipient: Phone number or email (without +)
        
        Returns:
            True if sent successfully, False otherwise
        """
        # Clean recipient (remove +, spaces, dashes)
        recipient = recipient.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # AppleScript to send iMessage
        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{recipient}" of targetService
            send "{message}" to targetBuddy
        end tell
        '''
        
        # Escape quotes in message for AppleScript
        script = script.replace('"', '\\"')
        # Actually, better approach - use proper escaping
        escaped_message = message.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{recipient}" of targetService
            send "{escaped_message}" to targetBuddy
        end tell
        '''
        
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"iMessage sent successfully to {recipient}")
                return True
            else:
                logger.error(f"Error sending iMessage: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("iMessage send timed out")
            return False
        except Exception as e:
            logger.error(f"Error sending iMessage: {e}", exc_info=True)
            return False
    
    def send_message(self, message: str, to_number: Optional[str] = None) -> bool:
        """
        Send iMessage with retry logic.
        
        Args:
            message: Message text to send
            to_number: Recipient phone number (defaults to USER_PHONE_NUMBER)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("iMessage not configured. Message would be:")
            logger.info(f"\n{message}")
            return False
        
        recipient = (to_number or self.to_number).replace("+", "")
        if not recipient:
            logger.error("No recipient phone number configured")
            return False
        
        # Split long messages (iMessage has limits, but let's keep it reasonable)
        max_length = 2000
        if len(message) > max_length:
            parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
            all_sent = True
            for i, part in enumerate(parts, 1):
                if len(parts) > 1:
                    part = f"({i}/{len(parts)})\n\n{part}"
                if not self._send_imessage_applescript(part, recipient):
                    all_sent = False
            return all_sent
        
        return self._send_imessage_applescript(message, recipient)
    
    def send_picks_message(self, picks: List[Dict], max_picks: int = 5) -> bool:
        """
        Format and send picks as iMessage.
        
        Args:
            picks: List of pick dictionaries
            max_picks: Maximum number of picks to include
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not picks:
            message = "📊 No picks found at this time. Check back later!"
            return self.send_message(message)
        
        # Format message (similar to SMS formatting)
        message_parts = ["🏀 HOURLY PICKS 🏀\n"]
        
        picks_to_send = picks[:max_picks]
        
        for i, pick in enumerate(picks_to_send, 1):
            game = pick.get("game")
            bet_type = pick.get("bet_type", "unknown")
            selection = pick.get("selection", "N/A")
            odds = pick.get("odds", 0)
            confidence = pick.get("confidence", 0)
            ev = pick.get("expected_value", 0)
            
            player_name = pick.get("player_name")
            prop_type = pick.get("prop_type") or pick.get("market_key", "")
            prop_value = pick.get("prop_value")
            
            if game:
                if game.sport in ["UFC", "BOXING"]:
                    game_info = f"{game.fighter1} vs {game.fighter2}"
                else:
                    game_info = f"{game.away_team} @ {game.home_team}"
                sport = game.sport
                
                if game.game_date:
                    game_time = game.game_date.strftime("%I:%M %p")
                    game_info += f" ({game_time})"
            else:
                game_info = "Unknown"
                sport = "N/A"
            
            best_odds = pick.get("best_odds", odds)
            odds_str = f"+{int(best_odds)}" if best_odds > 0 else str(int(best_odds))
            if pick.get("best_book") and best_odds != odds:
                odds_str += f" ({pick['best_book']})"
            
            conf_pct = int(confidence * 100)
            ev_pct = f"+{ev*100:.1f}%" if ev > 0 else f"{ev*100:.1f}%"
            
            potential_earnings = pick.get("potential_earnings", {})
            potential_profit = pick.get("potential_profit", {})
            recommended_stake = pick.get("recommended_stake")
            
            if bet_type == "prop" and player_name:
                prop_type_names = {
                    "player_points": "Pts",
                    "player_rebounds": "Reb",
                    "player_assists": "Ast",
                }
                readable_prop = prop_type_names.get(prop_type, prop_type.replace("player_", "").replace("_", " ").title())
                
                pick_line = f"\n{i}. {sport}: {player_name} {readable_prop}"
                if prop_value:
                    pick_line += f"\n   {selection} {prop_value:.1f}"
                else:
                    pick_line += f"\n   {selection}"
            else:
                pick_line = f"\n{i}. {sport}: {selection}"
            
            pick_line += f"\n   {game_info}"
            pick_line += f"\n   {bet_type.upper()} | {odds_str} | {conf_pct}% | EV: {ev_pct}"
            
            if potential_earnings and recommended_stake:
                rec_payout = potential_earnings.get("recommended", 0)
                rec_profit = potential_profit.get("recommended", 0)
                pick_line += f"\n   💰 ${recommended_stake:.0f} → ${rec_payout:.2f} (+${rec_profit:.2f})"
            
            message_parts.append(pick_line)
        
        if len(picks) > max_picks:
            message_parts.append(f"\n... and {len(picks) - max_picks} more picks available")
        
        message = "".join(message_parts)
        return self.send_message(message)
    
    def send_parlays_message(self, parlays_by_sport: Dict[str, List[Dict]], max_parlays_per_sport: int = 1) -> bool:
        """
        Format and send diverse parlays as iMessage.
        
        Args:
            parlays_by_sport: Dictionary mapping sport to list of parlays
            max_parlays_per_sport: Maximum parlays to show per sport
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not parlays_by_sport:
            message = "📊 No parlay picks found at this time. Check back later!"
            return self.send_message(message)
        
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
            
            for i, parlay in enumerate(parlays[:max_parlays_per_sport], 1):
                num_legs = parlay.get("num_legs", 0)
                combined_odds = parlay.get("combined_odds", 0)
                combined_confidence = parlay.get("combined_confidence", 0)
                
                odds_str = f"+{int(combined_odds)}" if combined_odds > 0 else str(int(combined_odds))
                conf_pct = int(combined_confidence * 100)
                
                message_parts.append(f"\n{i}. {num_legs}-Leg Parlay")
                message_parts.append(f"   Odds: {odds_str} | Confidence: {conf_pct}%")
                
                legs = parlay.get("legs", parlay.get("picks", []))
                message_parts.append("   Legs:")
                for j, leg in enumerate(legs[:5], 1):
                    game = leg.get("game")
                    selection = leg.get("selection", "N/A")
                    bet_type = leg.get("bet_type", "unknown")
                    
                    if game:
                        if game.sport in ["UFC", "BOXING"]:
                            game_info = f"{game.fighter1} vs {game.fighter2}"
                        else:
                            game_info = f"{game.away_team} @ {game.home_team}"
                    else:
                        game_info = "Unknown"
                    
                    message_parts.append(f"      {j}. {selection} ({bet_type})")
                    message_parts.append(f"         {game_info}")
                
                if len(legs) > 5:
                    message_parts.append(f"      ... +{len(legs) - 5} more legs")
                
                message_parts.append("")
        
        message = "\n".join(message_parts)
        return self.send_message(message)

