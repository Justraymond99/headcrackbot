"""Debug script to check Railway deployment status."""
import os
from dotenv import load_dotenv
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def check_setup():
    """Check if everything is configured correctly."""
    print("=" * 60)
    print("Railway Deployment Debug Check")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("📋 Environment Variables:")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat = os.getenv("TELEGRAM_CHAT_ID", "")
    odds_key = os.getenv("ODDS_API_KEY", "")
    sportsdata_key = os.getenv("SPORTSDATA_API_KEY", "")
    
    print(f"  TELEGRAM_BOT_TOKEN: {'✅ Set' if telegram_token else '❌ Missing'}")
    if telegram_token:
        print(f"    Value: {telegram_token[:20]}...")
    print(f"  TELEGRAM_CHAT_ID: {'✅ Set' if telegram_chat else '❌ Missing'}")
    if telegram_chat:
        print(f"    Value: {telegram_chat}")
    print(f"  ODDS_API_KEY: {'✅ Set' if odds_key else '❌ Missing'}")
    print(f"  SPORTSDATA_API_KEY: {'✅ Set' if sportsdata_key else '❌ Missing'}")
    print()
    
    # Check database
    print("🗄️  Database Check:")
    try:
        from models import engine, SessionLocal
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"  Tables found: {len(tables)}")
        if 'games' in tables:
            print("  ✅ 'games' table exists")
        else:
            print("  ❌ 'games' table missing - database not initialized!")
        
        if 'sent_picks' in tables:
            print("  ✅ 'sent_picks' table exists")
        else:
            print("  ❌ 'sent_picks' table missing")
        
        # Check if games exist
        session = SessionLocal()
        from models import Game
        game_count = session.query(Game).count()
        print(f"  Games in database: {game_count}")
        session.close()
        
    except Exception as e:
        print(f"  ❌ Database error: {e}")
    print()
    
    # Check Telegram service
    print("📱 Telegram Service Check:")
    try:
        from telegram_service import TelegramService
        telegram = TelegramService()
        if telegram.is_configured:
            print("  ✅ Telegram service is configured")
            # Test send
            test_msg = f"🧪 Test message from Railway - {datetime.now().strftime('%H:%M:%S')}"
            success = telegram.send_message(test_msg)
            if success:
                print("  ✅ Test message sent successfully!")
            else:
                print("  ❌ Failed to send test message")
        else:
            print("  ❌ Telegram service not configured")
    except Exception as e:
        print(f"  ❌ Telegram error: {e}")
    print()
    
    # Check scheduler timing
    print("⏰ Scheduler Timing:")
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0)
    if now.minute >= 30:
        next_hour = next_hour.replace(hour=next_hour.hour + 1)
    next_half = now.replace(minute=30, second=0, microsecond=0)
    if now.minute >= 30:
        next_half = next_half.replace(hour=next_half.hour + 1)
    
    print(f"  Current time: {now.strftime('%H:%M:%S')}")
    print(f"  Next :00 pick: {next_hour.strftime('%H:%M')}")
    print(f"  Next :30 pick: {next_half.strftime('%H:%M')}")
    print()
    
    # Test pick generation
    print("🎯 Testing Pick Generation:")
    try:
        from enhanced_scheduler import EnhancedHourlyPicksGenerator
        generator = EnhancedHourlyPicksGenerator()
        
        picks = generator.generate_hourly_picks(
            min_ev=0.05,
            min_confidence=0.6,
            max_picks=5,
            refresh_odds=False,  # Don't refresh for quick test
            filter_recent=False
        )
        
        print(f"  Generated {len(picks)} picks")
        if picks:
            print("  ✅ Picks can be generated")
        else:
            print("  ⚠️  No picks generated (might be normal if no games meet criteria)")
    except Exception as e:
        print(f"  ❌ Error generating picks: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    print("=" * 60)
    print("Debug check complete!")
    print("=" * 60)

if __name__ == "__main__":
    check_setup()

