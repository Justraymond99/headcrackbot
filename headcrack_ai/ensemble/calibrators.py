from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.isotonic import IsotonicRegression


@dataclass
class Calibrator:
    method: str
    model: IsotonicRegression | None = None

    def fit(self, predicted: list[float], outcomes: list[int]) -> "Calibrator":
        if len(predicted) < 5:
            self.method = "none"
            return self
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(np.array(predicted), np.array(outcomes))
        self.method = "isotonic"
        self.model = iso
        return self

    def calibrate(self, probability: float) -> float:
        if self.model is None:
            return probability
        return float(self.model.predict([probability])[0])
