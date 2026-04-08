from fastapi.testclient import TestClient

from electronics_rag_assistant_backend.dependencies import get_catalog_search_service
from electronics_rag_assistant_backend.main import app
from electronics_rag_assistant_shared.catalog import InternalCategory
from electronics_rag_assistant_shared.search import (
    ParsedSearchQuery,
    ProductSearchHit,
    SearchIntent,
    SearchResponse,
)


class StubCatalogSearchService:
    def search(self, _request) -> SearchResponse:
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
                    description="Good monitor",
                    specs={"Spec": "Value"},
                    score=0.92,
                )
            ],
        )


class FailingCatalogSearchService:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def search(self, _request) -> SearchResponse:
        raise self._exc


def test_assistant_search_endpoint_returns_hits() -> None:
    app.dependency_overrides[get_catalog_search_service] = lambda: StubCatalogSearchService()
    client = TestClient(app)

    response = client.post("/api/v1/assistant/search", json={"query": "monitor Dell do 400 USD"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["total_hits"] == 1
    assert response.json()["hits"][0]["source_id"] == "bestbuy:1"


def test_assistant_search_endpoint_maps_pln_budget_to_422() -> None:
    app.dependency_overrides[get_catalog_search_service] = (
        lambda: FailingCatalogSearchService(
            ValueError("Budżet w PLN nie jest jeszcze obsługiwany.")
        )
    )
    client = TestClient(app)

    response = client.post("/api/v1/assistant/search", json={"query": "monitor do 1000 zl"})

    app.dependency_overrides.clear()
    assert response.status_code == 422
    assert "Budżet w PLN" in response.json()["detail"]


def test_assistant_search_endpoint_maps_missing_index_to_503() -> None:
    app.dependency_overrides[get_catalog_search_service] = (
        lambda: FailingCatalogSearchService(RuntimeError("Indeks katalogu nie jest gotowy."))
    )
    client = TestClient(app)

    response = client.post("/api/v1/assistant/search", json={"query": "monitor Dell"})

    app.dependency_overrides.clear()
    assert response.status_code == 503
    assert "Indeks katalogu" in response.json()["detail"]
