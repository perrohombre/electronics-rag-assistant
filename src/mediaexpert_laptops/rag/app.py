"""FastAPI application for the laptop RAG assistant."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from qdrant_client import QdrantClient

from mediaexpert_laptops.rag.answer import AnswerService
from mediaexpert_laptops.rag.embedding import OpenAIEmbedder
from mediaexpert_laptops.rag.index import LaptopIndex
from mediaexpert_laptops.rag.models import (
    AnswerResponse,
    ImportReport,
    IndexReport,
    SearchRequest,
    SearchResponse,
)
from mediaexpert_laptops.rag.query_analysis import QueryAnalysisService
from mediaexpert_laptops.rag.repository import LaptopRepository
from mediaexpert_laptops.rag.search import SearchService
from mediaexpert_laptops.rag.settings import Settings, get_settings

app = FastAPI(title="Media Expert Laptop RAG")


def get_repository(settings: Settings = Depends(get_settings)) -> LaptopRepository:
    """Return repository dependency."""

    return LaptopRepository(settings.catalog_db_path)


def get_laptop_index(settings: Settings = Depends(get_settings)) -> LaptopIndex:
    """Return Qdrant index dependency."""

    return LaptopIndex(
        client=QdrantClient(url=settings.qdrant_url),
        collection_name=settings.qdrant_collection,
        vector_size=settings.embedding_dimensions,
    )


def get_embedder(settings: Settings = Depends(get_settings)) -> OpenAIEmbedder:
    """Return embedding provider."""

    return OpenAIEmbedder(
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )


def get_search_service(
    settings: Settings = Depends(get_settings),
    repository: LaptopRepository = Depends(get_repository),
    index: LaptopIndex = Depends(get_laptop_index),
    embedder: OpenAIEmbedder = Depends(get_embedder),
) -> SearchService:
    """Return search service."""

    return SearchService(
        repository=repository,
        index=index,
        embedder=embedder,
        query_analysis=QueryAnalysisService(
            api_key=settings.openai_api_key,
            model=settings.query_model,
            known_brands=repository.list_brands(),
        ),
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Health endpoint."""

    return {"status": "ok"}


@app.post("/catalog/import", response_model=ImportReport)
def import_catalog(
    settings: Settings = Depends(get_settings),
    repository: LaptopRepository = Depends(get_repository),
) -> ImportReport:
    """Import CSV into SQLite."""

    return repository.import_csv(settings.dataset_csv_path)


@app.post("/catalog/index", response_model=IndexReport)
def index_catalog(
    settings: Settings = Depends(get_settings),
    repository: LaptopRepository = Depends(get_repository),
    index: LaptopIndex = Depends(get_laptop_index),
    embedder: OpenAIEmbedder = Depends(get_embedder),
) -> IndexReport:
    """Index imported laptops in Qdrant."""

    return index.index_laptops(
        laptops=repository.list_laptops(),
        embedder=embedder,
        embedding_model=settings.embedding_model,
    )


@app.post("/search", response_model=SearchResponse)
def search_laptops(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """Search laptops with explicit filters plus semantic search."""

    return service.search(request)


@app.post("/answer", response_model=AnswerResponse)
def answer_laptops(
    request: SearchRequest,
    settings: Settings = Depends(get_settings),
    search_service: SearchService = Depends(get_search_service),
) -> AnswerResponse:
    """Generate grounded answer from search results."""

    return AnswerService(
        search_service=search_service,
        api_key=settings.openai_api_key,
        model=settings.answer_model,
    ).answer(request)
