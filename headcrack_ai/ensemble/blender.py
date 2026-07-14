from __future__ import annotations

from dataclasses import dataclass

from ..probability import clamp_probability


@dataclass(frozen=True)
class ModelInput:
    name: str
    probability: float
    weight: float = 1.0


def blend_probabilities(inputs: list[ModelInput], book_anchor: float | None = None, anchor_weight: float = 0.15) -> float:
    """Weighted ensemble with optional book anchor to prevent extreme drift."""
    if not inputs:
        raise ValueError("inputs required")
    total_w = sum(i.weight for i in inputs)
    blended = sum(i.probability * i.weight for i in inputs) / total_w
    if book_anchor is not None:
        blended = (1 - anchor_weight) * blended + anchor_weight * book_anchor
    return clamp_probability(blended)


def default_soccer_blend(
    poisson_p: float,
    ml_p: float | None,
    book_p: float,
    poisson_weight: float = 0.35,
    ml_weight: float = 0.45,
) -> float:
    inputs = [ModelInput("poisson", poisson_p, poisson_weight)]
    if ml_p is not None:
        inputs.append(ModelInput("ml", ml_p, ml_weight))
    else:
        poisson_weight += ml_weight
        inputs[0] = ModelInput("poisson", poisson_p, poisson_weight)
    return blend_probabilities(inputs, book_anchor=book_p)
