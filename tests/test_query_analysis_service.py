import json
from datetime import UTC, datetime

from electronics_rag_assistant_backend.services.query_analysis import (
    LLMQueryAnalysisOutput,
    QueryAnalysisService,
)
from electronics_rag_assistant_backend.storage.sqlite_catalog_repository import (
    SQLiteCatalogRepository,
)
from electronics_rag_assistant_shared.catalog import (
    CategorySnapshot,
    InternalCategory,
    ProductRecord,
)
from electronics_rag_assistant_shared.search import CurrencyCode, SearchIntent


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


def _seed_repository(tmp_path) -> SQLiteCatalogRepository:
    repository = SQLiteCatalogRepository(tmp_path / "catalog.db")
    synced_at = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    repository.replace_category_snapshot(
        CategorySnapshot(
            internal_category=InternalCategory.MONITORS,
            source_category_id="cat-monitors",
            source_category_name="Monitors",
            source_category_path=["Displays", "Monitors"],
            source_category_url="https://example.com/monitors",
            product_count=3,
            last_synced_at=synced_at,
        ),
        [
            ProductRecord(
                source_id="bestbuy:31",
                sku="31",
                name="Dell Monitor 31",
                brand="Dell",
                internal_category=InternalCategory.MONITORS,
                source_category_id="cat-monitors",
                price_usd=399.0,
                availability="available",
                url="https://example.com/31",
                image_url=None,
                description="Monitor",
                specs={},
                last_synced_at=synced_at,
            ),
            ProductRecord(
                source_id="bestbuy:32",
                sku="32",
                name="LG Monitor 32",
                brand="LG",
                internal_category=InternalCategory.MONITORS,
                source_category_id="cat-monitors",
                price_usd=429.0,
                availability="available",
                url="https://example.com/32",
                image_url=None,
                description="Monitor",
                specs={},
                last_synced_at=synced_at,
            ),
            ProductRecord(
                source_id="bestbuy:33",
                sku="33",
                name="Dell Monitor 33",
                brand="dell",
                internal_category=InternalCategory.MONITORS,
                source_category_id="cat-monitors",
                price_usd=449.0,
                availability="available",
                url="https://example.com/33",
                image_url=None,
                description="Monitor",
                specs={},
                last_synced_at=synced_at,
            ),
        ],
    )
    return repository


def test_query_analysis_service_normalizes_llm_output_and_uses_dynamic_brands(tmp_path) -> None:
    repository = _seed_repository(tmp_path)
    responses_api = StubResponsesAPI(
        output_parsed=LLMQueryAnalysisOutput(
            intent=SearchIntent.SEARCH,
            category="monitors",
            brand="dell",
            budget_value=400.0,
            budget_currency="USD",
            availability="available",
            semantic_query="monitor do programowania",
        )
    )
    service = QueryAnalysisService(
        repository=repository,
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=10,
        max_brands=10,
        max_output_tokens=200,
        client=StubOpenAIClient(responses_api),
    )

    parsed = service.analyze("Jaki monitor Dell do programowania do 400 USD?")

    assert parsed.intent == SearchIntent.SEARCH
    assert parsed.category == InternalCategory.MONITORS
    assert parsed.brand == "Dell"
    assert parsed.budget_value == 400.0
    assert parsed.budget_currency == CurrencyCode.USD
    assert parsed.availability == "available"
    assert parsed.semantic_query == "monitor do programowania"

    llm_input = json.loads(responses_api.last_kwargs["input"])
    assert llm_input["allowed_categories"] == [category.value for category in InternalCategory]
    assert llm_input["brand_candidates"] == ["Dell", "LG"]
    assert responses_api.last_kwargs["model"] == "gpt-5.4-mini"


def test_query_analysis_service_nulls_unknown_fields_without_guessing(tmp_path) -> None:
    repository = _seed_repository(tmp_path)
    service = QueryAnalysisService(
        repository=repository,
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=10,
        max_brands=10,
        max_output_tokens=200,
        client=StubOpenAIClient(
            StubResponsesAPI(
                output_parsed=LLMQueryAnalysisOutput(
                    intent=SearchIntent.SEARCH,
                    category="printers",
                    brand="Acme",
                    budget_value=500.0,
                    budget_currency="EUR",
                    availability="sometimes",
                    semantic_query=None,
                )
            )
        ),
    )

    parsed = service.analyze("Czegos do pracy")

    assert parsed.category is None
    assert parsed.brand is None
    assert parsed.budget_value is None
    assert parsed.budget_currency is None
    assert parsed.availability is None
    assert parsed.semantic_query == "Czegos do pracy"


def test_query_analysis_service_falls_back_on_openai_failure(tmp_path) -> None:
    repository = _seed_repository(tmp_path)
    service = QueryAnalysisService(
        repository=repository,
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=10,
        max_brands=10,
        max_output_tokens=200,
        client=StubOpenAIClient(StubResponsesAPI(exc=RuntimeError("boom"))),
    )

    parsed = service.analyze("Porownaj sluchawki do 300 zl na stanie")

    assert parsed.intent == SearchIntent.COMPARISON
    assert parsed.category is None
    assert parsed.brand is None
    assert parsed.budget_value == 300.0
    assert parsed.budget_currency == CurrencyCode.PLN
    assert parsed.availability == "available"


def test_query_analysis_service_uses_fallback_without_api_key(tmp_path) -> None:
    repository = _seed_repository(tmp_path)
    service = QueryAnalysisService(
        repository=repository,
        api_key="",
        model="gpt-5.4-mini",
        timeout_seconds=10,
        max_brands=10,
        max_output_tokens=200,
    )

    parsed = service.analyze("Laptop do 500 USD")

    assert parsed.intent == SearchIntent.SEARCH
    assert parsed.category is None
    assert parsed.brand is None
    assert parsed.budget_value == 500.0
    assert parsed.budget_currency == CurrencyCode.USD
