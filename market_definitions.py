"""Betting market definitions and mappings for The Odds API."""

# Featured Markets
FEATURED_MARKETS = {
    "h2h": "Head to Head / Moneyline",
    "spreads": "Points Spread / Handicap",
    "totals": "Total Points/Goals / Over/Under",
    "outrights": "Outrights / Futures",
}

# Additional Markets
ADDITIONAL_MARKETS = {
    "alternate_spreads": "Alternate Spreads",
    "alternate_totals": "Alternate Totals",
    "btts": "Both Teams to Score",
    "draw_no_bet": "Draw No Bet",
    "h2h_3_way": "Head to Head 3 Way",
    "team_totals": "Team Totals",
    "alternate_team_totals": "Alternate Team Totals",
}

# Game Period Markets - Quarters
QUARTER_MARKETS = [
    "h2h_q1", "h2h_q2", "h2h_q3", "h2h_q4",
    "h2h_3_way_q1", "h2h_3_way_q2", "h2h_3_way_q3", "h2h_3_way_q4",
    "spreads_q1", "spreads_q2", "spreads_q3", "spreads_q4",
    "totals_q1", "totals_q2", "totals_q3", "totals_q4",
    "alternate_spreads_q1", "alternate_spreads_q2", "alternate_spreads_q3", "alternate_spreads_q4",
    "alternate_totals_q1", "alternate_totals_q2", "alternate_totals_q3", "alternate_totals_q4",
    "team_totals_q1", "team_totals_q2", "team_totals_q3", "team_totals_q4",
    "alternate_team_totals_q1", "alternate_team_totals_q2", "alternate_team_totals_q3", "alternate_team_totals_q4",
]

# Game Period Markets - Halves
HALF_MARKETS = [
    "h2h_h1", "h2h_h2",
    "h2h_3_way_h1", "h2h_3_way_h2",
    "spreads_h1", "spreads_h2",
    "totals_h1", "totals_h2",
    "alternate_spreads_h1", "alternate_spreads_h2",
    "alternate_totals_h1", "alternate_totals_h2",
    "team_totals_h1", "team_totals_h2",
    "alternate_team_totals_h1", "alternate_team_totals_h2",
]

# Game Period Markets - Periods (Hockey)
PERIOD_MARKETS = [
    "h2h_p1", "h2h_p2", "h2h_p3",
    "h2h_3_way_p1", "h2h_3_way_p2", "h2h_3_way_p3",
    "spreads_p1", "spreads_p2", "spreads_p3",
    "totals_p1", "totals_p2", "totals_p3",
    "alternate_spreads_p1", "alternate_spreads_p2", "alternate_spreads_p3",
    "alternate_totals_p1", "alternate_totals_p2", "alternate_totals_p3",
    "team_totals_p1", "team_totals_p2", "team_totals_p3",
    "alternate_team_totals_p1", "alternate_team_totals_p2", "alternate_team_totals_p3",
]

# Game Period Markets - Innings (Baseball)
INNINGS_MARKETS = [
    "h2h_1st_1_innings", "h2h_1st_3_innings", "h2h_1st_5_innings", "h2h_1st_7_innings",
    "h2h_3_way_1st_1_innings", "h2h_3_way_1st_3_innings", "h2h_3_way_1st_5_innings", "h2h_3_way_1st_7_innings",
    "spreads_1st_1_innings", "spreads_1st_3_innings", "spreads_1st_5_innings", "spreads_1st_7_innings",
    "totals_1st_1_innings", "totals_1st_3_innings", "totals_1st_5_innings", "totals_1st_7_innings",
    "alternate_spreads_1st_1_innings", "alternate_spreads_1st_3_innings", "alternate_spreads_1st_5_innings", "alternate_spreads_1st_7_innings",
    "alternate_totals_1st_1_innings", "alternate_totals_1st_3_innings", "alternate_totals_1st_5_innings", "alternate_totals_1st_7_innings",
]

# NFL/NCAAF/CFL Player Props
NFL_PLAYER_PROPS = [
    "player_assists", "player_defensive_interceptions", "player_field_goals", "player_kicking_points",
    "player_pass_attempts", "player_pass_completions", "player_pass_interceptions", "player_pass_longest_completion",
    "player_pass_rush_yds", "player_pass_rush_reception_tds", "player_pass_rush_reception_yds", "player_pass_tds",
    "player_pass_yds", "player_pass_yds_q1", "player_pats", "player_receptions", "player_reception_longest",
    "player_reception_tds", "player_reception_yds", "player_rush_attempts", "player_rush_longest",
    "player_rush_reception_tds", "player_rush_reception_yds", "player_rush_tds", "player_rush_yds",
    "player_sacks", "player_solo_tackles", "player_tackles_assists", "player_tds_over",
    "player_1st_td", "player_anytime_td", "player_last_td",
]

# NBA/NCAAB/WNBA Player Props
NBA_PLAYER_PROPS = [
    "player_points", "player_points_q1", "player_rebounds", "player_rebounds_q1",
    "player_assists", "player_assists_q1", "player_threes", "player_blocks", "player_steals",
    "player_blocks_steals", "player_turnovers", "player_points_rebounds_assists", "player_points_rebounds",
    "player_points_assists", "player_rebounds_assists", "player_field_goals", "player_frees_made",
    "player_frees_attempts", "player_first_basket", "player_first_team_basket", "player_double_double",
    "player_triple_double", "player_method_of_first_basket",
    # Alternate lines (ALT)
    "player_alt_points", "player_alt_rebounds", "player_alt_assists",
    "player_alt_points_rebounds", "player_alt_points_assists", "player_alt_rebounds_assists",
    "player_alt_points_rebounds_assists",
    # Score thresholds
    "player_to_score_10_plus", "player_to_score_15_plus", "player_to_score_20_plus",
    "player_to_score_25_plus", "player_to_score_30_plus",
]

# MLB Player Props
MLB_PLAYER_PROPS = [
    "batter_home_runs", "batter_first_home_run", "batter_hits", "batter_total_bases",
    "batter_rbis", "batter_runs_scored", "batter_hits_runs_rbis", "batter_singles",
    "batter_doubles", "batter_triples", "batter_walks", "batter_strikeouts", "batter_stolen_bases",
    "pitcher_strikeouts", "pitcher_record_a_win", "pitcher_hits_allowed", "pitcher_walks",
    "pitcher_earned_runs", "pitcher_outs",
]

# NHL Player Props
NHL_PLAYER_PROPS = [
    "player_points", "player_power_play_points", "player_assists", "player_blocked_shots",
    "player_shots_on_goal", "player_goals", "player_total_saves", "player_goal_scorer_first",
    "player_goal_scorer_last", "player_goal_scorer_anytime",
]

# Soccer Player Props
SOCCER_PLAYER_PROPS = [
    "player_goal_scorer_anytime", "player_first_goal_scorer", "player_last_goal_scorer",
    "player_to_receive_card", "player_to_receive_red_card", "player_shots_on_target",
    "player_shots", "player_assists",
]

# Soccer Additional Markets
SOCCER_MARKETS = [
    "alternate_spreads_corners", "alternate_totals_corners", "alternate_spreads_cards",
    "alternate_totals_cards", "double_chance",
]

# All player prop markets
ALL_PLAYER_PROPS = NFL_PLAYER_PROPS + NBA_PLAYER_PROPS + MLB_PLAYER_PROPS + NHL_PLAYER_PROPS + SOCCER_PLAYER_PROPS

# Sport-specific player props mapping
SPORT_PLAYER_PROPS = {
    "NFL": NFL_PLAYER_PROPS,
    "NCAAF": NFL_PLAYER_PROPS,
    "CFL": NFL_PLAYER_PROPS,
    "NBA": NBA_PLAYER_PROPS,
    "NCAAB": NBA_PLAYER_PROPS,
    "WNBA": NBA_PLAYER_PROPS,
    "MLB": MLB_PLAYER_PROPS,
    "NHL": NHL_PLAYER_PROPS,
    "soccer": SOCCER_PLAYER_PROPS,
    "EPL": SOCCER_PLAYER_PROPS,
    "La Liga": SOCCER_PLAYER_PROPS,
    "Serie A": SOCCER_PLAYER_PROPS,
    "Bundesliga": SOCCER_PLAYER_PROPS,
    "Ligue 1": SOCCER_PLAYER_PROPS,
    "MLS": SOCCER_PLAYER_PROPS,
}

# Market descriptions
MARKET_DESCRIPTIONS = {
    # Featured
    "h2h": "Head to Head / Moneyline",
    "spreads": "Points Spread / Handicap",
    "totals": "Total Points/Goals / Over/Under",
    
    # NFL Player Props
    "player_pass_yds": "Passing Yards",
    "player_rush_yds": "Rushing Yards",
    "player_reception_yds": "Receiving Yards",
    "player_pass_tds": "Passing Touchdowns",
    "player_rush_tds": "Rushing Touchdowns",
    "player_reception_tds": "Receiving Touchdowns",
    "player_anytime_td": "Anytime Touchdown Scorer",
    
    # NBA Player Props
    "player_points": "Points",
    "player_rebounds": "Rebounds",
    "player_assists": "Assists",
    "player_threes": "Three Pointers Made",
    "player_blocks": "Blocks",
    "player_steals": "Steals",
    "player_points_rebounds_assists": "Points + Rebounds + Assists",
    "player_points_rebounds": "Points + Rebounds",
    "player_points_assists": "Points + Assists",
    "player_rebounds_assists": "Rebounds + Assists",
    # Alternate lines
    "player_alt_points": "ALT POINTS",
    "player_alt_rebounds": "ALT REBOUNDS",
    "player_alt_assists": "ALT ASSISTS",
    "player_alt_points_rebounds": "ALT PTS + REB",
    "player_alt_points_assists": "ALT PTS + AST",
    "player_alt_rebounds_assists": "ALT REB + AST",
    "player_alt_points_rebounds_assists": "ALT PTS + REB + AST",
    # Score thresholds
    "player_to_score_10_plus": "TO SCORE 10+ POINTS",
    "player_to_score_15_plus": "TO SCORE 15+ POINTS",
    "player_to_score_20_plus": "TO SCORE 20+ POINTS",
    "player_to_score_25_plus": "TO SCORE 25+ POINTS",
    "player_to_score_30_plus": "TO SCORE 30+ POINTS",
    
    # MLB Player Props
    "batter_home_runs": "Home Runs",
    "batter_hits": "Hits",
    "batter_rbis": "RBIs",
    "pitcher_strikeouts": "Strikeouts",
    
    # NHL Player Props
    "player_goals": "Goals",
    "player_assists": "Assists",
    "player_points": "Points",
    "player_shots_on_goal": "Shots on Goal",
    "player_goal_scorer_anytime": "Anytime Goal Scorer",
    
    # Soccer Player Props
    "player_goal_scorer_anytime": "Anytime Goal Scorer",
    "player_first_goal_scorer": "First Goal Scorer",
    "player_shots_on_target": "Shots on Target",
}

def get_market_description(market_key: str) -> str:
    """Get human-readable description for a market key."""
    return MARKET_DESCRIPTIONS.get(market_key, market_key.replace("_", " ").title())

def is_yes_no_prop(market_key: str) -> bool:
    """Check if a prop is a Yes/No type (e.g., anytime TD scorer)."""
    yes_no_markets = [
        "player_1st_td", "player_anytime_td", "player_last_td",
        "player_first_basket", "player_first_team_basket", "player_double_double",
        "player_triple_double", "batter_first_home_run", "pitcher_record_a_win",
        "player_goal_scorer_first", "player_goal_scorer_last", "player_goal_scorer_anytime",
        "player_to_receive_card", "player_to_receive_red_card", "player_first_goal_scorer",
        "player_last_goal_scorer",
        # Score thresholds are Yes/No props
        "player_to_score_10_plus", "player_to_score_15_plus", "player_to_score_20_plus",
        "player_to_score_25_plus", "player_to_score_30_plus",
    ]
    return market_key in yes_no_markets or "to_score" in market_key.lower()

def is_over_under_prop(market_key: str) -> bool:
    """Check if a prop is an Over/Under type."""
    return not is_yes_no_prop(market_key) and "player_" in market_key or "batter_" in market_key or "pitcher_" in market_key

