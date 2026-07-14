from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import reduce
from operator import mul
from typing import Any


class Sport(str, Enum):
    SOCCER = "soccer"
    MMA = "mma"
    NBA = "nba"
    NFL = "nfl"
    MLB = "mlb"
    NHL = "nhl"
    ESPORTS = "esports"
    PRO_WRESTLING = "pro_wrestling"


class MarketType(str, Enum):
    MONEYLINE = "moneyline"
    QUALIFY = "qualify"
    SPREAD = "spread"
    TOTAL_GOALS = "total_goals"
    TEAM_TOTAL = "team_total"
    BOTH_TEAMS_TO_SCORE = "both_teams_to_score"
    CORNERS = "corners"
    CARDS = "cards"
    PLAYER_GOAL = "player_goal"
    PLAYER_ASSIST = "player_assist"
    PLAYER_SHOTS = "player_shots"
    PLAYER_SHOTS_ON_TARGET = "player_shots_on_target"
    CUSTOM = "custom"


class ResultStatus(str, Enum):
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"


class VenueType(str, Enum):
    """Where a quote comes from — sportsbooks and prediction markets are different venues."""

    SPORTSBOOK = "sportsbook"
    PREDICTION_MARKET = "prediction_market"
    MANUAL = "manual"


def venue_type_for_name(name: str) -> VenueType:
    key = (name or "").lower().strip()
    if key in {"kalshi", "polymarket"}:
        return VenueType.PREDICTION_MARKET
    if key in {"manual", "upload", "csv"}:
        return VenueType.MANUAL
    return VenueType.SPORTSBOOK


@dataclass(frozen=True)
class AmericanOdds:
    value: int

    @property
    def decimal(self) -> float:
        if self.value > 0:
            return 1.0 + self.value / 100.0
        if self.value < 0:
            return 1.0 + 100.0 / abs(self.value)
        raise ValueError("American odds cannot be zero")

    @property
    def implied_probability(self) -> float:
        if self.value > 0:
            return 100.0 / (self.value + 100.0)
        if self.value < 0:
            return abs(self.value) / (abs(self.value) + 100.0)
        raise ValueError("American odds cannot be zero")


@dataclass(frozen=True)
class Market:
    market_id: str
    sport: Sport
    event_id: str
    label: str
    market_type: MarketType
    sportsbook: str
    odds: AmericanOdds
    team: str | None = None
    opponent: str | None = None
    player: str | None = None
    threshold: float | None = None
    starts_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    venue_type: VenueType = VenueType.SPORTSBOOK
    canonical_event_id: str | None = None
    canonical_outcome_id: str | None = None
    quoted_at: datetime | None = None
    bid: float | None = None  # probability or decimal price depending on venue
    ask: float | None = None
    liquidity: float | None = None
    source_url: str | None = None

    @property
    def venue(self) -> str:
        return self.sportsbook

    @property
    def is_prediction_market(self) -> bool:
        return self.venue_type == VenueType.PREDICTION_MARKET


@dataclass(frozen=True)
class Prediction:
    market_id: str
    model_probability: float
    model_name: str
    confidence: float = 0.5
    features: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not 0 <= self.model_probability <= 1:
            raise ValueError("model_probability must be between 0 and 1")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class BetLeg:
    market: Market
    prediction: Prediction
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def implied_probability(self) -> float:
        return self.market.odds.implied_probability

    @property
    def model_probability(self) -> float:
        return self.prediction.model_probability

    @property
    def edge(self) -> float:
        return self.model_probability - self.implied_probability

    @property
    def decimal_odds(self) -> float:
        return self.market.odds.decimal

    @property
    def ev_per_dollar(self) -> float:
        profit = self.decimal_odds - 1.0
        return self.model_probability * profit - (1.0 - self.model_probability)


@dataclass(frozen=True)
class Parlay:
    legs: tuple[BetLeg, ...]
    stake: float
    target_band: str
    correlation_score: float
    risk_score: float
    notes: str = ""
    venue: str | None = None  # single sportsbook for placeable slips
    preset: str = "balanced"
    combined_odds_estimated: bool = True

    @property
    def decimal_odds(self) -> float:
        return reduce(mul, (leg.decimal_odds for leg in self.legs), 1.0)

    @property
    def sportsbook(self) -> str:
        if self.venue:
            return self.venue
        books = {leg.market.sportsbook for leg in self.legs}
        return next(iter(books)) if len(books) == 1 else "mixed"

    @property
    def gross_payout(self) -> float:
        return self.stake * self.decimal_odds

    @property
    def profit(self) -> float:
        return self.gross_payout - self.stake

    @property
    def naive_probability(self) -> float:
        return reduce(mul, (leg.model_probability for leg in self.legs), 1.0)

    @property
    def adjusted_probability(self) -> float:
        # Correlation helps when legs tell the same story, but risk penalizes fragility.
        correlation_multiplier = min(1.35, max(0.70, 1.0 + self.correlation_score * 0.12))
        risk_multiplier = min(1.0, max(0.55, 1.0 - self.risk_score * 0.08))
        return min(0.99, self.naive_probability * correlation_multiplier * risk_multiplier)

    @property
    def expected_value(self) -> float:
        p = self.adjusted_probability
        return p * self.profit - (1.0 - p) * self.stake


@dataclass
class BankrollState:
    starting_bankroll: float
    current_bankroll: float
    unit_size: float
    max_daily_risk_pct: float = 0.10
    max_event_risk_pct: float = 0.05


@dataclass
class BetRecord:
    bet_id: str
    legs: tuple[BetLeg, ...]
    stake: float
    decimal_odds: float
    status: ResultStatus = ResultStatus.PENDING
    payout: float = 0.0
    placed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def profit_loss(self) -> float:
        if self.status == ResultStatus.WON:
            return self.payout - self.stake
        if self.status == ResultStatus.LOST:
            return -self.stake
        return 0.0
