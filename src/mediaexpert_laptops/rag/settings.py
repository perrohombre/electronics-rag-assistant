"""Runtime settings for the RAG application."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    dataset_csv_path: str = Field(
        default="data/raw/mediaexpert_laptops.csv",
        alias="DATASET_CSV_PATH",
    )
    catalog_db_path: str = Field(default="data/catalog.db", alias="CATALOG_DB_PATH")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="laptops", alias="QDRANT_COLLECTION")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=1536, alias="OPENAI_EMBEDDING_DIMENSIONS")
    query_model: str = Field(default="gpt-5.4-mini", alias="OPENAI_QUERY_MODEL")
    answer_model: str = Field(default="gpt-5.4-mini", alias="OPENAI_ANSWER_MODEL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""

    return Settings()

