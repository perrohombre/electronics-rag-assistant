"""Helpers for managing Streamlit session state in the demo UI."""

from __future__ import annotations

from collections.abc import Iterable, MutableMapping
from copy import deepcopy
from typing import Any

from electronics_rag_assistant_shared.search import CompareResponse, ProductSummary, SearchResponse

UIState = MutableMapping[str, Any]

_DEFAULT_STATE: dict[str, Any] = {
    "search_response": None,
    "selected_compare_ids": [],
    "compare_response": None,
    "selected_product_id": None,
    "product_details_cache": {},
    "feedback": None,
}


def initialize_ui_state(state: UIState) -> None:
    """Ensure all expected UI state keys exist."""

    for key, default_value in _DEFAULT_STATE.items():
        if key not in state:
            state[key] = deepcopy(default_value)


def set_feedback(state: UIState, *, level: str, message: str) -> None:
    """Store one user-facing feedback message in session state."""

    state["feedback"] = {
        "level": level,
        "message": message,
    }


def clear_feedback(state: UIState) -> None:
    """Clear the latest stored feedback message."""

    state["feedback"] = None


def set_search_response(state: UIState, search_response: SearchResponse) -> None:
    """Persist a fresh search response and clear old comparisons."""

    state["search_response"] = search_response
    state["compare_response"] = None


def add_compare_product(state: UIState, product_id: str) -> tuple[bool, str | None]:
    """Add one product to the compare basket if there is free capacity."""

    selected_ids = list(state["selected_compare_ids"])
    if product_id in selected_ids:
        return False, "Ten produkt jest już w koszyku porównania."
    if len(selected_ids) >= 2:
        return False, "Koszyk porównania jest pełny. Usuń jeden produkt, aby dodać kolejny."

    selected_ids.append(product_id)
    state["selected_compare_ids"] = selected_ids
    state["compare_response"] = None
    return True, None


def remove_compare_product(state: UIState, product_id: str) -> bool:
    """Remove one product from the compare basket."""

    selected_ids = [item for item in state["selected_compare_ids"] if item != product_id]
    was_removed = len(selected_ids) != len(state["selected_compare_ids"])
    state["selected_compare_ids"] = selected_ids
    if was_removed:
        state["compare_response"] = None
    return was_removed


def clear_compare_selection(state: UIState) -> None:
    """Remove all products from the compare basket."""

    state["selected_compare_ids"] = []
    state["compare_response"] = None


def cache_product_details(state: UIState, product: ProductSummary) -> None:
    """Save one fetched product summary in the session cache."""

    cache = dict(state["product_details_cache"])
    cache[product.source_id] = product
    state["product_details_cache"] = cache


def get_cached_product_details(state: UIState, product_id: str) -> ProductSummary | None:
    """Return one cached product summary if available."""

    cache = state["product_details_cache"]
    return cache.get(product_id) if isinstance(cache, dict) else None


def set_selected_product(state: UIState, product_id: str | None) -> None:
    """Persist the currently opened product details selection."""

    state["selected_product_id"] = product_id


def set_compare_response(state: UIState, compare_response: CompareResponse) -> None:
    """Persist the latest successful comparison response."""

    state["compare_response"] = compare_response


def clear_stale_product_selection(state: UIState, product_ids: Iterable[str]) -> None:
    """Remove missing products from all relevant UI state containers."""

    stale_ids = set(product_ids)
    if not stale_ids:
        return

    state["selected_compare_ids"] = [
        product_id
        for product_id in state["selected_compare_ids"]
        if product_id not in stale_ids
    ]

    selected_product_id = state["selected_product_id"]
    if selected_product_id in stale_ids:
        state["selected_product_id"] = None

    cache = dict(state["product_details_cache"])
    for product_id in stale_ids:
        cache.pop(product_id, None)
    state["product_details_cache"] = cache
    state["compare_response"] = None


def get_cited_product_labels(search_response: SearchResponse | None) -> list[str]:
    """Resolve cited product IDs into readable names based on search results."""

    if search_response is None or search_response.assistant_answer is None:
        return []

    known_names = {
        hit.source_id: hit.name
        for hit in search_response.hits
    }
    return [
        known_names.get(source_id, source_id)
        for source_id in search_response.assistant_answer.cited_source_ids
    ]


def get_known_product_label(state: UIState, product_id: str) -> str:
    """Resolve one product ID into the best available user-facing label."""

    cached_product = get_cached_product_details(state, product_id)
    if cached_product is not None:
        return cached_product.name

    search_response = state.get("search_response")
    if isinstance(search_response, SearchResponse):
        for hit in search_response.hits:
            if hit.source_id == product_id:
                return hit.name

    compare_response = state.get("compare_response")
    if isinstance(compare_response, CompareResponse):
        for product in compare_response.products:
            if product.source_id == product_id:
                return product.name

    return product_id
