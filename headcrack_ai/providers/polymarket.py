"""Public read-only Polymarket adapter (Gamma discovery + public mid prices)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from ..http.retry import retry_http
from ..logging_config import get_logger
from ..models import AmericanOdds, Market, MarketType, Sport, VenueType
from ..probability import decimal_to_american
from ..providers.matcher import attach_canonical_ids, canonical_event_key, canonical_outcome_key, normalize_name

logger = get_logger(__name__)

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"


class PolymarketClient:
    def __init__(self, gamma_base: str = GAMMA_BASE, clob_base: str = CLOB_BASE) -> None:
        self.gamma_base = gamma_base.rstrip("/")
        self.clob_base = clob_base.rstrip("/")

    @retry_http()
    def _get_json(self, base: str, path: str, params: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode(params or {}, doseq=True)
        url = f"{base}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{query}"
        logger.debug("Polymarket GET %s", url)
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "headcrack-ai/1.0"})
        with urllib.request.urlopen(req, timeout=25) as response:  # nosec B310
            return json.loads(response.read().decode("utf-8"))

    def search_events(self, query: str = "world cup", limit: int = 25) -> list[dict[str, Any]]:
        # public-search returns mixed payloads; prefer /events with text filters when possible
        try:
            payload = self._get_json(
                self.gamma_base,
                "public-search",
                {"q": query, "limit_per_type": limit},
            )
            events = payload.get("events") or payload.get("results") or []
            if isinstance(events, list) and events:
                return events
        except Exception:
            logger.exception("Polymarket public-search failed; falling back to /events")
        events = self._get_json(
            self.gamma_base,
            "events",
            {"limit": limit, "active": "true", "closed": "false"},
        )
        if isinstance(events, list):
            q = query.lower()
            return [e for e in events if q in json.dumps(e).lower()][:limit]
        return []

    def list_sports_events(self, limit: int = 40) -> list[dict[str, Any]]:
        try:
            events = self._get_json(
                self.gamma_base,
                "events",
                {"limit": limit, "active": "true", "closed": "false", "tag_slug": "sports"},
            )
            return events if isinstance(events, list) else []
        except Exception:
            logger.exception("Polymarket sports events fetch failed")
            return []

    def get_midpoint(self, token_id: str) -> float | None:
        try:
            payload = self._get_json(self.clob_base, "midpoint", {"token_id": token_id})
            mid = payload.get("mid") if isinstance(payload, dict) else None
            return float(mid) if mid is not None else None
        except Exception:
            return None


def _probability_to_american(p: float) -> int:
    p = min(0.99, max(0.01, float(p)))
    decimal = 1.0 / p
    return decimal_to_american(decimal)


def _parse_outcomes(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            return [raw]
    return []


def _parse_prices(raw: Any) -> list[float]:
    if raw is None:
        return []
    if isinstance(raw, list):
        out = []
        for x in raw:
            try:
                out.append(float(x))
            except (TypeError, ValueError):
                continue
        return out
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return _parse_prices(parsed)
        except json.JSONDecodeError:
            return []
    return []


def _parse_token_ids(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            return [raw]
    return []


def normalize_polymarket_events(
    events: list[dict[str, Any]],
    sport: Sport = Sport.SOCCER,
) -> list[Market]:
    markets: list[Market] = []
    now = datetime.now(timezone.utc)
    for event in events:
        event_id = str(event.get("id") or event.get("slug") or "")
        event_title = str(event.get("title") or event.get("question") or event_id)
        for market_payload in event.get("markets") or [event]:
            question = str(market_payload.get("question") or market_payload.get("title") or event_title)
            outcomes = _parse_outcomes(market_payload.get("outcomes"))
            prices = _parse_prices(market_payload.get("outcomePrices"))
            tokens = _parse_token_ids(market_payload.get("clobTokenIds"))
            condition_id = str(market_payload.get("conditionId") or market_payload.get("id") or event_id)
            liquidity = market_payload.get("liquidityNum") or market_payload.get("liquidity")
            volume = market_payload.get("volumeNum") or market_payload.get("volume")
            home, away = _infer_event_sides(question)

            for idx, outcome in enumerate(outcomes or ["Yes"]):
                price = prices[idx] if idx < len(prices) else None
                if price is None or not (0 < float(price) < 1):
                    continue
                token = tokens[idx] if idx < len(tokens) else None
                american = _probability_to_american(float(price))
                binary_outcome = outcome.lower() in {"yes", "no"}
                team = None
                if binary_outcome and outcome.lower() == "yes":
                    team = home
                elif not binary_outcome:
                    team = outcome
                market_type = MarketType.MONEYLINE if team else MarketType.CUSTOM
                market = Market(
                    market_id=f"polymarket:{condition_id}:{idx}:{normalize_name(outcome)}",
                    sport=sport,
                    event_id=event_id or condition_id,
                    label=f"Polymarket — {question} · {outcome}",
                    market_type=market_type,
                    sportsbook="polymarket",
                    odds=AmericanOdds(american),
                    team=team,
                    opponent=away if team and home and normalize_name(team) == normalize_name(home) else home,
                    metadata={
                        "source": "polymarket_public",
                        "home_team": home,
                        "away_team": away,
                        "league": "Prediction markets",
                        "outcome_name": outcome,
                        "condition_id": condition_id,
                        "token_id": token,
                    },
                    venue_type=VenueType.PREDICTION_MARKET,
                    canonical_event_id=canonical_event_key(home, away, "prediction"),
                    canonical_outcome_id=canonical_outcome_key(
                        market_type,
                        team=team,
                        outcome=outcome,
                    ),
                    quoted_at=now,
                    bid=float(price),
                    ask=float(price),
                    liquidity=float(liquidity or volume or 0) or None,
                    source_url=f"https://polymarket.com/event/{event.get('slug') or event_id}",
                )
                markets.append(attach_canonical_ids(market))
    return markets


def _infer_event_sides(question: str) -> tuple[str | None, str | None]:
    import re

    vs_match = re.search(r"(.+?)\s+v(?:s\.?|ersus)?\s+(.+)", question, flags=re.IGNORECASE)
    if vs_match:
        return vs_match.group(1).strip(), vs_match.group(2).strip().split("?")[0].strip()

    beat_match = re.search(
        r"(?:will\s+)?(.+?)\s+(?:beat|defeat)\s+(.+?)(?:\?|$)",
        question,
        flags=re.IGNORECASE,
    )
    if beat_match:
        return beat_match.group(1).strip(), beat_match.group(2).strip()
    return None, None


def fetch_polymarket_soccer_markets(
    queries: list[str] | None = None,
    limit: int = 40,
    client: PolymarketClient | None = None,
) -> list[Market]:
    api = client or PolymarketClient()
    queries = queries or ["world cup", "soccer", "fifa"]
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        try:
            batch = api.search_events(query=query, limit=limit)
        except Exception:
            logger.exception("Polymarket search failed for %s", query)
            continue
        for event in batch:
            key = str(event.get("id") or event.get("slug") or id(event))
            if key in seen:
                continue
            seen.add(key)
            events.append(event)
        if len(events) >= limit:
            break
    if not events:
        events = api.list_sports_events(limit=limit)
    return normalize_polymarket_events(events[:limit])
