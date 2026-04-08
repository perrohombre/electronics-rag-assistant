"""Dependency wiring for FastAPI routes."""

from collections.abc import Generator

from fastapi import Depends
from qdrant_client import QdrantClient

from electronics_rag_assistant_backend.indexing.openai_embedder import OpenAIEmbedder
from electronics_rag_assistant_backend.indexing.qdrant_product_index import QdrantProductIndex
from electronics_rag_assistant_backend.services.catalog_index import CatalogIndexService
from electronics_rag_assistant_backend.services.catalog_search import CatalogSearchService
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


def get_qdrant_client(
    settings: Settings = Depends(get_settings),
) -> Generator[QdrantClient, None, None]:
    """Yield a configured Qdrant client and close it after the request."""

    client = QdrantClient(url=settings.qdrant_url)
    try:
        yield client
    finally:
        client.close()


def get_product_index(
    settings: Settings = Depends(get_settings),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> QdrantProductIndex:
    """Return the configured Qdrant product index wrapper."""

    return QdrantProductIndex(
        qdrant_client,
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.openai_embedding_dimensions,
    )


def get_embedder(
    settings: Settings = Depends(get_settings),
) -> OpenAIEmbedder:
    """Return the configured embedding provider."""

    return OpenAIEmbedder(
        api_key=settings.openai_api_key,
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
        batch_size=settings.openai_embedding_batch_size,
    )


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


def get_catalog_index_service(
    settings: Settings = Depends(get_settings),
    repository: SQLiteCatalogRepository = Depends(get_catalog_repository),
    product_index: QdrantProductIndex = Depends(get_product_index),
    embedder: OpenAIEmbedder = Depends(get_embedder),
) -> CatalogIndexService:
    """Return the catalog indexing service."""

    return CatalogIndexService(
        repository=repository,
        product_index=product_index,
        embedder=embedder,
        embedding_model=settings.openai_embedding_model,
    )


def get_catalog_search_service(
    settings: Settings = Depends(get_settings),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    embedder: OpenAIEmbedder = Depends(get_embedder),
) -> CatalogSearchService:
    """Return the semantic retrieval service."""

    return CatalogSearchService(
        qdrant_client=qdrant_client,
        embedder=embedder,
        collection_name=settings.qdrant_collection_name,
    )
