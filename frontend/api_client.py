"""Thin frontend HTTP client for the Streamlit demo application."""

from __future__ import annotations

import os
from typing import Any

import httpx

from electronics_rag_assistant_shared.search import (
    CompareRequest,
    CompareResponse,
    ProductSummary,
    SearchRequest,
    SearchResponse,
)


class FrontendAPIError(Exception):
    """Base error surfaced by the Streamlit API client."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class ValidationAPIError(FrontendAPIError):
    """Raised when the backend rejects the request payload or query."""


class NotFoundAPIError(FrontendAPIError):
    """Raised when the backend cannot find the requested resource."""


class ServiceUnavailableAPIError(FrontendAPIError):
    """Raised when the backend or one of its dependencies is unavailable."""


class ConnectionAPIError(FrontendAPIError):
    """Raised when the Streamlit frontend cannot connect to the backend."""


class UnexpectedAPIError(FrontendAPIError):
    """Raised when the backend returns an unexpected failure."""


def build_api_base_url() -> str:
    """Resolve the backend base URL from environment variables."""

    configured_url = os.getenv("API_BASE_URL", "").strip()
    if configured_url:
        return configured_url.rstrip("/")

    api_host = os.getenv("API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    api_port = os.getenv("API_PORT", "8000").strip() or "8000"
    return f"http://{api_host}:{api_port}"


class FrontendAPIClient:
    """Small typed wrapper around the FastAPI backend."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(base_url=self._base_url, timeout=timeout_seconds)

    @property
    def base_url(self) -> str:
        """Return the configured backend base URL."""

        return self._base_url

    def search_products(self, *, query: str, limit: int) -> SearchResponse:
        """Execute the assistant search flow."""

        payload = SearchRequest(query=query, limit=limit).model_dump(mode="json")
        data = self._request_json("POST", "/api/v1/assistant/search", json=payload)
        return SearchResponse.model_validate(data)

    def compare_products(
        self,
        *,
        product_ids: list[str],
        query: str | None = None,
    ) -> CompareResponse:
        """Compare exactly two catalog products."""

        payload = CompareRequest(product_ids=product_ids, query=query).model_dump(
            mode="json",
            exclude_none=True,
        )
        data = self._request_json("POST", "/api/v1/assistant/compare", json=payload)
        return CompareResponse.model_validate(data)

    def get_product(self, product_id: str) -> ProductSummary:
        """Fetch one product by source identifier."""

        data = self._request_json("GET", f"/api/v1/products/{product_id}")
        return ProductSummary.model_validate(data)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._client.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise ConnectionAPIError(
                "Nie udało się połączyć z lokalnym API. "
                f"Sprawdź, czy backend działa pod {self._base_url} "
                "oraz czy `API_BASE_URL` / `API_HOST` / `API_PORT` są poprawne."
            ) from exc

        if 200 <= response.status_code < 300:
            return self._decode_json(response)

        detail = self._extract_detail(response)
        if response.status_code == 422:
            raise ValidationAPIError(detail)
        if response.status_code == 404:
            raise NotFoundAPIError(detail)
        if response.status_code == 503:
            raise ServiceUnavailableAPIError(detail)
        raise UnexpectedAPIError(detail)

    def _decode_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError as exc:
            raise UnexpectedAPIError("Backend zwrócił niepoprawną odpowiedź JSON.") from exc

    def _extract_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        detail = payload.get("detail") if isinstance(payload, dict) else None
        if isinstance(detail, str) and detail.strip():
            return detail.strip()

        return f"Backend zwrócił błąd HTTP {response.status_code}."
