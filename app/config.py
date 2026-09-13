"""Application configuration.

Loads settings from environment variables / a .env file. Designed so the
app boots cleanly even when OPENAI_API_KEY is not set — AI agents check
`settings.ai_enabled` and fall back to deterministic logic when it is False.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"

    @property
    def ai_enabled(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip())

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV.lower() in ("development", "dev", "test", "testing")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
