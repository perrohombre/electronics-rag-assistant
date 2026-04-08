from electronics_rag_assistant_backend.services.grounded_answer import (
    GroundedAnswerService,
    LLMGroundedAnswerOutput,
)
from electronics_rag_assistant_shared.catalog import InternalCategory
from electronics_rag_assistant_shared.search import (
    ParsedSearchQuery,
    ProductSearchHit,
    ProductSummary,
    SearchIntent,
)


class StubParsedResponse:
    def __init__(self, output_parsed) -> None:
        self.output_parsed = output_parsed


class StubResponsesAPI:
    def __init__(self, *, output_parsed=None, exc: Exception | None = None) -> None:
        self._output_parsed = output_parsed
        self._exc = exc
        self.last_kwargs: dict | None = None

    def parse(self, **kwargs):
        self.last_kwargs = kwargs
        if self._exc is not None:
            raise self._exc
        return StubParsedResponse(self._output_parsed)


class StubOpenAIClient:
    def __init__(self, responses_api: StubResponsesAPI) -> None:
        self.responses = responses_api


def _build_parsed_query() -> ParsedSearchQuery:
    return ParsedSearchQuery(
        raw_query="monitor Dell do 400 USD",
        normalized_query="monitor dell do 400 usd",
        intent=SearchIntent.SEARCH,
        category=InternalCategory.MONITORS,
        brand="Dell",
        budget_value=400.0,
        budget_currency="USD",
        availability="available",
        semantic_query="monitor Dell do 400 USD",
    )


def _build_hit(source_id: str, name: str, price_usd: float) -> ProductSearchHit:
    return ProductSearchHit(
        source_id=source_id,
        sku=source_id.split(":")[-1],
        name=name,
        brand="Dell",
        internal_category=InternalCategory.MONITORS,
        source_category_id="monitors-cat",
        price_usd=price_usd,
        availability="available",
        url="https://example.com/product",
        image_url=None,
        description=f"{name} do pracy i programowania",
        specs={"Screen": "27 in", "Refresh": "144 Hz"},
        score=0.9,
    )


def _build_product_summary(source_id: str, name: str, price_usd: float) -> ProductSummary:
    return ProductSummary(
        source_id=source_id,
        sku=source_id.split(":")[-1],
        name=name,
        brand="Dell",
        internal_category=InternalCategory.MONITORS,
        source_category_id="monitors-cat",
        price_usd=price_usd,
        availability="available",
        url="https://example.com/product",
        image_url=None,
        description=f"{name} do pracy i programowania",
        specs={"Screen": "27 in", "Refresh": "144 Hz"},
    )


def test_grounded_answer_service_uses_llm_answer_with_valid_citations() -> None:
    responses_api = StubResponsesAPI(
        output_parsed=LLMGroundedAnswerOutput(
            message="Najlepszym wyborem jest Dell Monitor 27 ze względu na cenę i parametry.",
            cited_source_ids=["bestbuy:1"],
        )
    )
    service = GroundedAnswerService(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=15,
        max_output_tokens=500,
        client=StubOpenAIClient(responses_api),
    )

    answer = service.generate_search_answer(
        query="monitor Dell do 400 USD",
        parsed_query=_build_parsed_query(),
        hits=[_build_hit("bestbuy:1", "Dell Monitor 27", 349.0)],
    )

    assert "Dell Monitor 27" in answer.message
    assert answer.cited_source_ids == ["bestbuy:1"]
    assert responses_api.last_kwargs["model"] == "gpt-5.4-mini"


def test_grounded_answer_service_falls_back_when_llm_returns_invalid_citations() -> None:
    service = GroundedAnswerService(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=15,
        max_output_tokens=500,
        client=StubOpenAIClient(
            StubResponsesAPI(
                output_parsed=LLMGroundedAnswerOutput(
                    message="Dell Monitor 27 wygląda najlepiej.",
                    cited_source_ids=["bestbuy:999"],
                )
            )
        ),
    )

    answer = service.generate_search_answer(
        query="monitor Dell do 400 USD",
        parsed_query=_build_parsed_query(),
        hits=[_build_hit("bestbuy:1", "Dell Monitor 27", 349.0)],
    )

    assert "Najlepiej dopasowany produkt" in answer.message
    assert answer.cited_source_ids == ["bestbuy:1"]


def test_grounded_answer_service_returns_no_results_message_without_hits() -> None:
    service = GroundedAnswerService(
        api_key="",
        model="gpt-5.4-mini",
        timeout_seconds=15,
        max_output_tokens=500,
    )

    answer = service.generate_search_answer(
        query="monitor Dell do 400 USD",
        parsed_query=_build_parsed_query(),
        hits=[],
    )

    assert (
        answer.message
        == "Nie znalazłem produktów spełniających to zapytanie w aktualnym katalogu."
    )
    assert answer.cited_source_ids == []


def test_grounded_answer_service_generates_comparison_fallback_without_client() -> None:
    service = GroundedAnswerService(
        api_key="",
        model="gpt-5.4-mini",
        timeout_seconds=15,
        max_output_tokens=500,
    )

    answer = service.generate_comparison_answer(
        query="do programowania",
        products=[
            _build_product_summary("bestbuy:1", "Dell Monitor 27", 349.0),
            _build_product_summary("bestbuy:2", "Dell Monitor 32", 429.0),
        ],
    )

    assert "Porównanie" in answer.message
    assert answer.cited_source_ids == ["bestbuy:1", "bestbuy:2"]
