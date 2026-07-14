"""Market data provider adapters.

Adapters should respect provider terms and only use official/allowed APIs or manual exports.

Sportsbooks and prediction markets are different venues:
- odds_api: live sportsbook prices
- kalshi / polymarket: public prediction-market prices (read-only; no order execution)
- kalshi_manual: CSV/offline fallback
- matcher: deterministic sportsbook ↔ prediction-market linking
"""

from .kalshi import KalshiClient, fetch_kalshi_soccer_markets, normalize_kalshi_markets
from .kalshi_manual import cents_to_american, load_kalshi_csv, normalize_kalshi_rows
from .matcher import attach_canonical_ids, match_prediction_to_books, normalize_name
from .odds_api import OddsApiClient, normalize_odds_api_events
from .polymarket import PolymarketClient, fetch_polymarket_soccer_markets, normalize_polymarket_events

__all__ = [
    "KalshiClient",
    "OddsApiClient",
    "PolymarketClient",
    "attach_canonical_ids",
    "cents_to_american",
    "fetch_kalshi_soccer_markets",
    "fetch_polymarket_soccer_markets",
    "load_kalshi_csv",
    "match_prediction_to_books",
    "normalize_kalshi_markets",
    "normalize_kalshi_rows",
    "normalize_name",
    "normalize_odds_api_events",
    "normalize_polymarket_events",
]
