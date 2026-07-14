"""Public read-only Kalshi market-data adapter (no trading / no auth required)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from ..http.retry import retry_http
from ..logging_config import get_logger
from ..models import AmericanOdds, Market, MarketType, Sport, VenueType
from ..providers.kalshi_manual import cents_to_american
from ..providers.matcher import attach_canonical_ids, canonical_event_key, canonical_outcome_key, normalize_name

logger = get_logger(__name__)

DEFAULT_KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Kalshi multigame titles often omit "soccer"/"world cup" — match soccer-ish content instead.
SOCCER_SIGNAL_TERMS: tuple[str, ...] = (
    "world cup",
    "soccer",
    "football",
    "fifa",
    "advances",
    "goal",
    "corner",
    "reg time",
    "1h goal",
    "france",
    "spain",
    "england",
    "argentina",
    "brazil",
    "germany",
    "portugal",
    "mbappe",
    "messi",
    "yamal",
    "kane",
    "alvarez",
    "olise",
    "tchouameni",
    "oyarzabal",
)

SOCCER_EVENT_HINTS: tuple[str, ...] = (
    "sport",
    "soccer",
    "fifa",
    "worldcup",
    "wc26",
)


class KalshiClient:
    def __init__(self, base_url: str = DEFAULT_KALSHI_BASE) -> None:
        self.base_url = base_url.rstrip("/")

    @retry_http()
    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode(params or {})
        url = f"{self.base_url}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{query}"
        logger.debug("Kalshi GET %s", path)
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "headcrack-ai/1.0"})
        with urllib.request.urlopen(req, timeout=25) as response:  # nosec B310
            return json.loads(response.read().decode("utf-8"))

    def list_markets(
        self,
        *,
        status: str = "open",
        limit: int = 200,
        series_ticker: str | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"status": status, "limit": limit}
        if series_ticker:
            params["series_ticker"] = series_ticker
        if cursor:
            params["cursor"] = cursor
        return self._get_json("markets", params)

    def search_soccer_markets(self, query_terms: list[str] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Pull open markets and filter to soccer / World Cup-ish contracts."""
        terms = [t.lower() for t in (query_terms or list(SOCCER_SIGNAL_TERMS))]
        markets: list[dict[str, Any]] = []
        cursor = None
        pages = 0
        while pages < 15 and len(markets) < limit:
            payload = self.list_markets(status="open", limit=200, cursor=cursor)
            for market in payload.get("markets", []):
                if _yes_price_cents(market) is None:
                    continue
                title = (market.get("title") or market.get("subtitle") or "").lower()
                event = (market.get("event_ticker") or "").lower()
                blob = f"{title} {event}"
                if any(term in blob for term in terms):
                    if not _looks_like_soccer_contract(blob):
                        continue
                    markets.append(market)
                    if len(markets) >= limit:
                        break
                    continue
                if any(hint in event for hint in SOCCER_EVENT_HINTS) and any(
                    token in blob
                    for token in ("advances", "goal", "corner", "france", "spain", "england", "argentina")
                ):
                    markets.append(market)
                    if len(markets) >= limit:
                        break
            cursor = payload.get("cursor")
            pages += 1
            if not cursor:
                break
        return markets


def _looks_like_soccer_contract(blob: str) -> bool:
    soccer_markers = (
        "advances",
        "goal",
        "corner",
        "reg time",
        "both teams to score",
        "france",
        "spain",
        "england",
        "argentina",
        "brazil",
        "germany",
        "portugal",
        "mbappe",
        "messi",
        "yamal",
        "kane",
    )
    return any(marker in blob for marker in soccer_markers)


def _parse_dollar_price(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    # API returns 0-1 probabilities as dollar strings.
    if value <= 1:
        return value * 100.0
    if value < 100:
        return value
    return None


def _dollar_probability(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    if value <= 1:
        return value
    if value < 100:
        return value / 100.0
    return None


def _yes_price_cents(row: dict[str, Any]) -> float | None:
    for key in (
        "yes_ask_dollars",
        "yes_bid_dollars",
        "last_price_dollars",
        "yes_ask",
        "yes_bid",
        "last_price",
        "yes_price",
    ):
        cents = _parse_dollar_price(row.get(key))
        if cents is not None:
            return cents
    return None


def _infer_market_type(title: str) -> MarketType:
    lower = title.lower()
    if "win" in lower or "beat" in lower or "winner" in lower:
        return MarketType.MONEYLINE
    if "draw" in lower:
        return MarketType.MONEYLINE
    if "over" in lower or "under" in lower or "goals" in lower:
        return MarketType.TOTAL_GOALS
    return MarketType.CUSTOM


def _infer_team(title: str, yes_subtitle: str | None = None) -> str | None:
    text = f"{title} {yes_subtitle or ''}"
    if yes_subtitle:
        clean = yes_subtitle.strip()
        if clean and clean.lower() not in {"yes", "no"}:
            return clean
    # Heuristic: first capitalized run that looks like a country/club is not reliable.
    # Prefer substring match against known aliases when present in the title.
    for alias in ("france", "spain", "england", "argentina", "brazil", "germany", "portugal"):
        if alias in text.lower():
            return alias.title() if alias != "usa" else "United States"
    return None


def normalize_kalshi_markets(
    rows: list[dict[str, Any]],
    sport: Sport = Sport.SOCCER,
) -> list[Market]:
    """Convert Kalshi API market objects into Headcrack Market rows (YES side)."""
    markets: list[Market] = []
    now = datetime.now(timezone.utc)
    for row in rows:
        ticker = str(row.get("ticker") or "")
        if not ticker:
            continue
        cents = _yes_price_cents(row)
        if cents is None:
            continue
        try:
            american = cents_to_american(cents)
        except ValueError:
            continue
        title = str(row.get("title") or row.get("subtitle") or ticker)
        event_ticker = str(row.get("event_ticker") or ticker)
        team = _infer_team(title, row.get("yes_sub_title"))
        market_type = _infer_market_type(title)
        home = team
        away = None
        # Try "A vs B" / "A vs. B" / "A v B"
        vs_match = None
        import re

        vs_match = re.search(r"(.+?)\s+v(?:s\.?|ersus)?\s+(.+)", title, flags=re.IGNORECASE)
        if vs_match:
            home = vs_match.group(1).strip()
            away = vs_match.group(2).strip().split("?")[0].strip()
        yes_bid = row.get("yes_bid_dollars", row.get("yes_bid"))
        yes_ask = row.get("yes_ask_dollars", row.get("yes_ask"))
        volume = (
            row.get("volume_fp")
            or row.get("volume_24h_fp")
            or row.get("volume")
            or row.get("volume_24h")
            or row.get("open_interest_fp")
            or row.get("open_interest")
        )
        liquidity = row.get("liquidity_dollars") or row.get("liquidity")
        market = Market(
            market_id=f"kalshi:{ticker}:yes",
            sport=sport,
            event_id=event_ticker,
            label=f"Kalshi YES — {title}",
            market_type=market_type,
            sportsbook="kalshi",
            odds=AmericanOdds(american),
            team=team or home,
            opponent=away,
            player=None,
            threshold=None,
            metadata={
                "source": "kalshi_public",
                "home_team": home,
                "away_team": away,
                "league": "Prediction markets",
                "outcome_name": "yes",
                "ticker": ticker,
                "raw": {
                    "yes_bid": yes_bid,
                    "yes_ask": yes_ask,
                    "volume": volume,
                },
            },
            venue_type=VenueType.PREDICTION_MARKET,
            canonical_event_id=canonical_event_key(home, away, "prediction"),
            canonical_outcome_id=canonical_outcome_key(
                market_type, team=team or home, outcome="yes"
            ),
            quoted_at=now,
            bid=_dollar_probability(yes_bid),
            ask=_dollar_probability(yes_ask),
            liquidity=_dollar_probability(liquidity) or (
                float(liquidity) if isinstance(liquidity, (int, float)) else None
            ),
            source_url=f"https://kalshi.com/markets/{normalize_name(event_ticker)}",
        )
        markets.append(attach_canonical_ids(market))
    return markets


def fetch_kalshi_soccer_markets(limit: int = 80, client: KalshiClient | None = None) -> list[Market]:
    api = client or KalshiClient()
    try:
        rows = api.search_soccer_markets(limit=limit)
    except Exception:
        logger.exception("Kalshi public market fetch failed")
        return []
    return normalize_kalshi_markets(rows)
