# Quick Start - Enhanced Hourly Picks

## What's New? 🎉

The enhanced version adds several improvements to make your hourly picks system better:

### ✨ Key Features

1. **No Duplicate Picks** - Won't send the same pick multiple times
2. **Smart Timing** - Only sends picks for games happening soon (1-24 hours)
3. **Retry Logic** - Automatically retries if APIs fail
4. **Better Messages** - Shows game times and best odds
5. **Rate Limit Handling** - Handles Twilio rate limits gracefully

## Quick Setup

### 1. Update Database

```bash
python -c "from models import init_db; init_db()"
```

### 2. Update Your Scheduler

Edit `scheduler.py` and change:

```python
# OLD:
from hourly_picks import HourlyPicksGenerator

# NEW:
from hourly_picks_enhanced import EnhancedHourlyPicksGenerator

# And update the class name:
generator = EnhancedHourlyPicksGenerator()
```

### 3. (Optional) Customize Settings

Add to `.env`:

```env
# Prevent sending same picks within 6 hours
PICKS_FILTER_RECENT=true
PICKS_RECENT_HOURS=6

# Only send picks for games 1-24 hours away
PICKS_MIN_HOURS_AHEAD=1
PICKS_MAX_HOURS_AHEAD=24
```

### 4. Test It

```python
from hourly_picks_enhanced import EnhancedHourlyPicksGenerator

generator = EnhancedHourlyPicksGenerator()
generator.send_hourly_picks()
```

## What Changed?

- **Before**: Could send duplicate picks, no time filtering, no retries
- **After**: Smart filtering, time-based picks, automatic retries, better messages

## Backward Compatibility

The original `hourly_picks.py` still works! The enhanced version is optional. You can:
- Keep using the original (no changes needed)
- Switch to enhanced (better features)
- Use both (test enhanced, keep original as backup)

## Need Help?

See `IMPROVEMENTS.md` for detailed documentation.

