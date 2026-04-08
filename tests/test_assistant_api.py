from fastapi.testclient import TestClient

from electronics_rag_assistant_backend.dependencies import get_assistant_service
from electronics_rag_assistant_backend.main import app
from electronics_rag_assistant_shared.catalog import InternalCategory
from electronics_rag_assistant_shared.search import (
    AssistantAnswer,
    CompareResponse,
    ParsedSearchQuery,
    ProductSummary,
    SearchIntent,
    SearchResponse,
)


class StubAssistantService:
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
            hits=[],
            assistant_answer=AssistantAnswer(
                message="Dell Monitor 27 wygląda najlepiej do pracy i programowania.",
                cited_source_ids=["bestbuy:1"],
            ),
        )

    def compare(self, _request) -> CompareResponse:
        return CompareResponse(
            query="do programowania",
            product_ids=["bestbuy:1", "bestbuy:2"],
            products=[
                ProductSummary(
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
                ),
                ProductSummary(
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
                ),
            ],
            assistant_answer=AssistantAnswer(
                message="Dell Monitor 27 jest tańszy, a Dell Monitor 32 większy.",
                cited_source_ids=["bestbuy:1", "bestbuy:2"],
            ),
        )

    def get_product(self, product_id: str) -> ProductSummary:
        if product_id != "bestbuy:1":
            raise LookupError(f"Nie znaleziono produktu: {product_id}")
        return ProductSummary(
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
        )


class FailingAssistantService:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def search(self, _request) -> SearchResponse:
        raise self._exc

    def compare(self, _request) -> CompareResponse:
        raise self._exc

    def get_product(self, _product_id: str) -> ProductSummary:
        raise self._exc


def test_assistant_search_endpoint_returns_answer_and_hits() -> None:
    app.dependency_overrides[get_assistant_service] = lambda: StubAssistantService()
    client = TestClient(app)

    response = client.post("/api/v1/assistant/search", json={"query": "monitor Dell do 400 USD"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["assistant_answer"]["cited_source_ids"] == ["bestbuy:1"]


def test_assistant_search_endpoint_maps_pln_budget_to_422() -> None:
    app.dependency_overrides[get_assistant_service] = (
        lambda: FailingAssistantService(ValueError("Budżet w PLN nie jest jeszcze obsługiwany."))
    )
    client = TestClient(app)

    response = client.post("/api/v1/assistant/search", json={"query": "monitor do 1000 zl"})

    app.dependency_overrides.clear()
    assert response.status_code == 422
    assert "Budżet w PLN" in response.json()["detail"]


def test_assistant_compare_endpoint_returns_grounded_comparison() -> None:
    app.dependency_overrides[get_assistant_service] = lambda: StubAssistantService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/assistant/compare",
        json={"product_ids": ["bestbuy:1", "bestbuy:2"], "query": "do programowania"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["assistant_answer"]["cited_source_ids"] == ["bestbuy:1", "bestbuy:2"]
    assert len(response.json()["products"]) == 2


def test_assistant_compare_endpoint_maps_missing_products_to_404() -> None:
    app.dependency_overrides[get_assistant_service] = (
        lambda: FailingAssistantService(LookupError("Nie znaleziono produktu: bestbuy:404"))
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/assistant/compare",
        json={"product_ids": ["bestbuy:1", "bestbuy:404"]},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert "bestbuy:404" in response.json()["detail"]


def test_product_details_endpoint_returns_product_summary() -> None:
    app.dependency_overrides[get_assistant_service] = lambda: StubAssistantService()
    client = TestClient(app)

    response = client.get("/api/v1/products/bestbuy:1")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["source_id"] == "bestbuy:1"


def test_product_details_endpoint_maps_missing_product_to_404() -> None:
    app.dependency_overrides[get_assistant_service] = (
        lambda: FailingAssistantService(LookupError("Nie znaleziono produktu: bestbuy:404"))
    )
    client = TestClient(app)

    response = client.get("/api/v1/products/bestbuy:404")

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert "bestbuy:404" in response.json()["detail"]
