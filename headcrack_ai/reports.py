from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Iterable

from .models import ResultStatus
from .persistence import SQLiteStore

SETTLED = {ResultStatus.WON.value, ResultStatus.LOST.value}

CONFIDENCE_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("0-40%", 0.0, 0.40),
    ("40-55%", 0.40, 0.55),
    ("55-70%", 0.55, 0.70),
    ("70-85%", 0.70, 0.85),
    ("85-100%", 0.85, 1.0001),
)


def _profit_loss(record: dict[str, Any]) -> float:
    if record["status"] == ResultStatus.WON.value:
        return record["payout"] - record["stake"]
    if record["status"] == ResultStatus.LOST.value:
        return -record["stake"]
    return 0.0


def summarize(records: Iterable[dict[str, Any]]) -> dict[str, float | int]:
    rows = list(records)
    settled = [row for row in rows if row["status"] in SETTLED]
    total_staked = sum(row["stake"] for row in settled)
    total_profit = sum(_profit_loss(row) for row in settled)
    wins = sum(1 for row in settled if row["status"] == ResultStatus.WON.value)
    return {
        "bets": len(rows),
        "settled": len(settled),
        "wins": wins,
        "losses": len(settled) - wins,
        "total_staked": round(total_staked, 2),
        "profit_loss": round(total_profit, 2),
        "roi": round(total_profit / total_staked, 4) if total_staked else 0.0,
        "hit_rate": round(wins / len(settled), 4) if settled else 0.0,
    }


def _group_by_leg_field(records: Iterable[dict[str, Any]], field: str) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        values = sorted({str(leg.get(field, "unknown")) for leg in record["legs"]})
        grouped["+".join(values) or "unknown"].append(record)
    return {key: summarize(value) for key, value in sorted(grouped.items())}


def roi_by_market(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    return _group_by_leg_field(records, "market_type")


def roi_by_sport(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    return _group_by_leg_field(records, "sport")


def roi_by_sportsbook(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    return _group_by_leg_field(records, "sportsbook")


def _bucket_for(confidence: float) -> str:
    for label, low, high in CONFIDENCE_BUCKETS:
        if low <= confidence < high:
            return label
    return CONFIDENCE_BUCKETS[-1][0]


def hit_rate_by_confidence(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        confidences = [float(leg.get("confidence", 0.0)) for leg in record["legs"]]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        grouped[_bucket_for(avg_confidence)].append(record)
    ordered = {label: summarize(grouped[label]) for label, _, _ in CONFIDENCE_BUCKETS if grouped[label]}
    return ordered


def model_performance(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    """Attribute every settled bet to each model appearing in its legs."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        for model in {str(leg.get("model_name", "unknown")) for leg in record["legs"]}:
            grouped[model].append(record)
    return {model: summarize(value) for model, value in grouped.items()}


def _rank_models(records: Iterable[dict[str, Any]], reverse: bool) -> list[tuple[str, dict[str, float | int]]]:
    performance = model_performance(records)
    ranked = [(model, stats) for model, stats in performance.items() if stats["settled"]]
    ranked.sort(key=lambda item: item[1]["roi"], reverse=reverse)
    return ranked


def best_models(records: Iterable[dict[str, Any]], limit: int = 3) -> list[tuple[str, dict[str, float | int]]]:
    return _rank_models(records, reverse=True)[:limit]


def worst_models(records: Iterable[dict[str, Any]], limit: int = 3) -> list[tuple[str, dict[str, float | int]]]:
    return _rank_models(records, reverse=False)[:limit]


def build_tracking_report(store: SQLiteStore) -> dict[str, Any]:
    records = store.all_bet_records()
    return {
        "overall": summarize(records),
        "roi_by_market": roi_by_market(records),
        "roi_by_sport": roi_by_sport(records),
        "roi_by_sportsbook": roi_by_sportsbook(records),
        "hit_rate_by_confidence": hit_rate_by_confidence(records),
        "model_performance": model_performance(records),
        "best_models": best_models(records),
        "worst_models": worst_models(records),
    }


def _format_summary_line(label: str, stats: dict[str, float | int]) -> str:
    pl = stats["profit_loss"]
    direction = "up" if pl >= 0 else "down"
    return (
        f"- **{label}**: {stats['bets']} bets placed, {stats['settled']} finished, "
        f"won {stats['wins']} of {stats['settled']} ({stats['hit_rate']:.0%}), "
        f"put in ${stats['total_staked']:.2f}, {direction} ${abs(pl):.2f} "
        f"({stats['roi']:+.0%} return)"
    )


def format_tracking_report(report: dict[str, Any]) -> str:
    lines = ["# Your Betting Results", "", "## Overall"]
    lines.append(_format_summary_line("All bets", report["overall"]))

    sections: list[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = [
        ("By bet type", lambda r: r["roi_by_market"]),
        ("By sport", lambda r: r["roi_by_sport"]),
        ("By sportsbook", lambda r: r["roi_by_sportsbook"]),
        ("By how confident we were", lambda r: r["hit_rate_by_confidence"]),
    ]
    for title, getter in sections:
        grouped = getter(report)
        lines.extend(["", f"## {title}"])
        if not grouped:
            lines.append("- No finished bets yet.")
            continue
        for label, stats in grouped.items():
            lines.append(_format_summary_line(label.replace("+", " + "), stats))

    lines.extend(["", "## What's working"])
    if report["best_models"]:
        lines.extend(_format_summary_line(model, stats) for model, stats in report["best_models"])
    else:
        lines.append("- No finished bets yet.")

    lines.extend(["", "## What's not working"])
    if report["worst_models"]:
        lines.extend(_format_summary_line(model, stats) for model, stats in report["worst_models"])
    else:
        lines.append("- No finished bets yet.")

    return "\n".join(lines)
