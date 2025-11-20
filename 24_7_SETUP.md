# 🚀 24/7 Hourly Picks Setup Guide

Your scheduler is ready to run 24/7! Here are your options:

## Option 1: Simple Background Process (Recommended for Testing)

**Start:**
```bash
./start_24_7.sh
```

**Stop:**
```bash
./stop_scheduler.sh
```

**View logs:**
```bash
tail -f logs/scheduler.log
```

This runs the scheduler in the background. It will stop when you restart your Mac.

---

## Option 2: macOS LaunchAgent (Auto-start on Boot) ⭐ BEST FOR 24/7

This will automatically start the scheduler when your Mac boots and keep it running 24/7.

**Setup (one time):**
```bash
./setup_launchd.sh
```

**Check status:**
```bash
launchctl list | grep hourlypicks
```

**Stop:**
```bash
launchctl unload ~/Library/LaunchAgents/com.hourlypicks.scheduler.plist
```

**Start:**
```bash
launchctl load ~/Library/LaunchAgents/com.hourlypicks.scheduler.plist
```

**View logs:**
```bash
tail -f logs/scheduler.log
```

---

## What It Does

The scheduler runs **24/7** and sends picks via Telegram:

- **Every hour at :00** - Individual picks (top 5 value bets)
- **Every hour at :30** - Best parlay from each sport
- **Daily at 9 PM** - Performance summary (if enabled)
- **Every 2 hours** - Line movement alerts (if enabled)
- **Every 4 hours** - Pick results follow-up (if enabled)

---

## Configuration

Edit your `.env` file to customize:

```env
# Telegram (required)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Pick settings
PICKS_MIN_EV=0.05              # Minimum expected value
PICKS_MIN_CONFIDENCE=0.6       # Minimum confidence
PICKS_MAX_COUNT=5              # Max picks per message
PICKS_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING

# Parlay settings
PARLAYS_MIN_CONFIDENCE=0.5
PARLAYS_MAX_PER_SPORT=1

# Optional features
SEND_PICKS_ON_STARTUP=true     # Send picks immediately when starting
ENABLE_PERFORMANCE_TRACKING=false
ENABLE_LINE_MOVEMENT_ALERTS=false
ENABLE_RESULTS_FOLLOWUP=false
```

---

## Troubleshooting

**Scheduler not running?**
```bash
# Check if it's running
ps aux | grep enhanced_scheduler

# Check logs
tail -f logs/scheduler.log
tail -f logs/scheduler.error.log
```

**Not receiving picks?**
- Check Telegram bot token and chat ID in `.env`
- Make sure you've messaged the bot on Telegram
- Check logs for errors

**Want to test first?**
```bash
# Run once to test
python3 enhanced_scheduler.py
# Press Ctrl+C to stop
```

---

## 🎉 You're All Set!

Your picks will now be sent automatically via Telegram every hour, 24/7!

