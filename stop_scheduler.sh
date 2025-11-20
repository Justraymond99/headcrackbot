#!/bin/bash
# Stop the hourly picks scheduler

echo "🛑 Stopping Hourly Picks Scheduler..."

if pgrep -f "enhanced_scheduler.py" > /dev/null; then
    PID=$(pgrep -f "enhanced_scheduler.py")
    echo "   Found process: $PID"
    pkill -f "enhanced_scheduler.py"
    sleep 2
    
    if pgrep -f "enhanced_scheduler.py" > /dev/null; then
        echo "⚠️  Process still running, force killing..."
        pkill -9 -f "enhanced_scheduler.py"
    fi
    
    echo "✅ Scheduler stopped!"
else
    echo "ℹ️  Scheduler is not running."
fi

