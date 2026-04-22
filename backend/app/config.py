"""Application configuration loaded from environment variables.

We use pydantic-settings so that misconfiguration fails fast at startup
with a clear error, instead of crashing later at runtime.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./fortune.db"
    cors_origins: str = "http://localhost:5173"

    # OpenAI — all optional. Missing key = graceful fallback to seed messages.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 5.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()
