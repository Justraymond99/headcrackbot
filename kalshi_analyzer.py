"""Kalshi event contract analyzer - finds value in prediction markets.

Analyzes Kalshi markets to identify mispriced contracts by comparing
market-implied probabilities against estimated true probabilities derived
from volume patterns, spread analysis, and historical category biases.
"""
import logging
import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from kalshi_client import KalshiClient
from models import KalshiEvent, KalshiMarket, SessionLocal

logger = logging.getLogger(__name__)

# Category-level calibration offsets (positive = markets tend to under-price YES)
# These are rough priors; refine as you collect settlement data.
CATEGORY_BIAS = {
    "Economics": 0.00,
    "Politics": -0.02,  # Political markets tend to be slightly over-priced on favourites
    "Climate and Weather": 0.01,
    "Financials": 0.00,
    "Crypto": -0.01,
    "Sports": 0.00,
    "Tech & Science": 0.01,
    "Culture": 0.00,
    "Companies": 0.00,
}


class KalshiAnalyzer:
    """Analyze Kalshi prediction markets for value opportunities."""

    def __init__(self):
        self.client = KalshiClient()
        self.session = SessionLocal()

    # ------------------------------------------------------------------
    # Data ingestion
    # ------------------------------------------------------------------

    def fetch_and_store_markets(self, max_pages: int = 5) -> int:
        """Fetch open Kalshi events + markets and persist to the database.

        Returns:
            Number of markets stored/updated.
        """
        events = self.client.get_events(
            status="open",
            with_nested_markets=True,
            max_pages=max_pages,
        )

        stored = 0
        for event_data in events:
            try:
                stored += self._store_event(event_data)
            except Exception as e:
                logger.error(f"Error storing Kalshi event {event_data.get('event_ticker')}: {e}")
                self.session.rollback()
                continue

        try:
            self.session.commit()
            logger.info(f"Stored/updated {stored} Kalshi markets from {len(events)} events")
        except Exception as e:
            logger.error(f"Error committing Kalshi data: {e}")
            self.session.rollback()

        return stored

    def _store_event(self, event_data: Dict) -> int:
        """Persist one event and its nested markets. Returns count of markets stored."""
        event_ticker = event_data.get("event_ticker", "")
        if not event_ticker:
            return 0

        # Upsert event
        existing_event = self.session.query(KalshiEvent).filter_by(
            event_ticker=event_ticker
        ).first()

        if existing_event:
            existing_event.title = event_data.get("title", existing_event.title)
            existing_event.category = event_data.get("category", existing_event.category)
            existing_event.status = event_data.get("status", existing_event.status)
            existing_event.updated_at = datetime.utcnow()
            db_event = existing_event
        else:
            db_event = KalshiEvent(
                event_ticker=event_ticker,
                series_ticker=event_data.get("series_ticker", ""),
                title=event_data.get("title", ""),
                subtitle=event_data.get("sub_title", ""),
                category=event_data.get("category", "Other"),
                mutually_exclusive=event_data.get("mutually_exclusive", False),
                status=event_data.get("status", "open"),
            )
            self.session.add(db_event)
            self.session.flush()

        # Store nested markets
        count = 0
        for mkt in event_data.get("markets", []):
            try:
                self._store_market(mkt, db_event)
                count += 1
            except Exception as e:
                logger.debug(f"Error storing market {mkt.get('ticker')}: {e}")
                continue

        return count

    def _store_market(self, mkt: Dict, db_event: KalshiEvent):
        """Persist a single market record."""
        ticker = mkt.get("ticker", "")
        if not ticker:
            return

        # Parse close time
        close_time = None
        close_str = mkt.get("close_time") or mkt.get("expiration_time", "")
        if close_str:
            try:
                close_time = datetime.fromisoformat(close_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except (ValueError, TypeError):
                pass

        # Get pricing (prefer dollar fields per API changelog)
        yes_bid = mkt.get("yes_bid_dollars") or mkt.get("yes_bid") or 0
        yes_ask = mkt.get("yes_ask_dollars") or mkt.get("yes_ask") or 0
        last_price = mkt.get("last_price_dollars") or mkt.get("last_price") or 0
        volume = mkt.get("volume", 0) or 0
        volume_24h = mkt.get("volume_24h", 0) or 0
        open_interest = mkt.get("open_interest", 0) or 0

        # Dollar fields may be floats like 0.55; cents fields are ints like 55
        # Normalise everything to cents (0-100 scale) for consistency
        def to_cents(val):
            if val is None:
                return 0
            val = float(val)
            if val < 1.0:  # already in dollars
                return int(round(val * 100))
            return int(round(val))

        yes_bid_c = to_cents(yes_bid)
        yes_ask_c = to_cents(yes_ask)
        last_price_c = to_cents(last_price)

        existing = self.session.query(KalshiMarket).filter_by(ticker=ticker).first()

        if existing:
            existing.yes_bid = yes_bid_c
            existing.yes_ask = yes_ask_c
            existing.last_price = last_price_c
            existing.volume = volume
            existing.volume_24h = volume_24h
            existing.open_interest = open_interest
            existing.close_time = close_time
            existing.status = mkt.get("status", existing.status)
            existing.result = mkt.get("result", existing.result)
            existing.updated_at = datetime.utcnow()
        else:
            new_mkt = KalshiMarket(
                ticker=ticker,
                event_ticker=db_event.event_ticker,
                kalshi_event_id=db_event.id,
                title=mkt.get("title", ""),
                subtitle=mkt.get("subtitle", ""),
                category=db_event.category,
                market_type=mkt.get("market_type", "binary"),
                yes_bid=yes_bid_c,
                yes_ask=yes_ask_c,
                last_price=last_price_c,
                volume=volume,
                volume_24h=volume_24h,
                open_interest=open_interest,
                close_time=close_time,
                status=mkt.get("status", "open"),
                result=mkt.get("result"),
            )
            self.session.add(new_mkt)

    # ------------------------------------------------------------------
    # Value analysis
    # ------------------------------------------------------------------

    def estimate_true_probability(self, market: KalshiMarket) -> float:
        """Estimate the true probability of YES for a Kalshi market.

        Combines multiple signals:
        1. Mid-price (average of bid/ask) as the base estimate.
        2. Volume-weighted adjustment — high-volume markets are assumed to
           be more efficient, so we trust the mid-price more.
        3. Category bias correction.
        4. Spread penalty — wide spreads indicate uncertainty; shade toward 50%.

        Returns:
            Estimated probability (0.0 – 1.0).
        """
        # Mid price as base
        if market.yes_bid and market.yes_ask:
            mid = (market.yes_bid + market.yes_ask) / 2.0 / 100.0
        elif market.last_price:
            mid = market.last_price / 100.0
        else:
            return 0.5  # no data

        # Category bias
        bias = CATEGORY_BIAS.get(market.category or "", 0.0)
        adjusted = mid + bias

        # Spread penalty — shade toward 50% for illiquid markets
        spread = 0
        if market.yes_bid and market.yes_ask:
            spread = (market.yes_ask - market.yes_bid) / 100.0
        if spread > 0.10:
            shade_factor = min(spread / 0.30, 0.5)  # max 50% shade
            adjusted = adjusted * (1 - shade_factor) + 0.5 * shade_factor

        # Volume confidence — in very low-volume markets, regress toward 50%
        vol = market.volume or 0
        if vol < 100:
            vol_factor = vol / 100.0  # 0..1
            adjusted = adjusted * vol_factor + 0.5 * (1 - vol_factor)

        return max(0.01, min(0.99, adjusted))

    def calculate_ev(self, market: KalshiMarket, side: str = "yes") -> float:
        """Calculate expected value for buying YES or NO.

        On Kalshi, buying YES at ask price X cents means:
            Win: profit = (100 - X) cents
            Lose: loss = X cents
        EV = true_prob * (100 - X) - (1 - true_prob) * X
           = true_prob * 100 - X

        Args:
            market: KalshiMarket instance.
            side: 'yes' or 'no'.

        Returns:
            EV in cents. Positive = favorable.
        """
        true_prob = self.estimate_true_probability(market)

        if side == "yes":
            cost = market.yes_ask or market.last_price or 50
            # EV of buying YES at ask
            ev = true_prob * 100 - cost
        else:
            # Buying NO is equivalent to selling YES
            # Cost of NO = 100 - yes_bid (you sell YES at bid)
            no_cost = 100 - (market.yes_bid or market.last_price or 50)
            no_true_prob = 1 - true_prob
            ev = no_true_prob * 100 - no_cost

        return ev

    def calculate_confidence(self, market: KalshiMarket) -> float:
        """Compute a confidence score (0-1) for a Kalshi pick.

        Factors:
        - Volume / liquidity
        - Bid-ask spread tightness
        - Open interest
        - Time until close (closer = more certain pricing)
        """
        score = 0.5

        # Volume signal
        vol = market.volume or 0
        if vol >= 10000:
            score += 0.15
        elif vol >= 1000:
            score += 0.10
        elif vol >= 100:
            score += 0.05

        # Spread tightness
        if market.yes_bid and market.yes_ask:
            spread = market.yes_ask - market.yes_bid
            if spread <= 2:
                score += 0.10
            elif spread <= 5:
                score += 0.05
            elif spread > 15:
                score -= 0.10

        # Open interest
        oi = market.open_interest or 0
        if oi >= 5000:
            score += 0.10
        elif oi >= 1000:
            score += 0.05

        # Time until close
        if market.close_time:
            hours_left = (market.close_time - datetime.utcnow()).total_seconds() / 3600
            if 1 <= hours_left <= 48:
                score += 0.05  # Markets about to close tend to be well-priced

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Pick generation
    # ------------------------------------------------------------------

    def find_value_contracts(
        self,
        min_ev_cents: float = 3.0,
        min_confidence: float = 0.55,
        min_volume: int = 50,
        max_picks: int = 20,
        categories: Optional[List[str]] = None,
        hours_until_close: Optional[int] = None,
    ) -> List[Dict]:
        """Scan all stored Kalshi markets for value.

        Args:
            min_ev_cents: Minimum EV in cents to include.
            min_confidence: Minimum confidence score.
            min_volume: Minimum market volume.
            max_picks: Cap on returned picks.
            categories: Filter to specific categories.
            hours_until_close: Only include markets closing within this window.

        Returns:
            Sorted list of pick dicts, best first.
        """
        query = self.session.query(KalshiMarket).filter(
            KalshiMarket.status == "open",
            KalshiMarket.volume >= min_volume,
        )

        if categories:
            query = query.filter(KalshiMarket.category.in_(categories))

        if hours_until_close:
            cutoff = datetime.utcnow() + timedelta(hours=hours_until_close)
            query = query.filter(KalshiMarket.close_time <= cutoff)

        markets = query.all()
        logger.info(f"Analyzing {len(markets)} Kalshi markets for value...")

        picks = []
        for market in markets:
            true_prob = self.estimate_true_probability(market)
            confidence = self.calculate_confidence(market)

            if confidence < min_confidence:
                continue

            # Evaluate YES side
            ev_yes = self.calculate_ev(market, "yes")
            if ev_yes >= min_ev_cents:
                ask_price = market.yes_ask or market.last_price or 50
                implied_prob_yes = ask_price / 100.0
                american_odds = KalshiClient.probability_to_american_odds(implied_prob_yes)

                picks.append(self._build_pick(
                    market=market,
                    side="YES",
                    cost_cents=ask_price,
                    ev_cents=ev_yes,
                    true_prob=true_prob,
                    implied_prob=implied_prob_yes,
                    american_odds=american_odds,
                    confidence=confidence,
                ))

            # Evaluate NO side
            ev_no = self.calculate_ev(market, "no")
            if ev_no >= min_ev_cents:
                no_cost = 100 - (market.yes_bid or market.last_price or 50)
                implied_prob_no = no_cost / 100.0
                american_odds = KalshiClient.probability_to_american_odds(implied_prob_no)

                picks.append(self._build_pick(
                    market=market,
                    side="NO",
                    cost_cents=no_cost,
                    ev_cents=ev_no,
                    true_prob=1 - true_prob,
                    implied_prob=implied_prob_no,
                    american_odds=american_odds,
                    confidence=confidence,
                ))

        # Sort by value_score (EV-weighted confidence)
        picks.sort(key=lambda p: p["value_score"], reverse=True)

        top = picks[:max_picks]
        logger.info(f"Found {len(top)} Kalshi value picks (from {len(picks)} candidates)")
        return top

    def _build_pick(
        self,
        market: KalshiMarket,
        side: str,
        cost_cents: float,
        ev_cents: float,
        true_prob: float,
        implied_prob: float,
        american_odds: float,
        confidence: float,
    ) -> Dict:
        """Construct a standardized pick dict."""
        ev_pct = ev_cents / cost_cents if cost_cents > 0 else 0
        value_score = (ev_pct * 0.6) + (confidence * 0.4)

        # Potential profit per $1 risked
        payout_per_dollar = (100 - cost_cents) / cost_cents if cost_cents > 0 else 0

        # Build reasoning
        spread_info = ""
        if market.yes_bid and market.yes_ask:
            spread_info = f" | Spread: {market.yes_ask - market.yes_bid}c"

        # Human-readable event context
        event = self.session.query(KalshiEvent).filter_by(
            event_ticker=market.event_ticker
        ).first()
        event_title = event.title if event else market.event_ticker

        reasoning = (
            f"{side} @ {cost_cents}c (EV: +{ev_cents:.1f}c){spread_info} | "
            f"Vol: {market.volume:,} | Category: {market.category}"
        )

        return {
            # Kalshi-specific fields
            "source": "kalshi",
            "market_ticker": market.ticker,
            "event_ticker": market.event_ticker,
            "event_title": event_title,
            "market_title": market.title,
            "category": market.category or "Other",
            "side": side,
            "cost_cents": cost_cents,
            "ev_cents": ev_cents,
            "payout_per_dollar": payout_per_dollar,
            "close_time": market.close_time,
            "volume": market.volume or 0,
            "open_interest": market.open_interest or 0,

            # Fields compatible with the sports betting pick format
            "bet_type": "kalshi_contract",
            "selection": f"{side} — {market.title}",
            "odds": american_odds,
            "implied_probability": implied_prob,
            "true_probability": true_prob,
            "expected_value": ev_pct,  # as fraction (like sports picks)
            "confidence": confidence,
            "confidence_score": confidence,
            "value_score": value_score,
            "reasoning": reasoning,
        }

    # ------------------------------------------------------------------
    # Result tracking
    # ------------------------------------------------------------------

    def update_settled_markets(self) -> int:
        """Check for recently settled markets and update results.

        Returns:
            Number of markets updated.
        """
        settled_events = self.client.get_events(status="settled", with_nested_markets=True, max_pages=2)
        updated = 0

        for event_data in settled_events:
            for mkt_data in event_data.get("markets", []):
                ticker = mkt_data.get("ticker", "")
                result = mkt_data.get("result", "")
                if not ticker or not result:
                    continue

                db_mkt = self.session.query(KalshiMarket).filter_by(ticker=ticker).first()
                if db_mkt and db_mkt.result != result:
                    db_mkt.result = result
                    db_mkt.status = "settled"
                    db_mkt.updated_at = datetime.utcnow()
                    updated += 1

            # Update event status
            evt_ticker = event_data.get("event_ticker", "")
            db_evt = self.session.query(KalshiEvent).filter_by(event_ticker=evt_ticker).first()
            if db_evt:
                db_evt.status = "settled"
                db_evt.updated_at = datetime.utcnow()

        if updated:
            try:
                self.session.commit()
                logger.info(f"Updated {updated} settled Kalshi markets")
            except Exception as e:
                logger.error(f"Error committing settled results: {e}")
                self.session.rollback()

        return updated

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def __del__(self):
        if hasattr(self, "session"):
            self.session.close()
