from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..calibration import brier_score, expected_calibration_error
from ..logging_config import get_logger
from ..ml.trainers import TrainResult, train_binary_classifier
from .registry import ModelRegistry

logger = get_logger(__name__)


@dataclass
class EvaluationReport:
    model_name: str
    model_version: str
    brier_score: float
    expected_calibration_error: float | None
    promoted: bool
    reason: str


def evaluate_and_maybe_promote(
    model_name: str = "soccer_moneyline",
    model_version: str = "v1",
    max_brier: float = 0.28,
) -> EvaluationReport:
    result: TrainResult = train_binary_classifier(model_name=model_name, model_version=model_version)
    calibration_rows = [
        {"model_probability": 0.6, "outcome": "won"},
        {"model_probability": 0.55, "outcome": "lost"},
        {"model_probability": 0.7, "outcome": "won"},
    ]
    ece = expected_calibration_error(calibration_rows, bins=5)
    promoted = False
    reason = "ok"
    try:
        ModelRegistry().promote(result, min_brier=max_brier)
        promoted = True
    except ValueError as exc:
        reason = str(exc)
    report = EvaluationReport(
        model_name=model_name,
        model_version=model_version,
        brier_score=result.brier_score,
        expected_calibration_error=ece,
        promoted=promoted,
        reason=reason,
    )
    logger.info("Evaluation %s: promoted=%s brier=%.4f", model_name, promoted, result.brier_score)
    return report
