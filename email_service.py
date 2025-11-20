"""Email notification service for sending picks."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Handle email notifications via SMTP (Gmail, etc.)."""
    
    def __init__(self):
        # Gmail SMTP settings (can be changed for other providers)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_address = os.getenv("EMAIL_ADDRESS", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")  # Use App Password for Gmail
        self.to_email = os.getenv("USER_EMAIL", "")  # Your email to receive picks
        
        self.is_configured = bool(self.email_address and self.email_password and self.to_email)
        
        if not self.is_configured:
            logger.warning("Email credentials not configured. Email notifications will be disabled.")
            logger.info("Set EMAIL_ADDRESS, EMAIL_PASSWORD, and USER_EMAIL in .env to enable email notifications.")
    
    def send_email(
        self, 
        subject: str, 
        message: str, 
        html_message: Optional[str] = None,
        to_email: Optional[str] = None
    ) -> bool:
        """
        Send email with retry logic.
        
        Args:
            subject: Email subject line
            message: Plain text message body
            html_message: Optional HTML message body
            to_email: Recipient email (defaults to USER_EMAIL)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email not configured. Message would be:")
            logger.info(f"\nSubject: {subject}\n{message}")
            return False
        
        recipient = to_email or self.to_email
        if not recipient:
            logger.error("No recipient email configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_address
            msg['To'] = recipient
            
            # Add plain text part
            text_part = MIMEText(message, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_message:
                html_part = MIMEText(html_message, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Email authentication failed: {e}")
            logger.error("Make sure you're using an App Password for Gmail (not your regular password)")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            return False
    
    def send_picks_email(self, picks: List[Dict], max_picks: int = 10) -> bool:
        """
        Format and send picks as email.
        
        Args:
            picks: List of pick dictionaries
            max_picks: Maximum number of picks to include
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not picks:
            subject = "🏀 No Picks Available"
            message = "No picks found at this time. Check back later!"
            return self.send_email(subject, message)
        
        # Format plain text message
        message_parts = ["🏀 HOURLY PICKS 🏀\n\n"]
        
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
            
            # Format game info
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
            
            # Format pick
            if bet_type == "prop" and player_name:
                prop_type_names = {
                    "player_points": "Pts",
                    "player_rebounds": "Reb",
                    "player_assists": "Ast",
                    "player_pass_yds": "Pass Yds",
                    "player_rush_yds": "Rush Yds",
                    "player_reception_yds": "Rec Yds",
                    "player_threes": "3PM",
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
            pick_line += f"\n   {bet_type.upper()} | {odds_str} | Confidence: {conf_pct}% | EV: {ev_pct}"
            
            if potential_earnings and recommended_stake:
                rec_payout = potential_earnings.get("recommended", 0)
                rec_profit = potential_profit.get("recommended", 0)
                pick_line += f"\n   💰 Stake: ${recommended_stake:.2f} | Payout: ${rec_payout:.2f} (+${rec_profit:.2f})"
            elif potential_earnings:
                payout_25 = potential_earnings.get("stake_25", 0)
                profit_25 = potential_profit.get("stake_25", 0)
                pick_line += f"\n   💰 $25 → ${payout_25:.2f} (+${profit_25:.2f})"
            
            message_parts.append(pick_line)
        
        if len(picks) > max_picks:
            message_parts.append(f"\n... and {len(picks) - max_picks} more picks available")
        
        message = "\n".join(message_parts)
        subject = f"🏀 Hourly Picks - {len(picks_to_send)} Best Picks"
        
        # Create HTML version for better formatting
        html_message = message.replace("\n", "<br>").replace("🏀", "🏀")
        html_message = f"<html><body style='font-family: Arial, sans-serif;'>{html_message}</body></html>"
        
        return self.send_email(subject, message, html_message)
    
    def send_parlays_email(self, parlays_by_sport: Dict[str, List[Dict]], max_parlays_per_sport: int = 1) -> bool:
        """
        Format and send diverse parlays from each sport as email.
        
        Args:
            parlays_by_sport: Dictionary mapping sport to list of parlays
            max_parlays_per_sport: Maximum parlays to show per sport
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not parlays_by_sport:
            subject = "🎯 No Parlays Available"
            message = "No parlay picks found at this time. Check back later!"
            return self.send_email(subject, message)
        
        message_parts = ["🎯 BEST PARLAYS (Each Sport) 🎯\n\n"]
        
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
                
                payouts = parlay.get("potential_payouts", {})
                if payouts:
                    message_parts.append("   💰 Payouts:")
                    if payouts.get("stake_10"):
                        message_parts.append(f"      $10 → ${payouts['stake_10']:.2f} (+${payouts['stake_10']-10:.2f})")
                    if payouts.get("stake_25"):
                        message_parts.append(f"      $25 → ${payouts['stake_25']:.2f} (+${payouts['stake_25']-25:.2f})")
                
                legs = parlay.get("legs", parlay.get("picks", []))
                message_parts.append("   Legs:")
                for j, leg in enumerate(legs[:5], 1):
                    game = leg.get("game")
                    selection = leg.get("selection", "N/A")
                    bet_type = leg.get("bet_type", "unknown")
                    odds = leg.get("odds", 0)
                    odds_str_leg = f"+{int(odds)}" if odds > 0 else str(int(odds))
                    
                    if game:
                        if game.sport in ["UFC", "BOXING"]:
                            game_info = f"{game.fighter1} vs {game.fighter2}"
                        else:
                            game_info = f"{game.away_team} @ {game.home_team}"
                    else:
                        game_info = "Unknown"
                    
                    message_parts.append(f"      {j}. {selection} ({bet_type}) {odds_str_leg}")
                    message_parts.append(f"         {game_info}")
                
                if len(legs) > 5:
                    message_parts.append(f"      ... +{len(legs) - 5} more legs")
                
                message_parts.append("")
        
        message = "\n".join(message_parts)
        subject = "🎯 Hourly Parlay Picks"
        
        html_message = message.replace("\n", "<br>")
        html_message = f"<html><body style='font-family: Arial, sans-serif;'>{html_message}</body></html>"
        
        return self.send_email(subject, message, html_message)

