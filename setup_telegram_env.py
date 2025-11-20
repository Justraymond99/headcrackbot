"""Helper script to add Telegram credentials to .env file."""
import os
from pathlib import Path

def setup_env():
    """Add Telegram credentials to .env file."""
    env_path = Path(".env")
    
    bot_token = "8506045290:AAGm8d-kYJoBOtgwsNJalE_kZicAgDPFZXs"
    chat_id = "7197338861"
    
    # Read existing .env if it exists
    existing_lines = []
    if env_path.exists():
        with open(env_path, 'r') as f:
            existing_lines = f.readlines()
    
    # Check if already exists
    has_token = any("TELEGRAM_BOT_TOKEN" in line for line in existing_lines)
    has_chat_id = any("TELEGRAM_CHAT_ID" in line for line in existing_lines)
    
    # Update or add lines
    new_lines = []
    token_added = False
    chat_id_added = False
    
    for line in existing_lines:
        if line.startswith("TELEGRAM_BOT_TOKEN"):
            new_lines.append(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
            token_added = True
        elif line.startswith("TELEGRAM_CHAT_ID"):
            new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
            chat_id_added = True
        else:
            new_lines.append(line)
    
    # Add if not found
    if not token_added:
        new_lines.append(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
    if not chat_id_added:
        new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print("✅ Added Telegram credentials to .env file!")
    print(f"   TELEGRAM_BOT_TOKEN={bot_token[:20]}...")
    print(f"   TELEGRAM_CHAT_ID={chat_id}")

if __name__ == "__main__":
    setup_env()

