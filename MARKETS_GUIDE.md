# Betting Markets Guide

This system now supports all betting markets from The Odds API, including player props for all major sports.

## Featured Markets

- **h2h** - Head to Head / Moneyline
- **spreads** - Points Spread / Handicap  
- **totals** - Total Points/Goals / Over/Under
- **outrights** - Outrights / Futures

## Additional Markets

- **alternate_spreads** - Alternate Spreads
- **alternate_totals** - Alternate Totals
- **btts** - Both Teams to Score (Soccer)
- **draw_no_bet** - Draw No Bet (Soccer)
- **h2h_3_way** - Head to Head 3 Way
- **team_totals** - Team Totals
- **alternate_team_totals** - Alternate Team Totals

## Game Period Markets

### Quarters (Basketball, Football)
- h2h_q1, h2h_q2, h2h_q3, h2h_q4
- spreads_q1, spreads_q2, spreads_q3, spreads_q4
- totals_q1, totals_q2, totals_q3, totals_q4

### Halves
- h2h_h1, h2h_h2
- spreads_h1, spreads_h2
- totals_h1, totals_h2

### Periods (Hockey)
- h2h_p1, h2h_p2, h2h_p3
- spreads_p1, spreads_p2, spreads_p3
- totals_p1, totals_p2, totals_p3

### Innings (Baseball)
- h2h_1st_1_innings, h2h_1st_3_innings, h2h_1st_5_innings, h2h_1st_7_innings
- spreads_1st_1_innings, etc.
- totals_1st_1_innings, etc.

## Player Props by Sport

### NFL/NCAAF/CFL
- **Passing**: player_pass_yds, player_pass_tds, player_pass_attempts, player_pass_completions
- **Rushing**: player_rush_yds, player_rush_tds, player_rush_attempts
- **Receiving**: player_reception_yds, player_reception_tds, player_receptions
- **Touchdowns**: player_anytime_td, player_1st_td, player_last_td
- **Defense**: player_sacks, player_solo_tackles, player_tackles_assists
- **Kicking**: player_field_goals, player_kicking_points

### NBA/NCAAB/WNBA
- **Scoring**: player_points, player_points_q1
- **Rebounding**: player_rebounds, player_rebounds_q1
- **Assists**: player_assists, player_assists_q1
- **Defense**: player_blocks, player_steals, player_blocks_steals
- **Shooting**: player_threes, player_field_goals, player_frees_made
- **Combined**: player_points_rebounds_assists, player_points_rebounds, player_points_assists
- **Special**: player_first_basket, player_double_double, player_triple_double

### MLB
- **Batter**: batter_home_runs, batter_hits, batter_rbis, batter_runs_scored, batter_total_bases
- **Pitcher**: pitcher_strikeouts, pitcher_hits_allowed, pitcher_walks, pitcher_earned_runs
- **Special**: batter_first_home_run, pitcher_record_a_win

### NHL
- **Scoring**: player_goals, player_assists, player_points
- **Shooting**: player_shots_on_goal, player_blocked_shots
- **Special**: player_goal_scorer_anytime, player_goal_scorer_first, player_goal_scorer_last
- **Goalie**: player_total_saves

### Soccer
- **Scoring**: player_goal_scorer_anytime, player_first_goal_scorer, player_last_goal_scorer
- **Shooting**: player_shots_on_target, player_shots
- **Cards**: player_to_receive_card, player_to_receive_red_card
- **Assists**: player_assists

## Usage

The system automatically:
1. Fetches all available markets when you call `fetch_all_data()`
2. Stores player props in the database
3. Analyzes all markets when generating parlays
4. Includes player props in parlay recommendations

## Example

```python
from data_intake import DataIntake

intake = DataIntake()
# Fetch data including player props
intake.fetch_all_data(["NBA", "NFL"], fetch_player_props=True)

# Generate parlays - will include player props automatically
from research_engine import ResearchEngine
engine = ResearchEngine()
parlays = engine.generate_parlays(games, max_parlays=10)
```

## Notes

- Player props require individual event API calls (uses `/events/{eventId}/odds` endpoint)
- Yes/No props (e.g., anytime TD scorer) are stored separately from Over/Under props
- All markets are analyzed for expected value and confidence
- The system supports alternate lines and period-specific markets

