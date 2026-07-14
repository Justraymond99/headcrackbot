from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..daily_report import format_daily_report, generate_daily_report
from ..ingest import load_markets_json
from ..logging_config import get_logger, new_correlation_id, setup_logging
from ..llm_explain import get_default_narrator
from ..services import HeadcrackAIService
from ..soccer import SOCCER_LEAGUES

logger = get_logger(__name__)


@dataclass
class DailyJobResult:
    job_id: str
    leagues_scanned: list[str]
    total_lines: int
    report_path: str | None
    success: bool
    message: str


def run_daily_soccer(
    budget: float = 20.0,
    output_dir: str = "reports",
    markets_file: str | None = None,
) -> DailyJobResult:
    setup_logging()
    job_id = new_correlation_id()
    logger.info("Starting daily soccer job %s", job_id)
    service = HeadcrackAIService.from_env()
    if markets_file:
        legs = load_markets_json(markets_file)
        active = ["manual"]
    else:
        legs, active = service.fetch_soccer_today()
    if not legs:
        return DailyJobResult(job_id, active, 0, None, False, "No soccer lines available")

    store = service.store
    report = generate_daily_report(legs, store, budget=budget, narrator=get_default_narrator())
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = out / f"daily_soccer_{stamp}.md"
    path.write_text(format_daily_report(report), encoding="utf-8")
    json_path = out / f"daily_soccer_{stamp}.json"
    json_path.write_text(
        json.dumps(
            {
                "job_id": job_id,
                "leagues": active,
                "legs": report["legs_considered"],
                "warnings": report["no_bet_warnings"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Daily report written to %s", path)
    return DailyJobResult(job_id, active, len(legs), str(path), True, "ok")
