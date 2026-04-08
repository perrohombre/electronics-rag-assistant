"""Best Buy API client with rate limiting and retry support."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic, sleep
from typing import Any

import httpx


class BestBuyAPIError(RuntimeError):
    """Base exception for Best Buy API integration failures."""


class BestBuyAuthenticationError(BestBuyAPIError):
    """Raised when the Best Buy API key is missing or invalid."""


class BestBuyRequestError(BestBuyAPIError):
    """Raised when the Best Buy API returns a non-recoverable error."""


@dataclass(slots=True)
class BestBuyCollectionPage:
    """Single paginated response from a Best Buy collection endpoint."""

    items: list[dict[str, Any]]
    total_pages: int
    current_page: int
    total: int


class RequestThrottler:
    """Simple process-local throttler for API requests."""

    def __init__(self, requests_per_second: float) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")

        self._minimum_interval = 1.0 / requests_per_second
        self._lock = Lock()
        self._last_request_started = 0.0

    def wait(self) -> None:
        """Sleep if needed to keep requests under the configured rate."""

        with self._lock:
            now = monotonic()
            elapsed = now - self._last_request_started
            if self._last_request_started and elapsed < self._minimum_interval:
                sleep(self._minimum_interval - elapsed)
            self._last_request_started = monotonic()


class BestBuyClient:
    """Thin Best Buy API wrapper for products and categories."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        rate_limit_per_second: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise BestBuyAuthenticationError("BESTBUY_API_KEY is required")

        self._api_key = api_key
        self._max_retries = max_retries
        self._throttler = RequestThrottler(rate_limit_per_second)
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self._client.close()

    def get_categories(
        self,
        search_expression: str,
        *,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Return categories matching the provided search expression."""

        page = self._fetch_collection_page(
            resource="categories",
            search_expression=search_expression,
            items_key="categories",
            page=1,
            page_size=page_size,
            show="id,name,path,url",
        )
        return page.items

    def get_products_for_category(
        self,
        category_id: str,
        *,
        page_size: int,
        max_pages: int,
    ) -> list[dict[str, Any]]:
        """Return paginated products for a Best Buy category."""

        search_expression = f"categoryPath.id={category_id}&active=true"
        pages_to_fetch = max(max_pages, 1)
        current_page = 1
        collected: list[dict[str, Any]] = []

        while current_page <= pages_to_fetch:
            page = self._fetch_collection_page(
                resource="products",
                search_expression=search_expression,
                items_key="products",
                page=current_page,
                page_size=page_size,
                show=(
                    "sku,name,manufacturer,salePrice,regularPrice,onlineAvailability,"
                    "orderable,url,image,longDescription,shortDescription,details,modelNumber,"
                    "categoryPath"
                ),
            )
            collected.extend(page.items)
            if current_page >= page.total_pages:
                break
            current_page += 1

        return collected

    def _fetch_collection_page(
        self,
        *,
        resource: str,
        search_expression: str,
        items_key: str,
        page: int,
        page_size: int,
        show: str,
    ) -> BestBuyCollectionPage:
        path = f"/{resource}({search_expression})"
        response = self._request(
            path,
            params={
                "apiKey": self._api_key,
                "format": "json",
                "page": page,
                "pageSize": page_size,
                "show": show,
            },
        )
        payload = response.json()
        return BestBuyCollectionPage(
            items=payload.get(items_key, []),
            total_pages=int(payload.get("totalPages", 1)),
            current_page=int(payload.get("currentPage", page)),
            total=int(payload.get("total", len(payload.get(items_key, [])))),
        )

    def _request(self, path: str, *, params: dict[str, Any]) -> httpx.Response:
        attempt = 0

        while True:
            self._throttler.wait()
            try:
                response = self._client.get(path, params=params)
            except httpx.HTTPError as exc:
                if attempt >= self._max_retries:
                    raise BestBuyRequestError("Best Buy request failed") from exc
                attempt += 1
                sleep(0.5 * attempt)
                continue

            if response.status_code < 400:
                return response

            if response.status_code == 403:
                raise BestBuyAuthenticationError(response.text or "Best Buy authentication failed")

            if response.status_code in {429, 500, 502, 503, 504} and attempt < self._max_retries:
                attempt += 1
                sleep(0.5 * attempt)
                continue

            raise BestBuyRequestError(
                f"Best Buy request failed with status {response.status_code}: {response.text}"
            )
