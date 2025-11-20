#!/bin/bash
# Start the hourly picks scheduler 24/7

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 Starting Hourly Picks Scheduler 24/7..."
echo "📁 Working directory: $SCRIPT_DIR"
echo ""

# Make sure logs directory exists
mkdir -p logs

# Check if already running
if pgrep -f "enhanced_scheduler.py" > /dev/null; then
    echo "⚠️  Scheduler is already running!"
    echo "   PID: $(pgrep -f 'enhanced_scheduler.py')"
    echo ""
    read -p "Kill existing process and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "enhanced_scheduler.py"
        sleep 2
    else
        echo "Exiting..."
        exit 1
    fi
fi

# Start in background with nohup
nohup python3 enhanced_scheduler.py > logs/scheduler.log 2>&1 &

PID=$!
echo "✅ Scheduler started!"
echo "   PID: $PID"
echo "   Logs: logs/scheduler.log"
echo ""
echo "📱 Your picks will be sent via Telegram every hour!"
echo ""
echo "To stop: pkill -f enhanced_scheduler.py"
echo "To view logs: tail -f logs/scheduler.log"
echo ""

# Wait a moment and check if it's still running
sleep 3
if ps -p $PID > /dev/null; then
    echo "✅ Scheduler is running successfully!"
else
    echo "❌ Scheduler failed to start. Check logs/scheduler.log for errors."
    exit 1
fi

