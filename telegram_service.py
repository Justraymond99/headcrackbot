"""Telegram bot service for sending picks (super easy, no registration!)."""
import requests
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class TelegramService:
    """Handle Telegram notifications via bot API (free, easy setup!)."""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        self.is_configured = bool(self.bot_token and self.chat_id)
        
        if not self.is_configured:
            logger.warning("Telegram credentials not configured. Telegram will be disabled.")
            logger.info("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        else:
            logger.info("✅ Telegram service configured (free, no registration!)")
    
    def send_message(self, message: str, chat_id: Optional[str] = None, parse_mode: str = "HTML") -> bool:
        """
        Send Telegram message.
        
        Args:
            message: Message text to send
            chat_id: Chat ID (defaults to TELEGRAM_CHAT_ID)
            parse_mode: Parse mode (HTML or Markdown)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Telegram not configured. Message would be:")
            logger.info(f"\n{message}")
            return False
        
        recipient = chat_id or self.chat_id
        if not recipient:
            logger.error("No chat ID configured")
            return False
        
        try:
            # Telegram supports up to 4096 characters per message
            max_length = 4096
            if len(message) > max_length:
                parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
                all_sent = True
                for i, part in enumerate(parts, 1):
                    if len(parts) > 1:
                        part = f"<b>({i}/{len(parts)})</b>\n\n{part}"
                    if not self._send_telegram_message(part, recipient, parse_mode):
                        all_sent = False
                return all_sent
            
            return self._send_telegram_message(message, recipient, parse_mode)
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}", exc_info=True)
            return False
    
    def _send_telegram_message(self, message: str, chat_id: str, parse_mode: str) -> bool:
        """Internal method to send message via Telegram API."""
        try:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                logger.info(f"Telegram message sent successfully to {chat_id}")
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}", exc_info=True)
            return False
    
    def send_picks_message(self, picks: List[Dict], max_picks: int = 10) -> bool:
        """
        Format and send picks as Telegram message.
        
        Args:
            picks: List of pick dictionaries
            max_picks: Maximum number of picks to include
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not picks:
            message = "📊 <b>No picks found at this time. Check back later!</b>"
            return self.send_message(message)
        
        # Format message with HTML
        message_parts = ["<b>🏀 HOURLY PICKS 🏀</b>\n"]
        
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
                
                pick_line = f"\n<b>{i}. {sport}: {player_name} {readable_prop}</b>"
                if prop_value:
                    pick_line += f"\n   {selection} {prop_value:.1f}"
                else:
                    pick_line += f"\n   {selection}"
            else:
                pick_line = f"\n<b>{i}. {sport}: {selection}</b>"
            
            pick_line += f"\n   <code>{game_info}</code>"
            pick_line += f"\n   {bet_type.upper()} | <b>{odds_str}</b> | {conf_pct}% | EV: {ev_pct}"
            
            if potential_earnings and recommended_stake:
                rec_payout = potential_earnings.get("recommended", 0)
                rec_profit = potential_profit.get("recommended", 0)
                pick_line += f"\n   💰 ${recommended_stake:.0f} → ${rec_payout:.2f} (+${rec_profit:.2f})"
            
            message_parts.append(pick_line)
        
        if len(picks) > max_picks:
            message_parts.append(f"\n<i>... and {len(picks) - max_picks} more picks available</i>")
        
        message = "\n".join(message_parts)
        return self.send_message(message)
    
    def send_parlays_message(self, parlays_by_sport: Dict[str, List[Dict]], max_parlays_per_sport: int = 1) -> bool:
        """
        Format and send diverse parlays as Telegram message.
        
        Args:
            parlays_by_sport: Dictionary mapping sport to list of parlays
            max_parlays_per_sport: Maximum parlays to show per sport
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not parlays_by_sport:
            message = "📊 <b>No parlay picks found at this time. Check back later!</b>"
            return self.send_message(message)
        
        message_parts = ["<b>🎯 BEST PARLAYS (Each Sport) 🎯</b>\n"]
        
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
            message_parts.append(f"\n<b>{emoji} {sport} {emoji}</b>")
            
            for i, parlay in enumerate(parlays[:max_parlays_per_sport], 1):
                num_legs = parlay.get("num_legs", 0)
                combined_odds = parlay.get("combined_odds", 0)
                combined_confidence = parlay.get("combined_confidence", 0)
                
                odds_str = f"+{int(combined_odds)}" if combined_odds > 0 else str(int(combined_odds))
                conf_pct = int(combined_confidence * 100)
                
                message_parts.append(f"\n<b>{i}. {num_legs}-Leg Parlay</b>")
                message_parts.append(f"   Odds: <b>{odds_str}</b> | Confidence: {conf_pct}%")
                
                legs = parlay.get("legs", parlay.get("picks", []))
                message_parts.append("   <i>Legs:</i>")
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
                    
                    message_parts.append(f"      {j}. <b>{selection}</b> ({bet_type})")
                    message_parts.append(f"         <code>{game_info}</code>")
                
                if len(legs) > 5:
                    message_parts.append(f"      <i>... +{len(legs) - 5} more legs</i>")
                
                message_parts.append("")
        
        message = "\n".join(message_parts)
        return self.send_message(message)

