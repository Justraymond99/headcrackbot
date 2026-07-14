from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..logging_config import get_logger
from ..ml.trainers import TrainResult, train_binary_classifier
from ..settings import get_settings


logger = get_logger(__name__)


@dataclass
class RegistryEntry:
    model_name: str
    model_version: str
    artifact_path: str
    metrics: dict[str, Any]
    promoted_at: str


class ModelRegistry:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or get_settings().model_registry_path)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"

    def promote(self, result: TrainResult, min_brier: float = 0.30) -> RegistryEntry:
        if result.brier_score > min_brier:
            raise ValueError(f"Brier {result.brier_score:.4f} exceeds gate {min_brier}")
        entry = RegistryEntry(
            model_name=result.model_name,
            model_version=result.model_version,
            artifact_path=result.artifact_path,
            metrics={"brier_score": result.brier_score, "log_loss": result.log_loss, "samples": result.samples},
            promoted_at=datetime.now(timezone.utc).isoformat(),
        )
        index = self._load_index()
        index[result.model_name] = entry.__dict__
        self.index_path.write_text(json.dumps(index, indent=2))
        logger.info("Promoted model %s %s", result.model_name, result.model_version)
        return entry

    def active(self, model_name: str) -> RegistryEntry | None:
        data = self._load_index().get(model_name)
        return RegistryEntry(**data) if data else None

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text())


def train_and_register(model_name: str = "soccer_moneyline", model_version: str = "v1") -> RegistryEntry:
    result = train_binary_classifier(model_name=model_name, model_version=model_version)
    return ModelRegistry().promote(result)
