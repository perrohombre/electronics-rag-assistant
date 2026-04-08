"""Dependency wiring for FastAPI routes."""

from collections.abc import Generator

from fastapi import Depends

from electronics_rag_assistant_backend.services.catalog_sync import CatalogSyncService
from electronics_rag_assistant_backend.settings import Settings, get_settings
from electronics_rag_assistant_backend.source.bestbuy_client import BestBuyClient
from electronics_rag_assistant_backend.storage.sqlite_catalog_repository import (
    SQLiteCatalogRepository,
)


def get_catalog_repository(
    settings: Settings = Depends(get_settings),
) -> SQLiteCatalogRepository:
    """Return the SQLite-backed catalog repository."""

    return SQLiteCatalogRepository(settings.catalog_db_path)


def get_bestbuy_client(
    settings: Settings = Depends(get_settings),
) -> Generator[BestBuyClient, None, None]:
    """Yield a configured Best Buy client and close it after the request."""

    client = BestBuyClient(
        api_key=settings.bestbuy_api_key,
        base_url=settings.bestbuy_base_url,
        timeout_seconds=settings.bestbuy_timeout_seconds,
        max_retries=settings.bestbuy_max_retries,
        rate_limit_per_second=settings.bestbuy_rate_limit_per_second,
    )
    try:
        yield client
    finally:
        client.close()


def get_catalog_sync_service(
    settings: Settings = Depends(get_settings),
    repository: SQLiteCatalogRepository = Depends(get_catalog_repository),
    bestbuy_client: BestBuyClient = Depends(get_bestbuy_client),
) -> CatalogSyncService:
    """Return the catalog sync service."""

    return CatalogSyncService(
        repository=repository,
        bestbuy_client=bestbuy_client,
        page_size=settings.bestbuy_page_size,
        max_pages_per_category=settings.bestbuy_max_pages_per_category,
    )
