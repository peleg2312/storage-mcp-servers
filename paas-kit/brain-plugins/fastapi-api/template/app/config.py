from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every setting comes from the environment (APP_ prefix) or a .env file; nothing secret lives in code."""

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    app_name: str = "my-api"
    database_url: str = "sqlite:///./app.db"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
