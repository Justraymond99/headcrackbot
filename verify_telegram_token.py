"""Verify Telegram bot token and help troubleshoot."""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def verify_token():
    """Verify the Telegram bot token."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        return False
    
    print(f"Testing bot token: {bot_token[:10]}...")
    print("\nTesting with Telegram API...")
    
    # Test 1: Get bot info
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get("ok"):
            bot_info = data.get("result", {})
            print("✅ Bot token is VALID!")
            print(f"   Bot username: @{bot_info.get('username', 'N/A')}")
            print(f"   Bot name: {bot_info.get('first_name', 'N/A')}")
            return True
        else:
            error_code = data.get("error_code")
            description = data.get("description", "Unknown error")
            print(f"❌ Error: {error_code} - {description}")
            
            if error_code == 401:
                print("\n🔍 Troubleshooting:")
                print("1. Check if the bot token is correct")
                print("2. Make sure you copied the ENTIRE token (including the colon)")
                print("3. The token should look like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
                print("4. Try creating a new bot with @BotFather if this one doesn't work")
                print("\nTo create a new bot:")
                print("1. Open Telegram and search for @BotFather")
                print("2. Send /newbot")
                print("3. Follow the instructions")
                print("4. Copy the new token")
            
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to Telegram API: {e}")
        return False

if __name__ == "__main__":
    verify_token()

