"""LLM-backed query analysis with deterministic fallback behavior."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from electronics_rag_assistant_backend.query.parser import (
    normalize_query,
    parse_search_query_fallback,
)
from electronics_rag_assistant_backend.storage.sqlite_catalog_repository import (
    SQLiteCatalogRepository,
)
from electronics_rag_assistant_shared.catalog import InternalCategory
from electronics_rag_assistant_shared.search import CurrencyCode, ParsedSearchQuery, SearchIntent


class LLMQueryAnalysisOutput(BaseModel):
    """Structured output returned by the LLM query analysis step."""

    model_config = ConfigDict(extra="ignore")

    intent: SearchIntent
    category: str | None = None
    brand: str | None = None
    budget_value: float | None = None
    budget_currency: str | None = None
    availability: str | None = None
    semantic_query: str | None = None


class QueryAnalysisService:
    """Analyze a user query with an LLM and normalize it for retrieval."""

    def __init__(
        self,
        *,
        repository: SQLiteCatalogRepository,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_brands: int,
        max_output_tokens: int,
        client: Any | None = None,
    ) -> None:
        self._repository = repository
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_brands = max_brands
        self._max_output_tokens = max_output_tokens
        self._client = client or (OpenAI(api_key=api_key) if api_key else None)

    def analyze(self, raw_query: str) -> ParsedSearchQuery:
        """Return a normalized parsed query, preferring structured LLM analysis."""

        if self._client is None:
            return parse_search_query_fallback(raw_query)

        brand_candidates = self._repository.list_distinct_brands(self._max_brands)
        normalized_query = normalize_query(raw_query)

        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=self._build_instructions(),
                input=self._build_input(raw_query, brand_candidates),
                text_format=LLMQueryAnalysisOutput,
                temperature=0,
                max_output_tokens=self._max_output_tokens,
                timeout=self._timeout_seconds,
            )
            parsed_output = response.output_parsed
            if parsed_output is None:
                raise ValueError("LLM query analysis returned no parsed output")
            return self._normalize_output(
                raw_query=raw_query,
                normalized_query=normalized_query,
                parsed_output=parsed_output,
                brand_candidates=brand_candidates,
            )
        except Exception:
            return parse_search_query_fallback(raw_query)

    def _build_instructions(self) -> str:
        return (
            "You analyze ecommerce product-search queries and return structured data only. "
            "Use only the allowed categories and brand candidates from the input context. "
            "If category, brand, budget, currency, or availability are not clearly stated, "
            "return null for that field. Do not guess missing filters. "
            "Do not infer category or brand from weak hints. "
            "If the user explicitly asks to compare products, set intent to comparison; "
            "otherwise set intent to search. "
            "If semantic_query is not obvious, return null."
        )

    def _build_input(self, raw_query: str, brand_candidates: list[str]) -> str:
        payload = {
            "user_query": raw_query.strip(),
            "allowed_categories": [category.value for category in InternalCategory],
            "brand_candidates": brand_candidates,
            "notes": {
                "currency_policy": (
                    "Return PLN only when the user explicitly uses PLN or zl/zł. "
                    "Otherwise return USD only when clearly stated."
                ),
                "optional_fields": (
                    "category, brand, budget_value, budget_currency, availability, and "
                    "semantic_query may be null."
                ),
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    def _normalize_output(
        self,
        *,
        raw_query: str,
        normalized_query: str,
        parsed_output: LLMQueryAnalysisOutput,
        brand_candidates: list[str],
    ) -> ParsedSearchQuery:
        brand_lookup = {brand.casefold(): brand for brand in brand_candidates}
        category_lookup = {category.value.casefold(): category for category in InternalCategory}
        currency_lookup = {
            CurrencyCode.USD.value.casefold(): CurrencyCode.USD,
            CurrencyCode.PLN.value.casefold(): CurrencyCode.PLN,
        }
        availability_lookup = {
            "available": "available",
            "unavailable": "unavailable",
        }

        normalized_brand = None
        if parsed_output.brand:
            normalized_brand = brand_lookup.get(parsed_output.brand.strip().casefold())

        normalized_category = None
        if parsed_output.category:
            normalized_category = category_lookup.get(parsed_output.category.strip().casefold())

        normalized_currency = None
        if parsed_output.budget_currency:
            normalized_currency = currency_lookup.get(
                parsed_output.budget_currency.strip().casefold()
            )

        normalized_availability = None
        if parsed_output.availability:
            normalized_availability = availability_lookup.get(
                parsed_output.availability.strip().casefold()
            )

        semantic_query = raw_query.strip()
        if parsed_output.semantic_query and parsed_output.semantic_query.strip():
            semantic_query = parsed_output.semantic_query.strip()

        budget_value = parsed_output.budget_value
        if budget_value is not None and normalized_currency is None:
            budget_value = None

        return ParsedSearchQuery(
            raw_query=raw_query.strip(),
            normalized_query=normalized_query,
            intent=parsed_output.intent,
            category=normalized_category,
            brand=normalized_brand,
            budget_value=budget_value,
            budget_currency=normalized_currency,
            availability=normalized_availability,
            semantic_query=semantic_query,
        )
