from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable

from .models import ResultStatus
from .persistence import SQLiteStore


def _outcome_to_int(outcome: str) -> int:
    return 1 if outcome == ResultStatus.WON.value else 0


def brier_score(rows: Iterable[dict[str, Any]]) -> float | None:
    rows = list(rows)
    if not rows:
        return None
    total = sum((row["model_probability"] - _outcome_to_int(row["outcome"])) ** 2 for row in rows)
    return round(total / len(rows), 4)


def log_loss(rows: Iterable[dict[str, Any]], epsilon: float = 1e-12) -> float | None:
    rows = list(rows)
    if not rows:
        return None
    total = 0.0
    for row in rows:
        p = min(1.0 - epsilon, max(epsilon, row["model_probability"]))
        y = _outcome_to_int(row["outcome"])
        total += -(y * math.log(p) + (1 - y) * math.log(1.0 - p))
    return round(total / len(rows), 4)


def reliability_bins(rows: Iterable[dict[str, Any]], bins: int = 10) -> list[dict[str, Any]]:
    """Group predictions into probability bins and compare predicted vs observed."""
    rows = list(rows)
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        p = min(0.999999, max(0.0, row["model_probability"]))
        index = min(bins - 1, int(p * bins))
        buckets[index].append(row)

    result: list[dict[str, Any]] = []
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        bucket = buckets.get(index, [])
        if not bucket:
            continue
        predicted = sum(row["model_probability"] for row in bucket) / len(bucket)
        observed = sum(_outcome_to_int(row["outcome"]) for row in bucket) / len(bucket)
        result.append(
            {
                "bin": f"{low:.0%}-{high:.0%}",
                "count": len(bucket),
                "avg_predicted": round(predicted, 4),
                "observed": round(observed, 4),
                "calibration_error": round(abs(predicted - observed), 4),
            }
        )
    return result


def expected_calibration_error(rows: Iterable[dict[str, Any]], bins: int = 10) -> float | None:
    rows = list(rows)
    if not rows:
        return None
    total = len(rows)
    ece = 0.0
    for bucket in reliability_bins(rows, bins=bins):
        weight = bucket["count"] / total
        ece += weight * bucket["calibration_error"]
    return round(ece, 4)


def build_calibration_report(store: SQLiteStore, bins: int = 10) -> dict[str, Any]:
    rows = store.calibration_rows()
    per_model: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("model_name", "unknown"))].append(row)
    for model, model_rows in grouped.items():
        per_model[model] = {
            "samples": len(model_rows),
            "brier_score": brier_score(model_rows),
            "log_loss": log_loss(model_rows),
            "expected_calibration_error": expected_calibration_error(model_rows, bins=bins),
        }

    return {
        "samples": len(rows),
        "brier_score": brier_score(rows),
        "log_loss": log_loss(rows),
        "expected_calibration_error": expected_calibration_error(rows, bins=bins),
        "reliability_bins": reliability_bins(rows, bins=bins),
        "per_model": per_model,
    }


def format_calibration_report(report: dict[str, Any]) -> str:
    lines = ["# How Accurate Are Our Predictions?", ""]
    if not report["samples"]:
        lines.append("No finished picks to review yet. Import results after games finish.")
        return "\n".join(lines)

    lines.append(f"We checked **{report['samples']}** picks against real outcomes.")
    lines.append(
        f"- **Accuracy score:** {report['brier_score']} "
        f"(lower is better — 0.25 means we're basically guessing)"
    )
    lines.append(
        f"- **Trust gap:** {report['expected_calibration_error']:.0%} "
        f"(how far off our confidence was on average)"
    )

    lines.extend(["", "## When we said X%, did it actually happen?"])
    for bucket in report["reliability_bins"]:
        lines.append(
            f"- **{bucket['bin']}**: we predicted {bucket['avg_predicted']:.0%}, "
            f"it actually happened {bucket['observed']:.0%} "
            f"({bucket['count']} picks)"
        )

    if report["per_model"]:
        lines.extend(["", "## By prediction model"])
        for model, stats in report["per_model"].items():
            lines.append(
                f"- **{model}**: {stats['samples']} picks, "
                f"accuracy score {stats['brier_score']}"
            )

    return "\n".join(lines)
