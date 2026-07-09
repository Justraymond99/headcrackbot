from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_SQLITE_URL = "sqlite:///headcrack_ai.sqlite3"


def require_sqlite_url(database_url: str) -> str:
    """Accept only SQLite-backed URLs until another store backend exists."""
    if database_url.startswith("sqlite:///"):
        return database_url
    # Allow bare local SQLite paths for developer convenience.
    if "://" not in database_url:
        return database_url
    raise ValueError(
        "Headcrack AI currently supports SQLite persistence only. "
        "Set HEADCRACK_DATABASE_URL to sqlite:///path/to/headcrack_ai.sqlite3 "
        "or unset DATABASE_URL until a PostgresStore backend exists."
    )


@dataclass(frozen=True)
class HeadcrackConfig:
    database_url: str = DEFAULT_SQLITE_URL
    odds_api_key: str | None = None
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    default_regions: str = "us"
    default_odds_format: str = "american"

    @classmethod
    def from_env(cls) -> "HeadcrackConfig":
        raw_database_url = os.getenv("HEADCRACK_DATABASE_URL") or os.getenv("DATABASE_URL") or DEFAULT_SQLITE_URL
        return cls(
            database_url=require_sqlite_url(raw_database_url),
            odds_api_key=os.getenv("ODDS_API_KEY"),
            odds_api_base_url=os.getenv("ODDS_API_BASE_URL", "https://api.the-odds-api.com/v4"),
            default_regions=os.getenv("ODDS_API_REGIONS", "us"),
            default_odds_format=os.getenv("ODDS_API_FORMAT", "american"),
        )
