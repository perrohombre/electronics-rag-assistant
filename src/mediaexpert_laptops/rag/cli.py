"""CLI helpers for importing and indexing laptop data."""

from __future__ import annotations

from qdrant_client import QdrantClient

from mediaexpert_laptops.rag.embedding import OpenAIEmbedder
from mediaexpert_laptops.rag.index import LaptopIndex
from mediaexpert_laptops.rag.repository import LaptopRepository
from mediaexpert_laptops.rag.settings import get_settings


def import_catalog_main() -> None:
    """Import configured CSV into SQLite."""

    settings = get_settings()
    report = LaptopRepository(settings.catalog_db_path).import_csv(settings.dataset_csv_path)
    print(f"Imported {report.imported} laptops into {report.database_path}")


def index_catalog_main() -> None:
    """Index configured SQLite catalog into Qdrant."""

    settings = get_settings()
    repository = LaptopRepository(settings.catalog_db_path)
    embedder = OpenAIEmbedder(
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    index = LaptopIndex(
        client=QdrantClient(url=settings.qdrant_url),
        collection_name=settings.qdrant_collection,
        vector_size=settings.embedding_dimensions,
    )
    report = index.index_laptops(
        laptops=repository.list_laptops(),
        embedder=embedder,
        embedding_model=settings.embedding_model,
    )
    print(f"Indexed {report.indexed} laptops into {report.collection_name}")

