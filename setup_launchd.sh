#!/bin/bash
# Setup macOS LaunchAgent for 24/7 operation (auto-start on boot)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_NAME="com.hourlypicks.scheduler"
PLIST_FILE="$SCRIPT_DIR/$PLIST_NAME.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$LAUNCH_AGENTS_DIR/$PLIST_NAME.plist"

echo "🔧 Setting up macOS LaunchAgent for 24/7 operation"
echo "=================================================="
echo ""

# Check if plist exists
if [ ! -f "$PLIST_FILE" ]; then
    echo "❌ Plist file not found: $PLIST_FILE"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"

# Copy plist to LaunchAgents
echo "📋 Copying plist to LaunchAgents..."
cp "$PLIST_FILE" "$TARGET_PLIST"

# Update paths in plist (use absolute paths)
sed -i '' "s|/Users/yungray/Desktop/chess game/tictactoe|$SCRIPT_DIR|g" "$TARGET_PLIST"

echo "✅ Plist installed to: $TARGET_PLIST"
echo ""

# Unload if already loaded
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "🛑 Unloading existing service..."
    launchctl unload "$TARGET_PLIST" 2>/dev/null || true
fi

# Load the service
echo "🚀 Loading service..."
launchctl load "$TARGET_PLIST"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Service loaded successfully!"
    echo ""
    echo "📱 Your scheduler will now:"
    echo "   - Start automatically on boot"
    echo "   - Restart automatically if it crashes"
    echo "   - Run 24/7 in the background"
    echo ""
    echo "To check status: launchctl list | grep $PLIST_NAME"
    echo "To stop: launchctl unload $TARGET_PLIST"
    echo "To start: launchctl load $TARGET_PLIST"
    echo "To view logs: tail -f logs/scheduler.log"
else
    echo "❌ Failed to load service. Check the plist file for errors."
    exit 1
fi

