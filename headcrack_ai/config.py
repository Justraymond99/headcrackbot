from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class HeadcrackConfig:
    database_url: str = "sqlite:///headcrack_ai.sqlite3"
    odds_api_key: str | None = None
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    default_regions: str = "us"
    default_odds_format: str = "american"


    @classmethod
    def from_env(cls) -> "HeadcrackConfig":
        return cls(
            database_url=os.getenv("HEADCRACK_DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///headcrack_ai.sqlite3")),
            odds_api_key=os.getenv("ODDS_API_KEY"),
            odds_api_base_url=os.getenv("ODDS_API_BASE_URL", "https://api.the-odds-api.com/v4"),
            default_regions=os.getenv("ODDS_API_REGIONS", "us"),
            default_odds_format=os.getenv("ODDS_API_FORMAT", "american"),
        )
