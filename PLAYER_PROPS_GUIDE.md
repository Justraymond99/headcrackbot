# Player Props Integration Guide

## 🏀 Player Props Now Included!

The hourly picks system now fully supports player props including:
- **Points, Rebounds, Assists** (NBA/NBA)
- **Passing/Rushing/Receiving Yards** (NFL)
- **Home Runs, Hits, Strikeouts** (MLB)
- **Goals, Assists** (NHL)
- **Over/Under** props for all stats
- **Yes/No** props (e.g., Anytime TD, First Basket)

## 📱 Message Format

Player props are formatted specially in SMS messages:

### Example Player Prop Message:
```
🏀 HOURLY PICKS 🏀

1. NBA: LeBron James Pts
   Over 25.5
   Lakers @ Warriors (8:00 PM)
   -110 | 🔥 78% | EV: +6.2%

2. NFL: Patrick Mahomes Pass Yds
   Over 285.5
   Chiefs @ Bills (1:00 PM)
   -115 | 🟢 68% | EV: +5.1%

3. NBA: Steph Curry 3PM
   Over 4.5
   Lakers @ Warriors (8:00 PM)
   +120 | 🟡 65% | EV: +4.8%
```

## 🎯 Supported Prop Types

### NBA Props:
- Points (`player_points`)
- Rebounds (`player_rebounds`)
- Assists (`player_assists`)
- Three Pointers Made (`player_threes`)
- Blocks (`player_blocks`)
- Steals (`player_steals`)
- Points + Rebounds (`player_points_rebounds`)
- Points + Assists (`player_points_assists`)
- Triple Double (`player_triple_double`)
- And many more...

### NFL Props:
- Passing Yards (`player_pass_yds`)
- Rushing Yards (`player_rush_yds`)
- Receiving Yards (`player_reception_yds`)
- Passing TDs (`player_pass_tds`)
- Rushing TDs (`player_rush_tds`)
- Anytime TD (`player_anytime_td`)
- Receptions (`player_receptions`)
- And more...

### MLB Props:
- Home Runs (`batter_home_runs`)
- Hits (`batter_hits`)
- RBIs (`batter_rbis`)
- Strikeouts (`pitcher_strikeouts`)
- And more...

### NHL Props:
- Goals (`player_goals`)
- Assists (`player_assists`)
- Points (`player_points`)
- Shots on Goal (`player_shots_on_goal`)
- And more...

## ⚙️ Configuration

Player props are automatically included in your picks. They use the same filtering criteria:

```env
# Minimum EV for props (can be lower than regular bets)
PICKS_MIN_EV=0.03  # Props often have lower EV thresholds

# Minimum confidence for props
PICKS_MIN_CONFIDENCE=0.55  # Props can use slightly lower confidence

# Preferred prop types (optional)
PICKS_PREFERRED_PROP_TYPES=player_points,player_pass_yds,player_assists
```

## 🎨 Features Available for Props

All advanced features work with player props:

1. **Bet Sizing** - Recommendations for prop bets
2. **Performance Tracking** - Track prop bet win rate separately
3. **Duplicate Prevention** - Won't send same prop twice
4. **Time Filtering** - Only props for games in your time window
5. **Line Shopping** - Best odds for props across books
6. **Validation** - Checks if props still have value
7. **Explanations** - Why this prop was selected

## 📊 Prop-Specific Features

### Prop Type Preferences

You can prioritize certain prop types:

```env
# Prefer points props over rebounds
PICKS_PREFERRED_PROP_TYPES=player_points,player_pass_yds,player_assists
```

### Prop Performance Tracking

Player props are tracked separately in performance summaries:

```
By Bet Type:
  moneyline: 62.5% (10-6)
  spread: 58.3% (7-5)
  prop: 65.0% (13-7)  ← Player props!
  total: 60.0% (6-4)
```

## 💡 Tips for Player Props

1. **Lower Thresholds**: Props can have slightly lower EV but still be valuable
2. **Diversification**: Props add great diversification to parlays
3. **Line Shopping**: Always check multiple books for prop odds
4. **Recent Form**: Props often depend on recent player performance
5. **Matchups**: Check head-to-head stats for player props

## 🔧 Integration Example

Player props are automatically included when you generate picks:

```python
from hourly_picks_enhanced import EnhancedHourlyPicksGenerator

generator = EnhancedHourlyPicksGenerator()
picks = generator.generate_hourly_picks(
    max_picks=10,
    min_ev=0.03,  # Lower for props
    min_confidence=0.55  # Lower for props
)

# Picks will include both regular bets AND player props!
for pick in picks:
    if pick.get("bet_type") == "prop":
        print(f"Prop: {pick['player_name']} {pick['prop_type']} {pick['selection']}")
    else:
        print(f"Regular: {pick['selection']}")
```

## 📝 Message Examples

### Player Prop Pick:
```
1. NBA: Jayson Tatum Pts
   Over 28.5
   Celtics @ Heat (7:30 PM)
   -110 | 🔥 80% | EV: +7.5%
   💰 Recommended: $30.00 (3.0% of bankroll)
   💡 Strong positive EV: +7.5% | High confidence model prediction
```

### Mixed Picks (Regular + Props):
```
🏀 HOURLY PICKS 🏀

1. NBA: Lakers
   Warriors @ Lakers (8:00 PM)
   MONEYLINE | +150 | 🔥 75% | EV: +6.0%

2. NBA: LeBron James Pts
   Over 27.5
   Warriors @ Lakers (8:00 PM)
   -115 | 🟢 70% | EV: +5.5%

3. NBA: Warriors -3.5
   Warriors @ Lakers (8:00 PM)
   SPREAD | -110 | 🟢 68% | EV: +4.2%
```

## 🚀 Next Steps

1. **Enable Props**: Make sure `fetch_player_props=True` in data intake
2. **Adjust Thresholds**: Lower EV/confidence for props if needed
3. **Monitor Performance**: Track prop win rate separately
4. **Use in Parlays**: Mix props with regular bets for better parlays

Player props are now fully integrated and will appear in your hourly picks! 🎉

