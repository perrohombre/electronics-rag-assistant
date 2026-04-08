"""Translate parsed query constraints into Qdrant metadata filters."""

from __future__ import annotations

from qdrant_client.http import models

from electronics_rag_assistant_shared.search import CurrencyCode, ParsedSearchQuery


def build_qdrant_filter(parsed_query: ParsedSearchQuery) -> models.Filter:
    """Build a Qdrant filter from parsed hard constraints."""

    if parsed_query.budget_currency == CurrencyCode.PLN:
        raise ValueError("Budżet w PLN nie jest jeszcze obsługiwany. Podaj kwotę w USD.")

    must_conditions: list[models.Condition] = [
        models.FieldCondition(
            key="availability",
            match=models.MatchValue(value=parsed_query.availability or "available"),
        )
    ]

    if parsed_query.category is not None:
        must_conditions.append(
            models.FieldCondition(
                key="internal_category",
                match=models.MatchValue(value=parsed_query.category),
            )
        )

    if parsed_query.brand is not None:
        must_conditions.append(
            models.FieldCondition(
                key="brand",
                match=models.MatchValue(value=parsed_query.brand),
            )
        )

    if parsed_query.budget_value is not None:
        must_conditions.append(
            models.FieldCondition(
                key="price_usd",
                range=models.Range(lte=parsed_query.budget_value),
            )
        )

    return models.Filter(must=must_conditions)
