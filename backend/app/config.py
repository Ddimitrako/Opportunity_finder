from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Opportunity Finder API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"

    khmdhs_base_url: AnyHttpUrl = "https://cerpp.eprocurement.gov.gr"
    khmdhs_verify_ssl: bool = False
    khmdhs_timeout_seconds: float = 18

    ted_base_url: AnyHttpUrl = "https://api.ted.europa.eu"
    ted_timeout_seconds: float = 18

    openai_api_key: str | None = Field(default=None, repr=False)
    openai_model: str = "gpt-4.1-mini"

    bookmark_db_path: Path = Path("data/opportunity_finder.sqlite3")

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", "backend/.env", "backend/.env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
