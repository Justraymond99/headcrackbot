from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .feature_store import LEAGUE_AVG_SHOTS_ALLOWED, FeatureStore
from .models import Prediction
from .probability import clamp_probability, poisson_over_probability

MODEL_NAME = "soccer_player_shots_poisson_v1"


@dataclass(frozen=True)
class ShotProjection:
    player: str
    threshold: float
    expected_shots: float
    over_probability: float
    confidence: float
    features: dict[str, Any]


@dataclass
class PlayerShotModel:
    """Poisson shot model driven by the historical feature store.

    Expected shots come from a player's recent per-game rate, scaled by how many
    shots the opponent typically concedes relative to a league baseline. The
    over probability for a shots line then falls out of the Poisson upper tail.
    """

    feature_store: FeatureStore
    window: int = 10
    opponent_baseline: float = LEAGUE_AVG_SHOTS_ALLOWED
    max_opponent_multiplier: float = 1.5
    min_opponent_multiplier: float = 0.6

    def _opponent_multiplier(self, opponent: str | None, before_date: str | None) -> tuple[float, float | None]:
        if not opponent:
            return 1.0, None
        allowed = self.feature_store.opponent_shots_allowed(
            opponent, window=self.window, before_date=before_date
        )
        if allowed is None or self.opponent_baseline <= 0:
            return 1.0, allowed
        multiplier = allowed / self.opponent_baseline
        multiplier = min(self.max_opponent_multiplier, max(self.min_opponent_multiplier, multiplier))
        return multiplier, allowed

    def project(
        self,
        player: str,
        threshold: float,
        opponent: str | None = None,
        before_date: str | None = None,
    ) -> ShotProjection | None:
        features = self.feature_store.player_shot_features(
            player, window=self.window, before_date=before_date
        )
        if features is None:
            return None

        multiplier, opponent_allowed = self._opponent_multiplier(opponent, before_date)
        base_rate = features["shots_per_90"] * features["avg_minutes"] / 90.0
        expected_shots = max(0.01, base_rate * multiplier)
        over_probability = clamp_probability(poisson_over_probability(threshold, expected_shots))

        games = features["games"]
        confidence = round(min(0.9, 0.25 + 0.65 * min(1.0, games / self.window)), 4)

        enriched = {
            **features,
            "opponent": opponent,
            "opponent_shots_allowed": opponent_allowed,
            "opponent_multiplier": round(multiplier, 3),
            "expected_shots": round(expected_shots, 3),
            "threshold": threshold,
        }
        return ShotProjection(
            player=player,
            threshold=threshold,
            expected_shots=round(expected_shots, 3),
            over_probability=round(over_probability, 4),
            confidence=confidence,
            features=enriched,
        )

    def prediction(
        self,
        market_id: str,
        player: str,
        threshold: float,
        opponent: str | None = None,
        before_date: str | None = None,
    ) -> Prediction | None:
        projection = self.project(player, threshold, opponent=opponent, before_date=before_date)
        if projection is None:
            return None
        return Prediction(
            market_id=market_id,
            model_probability=projection.over_probability,
            model_name=MODEL_NAME,
            confidence=projection.confidence,
            features=projection.features,
        )
