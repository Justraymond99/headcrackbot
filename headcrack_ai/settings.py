from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Persistence (legacy SQLite app store)
    headcrack_database_url: str = Field(default="sqlite:///headcrack_ai.sqlite3", alias="HEADCRACK_DATABASE_URL")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    # Warehouse (Postgres in prod, SQLite for local dev)
    warehouse_url: str = Field(
        default="sqlite:///headcrack_warehouse.sqlite3",
        alias="HEADCRACK_WAREHOUSE_URL",
    )

    odds_api_key: str | None = Field(default=None, alias="ODDS_API_KEY")
    odds_api_base_url: str = Field(default="https://api.the-odds-api.com/v4", alias="ODDS_API_BASE_URL")
    odds_api_regions: str = Field(default="us", alias="ODDS_API_REGIONS")
    odds_api_format: str = Field(default="american", alias="ODDS_API_FORMAT")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=False, alias="LOG_JSON")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    mlflow_tracking_uri: str = Field(default="file:./mlruns", alias="MLFLOW_TRACKING_URI")
    model_registry_path: str = Field(default="models/registry", alias="MODEL_REGISTRY_PATH")

    http_retry_attempts: int = Field(default=3, alias="HTTP_RETRY_ATTEMPTS")
    http_retry_backoff: float = Field(default=1.5, alias="HTTP_RETRY_BACKOFF")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    kalshi_base_url: str = Field(
        default="https://api.elections.kalshi.com/trade-api/v2",
        alias="KALSHI_BASE_URL",
    )
    polymarket_gamma_url: str = Field(default="https://gamma-api.polymarket.com", alias="POLYMARKET_GAMMA_URL")
    polymarket_clob_url: str = Field(default="https://clob.polymarket.com", alias="POLYMARKET_CLOB_URL")
    enable_prediction_markets: bool = Field(default=False, alias="ENABLE_PREDICTION_MARKETS")

    def resolved_database_url(self) -> str:
        return self.headcrack_database_url or self.database_url or "sqlite:///headcrack_ai.sqlite3"


@lru_cache
def get_settings() -> Settings:
    return Settings()
