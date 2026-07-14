from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    version: str
    description: str
    builder: Callable[..., dict[str, float]]


REGISTRY: dict[str, FeatureSpec] = {}


def register(spec: FeatureSpec) -> FeatureSpec:
    REGISTRY[spec.name] = spec
    return spec


def list_features() -> list[str]:
    return sorted(REGISTRY.keys())
