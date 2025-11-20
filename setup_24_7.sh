#!/bin/bash
# Setup script for 24/7 hourly picks scheduler

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🎯 Setting up 24/7 Hourly Picks Scheduler"
echo "=========================================="
echo ""

# Make scripts executable
chmod +x start_24_7.sh
chmod +x stop_scheduler.sh

echo "✅ Scripts are now executable"
echo ""

# Check if .env file exists and has Telegram config
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "   Please create .env file with your Telegram credentials"
    exit 1
fi

if ! grep -q "TELEGRAM_BOT_TOKEN" .env || ! grep -q "TELEGRAM_CHAT_ID" .env; then
    echo "⚠️  Telegram credentials not found in .env file!"
    echo "   Please add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
    exit 1
fi

echo "✅ Telegram credentials found in .env"
echo ""

# Create logs directory
mkdir -p logs
echo "✅ Logs directory created"
echo ""

echo "📋 Setup Options:"
echo ""
echo "Option 1: Run in background (simple, recommended)"
echo "   ./start_24_7.sh"
echo ""
echo "Option 2: Use macOS LaunchAgent (auto-start on boot)"
echo "   ./setup_launchd.sh"
echo ""
echo "Option 3: Run in terminal (for testing)"
echo "   python3 enhanced_scheduler.py"
echo ""

read -p "Start scheduler now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./start_24_7.sh
fi

