from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class TrainingExample:
    features: dict[str, float]
    label: int  # 1 = hit, 0 = miss
    market_type: str
    implied_probability: float


def examples_to_matrix(examples: list[TrainingExample]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if not examples:
        raise ValueError("No training examples")
    keys = sorted({k for ex in examples for k in ex.features})
    x = np.array([[ex.features.get(k, 0.0) for k in keys] for ex in examples], dtype=float)
    y = np.array([ex.label for ex in examples], dtype=int)
    return x, y, keys


def synthetic_soccer_examples(n: int = 200) -> list[TrainingExample]:
    """Bootstrap training data when warehouse history is thin."""
    rng = np.random.default_rng(42)
    rows: list[TrainingExample] = []
    for _ in range(n):
        implied = float(rng.uniform(0.35, 0.75))
        home_form = float(rng.uniform(0.8, 2.5))
        away_form = float(rng.uniform(0.8, 2.5))
        edge = (home_form - away_form) * 0.05
        true_p = min(0.95, max(0.05, implied + edge))
        label = int(rng.random() < true_p)
        rows.append(
            TrainingExample(
                features={
                    "home_avg_goals_for": home_form,
                    "away_avg_goals_for": away_form,
                    "implied_probability": implied,
                },
                label=label,
                market_type="moneyline",
                implied_probability=implied,
            )
        )
    return rows
