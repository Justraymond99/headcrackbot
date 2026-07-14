from __future__ import annotations

from dataclasses import dataclass

from .settings import get_settings

DEFAULT_SQLITE_URL = "sqlite:///headcrack_ai.sqlite3"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


_load_dotenv()


def require_sqlite_url(database_url: str) -> str:
    """Legacy app store must remain SQLite for now."""
    if database_url.startswith("sqlite:///"):
        return database_url
    if "://" not in database_url:
        return database_url
    raise ValueError(
        "Headcrack AI app persistence supports SQLite only. "
        "Set HEADCRACK_DATABASE_URL to sqlite:///path/to/headcrack_ai.sqlite3. "
        "Use HEADCRACK_WAREHOUSE_URL for Postgres warehouse."
    )


@dataclass(frozen=True)
class HeadcrackConfig:
    database_url: str = DEFAULT_SQLITE_URL
    warehouse_url: str = "sqlite:///headcrack_warehouse.sqlite3"
    odds_api_key: str | None = None
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    default_regions: str = "us"
    default_odds_format: str = "american"
    kalshi_base_url: str = "https://api.elections.kalshi.com/trade-api/v2"
    polymarket_gamma_url: str = "https://gamma-api.polymarket.com"
    polymarket_clob_url: str = "https://clob.polymarket.com"
    enable_prediction_markets: bool = False

    @classmethod
    def from_env(cls) -> "HeadcrackConfig":
        settings = get_settings()
        raw_database_url = settings.resolved_database_url()
        return cls(
            database_url=require_sqlite_url(raw_database_url),
            warehouse_url=settings.warehouse_url,
            odds_api_key=settings.odds_api_key,
            odds_api_base_url=settings.odds_api_base_url,
            default_regions=settings.odds_api_regions,
            default_odds_format=settings.odds_api_format,
            kalshi_base_url=settings.kalshi_base_url,
            polymarket_gamma_url=settings.polymarket_gamma_url,
            polymarket_clob_url=settings.polymarket_clob_url,
            enable_prediction_markets=settings.enable_prediction_markets,
        )
