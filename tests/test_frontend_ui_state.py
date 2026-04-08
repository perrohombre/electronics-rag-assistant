from frontend.ui_state import (
    add_compare_product,
    cache_product_details,
    clear_compare_selection,
    clear_stale_product_selection,
    get_cited_product_labels,
    get_known_product_label,
    initialize_ui_state,
    remove_compare_product,
    set_compare_response,
)

from electronics_rag_assistant_shared.catalog import InternalCategory
from electronics_rag_assistant_shared.search import (
    AssistantAnswer,
    CompareResponse,
    ParsedSearchQuery,
    ProductSearchHit,
    ProductSummary,
    SearchIntent,
    SearchResponse,
)


def _build_search_response() -> SearchResponse:
    return SearchResponse(
        query="monitor Dell do 400 USD",
        parsed_query=ParsedSearchQuery(
            raw_query="monitor Dell do 400 USD",
            normalized_query="monitor dell do 400 usd",
            intent=SearchIntent.SEARCH,
            category=InternalCategory.MONITORS,
            brand="Dell",
            budget_value=400.0,
            budget_currency="USD",
            availability="available",
            semantic_query="monitor Dell do 400 USD",
        ),
        total_hits=2,
        hits=[
            ProductSearchHit(
                source_id="bestbuy:1",
                sku="1",
                name="Dell Monitor 27",
                brand="Dell",
                internal_category=InternalCategory.MONITORS,
                source_category_id="monitors-cat",
                price_usd=349.0,
                availability="available",
                url="https://example.com/1",
                image_url=None,
                description="Monitor do pracy",
                specs={"Screen": "27 in"},
                score=0.95,
            ),
            ProductSearchHit(
                source_id="bestbuy:2",
                sku="2",
                name="LG Monitor 32",
                brand="LG",
                internal_category=InternalCategory.MONITORS,
                source_category_id="monitors-cat",
                price_usd=429.0,
                availability="available",
                url="https://example.com/2",
                image_url=None,
                description="Większy monitor",
                specs={"Screen": "32 in"},
                score=0.87,
            ),
        ],
        assistant_answer=AssistantAnswer(
            message="Dell Monitor 27 wygląda najlepiej, ale LG Monitor 32 też jest mocny.",
            cited_source_ids=["bestbuy:1", "bestbuy:999", "bestbuy:2"],
        ),
    )


def _build_product_summary(source_id: str, name: str) -> ProductSummary:
    return ProductSummary(
        source_id=source_id,
        sku=source_id.split(":")[-1],
        name=name,
        brand="Dell",
        internal_category=InternalCategory.MONITORS,
        source_category_id="monitors-cat",
        price_usd=349.0,
        availability="available",
        url="https://example.com/product",
        image_url=None,
        description="Monitor do pracy",
        specs={"Screen": "27 in"},
    )


def test_initialize_ui_state_sets_expected_defaults() -> None:
    state: dict = {}

    initialize_ui_state(state)

    assert state["search_response"] is None
    assert state["selected_compare_ids"] == []
    assert state["compare_response"] is None
    assert state["selected_product_id"] is None
    assert state["product_details_cache"] == {}
    assert state["feedback"] is None


def test_compare_basket_helpers_enforce_capacity_and_clear_compare_response() -> None:
    state: dict = {}
    initialize_ui_state(state)
    set_compare_response(
        state,
        CompareResponse(
            query="do programowania",
            product_ids=["bestbuy:1", "bestbuy:2"],
            products=[
                _build_product_summary("bestbuy:1", "Dell Monitor 27"),
                _build_product_summary("bestbuy:2", "LG Monitor 32"),
            ],
            assistant_answer=AssistantAnswer(
                message="Porównanie gotowe.",
                cited_source_ids=["bestbuy:1", "bestbuy:2"],
            ),
        ),
    )

    added_first, warning_first = add_compare_product(state, "bestbuy:1")
    added_second, warning_second = add_compare_product(state, "bestbuy:2")
    added_third, warning_third = add_compare_product(state, "bestbuy:3")

    assert added_first is True
    assert warning_first is None
    assert added_second is True
    assert warning_second is None
    assert added_third is False
    assert warning_third is not None
    assert state["selected_compare_ids"] == ["bestbuy:1", "bestbuy:2"]
    assert state["compare_response"] is None

    assert remove_compare_product(state, "bestbuy:1") is True
    assert state["selected_compare_ids"] == ["bestbuy:2"]

    clear_compare_selection(state)
    assert state["selected_compare_ids"] == []
    assert state["compare_response"] is None


def test_clear_stale_product_selection_removes_missing_ids_from_state() -> None:
    state: dict = {}
    initialize_ui_state(state)
    state["selected_compare_ids"] = ["bestbuy:1", "bestbuy:2"]
    state["selected_product_id"] = "bestbuy:2"
    cache_product_details(state, _build_product_summary("bestbuy:1", "Dell Monitor 27"))
    cache_product_details(state, _build_product_summary("bestbuy:2", "LG Monitor 32"))

    clear_stale_product_selection(state, ["bestbuy:2"])

    assert state["selected_compare_ids"] == ["bestbuy:1"]
    assert state["selected_product_id"] is None
    assert "bestbuy:2" not in state["product_details_cache"]


def test_cited_product_labels_preserve_order_and_fallback_to_source_id() -> None:
    labels = get_cited_product_labels(_build_search_response())

    assert labels == ["Dell Monitor 27", "bestbuy:999", "LG Monitor 32"]


def test_known_product_label_prefers_cache_then_search_then_compare() -> None:
    state: dict = {}
    initialize_ui_state(state)
    state["search_response"] = _build_search_response()
    state["compare_response"] = CompareResponse(
        query="do pracy",
        product_ids=["bestbuy:3", "bestbuy:4"],
        products=[
            _build_product_summary("bestbuy:3", "Samsung Monitor 34"),
            _build_product_summary("bestbuy:4", "Dell Monitor 25"),
        ],
        assistant_answer=AssistantAnswer(
            message="Porównanie gotowe.",
            cited_source_ids=["bestbuy:3", "bestbuy:4"],
        ),
    )
    cache_product_details(state, _build_product_summary("bestbuy:5", "Cache Monitor 40"))

    assert get_known_product_label(state, "bestbuy:5") == "Cache Monitor 40"
    assert get_known_product_label(state, "bestbuy:1") == "Dell Monitor 27"
    assert get_known_product_label(state, "bestbuy:3") == "Samsung Monitor 34"
    assert get_known_product_label(state, "bestbuy:404") == "bestbuy:404"
