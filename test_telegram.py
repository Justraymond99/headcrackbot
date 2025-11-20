"""Quick script to test Telegram setup and get your Chat ID."""
import os
from dotenv import load_dotenv
from telegram_service import TelegramService

# Load environment variables
load_dotenv()

def test_telegram():
    """Test Telegram connection and show Chat ID."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    
    print("=" * 50)
    print("Telegram Setup Test")
    print("=" * 50)
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        print("\nPlease add to .env:")
        print("TELEGRAM_BOT_TOKEN=8506045290:AAm8d-kYJoB0tgwsNJalE_kZicAgDPFZXs")
        return
    
    print(f"✅ Bot Token found: {bot_token[:10]}...")
    
    if not chat_id:
        print("\n⚠️  TELEGRAM_CHAT_ID not found in .env file")
        print("\nTo get your Chat ID:")
        print("1. Open Telegram and start a chat with your bot")
        print("2. Send any message to your bot (e.g., 'Hello')")
        print("3. Visit this URL in your browser:")
        print(f"   https://api.telegram.org/bot{bot_token}/getUpdates")
        print("4. Look for 'chat':{'id':123456789} in the response")
        print("5. Add to .env: TELEGRAM_CHAT_ID=123456789")
        return
    
    print(f"✅ Chat ID found: {chat_id}")
    
    # Test sending a message
    print("\n" + "=" * 50)
    print("Testing Telegram connection...")
    print("=" * 50)
    
    telegram = TelegramService()
    
    if telegram.is_configured:
        print("✅ Telegram service is configured!")
        print("\nSending test message...")
        success = telegram.send_message(
            "🎉 <b>Test Message</b>\n\n"
            "Your Telegram bot is working correctly! "
            "You'll now receive hourly picks via Telegram instead of SMS."
        )
        
        if success:
            print("✅ Test message sent successfully!")
            print("\n🎉 Setup complete! Your hourly picks will now be sent via Telegram.")
        else:
            print("❌ Failed to send test message. Check your bot token and chat ID.")
    else:
        print("❌ Telegram service is not configured properly")
        print("Check your .env file for TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")

if __name__ == "__main__":
    test_telegram()

