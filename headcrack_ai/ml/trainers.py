from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import brier_score_loss, log_loss

from ..logging_config import get_logger
from .datasets import TrainingExample, examples_to_matrix, synthetic_soccer_examples

logger = get_logger(__name__)

try:
    import lightgbm as lgb

    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False


@dataclass
class TrainResult:
    model_name: str
    model_version: str
    artifact_path: str
    feature_keys: list[str]
    brier_score: float
    log_loss: float
    samples: int


def _build_estimator():
    if HAS_LIGHTGBM:
        return lgb.LGBMClassifier(
            n_estimators=80,
            learning_rate=0.08,
            max_depth=4,
            random_state=42,
        )
    return GradientBoostingClassifier(random_state=42)


def train_binary_classifier(
    examples: list[TrainingExample] | None = None,
    model_name: str = "soccer_moneyline",
    model_version: str = "v1",
    registry_dir: str | None = None,
) -> TrainResult:
    from ..settings import get_settings

    registry_dir = registry_dir or get_settings().model_registry_path
    examples = examples or synthetic_soccer_examples()
    x, y, keys = examples_to_matrix(examples)
    if len(np.unique(y)) < 2:
        raise ValueError("Need both positive and negative labels to train")

    clf = _build_estimator()
    clf.fit(x, y)
    proba = clf.predict_proba(x)[:, 1]
    brier = float(brier_score_loss(y, proba))
    ll = float(log_loss(y, proba))

    out_dir = Path(registry_dir) / model_name
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"{model_version}.joblib"
    meta = out_dir / f"{model_version}.json"
    joblib.dump({"model": clf, "feature_keys": keys}, artifact)
    meta.write_text(
        json.dumps(
            {
                "model_name": model_name,
                "model_version": model_version,
                "feature_keys": keys,
                "brier_score": brier,
                "log_loss": ll,
                "backend": "lightgbm" if HAS_LIGHTGBM else "sklearn_gbt",
            },
            indent=2,
        )
    )
    logger.info("Trained %s %s — Brier %.4f", model_name, model_version, brier)
    return TrainResult(model_name, model_version, str(artifact), keys, brier, ll, len(examples))


def load_classifier(model_name: str, model_version: str = "v1", registry_dir: str | None = None):
    from ..settings import get_settings

    registry_dir = registry_dir or get_settings().model_registry_path
    path = Path(registry_dir) / model_name / f"{model_version}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"No model at {path}")
    return joblib.load(path)


def predict_probability(
    features: dict[str, float],
    model_name: str = "soccer_moneyline",
    model_version: str = "v1",
    registry_dir: str | None = None,
) -> float:
    bundle = load_classifier(model_name, model_version, registry_dir)
    keys: list[str] = bundle["feature_keys"]
    x = np.array([[features.get(k, 0.0) for k in keys]], dtype=float)
    return float(bundle["model"].predict_proba(x)[0, 1])
