from datetime import UTC, datetime

import pytest

from electronics_rag_assistant_backend.services.assistant_service import AssistantService
from electronics_rag_assistant_backend.storage.sqlite_catalog_repository import (
    SQLiteCatalogRepository,
)
from electronics_rag_assistant_shared.catalog import (
    CategorySnapshot,
    InternalCategory,
    ProductRecord,
)
from electronics_rag_assistant_shared.search import (
    AssistantAnswer,
    CompareRequest,
    ParsedSearchQuery,
    ProductSearchHit,
    SearchIntent,
    SearchRequest,
    SearchResponse,
)


class StubCatalogSearchService:
    def search(self, _request: SearchRequest) -> SearchResponse:
        return SearchResponse(
            query="monitor Dell do 400 USD",
            parsed_query=ParsedSearchQuery(
                raw_query="monitor Dell do 400 USD",
                normalized_query="monitor dell do 400 usd",
                intent=SearchIntent.SEARCH,
                category=InternalCategory.MONITORS,
                brand="Dell",
                budget_value=400.0,
                budget_currency="USD",
                availability="available",
                semantic_query="monitor Dell do 400 USD",
            ),
            total_hits=1,
            hits=[
                ProductSearchHit(
                    source_id="bestbuy:1",
                    sku="1",
                    name="Dell Monitor 27",
                    brand="Dell",
                    internal_category=InternalCategory.MONITORS,
                    source_category_id="monitors-cat",
                    price_usd=349.0,
                    availability="available",
                    url="https://example.com/1",
                    image_url=None,
                    description="Monitor do pracy i programowania",
                    specs={"Screen": "27 in"},
                    score=0.93,
                )
            ],
        )


class StubAnswerService:
    def __init__(self) -> None:
        self.search_calls: list[dict] = []
        self.compare_calls: list[dict] = []

    def generate_search_answer(self, *, query, parsed_query, hits) -> AssistantAnswer:
        self.search_calls.append(
            {
                "query": query,
                "parsed_query": parsed_query,
                "hits": hits,
            }
        )
        return AssistantAnswer(
            message="Dell Monitor 27 wygląda najlepiej do tego zastosowania.",
            cited_source_ids=["bestbuy:1"],
        )

    def generate_comparison_answer(self, *, query, products) -> AssistantAnswer:
        self.compare_calls.append(
            {
                "query": query,
                "products": products,
            }
        )
        return AssistantAnswer(
            message="Dell Monitor 27 jest tańszy, a Dell Monitor 32 większy.",
            cited_source_ids=[product.source_id for product in products],
        )


def _seed_repository(tmp_path) -> SQLiteCatalogRepository:
    repository = SQLiteCatalogRepository(tmp_path / "catalog.db")
    synced_at = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    repository.replace_category_snapshot(
        CategorySnapshot(
            internal_category=InternalCategory.MONITORS,
            source_category_id="monitors-cat",
            source_category_name="Monitors",
            source_category_path=["Displays", "Monitors"],
            source_category_url="https://example.com/monitors",
            product_count=2,
            last_synced_at=synced_at,
        ),
        [
            ProductRecord(
                source_id="bestbuy:1",
                sku="1",
                name="Dell Monitor 27",
                brand="Dell",
                internal_category=InternalCategory.MONITORS,
                source_category_id="monitors-cat",
                price_usd=349.0,
                availability="available",
                url="https://example.com/1",
                image_url=None,
                description="Monitor do pracy",
                specs={"Screen": "27 in"},
                last_synced_at=synced_at,
            ),
            ProductRecord(
                source_id="bestbuy:2",
                sku="2",
                name="Dell Monitor 32",
                brand="Dell",
                internal_category=InternalCategory.MONITORS,
                source_category_id="monitors-cat",
                price_usd=429.0,
                availability="available",
                url="https://example.com/2",
                image_url=None,
                description="Większy monitor do pracy",
                specs={"Screen": "32 in"},
                last_synced_at=synced_at,
            ),
        ],
    )
    return repository


def test_assistant_service_adds_grounded_answer_to_search_response(tmp_path) -> None:
    repository = _seed_repository(tmp_path)
    answer_service = StubAnswerService()
    service = AssistantService(
        catalog_search_service=StubCatalogSearchService(),
        answer_service=answer_service,
        repository=repository,
    )

    response = service.search(SearchRequest(query="monitor Dell do 400 USD"))

    assert response.assistant_answer is not None
    assert response.assistant_answer.cited_source_ids == ["bestbuy:1"]
    assert len(answer_service.search_calls) == 1


def test_assistant_service_compares_two_products_in_request_order(tmp_path) -> None:
    repository = _seed_repository(tmp_path)
    answer_service = StubAnswerService()
    service = AssistantService(
        catalog_search_service=StubCatalogSearchService(),
        answer_service=answer_service,
        repository=repository,
    )

    response = service.compare(
        CompareRequest(product_ids=["bestbuy:2", "bestbuy:1"], query="do programowania")
    )

    assert [product.source_id for product in response.products] == ["bestbuy:2", "bestbuy:1"]
    assert response.assistant_answer.cited_source_ids == ["bestbuy:2", "bestbuy:1"]
    assert len(answer_service.compare_calls) == 1


def test_assistant_service_raises_not_found_for_missing_compare_product(tmp_path) -> None:
    repository = _seed_repository(tmp_path)
    service = AssistantService(
        catalog_search_service=StubCatalogSearchService(),
        answer_service=StubAnswerService(),
        repository=repository,
    )

    with pytest.raises(LookupError, match="bestbuy:404"):
        service.compare(CompareRequest(product_ids=["bestbuy:1", "bestbuy:404"]))


def test_assistant_service_returns_product_details(tmp_path) -> None:
    repository = _seed_repository(tmp_path)
    service = AssistantService(
        catalog_search_service=StubCatalogSearchService(),
        answer_service=StubAnswerService(),
        repository=repository,
    )

    product = service.get_product("bestbuy:1")

    assert product.source_id == "bestbuy:1"
    assert product.name == "Dell Monitor 27"
