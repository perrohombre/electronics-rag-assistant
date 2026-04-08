from electronics_rag_assistant_backend.query.parser import parse_search_query
from electronics_rag_assistant_shared.catalog import InternalCategory
from electronics_rag_assistant_shared.search import CurrencyCode, SearchIntent


def test_parse_search_query_extracts_category_budget_and_default_availability() -> None:
    parsed = parse_search_query("Jaki laptop do 500 USD do pracy i studiow?")

    assert parsed.intent == SearchIntent.SEARCH
    assert parsed.category == InternalCategory.LAPTOPS
    assert parsed.brand is None
    assert parsed.budget_value == 500.0
    assert parsed.budget_currency == CurrencyCode.USD
    assert parsed.availability == "available"


def test_parse_search_query_detects_pln_and_comparison_intent() -> None:
    parsed = parse_search_query("Porownaj monitor Dell do 300 zl")

    assert parsed.intent == SearchIntent.COMPARISON
    assert parsed.category == InternalCategory.MONITORS
    assert parsed.brand == "Dell"
    assert parsed.budget_value == 300.0
    assert parsed.budget_currency == CurrencyCode.PLN


def test_parse_search_query_normalizes_polish_diacritics_and_brand_aliases() -> None:
    parsed = parse_search_query("Słuchawki Sony na stanie")

    assert parsed.intent == SearchIntent.SEARCH
    assert parsed.category == InternalCategory.HEADPHONES
    assert parsed.brand == "Sony"
    assert parsed.availability == "available"
