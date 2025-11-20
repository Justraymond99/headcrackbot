"""Get your Telegram Chat ID after messaging the bot."""
import requests

BOT_TOKEN = "8506045290:AAGm8d-kYJoBOtgwsNJalE_kZicAgDPFZXs"

def get_chat_id():
    """Get Chat ID from recent messages."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get("ok"):
            print(f"❌ Error: {data.get('description', 'Unknown error')}")
            return None
        
        updates = data.get("result", [])
        
        if not updates:
            print("⚠️  No messages found!")
            print("\n📱 Please do this:")
            print("1. Open Telegram")
            print("2. Search for @Justparlaysbot")
            print("3. Start a chat and send any message (e.g., 'Hello')")
            print("4. Run this script again")
            return None
        
        print("✅ Found recent messages!\n")
        print("📋 Chat IDs found:")
        print("-" * 50)
        
        chat_ids = set()
        for update in updates:
            if "message" in update and "chat" in update["message"]:
                chat = update["message"]["chat"]
                chat_id = chat.get("id")
                first_name = chat.get("first_name", "")
                username = chat.get("username", "")
                
                if chat_id:
                    chat_ids.add(chat_id)
                    name = f"{first_name} (@{username})" if username else first_name
                    print(f"  Chat ID: {chat_id}")
                    print(f"  Name: {name}")
                    print()
        
        if chat_ids:
            # Use the most recent one
            latest_chat_id = list(chat_ids)[-1]
            print("=" * 50)
            print(f"✅ Your Chat ID: {latest_chat_id}")
            print("\n📝 Add this to your .env file:")
            print(f"TELEGRAM_BOT_TOKEN=8506045290:AAGm8d-kYJoBOtgwsNJalE_kZicAgDPFZXs")
            print(f"TELEGRAM_CHAT_ID={latest_chat_id}")
            print("=" * 50)
            return latest_chat_id
        
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    get_chat_id()

