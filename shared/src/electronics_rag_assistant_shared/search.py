"""Shared models for query parsing and retrieval responses."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from electronics_rag_assistant_shared.catalog import InternalCategory


class SearchIntent(StrEnum):
    """Supported high-level query intents."""

    SEARCH = "search"
    COMPARISON = "comparison"


class CurrencyCode(StrEnum):
    """Currencies recognized in user queries."""

    USD = "USD"
    PLN = "PLN"


class ParsedSearchQuery(BaseModel):
    """Normalized representation of a user search query."""

    model_config = ConfigDict(use_enum_values=True)

    raw_query: str
    normalized_query: str
    intent: SearchIntent
    category: InternalCategory | None = None
    brand: str | None = None
    budget_value: float | None = None
    budget_currency: CurrencyCode | None = None
    availability: str | None = None
    semantic_query: str


class SearchRequest(BaseModel):
    """Request payload for semantic product retrieval."""

    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class ProductSearchHit(BaseModel):
    """Single search result returned by the retrieval layer."""

    model_config = ConfigDict(use_enum_values=True)

    source_id: str
    sku: str
    name: str
    brand: str | None = None
    internal_category: InternalCategory
    source_category_id: str
    price_usd: float | None = None
    availability: str
    url: str | None = None
    image_url: str | None = None
    description: str
    specs: dict[str, str] = Field(default_factory=dict)
    score: float


class SearchResponse(BaseModel):
    """Response payload for product retrieval."""

    query: str
    parsed_query: ParsedSearchQuery
    total_hits: int
    hits: list[ProductSearchHit] = Field(default_factory=list)
