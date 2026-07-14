"""Betting research and edge-finding tools."""

from .arbitrage import find_arbitrage_opportunities, find_prediction_arbs
from .betting_assistant import BettingAssistant
from .dfs_optimizer import build_dfs_entries, format_dfs_slip
from .ev_finder import find_positive_ev, format_ev_row
from .odds_screen import build_odds_screen, format_odds_screen_rows
from .projections import build_match_projections
from .whale_watch import detect_whale_activity, format_whale_row

__all__ = [
    "BettingAssistant",
    "build_dfs_entries",
    "build_match_projections",
    "build_odds_screen",
    "detect_whale_activity",
    "find_arbitrage_opportunities",
    "find_positive_ev",
    "find_prediction_arbs",
    "format_dfs_slip",
    "format_ev_row",
    "format_odds_screen_rows",
    "format_whale_row",
]
