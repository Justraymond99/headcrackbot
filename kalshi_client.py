"""Kalshi prediction market API client for fetching events, markets, and prices."""
import requests
import logging
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Kalshi public API base URL (no auth needed for market data)
KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Event categories on Kalshi
KALSHI_CATEGORIES = [
    "Economics",
    "Politics",
    "Climate and Weather",
    "Financials",
    "Tech & Science",
    "Culture",
    "Crypto",
    "Sports",
    "Companies",
    "Transportation",
    "Health",
    "Legal",
    "Energy",
]


class KalshiClient:
    """Client for the Kalshi prediction market REST API.

    All market-data endpoints are public and require no authentication.
    Prices are in cents (1-99) representing the market's implied probability.
    """

    def __init__(self, base_url: str = KALSHI_API_BASE, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "HeadCrackBot/1.0",
        })
        # Simple rate-limit tracking
        self._last_request_time = 0
        self._min_interval = 0.2  # 200ms between requests

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _throttle(self):
        """Simple throttle to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to the Kalshi API with retry logic."""
        url = f"{self.base_url}{path}"
        for attempt in range(3):
            try:
                self._throttle()
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    wait = (attempt + 1) * 2
                    logger.warning(f"Kalshi rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"Kalshi API HTTP error: {e} (status {response.status_code})")
                return {}
            except requests.exceptions.RequestException as e:
                logger.error(f"Kalshi API request error (attempt {attempt+1}): {e}")
                if attempt < 2:
                    time.sleep((attempt + 1) * 1)
                    continue
                return {}
        return {}

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def get_events(
        self,
        status: str = "open",
        series_ticker: Optional[str] = None,
        with_nested_markets: bool = True,
        limit: int = 200,
        max_pages: int = 10,
    ) -> List[Dict]:
        """Fetch events from Kalshi, paginating automatically.

        Args:
            status: Filter by status (open, closed, settled).
            series_ticker: Filter by series.
            with_nested_markets: Include market objects inside events.
            limit: Page size (max 200).
            max_pages: Safety cap on pagination.

        Returns:
            List of event dicts.
        """
        all_events: List[Dict] = []
        cursor: Optional[str] = None

        for page in range(max_pages):
            params: Dict = {"limit": limit, "status": status}
            if with_nested_markets:
                params["with_nested_markets"] = "true"
            if series_ticker:
                params["series_ticker"] = series_ticker
            if cursor:
                params["cursor"] = cursor

            data = self._get("/events", params=params)
            events = data.get("events", [])
            if not events:
                break

            all_events.extend(events)
            cursor = data.get("cursor", "")
            if not cursor:
                break

            logger.debug(f"Kalshi events page {page+1}: {len(events)} events (total {len(all_events)})")

        logger.info(f"Fetched {len(all_events)} Kalshi events (status={status})")
        return all_events

    def get_event(self, event_ticker: str) -> Dict:
        """Fetch a single event by ticker."""
        data = self._get(f"/events/{event_ticker}")
        return data.get("event", {})

    # ------------------------------------------------------------------
    # Markets
    # ------------------------------------------------------------------

    def get_markets(
        self,
        event_ticker: Optional[str] = None,
        series_ticker: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        status: str = "open",
        limit: int = 200,
        max_pages: int = 10,
    ) -> List[Dict]:
        """Fetch markets with optional filters.

        Args:
            event_ticker: Filter by parent event ticker.
            series_ticker: Filter by series ticker.
            tickers: Specific market tickers to retrieve.
            status: Market status filter.
            limit: Page size.
            max_pages: Safety cap.

        Returns:
            List of market dicts.
        """
        all_markets: List[Dict] = []
        cursor: Optional[str] = None

        for page in range(max_pages):
            params: Dict = {"limit": limit, "status": status}
            if event_ticker:
                params["event_ticker"] = event_ticker
            if series_ticker:
                params["series_ticker"] = series_ticker
            if tickers:
                params["tickers"] = ",".join(tickers)
            if cursor:
                params["cursor"] = cursor

            data = self._get("/markets", params=params)
            markets = data.get("markets", [])
            if not markets:
                break

            all_markets.extend(markets)
            cursor = data.get("cursor", "")
            if not cursor:
                break

        logger.info(f"Fetched {len(all_markets)} Kalshi markets")
        return all_markets

    def get_market(self, ticker: str) -> Dict:
        """Fetch a single market by ticker."""
        data = self._get(f"/markets/{ticker}")
        return data.get("market", {})

    def get_market_orderbook(self, ticker: str) -> Dict:
        """Fetch the order book for a market.

        Returns dict with 'yes' and 'no' arrays of [price, quantity] pairs.
        """
        data = self._get(f"/markets/{ticker}/orderbook")
        return data.get("orderbook", {})

    # ------------------------------------------------------------------
    # Series
    # ------------------------------------------------------------------

    def get_series(self, series_ticker: str) -> Dict:
        """Fetch series info."""
        data = self._get(f"/series/{series_ticker}")
        return data.get("series", {})

    # ------------------------------------------------------------------
    # Trades (public)
    # ------------------------------------------------------------------

    def get_trades(
        self,
        ticker: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Fetch recent public trades, optionally filtered by market ticker."""
        params: Dict = {"limit": limit}
        if ticker:
            params["ticker"] = ticker
        data = self._get("/markets/trades", params=params)
        return data.get("trades", [])

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def get_open_events_by_category(self) -> Dict[str, List[Dict]]:
        """Fetch all open events grouped by category.

        Returns:
            Dict mapping category name -> list of events.
        """
        events = self.get_events(status="open", with_nested_markets=True)
        by_category: Dict[str, List[Dict]] = {}
        for event in events:
            cat = event.get("category", "Other")
            by_category.setdefault(cat, []).append(event)

        for cat, evts in by_category.items():
            logger.info(f"  Kalshi category '{cat}': {len(evts)} events")
        return by_category

    def get_high_volume_markets(
        self,
        min_volume: int = 1000,
        status: str = "open",
    ) -> List[Dict]:
        """Return open markets with volume above a threshold, sorted by volume desc."""
        markets = self.get_markets(status=status)
        filtered = [m for m in markets if (m.get("volume", 0) or 0) >= min_volume]
        filtered.sort(key=lambda m: m.get("volume", 0) or 0, reverse=True)
        logger.info(f"Found {len(filtered)} high-volume Kalshi markets (>= {min_volume})")
        return filtered

    def get_closing_soon_markets(
        self,
        hours_until_close: int = 24,
        status: str = "open",
    ) -> List[Dict]:
        """Return open markets that close within the given hours."""
        markets = self.get_markets(status=status)
        cutoff = datetime.utcnow() + timedelta(hours=hours_until_close)
        closing_soon = []
        for m in markets:
            close_time_str = m.get("close_time") or m.get("expiration_time", "")
            if not close_time_str:
                continue
            try:
                close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00")).replace(tzinfo=None)
                if close_time <= cutoff:
                    m["_close_time_parsed"] = close_time
                    closing_soon.append(m)
            except (ValueError, TypeError):
                continue

        closing_soon.sort(key=lambda m: m.get("_close_time_parsed", cutoff))
        logger.info(f"Found {len(closing_soon)} Kalshi markets closing within {hours_until_close}h")
        return closing_soon

    @staticmethod
    def cents_to_probability(price_cents: int) -> float:
        """Convert Kalshi price (1-99 cents) to probability (0.01-0.99)."""
        return max(0.01, min(0.99, price_cents / 100.0))

    @staticmethod
    def probability_to_american_odds(prob: float) -> float:
        """Convert probability to American odds for compatibility with the rest of the system."""
        if prob <= 0 or prob >= 1:
            return 0
        if prob >= 0.5:
            return -100 * prob / (1 - prob)
        else:
            return 100 * (1 - prob) / prob

    @staticmethod
    def market_spread(market: Dict) -> Optional[float]:
        """Calculate the bid-ask spread for a market.

        Uses the dollar-denominated fields (preferred per Kalshi API changelog).
        Falls back to cents fields if dollar fields aren't present.
        """
        yes_bid = market.get("yes_bid_dollars") or market.get("yes_bid")
        yes_ask = market.get("yes_ask_dollars") or market.get("yes_ask")
        if yes_bid is not None and yes_ask is not None:
            try:
                return float(yes_ask) - float(yes_bid)
            except (ValueError, TypeError):
                return None
        return None
