from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Opportunity Finder API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"

    khmdhs_base_url: AnyHttpUrl = "https://cerpp.eprocurement.gov.gr"
    khmdhs_verify_ssl: bool = False
    khmdhs_timeout_seconds: float = 18

    ted_base_url: AnyHttpUrl = "https://api.ted.europa.eu"
    ted_timeout_seconds: float = 18

    diavgeia_base_url: AnyHttpUrl = "https://diavgeia.gov.gr/opendata"
    diavgeia_timeout_seconds: float = 18

    gemi_base_url: AnyHttpUrl = "https://opendata-api.businessportal.gr"
    gemi_api_key: str | None = Field(default=None, repr=False)
    gemi_timeout_seconds: float = 18

    market_refresh_enabled: bool = True
    market_refresh_hour: int = Field(default=7, ge=0, le=23)
    market_refresh_interval_hours: int = Field(default=24, ge=1, le=168)
    market_daily_overlap_days: int = Field(default=14, ge=1, le=180)
    market_initial_backfill_days: int = Field(default=730, ge=14, le=1800)
    market_user_agent: str = "OpportunityFinder-MarketRadar/1.0"

    openai_api_key: str | None = Field(default=None, repr=False)
    openai_model: str = "gpt-4.1-mini"

    bookmark_db_path: Path = Path("data/opportunity_finder.sqlite3")

    model_config = SettingsConfigDict(
        env_file=(
            PROJECT_ROOT / ".env",
            PROJECT_ROOT / ".env.local",
            BACKEND_DIR / ".env",
            BACKEND_DIR / ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
