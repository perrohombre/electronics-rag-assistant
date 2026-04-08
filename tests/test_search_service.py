from datetime import UTC, datetime

import pytest
from qdrant_client import QdrantClient

from electronics_rag_assistant_backend.indexing.qdrant_product_index import (
    EmbeddedProduct,
    QdrantProductIndex,
)
from electronics_rag_assistant_backend.services.catalog_search import CatalogSearchService
from electronics_rag_assistant_shared.catalog import InternalCategory, ProductRecord
from electronics_rag_assistant_shared.search import (
    CurrencyCode,
    ParsedSearchQuery,
    SearchIntent,
    SearchRequest,
)


class StubQueryEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            normalized = text.lower()
            if "monitor" in normalized:
                vectors.append([1.0, 0.0, 0.0])
            else:
                vectors.append([0.0, 1.0, 0.0])
        return vectors


class StubQueryAnalysisService:
    def __init__(self, parsed_query: ParsedSearchQuery) -> None:
        self._parsed_query = parsed_query

    def analyze(self, _raw_query: str) -> ParsedSearchQuery:
        return self._parsed_query


def _build_record(
    *,
    source_id: str,
    sku: str,
    name: str,
    brand: str,
    category: InternalCategory,
    price_usd: float,
    availability: str = "available",
) -> ProductRecord:
    return ProductRecord(
        source_id=source_id,
        sku=sku,
        name=name,
        brand=brand,
        internal_category=category,
        source_category_id=f"{category}-cat",
        price_usd=price_usd,
        availability=availability,
        url="https://example.com/product",
        image_url=None,
        description=f"{name} description",
        specs={"Spec": "Value"},
        last_synced_at=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
    )


def _seed_products(index: QdrantProductIndex) -> None:
    index.ensure_collection()
    index.upsert_products(
        [
            EmbeddedProduct(
                record=_build_record(
                    source_id="bestbuy:1",
                    sku="1",
                    name="Dell Monitor 27",
                    brand="Dell",
                    category=InternalCategory.MONITORS,
                    price_usd=349.0,
                ),
                vector=[1.0, 0.0, 0.0],
                document_text="Dell monitor for programming",
            ),
            EmbeddedProduct(
                record=_build_record(
                    source_id="bestbuy:2",
                    sku="2",
                    name="LG Monitor 32",
                    brand="LG",
                    category=InternalCategory.MONITORS,
                    price_usd=329.0,
                ),
                vector=[1.0, 0.0, 0.0],
                document_text="LG monitor for work",
            ),
            EmbeddedProduct(
                record=_build_record(
                    source_id="bestbuy:3",
                    sku="3",
                    name="Dell Headphones",
                    brand="Dell",
                    category=InternalCategory.HEADPHONES,
                    price_usd=129.0,
                    availability="unavailable",
                ),
                vector=[0.0, 1.0, 0.0],
                document_text="Dell headphones",
            ),
        ]
    )


def _build_parsed_query(
    *,
    raw_query: str,
    semantic_query: str,
    category: InternalCategory | None = None,
    brand: str | None = None,
    budget_value: float | None = None,
    budget_currency: CurrencyCode | None = None,
    availability: str | None = None,
) -> ParsedSearchQuery:
    return ParsedSearchQuery(
        raw_query=raw_query,
        normalized_query=raw_query.lower(),
        intent=SearchIntent.SEARCH,
        category=category,
        brand=brand,
        budget_value=budget_value,
        budget_currency=budget_currency,
        availability=availability,
        semantic_query=semantic_query,
    )


def test_search_service_returns_hits_matching_query_constraints() -> None:
    qdrant_client = QdrantClient(location=":memory:")
    index = QdrantProductIndex(qdrant_client, collection_name="products", vector_size=3)
    _seed_products(index)
    service = CatalogSearchService(
        qdrant_client=qdrant_client,
        embedder=StubQueryEmbedder(),
        query_analysis_service=StubQueryAnalysisService(
            _build_parsed_query(
                raw_query="monitor Dell do 400 USD",
                semantic_query="monitor Dell do 400 USD",
                category=InternalCategory.MONITORS,
                brand="Dell",
                budget_value=400.0,
                budget_currency=CurrencyCode.USD,
            )
        ),
        collection_name="products",
    )

    response = service.search(SearchRequest(query="monitor Dell do 400 USD", limit=5))

    assert response.parsed_query.category == InternalCategory.MONITORS
    assert response.parsed_query.brand == "Dell"
    assert response.total_hits == 1
    assert response.hits[0].source_id == "bestbuy:1"


def test_search_service_returns_no_hits_when_budget_filter_excludes_candidates() -> None:
    qdrant_client = QdrantClient(location=":memory:")
    index = QdrantProductIndex(qdrant_client, collection_name="products", vector_size=3)
    _seed_products(index)
    service = CatalogSearchService(
        qdrant_client=qdrant_client,
        embedder=StubQueryEmbedder(),
        query_analysis_service=StubQueryAnalysisService(
            _build_parsed_query(
                raw_query="monitor Dell do 200 USD",
                semantic_query="monitor Dell do 200 USD",
                category=InternalCategory.MONITORS,
                brand="Dell",
                budget_value=200.0,
                budget_currency=CurrencyCode.USD,
            )
        ),
        collection_name="products",
    )

    response = service.search(SearchRequest(query="monitor Dell do 200 USD", limit=5))

    assert response.total_hits == 0
    assert response.hits == []


def test_search_service_rejects_pln_budget_queries() -> None:
    qdrant_client = QdrantClient(location=":memory:")
    index = QdrantProductIndex(qdrant_client, collection_name="products", vector_size=3)
    _seed_products(index)
    service = CatalogSearchService(
        qdrant_client=qdrant_client,
        embedder=StubQueryEmbedder(),
        query_analysis_service=StubQueryAnalysisService(
            _build_parsed_query(
                raw_query="monitor do 1000 zl",
                semantic_query="monitor do 1000 zl",
                budget_value=1000.0,
                budget_currency=CurrencyCode.PLN,
            )
        ),
        collection_name="products",
    )

    with pytest.raises(ValueError, match="Budżet w PLN"):
        service.search(SearchRequest(query="monitor do 1000 zl", limit=5))


def test_search_service_requires_existing_index_collection() -> None:
    qdrant_client = QdrantClient(location=":memory:")
    service = CatalogSearchService(
        qdrant_client=qdrant_client,
        embedder=StubQueryEmbedder(),
        query_analysis_service=StubQueryAnalysisService(
            _build_parsed_query(
                raw_query="monitor Dell",
                semantic_query="monitor Dell",
                category=InternalCategory.MONITORS,
                brand="Dell",
            )
        ),
        collection_name="products",
    )

    with pytest.raises(RuntimeError, match="Indeks katalogu nie jest gotowy"):
        service.search(SearchRequest(query="monitor Dell", limit=5))


def test_search_service_performs_semantic_retrieval_without_category_filter() -> None:
    qdrant_client = QdrantClient(location=":memory:")
    index = QdrantProductIndex(qdrant_client, collection_name="products", vector_size=3)
    _seed_products(index)
    service = CatalogSearchService(
        qdrant_client=qdrant_client,
        embedder=StubQueryEmbedder(),
        query_analysis_service=StubQueryAnalysisService(
            _build_parsed_query(
                raw_query="czegos do programowania",
                semantic_query="monitor do programowania",
            )
        ),
        collection_name="products",
    )

    response = service.search(SearchRequest(query="czegos do programowania", limit=5))

    assert response.parsed_query.category is None
    assert response.parsed_query.brand is None
    assert response.total_hits == 2
    assert {hit.source_id for hit in response.hits} == {"bestbuy:1", "bestbuy:2"}
