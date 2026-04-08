from __future__ import annotations

import httpx
import pytest
from frontend.api_client import (
    ConnectionAPIError,
    FrontendAPIClient,
    NotFoundAPIError,
    ServiceUnavailableAPIError,
    ValidationAPIError,
    build_api_base_url,
)

from electronics_rag_assistant_shared.catalog import InternalCategory
from electronics_rag_assistant_shared.search import (
    AssistantAnswer,
    ParsedSearchQuery,
    ProductSearchHit,
    ProductSummary,
    SearchIntent,
    SearchResponse,
)


class StubHTTPClient:
    def __init__(
        self,
        *,
        response: httpx.Response | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._response = response
        self._exc = exc
        self.calls: list[dict] = []

    def request(self, method: str, path: str, json=None):  # noqa: ANN001
        self.calls.append({"method": method, "path": path, "json": json})
        if self._exc is not None:
            raise self._exc
        return self._response


def _build_search_response() -> SearchResponse:
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
                score=0.95,
            )
        ],
        assistant_answer=AssistantAnswer(
            message="Dell Monitor 27 wygląda najlepiej.",
            cited_source_ids=["bestbuy:1"],
        ),
    )


def test_build_api_base_url_prefers_explicit_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_BASE_URL", "http://api.local:9000/")
    monkeypatch.setenv("API_HOST", "ignored")
    monkeypatch.setenv("API_PORT", "9999")

    assert build_api_base_url() == "http://api.local:9000"


def test_build_api_base_url_falls_back_to_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.setenv("API_HOST", "127.0.0.2")
    monkeypatch.setenv("API_PORT", "8100")

    assert build_api_base_url() == "http://127.0.0.2:8100"


def test_frontend_api_client_returns_typed_search_response() -> None:
    payload = _build_search_response().model_dump(mode="json")
    client = FrontendAPIClient(
        base_url="http://api.local",
        client=StubHTTPClient(
            response=httpx.Response(
                200,
                json=payload,
                request=httpx.Request("POST", "http://api.local/api/v1/assistant/search"),
            )
        ),
    )

    response = client.search_products(query="monitor Dell do 400 USD", limit=5)

    assert response.total_hits == 1
    assert response.assistant_answer is not None
    assert response.hits[0].source_id == "bestbuy:1"


def test_frontend_api_client_maps_422_to_validation_error() -> None:
    client = FrontendAPIClient(
        base_url="http://api.local",
        client=StubHTTPClient(
            response=httpx.Response(
                422,
                json={"detail": "Budżet w PLN nie jest jeszcze obsługiwany."},
                request=httpx.Request("POST", "http://api.local/api/v1/assistant/search"),
            )
        ),
    )

    with pytest.raises(ValidationAPIError, match="Budżet w PLN"):
        client.search_products(query="monitor do 1000 zl", limit=5)


def test_frontend_api_client_maps_404_to_not_found_error() -> None:
    client = FrontendAPIClient(
        base_url="http://api.local",
        client=StubHTTPClient(
            response=httpx.Response(
                404,
                json={"detail": "Nie znaleziono produktu: bestbuy:404"},
                request=httpx.Request("GET", "http://api.local/api/v1/products/bestbuy:404"),
            )
        ),
    )

    with pytest.raises(NotFoundAPIError, match="bestbuy:404"):
        client.get_product("bestbuy:404")


def test_frontend_api_client_maps_503_to_service_unavailable_error() -> None:
    client = FrontendAPIClient(
        base_url="http://api.local",
        client=StubHTTPClient(
            response=httpx.Response(
                503,
                json={"detail": "Indeks katalogu nie jest gotowy."},
                request=httpx.Request("POST", "http://api.local/api/v1/assistant/search"),
            )
        ),
    )

    with pytest.raises(ServiceUnavailableAPIError, match="Indeks katalogu"):
        client.search_products(query="monitor Dell", limit=5)


def test_frontend_api_client_maps_connection_failures_to_connection_error() -> None:
    request = httpx.Request("POST", "http://api.local/api/v1/assistant/search")
    client = FrontendAPIClient(
        base_url="http://api.local",
        client=StubHTTPClient(exc=httpx.ConnectError("boom", request=request)),
    )

    with pytest.raises(ConnectionAPIError, match="http://api.local"):
        client.search_products(query="monitor Dell", limit=5)


def test_frontend_api_client_returns_typed_product_summary() -> None:
    product = ProductSummary(
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
    )
    client = FrontendAPIClient(
        base_url="http://api.local",
        client=StubHTTPClient(
            response=httpx.Response(
                200,
                json=product.model_dump(mode="json"),
                request=httpx.Request("GET", "http://api.local/api/v1/products/bestbuy:1"),
            )
        ),
    )

    response = client.get_product("bestbuy:1")

    assert response.name == "Dell Monitor 27"
    assert response.internal_category == InternalCategory.MONITORS
