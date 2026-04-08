import httpx
import pytest

from electronics_rag_assistant_backend.source.bestbuy_client import (
    BestBuyAuthenticationError,
    BestBuyClient,
    BestBuyRequestError,
)


def _build_client(transport: httpx.BaseTransport) -> BestBuyClient:
    return BestBuyClient(
        api_key="test-key",
        base_url="https://api.bestbuy.com/v1",
        timeout_seconds=5.0,
        max_retries=2,
        rate_limit_per_second=1000.0,
        transport=transport,
    )


def test_client_requires_api_key() -> None:
    with pytest.raises(BestBuyAuthenticationError):
        BestBuyClient(
            api_key="",
            base_url="https://api.bestbuy.com/v1",
            timeout_seconds=5.0,
            max_retries=2,
            rate_limit_per_second=5.0,
        )


def test_get_categories_returns_items_from_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/categories(name=\"Laptops\")"
        assert request.url.params["apiKey"] == "test-key"
        return httpx.Response(
            200,
            json={
                "categories": [
                    {
                        "id": "pcmcat1",
                        "name": "Laptops",
                        "path": [{"name": "Computers"}],
                        "url": "x",
                    }
                ],
                "totalPages": 1,
                "currentPage": 1,
                "total": 1,
            },
        )

    client = _build_client(httpx.MockTransport(handler))
    try:
        categories = client.get_categories('name="Laptops"')
    finally:
        client.close()

    assert categories == [
        {"id": "pcmcat1", "name": "Laptops", "path": [{"name": "Computers"}], "url": "x"}
    ]


def test_get_products_for_category_retries_transient_errors() -> None:
    responses = iter(
        [
            httpx.Response(503, text="temporary outage"),
            httpx.Response(
                200,
                json={
                    "products": [{"sku": 123, "name": "Laptop"}],
                    "totalPages": 1,
                    "currentPage": 1,
                    "total": 1,
                },
            ),
        ]
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return next(responses)

    client = _build_client(httpx.MockTransport(handler))
    try:
        products = client.get_products_for_category("pcmcat1", page_size=100, max_pages=1)
    finally:
        client.close()

    assert products == [{"sku": 123, "name": "Laptop"}]


def test_get_products_for_category_raises_on_non_recoverable_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad request")

    client = _build_client(httpx.MockTransport(handler))
    with pytest.raises(BestBuyRequestError):
        try:
            client.get_products_for_category("pcmcat1", page_size=100, max_pages=1)
        finally:
            client.close()
