from mediaexpert_laptops.rag.query_analysis import QueryAnalysisService


def test_fallback_query_analysis_extracts_explicit_filters() -> None:
    service = QueryAnalysisService(
        api_key="",
        model="unused",
        known_brands=["APPLE", "LENOVO"],
    )

    parsed = service.analyze("MacBook do 5000 zł minimum 16 GB RAM")

    assert parsed.brand == "APPLE"
    assert parsed.max_price_pln == 5000
    assert parsed.min_ram_gb == 16
    assert parsed.operating_system == "macOS"


def test_fallback_query_analysis_does_not_guess_unclear_filters() -> None:
    service = QueryAnalysisService(api_key="", model="unused", known_brands=["APPLE"])

    parsed = service.analyze("lekki laptop do nauki")

    assert parsed.brand is None
    assert parsed.max_price_pln is None
    assert parsed.min_ram_gb is None


def test_fallback_query_analysis_extracts_screen_limit() -> None:
    service = QueryAnalysisService(api_key="", model="unused", known_brands=["ASUS"])

    parsed = service.analyze("ASUS do 14 cali")

    assert parsed.brand == "ASUS"
    assert parsed.screen_size_max == 14
