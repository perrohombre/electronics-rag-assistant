from electronics_rag_assistant_backend.query.parser import (
    normalize_query,
    parse_search_query,
    parse_search_query_fallback,
)
from electronics_rag_assistant_shared.search import CurrencyCode, SearchIntent


def test_parse_search_query_fallback_extracts_only_safe_signals() -> None:
    parsed = parse_search_query_fallback("Porownaj monitor Dell do 300 zl")

    assert parsed.intent == SearchIntent.COMPARISON
    assert parsed.category is None
    assert parsed.brand is None
    assert parsed.budget_value == 300.0
    assert parsed.budget_currency == CurrencyCode.PLN
    assert parsed.availability is None


def test_parse_search_query_fallback_detects_explicit_availability_only() -> None:
    parsed = parse_search_query_fallback("Słuchawki Sony na stanie")

    assert parsed.intent == SearchIntent.SEARCH
    assert parsed.category is None
    assert parsed.brand is None
    assert parsed.availability == "available"


def test_parse_search_query_wrapper_delegates_to_fallback() -> None:
    parsed = parse_search_query("Laptop do 500 USD")

    assert parsed.intent == SearchIntent.SEARCH
    assert parsed.category is None
    assert parsed.brand is None
    assert parsed.budget_value == 500.0
    assert parsed.budget_currency == CurrencyCode.USD


def test_normalize_query_strips_polish_diacritics() -> None:
    assert normalize_query("Słuchawki Łódź") == "sluchawki lodz"
