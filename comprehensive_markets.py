"""Comprehensive market definitions for all sports and betting options."""
from typing import Dict, List

# Get all markets for each sport type
def get_all_markets_for_sport(sport: str) -> str:
    """
    Get comprehensive list of markets for a specific sport.
    
    Args:
        sport: Sport abbreviation (NBA, NFL, MLB, NHL, UFC, BOXING)
    
    Returns:
        Comma-separated string of all available markets
    """
    base_markets = "h2h,spreads,totals,alternate_spreads,alternate_totals,team_totals,alternate_team_totals"
    
    if sport in ["NBA", "NCAAB", "WNBA"]:
        # Basketball - quarters
        quarter_markets = "h2h_q1,h2h_q2,h2h_q3,h2h_q4,spreads_q1,spreads_q2,spreads_q3,spreads_q4,totals_q1,totals_q2,totals_q3,totals_q4"
        return f"{base_markets},{quarter_markets},h2h_h1,h2h_h2,spreads_h1,spreads_h2,totals_h1,totals_h2"
    
    elif sport in ["NFL", "NCAAF", "CFL"]:
        # Football - quarters and halves
        quarter_markets = "h2h_q1,h2h_q2,h2h_q3,h2h_q4,spreads_q1,spreads_q2,spreads_q3,spreads_q4,totals_q1,totals_q2,totals_q3,totals_q4"
        return f"{base_markets},{quarter_markets},h2h_h1,h2h_h2,spreads_h1,spreads_h2,totals_h1,totals_h2,h2h_3_way"
    
    elif sport in ["MLB"]:
        # Baseball - innings
        innings_markets = "h2h_1st_5_innings,spreads_1st_5_innings,totals_1st_5_innings,h2h_1st_3_innings,spreads_1st_3_innings,totals_1st_3_innings"
        return f"{base_markets},{innings_markets}"
    
    elif sport in ["NHL"]:
        # Hockey - periods
        period_markets = "h2h_p1,h2h_p2,h2h_p3,spreads_p1,spreads_p2,spreads_p3,totals_p1,totals_p2,totals_p3"
        return f"{base_markets},{period_markets},h2h_3_way"
    
    elif sport in ["UFC"]:
        # UFC - method, rounds, props
        ufc_markets = "h2h,h2h_3_way"  # Moneyline, Draw, Method of Victory, Round Props, etc.
        return ufc_markets
    
    elif sport in ["BOXING"]:
        # Boxing - similar to UFC
        boxing_markets = "h2h,h2h_3_way"  # Moneyline, Draw, Method, Round Props
        return boxing_markets
    
    else:
        # Default - basic markets
        return base_markets


def get_all_player_props_for_sport(sport: str) -> List[str]:
    """
    Get all player prop markets for a specific sport.
    
    Args:
        sport: Sport abbreviation
    
    Returns:
        List of player prop market keys
    """
    from market_definitions import SPORT_PLAYER_PROPS
    
    return SPORT_PLAYER_PROPS.get(sport.upper(), [])


def get_comprehensive_markets_string(sport: str, include_player_props: bool = True) -> str:
    """
    Get comprehensive markets string including all betting options.
    
    Args:
        sport: Sport abbreviation
        include_player_props: Whether to include player props
    
    Returns:
        Comma-separated string of all markets
    """
    main_markets = get_all_markets_for_sport(sport)
    
    if include_player_props and sport not in ["UFC", "BOXING"]:
        player_props = get_all_player_props_for_sport(sport)
        if player_props:
            # The Odds API might have limits, so we'll fetch props via event-specific calls
            # For now, return main markets - props will be fetched per-event
            return main_markets
    
    return main_markets


# Market priorities (most important first for limited API calls)
MARKET_PRIORITIES = {
    "NBA": [
        "h2h", "spreads", "totals", "team_totals",
        "alternate_spreads", "alternate_totals",
        "h2h_q1", "spreads_q1", "totals_q1",
        "h2h_h1", "spreads_h1", "totals_h1"
    ],
    "NFL": [
        "h2h", "spreads", "totals", "team_totals",
        "alternate_spreads", "alternate_totals",
        "h2h_q1", "spreads_q1", "totals_q1",
        "h2h_h1", "spreads_h1", "totals_h1",
        "h2h_3_way"
    ],
    "MLB": [
        "h2h", "spreads", "totals", "team_totals",
        "h2h_1st_5_innings", "spreads_1st_5_innings", "totals_1st_5_innings",
        "alternate_totals"
    ],
    "NHL": [
        "h2h", "spreads", "totals", "team_totals",
        "h2h_p1", "spreads_p1", "totals_p1",
        "h2h_3_way"
    ],
    "UFC": [
        "h2h", "h2h_3_way"
    ],
    "BOXING": [
        "h2h", "h2h_3_way"
    ]
}


def get_priority_markets(sport: str, max_markets: int = 10) -> str:
    """
    Get priority markets for a sport (useful when API has limits).
    
    Args:
        sport: Sport abbreviation
        max_markets: Maximum number of markets to include
    
    Returns:
        Comma-separated string of priority markets
    """
    priorities = MARKET_PRIORITIES.get(sport.upper(), ["h2h", "spreads", "totals"])
    return ",".join(priorities[:max_markets])

