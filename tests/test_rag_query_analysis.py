from mediaexpert_laptops.rag.query_analysis import QueryAnalysisService


def test_fallback_query_analysis_extracts_explicit_filters() -> None:
    service = QueryAnalysisService(
        api_key="",
        model="unused",
        known_brands=["APPLE", "LENOVO"],
    )

    decision = service.analyze("MacBook do 5000 zł minimum 16 GB RAM")
    parsed = decision.filters

    assert decision.action == "search"
    assert parsed.brand == "APPLE"
    assert parsed.max_price_pln == 5000
    assert parsed.min_ram_gb == 16
    assert parsed.operating_system == "macOS"


def test_fallback_query_analysis_does_not_guess_unclear_filters() -> None:
    service = QueryAnalysisService(api_key="", model="unused", known_brands=["APPLE"])

    decision = service.analyze("lekki laptop do nauki")
    parsed = decision.filters

    assert decision.action == "search"
    assert parsed.brand is None
    assert parsed.max_price_pln is None
    assert parsed.min_ram_gb is None


def test_fallback_query_analysis_extracts_screen_limit() -> None:
    service = QueryAnalysisService(api_key="", model="unused", known_brands=["ASUS"])

    decision = service.analyze("ASUS do 14 cali")
    parsed = decision.filters

    assert decision.action == "search"
    assert parsed.brand == "ASUS"
    assert parsed.screen_size_max == 14


def test_fallback_query_analysis_asks_for_budget_when_budget_word_is_unclear() -> None:
    service = QueryAnalysisService(api_key="", model="unused", known_brands=["LENOVO"])

    decision = service.analyze("budżetowy laptop")

    assert decision.action == "ask_clarification"
    assert decision.filters.max_price_pln is None
    assert decision.clarifying_question == "Jaki maksymalny budżet w złotówkach mam przyjąć?"


def test_fallback_query_analysis_searches_with_assumption_when_semantics_are_clear() -> None:
    service = QueryAnalysisService(api_key="", model="unused", known_brands=["LENOVO"])

    decision = service.analyze("tani laptop do programowania")

    assert decision.action == "search_with_assumption"
    assert decision.filters.max_price_pln is None
    assert decision.clarifying_question == "Jaki maksymalny budżet w złotówkach mam przyjąć?"
    assert decision.assumptions
