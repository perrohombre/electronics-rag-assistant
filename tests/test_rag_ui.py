from mediaexpert_laptops.rag.ui import _build_clarified_query, _strip_clarification


def test_build_clarified_query_replaces_previous_clarification() -> None:
    query = (
        "budżetowy laptop. Doprecyzowanie użytkownika: do 3000 zł. "
        "Doprecyzowanie użytkownika: do 4000 zł"
    )

    assert _build_clarified_query(query, "do 5000 zł") == (
        "budżetowy laptop. Doprecyzowanie użytkownika: do 5000 zł"
    )


def test_strip_clarification_returns_base_query() -> None:
    query = "klawiatura do laptopa. Doprecyzowanie użytkownika: zewnętrzna"

    assert _strip_clarification(query) == "klawiatura do laptopa"
