"""Helper script to add Telegram credentials to .env file."""
from getpass import getpass
from pathlib import Path


def setup_env():
    """Add Telegram credentials to .env file."""
    env_path = Path(".env")

    bot_token = getpass("New BotFather token (input hidden): ").strip()
    chat_id = input("Allowed numeric Telegram chat ID: ").strip()
    if not bot_token or ":" not in bot_token:
        raise SystemExit("A valid Telegram bot token is required.")
    if not chat_id.lstrip("-").isdigit():
        raise SystemExit("A numeric Telegram chat ID is required.")

    # Read existing .env if it exists
    existing_lines = []
    if env_path.exists():
        with open(env_path, 'r') as f:
            existing_lines = f.readlines()
    
    # Check if already exists
    # Update or add lines
    new_lines = []
    token_added = False
    chat_id_added = False

    for line in existing_lines:
        if line.startswith("TELEGRAM_BOT_TOKEN"):
            new_lines.append(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
            token_added = True
        elif line.startswith("TELEGRAM_ALLOWED_CHAT_IDS"):
            new_lines.append(f"TELEGRAM_ALLOWED_CHAT_IDS={chat_id}\n")
            chat_id_added = True
        else:
            new_lines.append(line)

    # Add if not found
    if not token_added:
        new_lines.append(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
    if not chat_id_added:
        new_lines.append(f"TELEGRAM_ALLOWED_CHAT_IDS={chat_id}\n")

    # Write back
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print("Telegram credentials added to .env.")
    print(f"Allowed chat ID: {chat_id}")


if __name__ == "__main__":
    setup_env()

