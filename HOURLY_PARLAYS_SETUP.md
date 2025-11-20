# Hourly Parlays Setup Guide

## ✅ What's New

Your system now sends the **best parlay picks from each sport** every hour! 

Each parlay includes:
- ✅ **Varied leg counts** (2-15 legs)
- ✅ **Diverse bet types** (moneylines, spreads, totals, props, alternate spreads, team totals, periods)
- ✅ **Different line amounts** (alternate spreads, alternate totals, etc.)

## 📅 Schedule

The system now runs two hourly jobs:

1. **Hourly Individual Picks** - :00 every hour
   - Sends best individual picks

2. **Hourly Parlays** - :30 every hour ⭐ NEW
   - Sends best parlay from each sport
   - Ensures variety in bet types and line amounts

## 🎯 Example Messages

### Hourly Parlays Message:
```
🎯 BEST PARLAYS (Each Sport) 🎯

🏀 NBA 🏀

1. 8-Leg Parlay
   Odds: +1247 | 🔥 78%
   Types: moneyline, spread, total, prop, alternate_spread, team_total
   💰 Payouts:
      $10 → $134.70 (+$124.70)
      $25 → $336.75 (+$311.75)
      $50 → $673.50 (+$623.50)
   Legs:
      1. Lakers -1.5 (alternate_spread) -110
         Warriors @ Lakers
      2. Over 225.5 (alternate_total) -110
         Warriors @ Lakers
      3. LeBron James Over 27.5 (prop) -110
         Warriors @ Lakers
      4. Lakers Team Total Over 112.5 (team_total) -110
         Warriors @ Lakers
      5. ... +3 more legs

🏈 NFL 🏈

1. 6-Leg Parlay
   Odds: +856 | 🟢 72%
   Types: moneyline, spread, prop, quarter
   💰 Payouts:
      $10 → $95.60 (+$85.60)
      $25 → $239.00 (+$214.00)
      $50 → $478.00 (+$428.00)
   Legs:
      1. Chiefs (moneyline) -150
         Chiefs @ Bills
      2. Chiefs Q1 Moneyline (quarter) -110
         Chiefs @ Bills
      3. Mahomes Over 275.5 Pass Yds (prop) -110
         Chiefs @ Bills
      ... +3 more legs
```

## ⚙️ Configuration

### Environment Variables

```bash
# Parlay confidence threshold
PARLAYS_MIN_CONFIDENCE=0.5  # Minimum combined confidence (0-1)

# Number of parlays per sport
PARLAYS_MAX_PER_SPORT=1  # Maximum parlays to send per sport

# Sports to include
PICKS_SPORTS=NBA,NFL,MLB,NHL,UFC,BOXING  # Or customize
```

## 🎲 Parlay Variety

Each hourly parlay ensures:

### Variety in Leg Counts:
- Small: 2-4 legs
- Medium: 5-8 legs
- Large: 9-15 legs

### Variety in Bet Types:
- Main bets: Moneylines, Spreads, Totals
- Alternate lines: Alternate Spreads, Alternate Totals
- Team totals: Individual team scoring
- Player props: Points, Yards, Stats, etc.
- Period bets: Quarters, Halves, Periods, Innings

### Variety in Line Amounts:
- Alternate spreads: -1.5, -3.5, -7.5, -14.5, etc.
- Alternate totals: Over/Under 210.5, 220.5, 230.5, etc.
- Team totals: Various team scoring lines
- Period totals: Quarter/half/period totals

## 🚀 How It Works

1. **Generates parlays for each sport** separately
2. **Ensures diversity** in bet types and leg counts
3. **Filters by confidence** (minimum threshold)
4. **Selects best parlay** from each sport
5. **Sends via SMS** every hour at :30

## 📊 Quality Scoring

Parlays are scored based on:
- Combined confidence
- Number of bet types (variety bonus)
- Number of different games (diversification)
- Expected value

## 💡 Tips

- **Higher confidence threshold** = fewer but higher quality parlays
- **More parlays per sport** = more options but longer messages
- **All sports included** = comprehensive coverage

## 🔧 Troubleshooting

### No Parlays Generated
- Check that games are scheduled
- Lower `PARLAYS_MIN_CONFIDENCE` if needed
- Verify odds are being fetched

### Too Many/Few Parlays
- Adjust `PARLAYS_MAX_PER_SPORT`
- Adjust `PARLAYS_MIN_CONFIDENCE`

### Long Messages
- Reduce `PARLAYS_MAX_PER_SPORT`
- System automatically splits long messages

## 📱 Next Steps

1. Set up your environment variables
2. Start the scheduler: `python enhanced_scheduler.py`
3. Receive best parlays from each sport every hour! 🎯

The system is now fully automated and will send you the best diverse parlays from each sport every hour! 🚀

