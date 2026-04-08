import pytest
from qdrant_client.http import models

from electronics_rag_assistant_backend.query.parser import parse_search_query
from electronics_rag_assistant_backend.retrieval.filter_builder import build_qdrant_filter


def test_build_qdrant_filter_adds_category_brand_price_and_availability_conditions() -> None:
    parsed_query = parse_search_query("Laptop Dell do 500 USD")

    query_filter = build_qdrant_filter(parsed_query)

    assert query_filter.must is not None
    assert len(query_filter.must) == 4

    category_condition = next(
        condition
        for condition in query_filter.must
        if isinstance(condition, models.FieldCondition) and condition.key == "internal_category"
    )
    brand_condition = next(
        condition
        for condition in query_filter.must
        if isinstance(condition, models.FieldCondition) and condition.key == "brand"
    )
    price_condition = next(
        condition
        for condition in query_filter.must
        if isinstance(condition, models.FieldCondition) and condition.key == "price_usd"
    )

    assert category_condition.match.value == "laptops"
    assert brand_condition.match.value == "Dell"
    assert price_condition.range.lte == 500.0


def test_build_qdrant_filter_defaults_to_available_only_when_query_has_no_constraints() -> None:
    parsed_query = parse_search_query("cos do pracy")

    query_filter = build_qdrant_filter(parsed_query)

    assert query_filter.must is not None
    assert len(query_filter.must) == 1
    assert query_filter.must[0].key == "availability"
    assert query_filter.must[0].match.value == "available"


def test_build_qdrant_filter_rejects_pln_budget() -> None:
    parsed_query = parse_search_query("monitor do 300 zl")

    with pytest.raises(ValueError, match="Budżet w PLN"):
        build_qdrant_filter(parsed_query)
