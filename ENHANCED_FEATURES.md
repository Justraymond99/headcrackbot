# Enhanced Features for Hourly Picks System

## 🎯 New Features Added

### 1. **Performance Tracking** 📊
Track which picks win/lose and analyze performance over time.

**Features:**
- Overall win rate tracking
- Sport-specific performance breakdown
- Bet type performance (moneyline, spread, totals)
- Average confidence and EV tracking
- Resolved vs pending picks tracking

**Usage:**
```python
from pick_performance_tracker import PickPerformanceTracker

tracker = PickPerformanceTracker()

# Get overall stats
stats = tracker.get_pick_performance_stats(days=7)
print(f"Win Rate: {stats['win_rate']*100:.1f}%")

# Get sport breakdown
sport_stats = tracker.get_sport_performance(days=7)
for sport, data in sport_stats.items():
    print(f"{sport}: {data['win_rate']*100:.1f}%")
```

### 2. **Parlay Suggestions** 🎯
Get top parlay combinations sent via SMS.

**Features:**
- AI-optimized parlay combinations
- 2-4 leg parlays
- Shows combined odds and confidence
- Diversified across different games

**Usage:**
```python
from pick_enhancements import PickEnhancements

enhancer = PickEnhancements()
enhancer.send_parlay_suggestions(max_parlays=2)
```

### 3. **Performance Summaries** 📈
Get daily/weekly performance summaries via SMS.

**Features:**
- Overall win/loss record
- Win rate percentage
- Average confidence and EV
- Sport-by-sport breakdown
- Configurable time period

**Usage:**
```python
enhancer = PickEnhancements()
# Send weekly summary
enhancer.send_performance_summary(days=7, include_sport_breakdown=True)
```

### 4. **Line Movement Alerts** 📈
Get notified when odds improve on picks you were sent.

**Features:**
- Monitors sent picks for favorable line movements
- Alerts when odds improve significantly
- Shows best bookmaker for improved odds
- Configurable minimum improvement threshold

**Usage:**
```python
enhancer = PickEnhancements()
# Check for movements in last 6 hours, alert if odds improved by 10+
enhancer.send_line_movement_alerts(min_improvement=10.0, hours=6)
```

### 5. **Pick Results Follow-up** 🏁
Get results of your picks after games finish.

**Features:**
- Automatically sends results of finished games
- Shows win/loss for each pick
- Summary record (W-L)
- Only sends for picks you were texted

**Usage:**
```python
enhancer = PickEnhancements()
# Send results for picks from last 24 hours
enhancer.send_pick_results_followup(hours=24)
```

## 🔧 Integration with Scheduler

You can add these features to your hourly scheduler. Update `scheduler.py`:

```python
from hourly_picks_enhanced import EnhancedHourlyPicksGenerator
from pick_enhancements import PickEnhancements
import os

def send_picks_job():
    """Main hourly picks job."""
    generator = EnhancedHourlyPicksGenerator()
    generator.send_hourly_picks()
    
    # Optional: Send parlay suggestions (once per day)
    if datetime.now().hour == 10:  # 10 AM
        enhancer = PickEnhancements()
        enhancer.send_parlay_suggestions()

def send_performance_summary_job():
    """Daily performance summary (runs once per day)."""
    enhancer = PickEnhancements()
    enhancer.send_performance_summary(days=7)

def check_line_movements_job():
    """Check for line movements (runs every 2 hours)."""
    enhancer = PickEnhancements()
    enhancer.send_line_movement_alerts(min_improvement=10.0, hours=6)

def send_results_followup_job():
    """Send pick results (runs every 4 hours)."""
    enhancer = PickEnhancements()
    enhancer.send_pick_results_followup(hours=24)
```

## 📅 Recommended Schedule

- **Hourly**: Main picks (existing)
- **Daily (10 AM)**: Parlay suggestions
- **Daily (9 PM)**: Performance summary
- **Every 2 hours**: Line movement alerts
- **Every 4 hours**: Pick results follow-up

## 🎛️ Configuration

Add to `.env`:

```env
# Performance tracking
ENABLE_PERFORMANCE_TRACKING=true
PERFORMANCE_SUMMARY_DAYS=7

# Parlay suggestions
ENABLE_PARLAY_SUGGESTIONS=true
PARLAY_SUGGESTIONS_TIME=10  # Hour of day (24-hour format)

# Line movements
ENABLE_LINE_MOVEMENT_ALERTS=true
LINE_MOVEMENT_MIN_IMPROVEMENT=10.0
LINE_MOVEMENT_CHECK_HOURS=6

# Results follow-up
ENABLE_RESULTS_FOLLOWUP=true
RESULTS_FOLLOWUP_HOURS=24
```

## 📊 Example Messages

### Performance Summary
```
📊 PERFORMANCE SUMMARY (7 days)
Total Picks: 42
Resolved: 35
Wins: 22 | Losses: 13
Win Rate: 62.9%
Avg Confidence: 68.5%
Avg EV: 6.2%

By Sport:
  NBA: 8-4 (66.7%)
  NFL: 7-3 (70.0%)
  MLB: 5-4 (55.6%)
```

### Line Movement Alert
```
📈 FAVORABLE LINE MOVEMENTS 📈

NBA: Lakers
  Warriors @ Lakers
  +150 → +165 (DraftKings)

NFL: Chiefs -3.5
  Chiefs @ Bills
  -110 → -105 (FanDuel)
```

### Pick Results
```
🏁 PICK RESULTS 🏁

✅ NBA: Lakers
   Warriors @ Lakers - WIN

❌ NFL: Chiefs -3.5
   Chiefs @ Bills - LOSS

Record: 5W-2L
```

## 🚀 Benefits

1. **Track Performance**: Know which picks are working
2. **Optimize Strategy**: See which sports/bet types perform best
3. **Catch Better Odds**: Get alerted when odds improve
4. **Stay Informed**: Get results automatically
5. **Better Parlays**: Get optimized parlay suggestions

## 🔄 Next Steps

1. **Update Database**: Run `init_db()` to ensure all tables exist
2. **Test Features**: Try each feature individually
3. **Configure Schedule**: Add jobs to scheduler as needed
4. **Monitor Performance**: Review stats regularly to improve

## 💡 Tips

- Start with performance summaries to see what's working
- Use line movement alerts to catch better odds
- Review parlay suggestions but don't bet everything
- Track results to improve your pick selection over time

