"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for local development."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    streamlit_server_port: int = Field(default=8501, alias="STREAMLIT_SERVER_PORT")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    bestbuy_api_key: str = Field(default="", alias="BESTBUY_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
