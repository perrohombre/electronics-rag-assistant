"""Grounded answer generation for search recommendations and product comparisons."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from electronics_rag_assistant_shared.search import (
    AssistantAnswer,
    ParsedSearchQuery,
    ProductSearchHit,
    ProductSummary,
)


class LLMGroundedAnswerOutput(BaseModel):
    """Structured answer returned by the LLM answering step."""

    model_config = ConfigDict(extra="ignore")

    message: str
    cited_source_ids: list[str] = Field(default_factory=list)


class GroundedAnswerService:
    """Generate Polish grounded answers using only supplied catalog records."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        client: Any | None = None,
    ) -> None:
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._client = client or (OpenAI(api_key=api_key) if api_key else None)

    def generate_search_answer(
        self,
        *,
        query: str,
        parsed_query: ParsedSearchQuery,
        hits: list[ProductSearchHit],
    ) -> AssistantAnswer:
        """Generate a grounded recommendation answer for a search query."""

        if not hits:
            return AssistantAnswer(
                message="Nie znalazłem produktów spełniających to zapytanie w aktualnym katalogu.",
                cited_source_ids=[],
            )

        if self._client is None:
            return self._fallback_search_answer(query=query, hits=hits)

        payload = {
            "query": query,
            "parsed_query": parsed_query.model_dump(mode="json"),
            "products": [self._product_to_payload(hit) for hit in hits],
        }
        fallback_answer = self._fallback_search_answer(query=query, hits=hits)
        return self._generate_with_llm(
            instructions=(
                "Odpowiadasz po polsku jako asystent zakupowy. "
                "Używaj wyłącznie informacji z przekazanych produktów. "
                "Nie dodawaj faktów spoza danych wejściowych. "
                "Jeśli dane są niewystarczające, powiedz to wprost. "
                "Zwróć krótką rekomendację lub podsumowanie najlepiej dopasowanych opcji."
            ),
            payload=payload,
            allowed_source_ids=[hit.source_id for hit in hits],
            fallback_answer=fallback_answer,
        )

    def generate_comparison_answer(
        self,
        *,
        query: str | None,
        products: list[ProductSummary],
    ) -> AssistantAnswer:
        """Generate a grounded answer comparing two catalog products."""

        fallback_answer = self._fallback_comparison_answer(query=query, products=products)
        if self._client is None:
            return fallback_answer

        payload = {
            "query": query,
            "products": [self._product_to_payload(product) for product in products],
        }
        return self._generate_with_llm(
            instructions=(
                "Odpowiadasz po polsku jako asystent zakupowy. "
                "Porównaj dokładnie dwa produkty wyłącznie na podstawie przekazanych danych. "
                "Wskaż najważniejsze różnice, ale nie wymyślaj brakujących parametrów. "
                "Jeśli nie da się jednoznacznie wskazać zwycięzcy, napisz to wprost."
            ),
            payload=payload,
            allowed_source_ids=[product.source_id for product in products],
            fallback_answer=fallback_answer,
        )

    def _generate_with_llm(
        self,
        *,
        instructions: str,
        payload: dict[str, Any],
        allowed_source_ids: list[str],
        fallback_answer: AssistantAnswer,
    ) -> AssistantAnswer:
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=(
                    f"{instructions} "
                    "Zwróć tylko krótką odpowiedź dla użytkownika i listę source_id, "
                    "na których opierasz odpowiedź."
                ),
                input=json.dumps(payload, ensure_ascii=False),
                text_format=LLMGroundedAnswerOutput,
                temperature=0.2,
                max_output_tokens=self._max_output_tokens,
                timeout=self._timeout_seconds,
            )
            parsed_output = response.output_parsed
            if parsed_output is None:
                raise ValueError("LLM answering returned no parsed output")
            return self._normalize_output(
                parsed_output=parsed_output,
                allowed_source_ids=allowed_source_ids,
                fallback_answer=fallback_answer,
            )
        except Exception:
            return fallback_answer

    def _normalize_output(
        self,
        *,
        parsed_output: LLMGroundedAnswerOutput,
        allowed_source_ids: list[str],
        fallback_answer: AssistantAnswer,
    ) -> AssistantAnswer:
        allowed_lookup = {source_id: source_id for source_id in allowed_source_ids}
        cited_source_ids: list[str] = []
        for source_id in parsed_output.cited_source_ids:
            canonical_source_id = allowed_lookup.get(source_id)
            if canonical_source_id is None or canonical_source_id in cited_source_ids:
                continue
            cited_source_ids.append(canonical_source_id)

        message = parsed_output.message.strip()
        if not message or not cited_source_ids:
            return fallback_answer

        return AssistantAnswer(message=message, cited_source_ids=cited_source_ids)

    def _fallback_search_answer(
        self,
        *,
        query: str,
        hits: list[ProductSearchHit],
    ) -> AssistantAnswer:
        top_hits = hits[:3]
        if len(top_hits) == 1:
            product = top_hits[0]
            message = (
                f"Najlepiej dopasowany produkt dla zapytania '{query}' to "
                f"{product.name}{self._format_price(product.price_usd)}. "
                f"{self._format_product_highlight(product)}"
            )
        else:
            ranked_products = "; ".join(
                f"{product.name}{self._format_price(product.price_usd)}"
                for product in top_hits
            )
            message = (
                f"Najlepiej dopasowane produkty dla zapytania '{query}' to: {ranked_products}. "
                f"W aktualnym katalogu najwyżej wypada {top_hits[0].name}. "
                f"{self._format_product_highlight(top_hits[0])}"
            )

        return AssistantAnswer(
            message=message.strip(),
            cited_source_ids=[product.source_id for product in top_hits],
        )

    def _fallback_comparison_answer(
        self,
        *,
        query: str | None,
        products: list[ProductSummary],
    ) -> AssistantAnswer:
        left_product, right_product = products
        comparison_focus = (
            f" w kontekście '{query}'" if query is not None and query.strip() else ""
        )
        left_price = self._format_price(left_product.price_usd)
        right_price = self._format_price(right_product.price_usd)
        message = (
            f"Porównanie{comparison_focus}: {left_product.name}{left_price} "
            f"oraz {right_product.name}{right_price}. "
            f"{left_product.name}: {self._format_product_highlight(left_product)} "
            f"{right_product.name}: {self._format_product_highlight(right_product)}"
        )
        return AssistantAnswer(
            message=message.strip(),
            cited_source_ids=[left_product.source_id, right_product.source_id],
        )

    def _product_to_payload(self, product: ProductSearchHit | ProductSummary) -> dict[str, Any]:
        return {
            "source_id": product.source_id,
            "name": product.name,
            "brand": product.brand,
            "internal_category": product.internal_category,
            "price_usd": product.price_usd,
            "availability": product.availability,
            "description": product.description,
            "specs": product.specs,
            "url": product.url,
        }

    def _format_product_highlight(self, product: ProductSearchHit | ProductSummary) -> str:
        highlights: list[str] = []
        if product.brand:
            highlights.append(f"marka: {product.brand}.")

        top_specs = [
            f"{key}: {value}"
            for key, value in list(product.specs.items())[:2]
            if value and str(value).strip()
        ]
        if top_specs:
            highlights.append(f"Najważniejsze parametry: {', '.join(top_specs)}.")

        description = product.description.strip()
        if description:
            highlights.append(description[:160].rstrip(".") + ".")

        if not highlights:
            highlights.append("Brak dodatkowych danych opisowych w katalogu.")

        return " ".join(highlights)

    def _format_price(self, price_usd: float | None) -> str:
        if price_usd is None:
            return ""
        return f" za {price_usd:.2f} USD"
