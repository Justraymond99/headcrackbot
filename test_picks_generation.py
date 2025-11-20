"""Test script to check if picks can be generated."""
import os
from dotenv import load_dotenv
from enhanced_scheduler import EnhancedHourlyPicksGenerator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def test_picks():
    """Test if picks can be generated."""
    print("=" * 60)
    print("Testing Picks Generation")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("📋 Checking Environment Variables:")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat = os.getenv("TELEGRAM_CHAT_ID", "")
    odds_key = os.getenv("ODDS_API_KEY", "")
    sportsdata_key = os.getenv("SPORTSDATA_API_KEY", "")
    
    print(f"  TELEGRAM_BOT_TOKEN: {'✅ Set' if telegram_token else '❌ Missing'}")
    print(f"  TELEGRAM_CHAT_ID: {'✅ Set' if telegram_chat else '❌ Missing'}")
    print(f"  ODDS_API_KEY: {'✅ Set' if odds_key else '❌ Missing'}")
    print(f"  SPORTSDATA_API_KEY: {'✅ Set' if sportsdata_key else '❌ Missing'}")
    print()
    
    if not telegram_token or not telegram_chat:
        print("⚠️  Telegram credentials missing! Picks won't be sent.")
        print()
    
    if not odds_key:
        print("⚠️  ODDS_API_KEY missing! Will use mock data.")
        print()
    
    # Test generating picks
    print("🔍 Testing Pick Generation...")
    print()
    
    try:
        generator = EnhancedHourlyPicksGenerator()
        
        print("Generating picks (this may take a minute)...")
        picks = generator.generate_hourly_picks(
            min_ev=0.05,
            min_confidence=0.6,
            max_picks=5,
            refresh_odds=True,
            filter_recent=False  # Don't filter for testing
        )
        
        print()
        print("=" * 60)
        print(f"✅ Generated {len(picks)} picks")
        print("=" * 60)
        
        if picks:
            print()
            print("📊 Sample picks:")
            for i, pick in enumerate(picks[:3], 1):
                game = pick.get("game")
                selection = pick.get("selection", "N/A")
                bet_type = pick.get("bet_type", "N/A")
                odds = pick.get("odds", 0)
                confidence = pick.get("confidence", 0)
                
                if game:
                    if game.sport in ["UFC", "BOXING"]:
                        game_info = f"{game.fighter1} vs {game.fighter2}"
                    else:
                        game_info = f"{game.away_team} @ {game.home_team}"
                else:
                    game_info = "Unknown"
                
                print(f"  {i}. {game_info}")
                print(f"     {bet_type}: {selection} | Odds: {odds} | Confidence: {confidence*100:.0f}%")
                print()
        else:
            print()
            print("⚠️  No picks generated. Possible reasons:")
            print("  - No scheduled games in database")
            print("  - No games meet the EV/confidence thresholds")
            print("  - API keys not configured (using mock data)")
            print("  - Games are too far in the future")
            print()
            print("💡 Try:")
            print("  - Check if games are in the database")
            print("  - Lower min_ev or min_confidence thresholds")
            print("  - Verify API keys are set")
        
        # Test sending
        if picks and telegram_token and telegram_chat:
            print()
            print("📱 Testing Telegram send...")
            success = generator.send_hourly_picks(
                min_ev=0.05,
                min_confidence=0.6,
                max_picks=5,
                refresh_odds=False  # Don't refresh again
            )
            if success:
                print("✅ Picks sent successfully via Telegram!")
            else:
                print("❌ Failed to send picks via Telegram")
        
    except Exception as e:
        print()
        print("❌ Error generating picks:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_picks()

