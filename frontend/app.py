"""Single-page Streamlit UI for the Electronics RAG Assistant demo."""

from __future__ import annotations

import html
import os

import streamlit as st

from electronics_rag_assistant_shared.search import CompareResponse, ProductSearchHit
from frontend.api_client import (
    ConnectionAPIError,
    FrontendAPIClient,
    NotFoundAPIError,
    ServiceUnavailableAPIError,
    UnexpectedAPIError,
    ValidationAPIError,
    build_api_base_url,
)
from frontend.ui_state import (
    add_compare_product,
    cache_product_details,
    clear_compare_selection,
    clear_feedback,
    clear_stale_product_selection,
    get_cached_product_details,
    get_cited_product_labels,
    get_known_product_label,
    initialize_ui_state,
    remove_compare_product,
    set_compare_response,
    set_feedback,
    set_search_response,
    set_selected_product,
)

st.set_page_config(
    page_title="Electronics RAG Assistant",
    page_icon="🛍️",
    layout="wide",
)

_CATEGORY_LABELS = {
    "laptops": "Laptopy",
    "monitors": "Monitory",
    "televisions": "Telewizory",
    "mice": "Myszki",
    "keyboards": "Klawiatury",
    "headphones": "Słuchawki",
}

_FEEDBACK_RENDERERS = {
    "info": st.info,
    "success": st.success,
    "warning": st.warning,
    "error": st.error,
}

_PAGE_STYLES = """
<style>
    .stApp {
        background:
            radial-gradient(circle at top right, rgba(234, 169, 88, 0.28), transparent 32%),
            radial-gradient(circle at left 18%, rgba(66, 139, 202, 0.12), transparent 30%),
            linear-gradient(180deg, #fbf6ec 0%, #f6efe2 42%, #f2ece2 100%);
        color: #203040;
    }
    .stApp, .stApp * {
        font-family: "Trebuchet MS", "Gill Sans", sans-serif;
    }
    h1, h2, h3 {
        font-family: Georgia, "Times New Roman", serif !important;
        color: #182434;
        letter-spacing: -0.02em;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #13202e 0%, #1f3347 100%);
    }
    [data-testid="stSidebar"] * {
        color: #f4efe5;
    }
    .hero-shell {
        background: linear-gradient(135deg, rgba(18, 36, 52, 0.96), rgba(28, 67, 94, 0.94));
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 24px;
        padding: 2rem 2.2rem;
        box-shadow: 0 24px 60px rgba(24, 36, 52, 0.18);
        margin-bottom: 1rem;
    }
    .hero-eyebrow {
        display: inline-block;
        padding: 0.35rem 0.8rem;
        border-radius: 999px;
        background: rgba(243, 187, 113, 0.18);
        color: #f6d9aa;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.9rem;
    }
    .hero-title {
        color: #f9f5ed;
        font-size: 2.55rem;
        line-height: 1.05;
        margin: 0;
    }
    .hero-body {
        margin-top: 0.8rem;
        max-width: 52rem;
        color: rgba(249, 245, 237, 0.9);
        font-size: 1.03rem;
        line-height: 1.6;
    }
    .note-panel {
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(24, 36, 52, 0.08);
        border-radius: 18px;
        padding: 1rem 1.2rem;
        margin: 0.4rem 0 1rem;
    }
    .assistant-panel {
        background: linear-gradient(180deg, rgba(255, 249, 237, 0.95), rgba(255, 255, 255, 0.88));
        border: 1px solid rgba(227, 164, 88, 0.34);
        border-radius: 22px;
        padding: 1.35rem 1.5rem;
        box-shadow: 0 16px 36px rgba(196, 148, 84, 0.14);
        margin-bottom: 0.9rem;
    }
    .assistant-kicker {
        color: #aa6b20;
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.5rem;
    }
    .assistant-message {
        color: #24303d;
        font-size: 1.06rem;
        line-height: 1.7;
        margin: 0;
    }
    .badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin: 0.35rem 0 0.85rem;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 0.26rem 0.68rem;
        font-size: 0.78rem;
        font-weight: 700;
        line-height: 1;
    }
    .badge-category {
        background: rgba(32, 114, 155, 0.12);
        color: #155a79;
    }
    .badge-available {
        background: rgba(52, 140, 90, 0.12);
        color: #226944;
    }
    .badge-unavailable {
        background: rgba(173, 87, 66, 0.12);
        color: #8b3d2e;
    }
    .badge-cited {
        background: rgba(230, 170, 83, 0.18);
        color: #8c5211;
    }
    .image-placeholder {
        border-radius: 18px;
        min-height: 170px;
        background: linear-gradient(160deg, #ece5d8, #ddd1bc);
        color: #51606f;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        font-weight: 700;
        padding: 1rem;
    }
    .card-title {
        font-size: 1.25rem;
        margin: 0.1rem 0 0.35rem;
        color: #1c2630;
    }
    .product-description {
        color: #495866;
        line-height: 1.55;
        margin-bottom: 0.65rem;
    }
    .spec-list {
        margin: 0;
        padding-left: 1.15rem;
        color: #334658;
    }
    .spec-list li {
        margin-bottom: 0.25rem;
    }
    .comparison-shell {
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(24, 36, 52, 0.08);
        border-radius: 24px;
        padding: 1.2rem 1.3rem 1.35rem;
        margin-top: 1.3rem;
        box-shadow: 0 18px 40px rgba(24, 36, 52, 0.08);
    }
    .sidebar-note {
        font-size: 0.9rem;
        color: rgba(244, 239, 229, 0.78);
        line-height: 1.45;
    }
    .sidebar-chip {
        display: inline-block;
        margin-top: 0.35rem;
        padding: 0.22rem 0.7rem;
        border-radius: 999px;
        background: rgba(244, 214, 164, 0.12);
        color: #f5d7aa;
        font-size: 0.78rem;
        font-weight: 700;
    }
</style>
"""


def main() -> None:
    """Render the single-page Streamlit application."""

    initialize_ui_state(st.session_state)
    api_client = FrontendAPIClient(base_url=build_api_base_url())
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

    _inject_styles()
    _render_hero()
    _render_feedback()
    _render_search_form(api_client)
    _render_search_results(api_client)
    _render_sidebar(api_client=api_client, qdrant_url=qdrant_url)


def _inject_styles() -> None:
    st.markdown(_PAGE_STYLES, unsafe_allow_html=True)


def _render_hero() -> None:
    st.markdown(
        """
        <div class="hero-shell">
            <div class="hero-eyebrow">RAG Shopping Assistant</div>
            <h1 class="hero-title">Wyszukuj, uzasadniaj i porównuj elektronikę</h1>
            <p class="hero-body">
                Ten prototyp łączy semantyczne wyszukiwanie produktów z odpowiedzią asystenta,
                która opiera się wyłącznie na rekordach z lokalnego katalogu.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_feedback() -> None:
    feedback = st.session_state.get("feedback")
    if not isinstance(feedback, dict):
        return

    level = feedback.get("level", "info")
    message = feedback.get("message", "")
    renderer = _FEEDBACK_RENDERERS.get(level, st.info)
    renderer(message)


def _render_search_form(api_client: FrontendAPIClient) -> None:
    st.markdown(
        """
        <div class="note-panel">
            <strong>Przykładowe zapytania:</strong> jaki monitor do programowania do 500 USD,
            porównaj dwa wybrane modele słuchawek, laptop do pracy i studiów.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("assistant-search-form", clear_on_submit=False):
        query = st.text_area(
            "Zapytanie",
            key="search_query_input",
            height=110,
            placeholder="Np. jaki monitor do programowania do 500 USD",
        )
        controls_column, spacer_column = st.columns([1, 3])
        with controls_column:
            limit = st.selectbox(
                "Limit wyników",
                options=[3, 5, 10],
                index=1,
                key="search_limit_input",
            )
        with spacer_column:
            st.caption(
                "Odpowiedź asystenta pojawi się nad wynikami, "
                "a koszyk porównania znajdziesz w sidebarze."
            )
        submitted = st.form_submit_button("Szukaj", type="primary", use_container_width=True)

    if submitted:
        _handle_search(api_client=api_client, query=query, limit=limit)


def _handle_search(api_client: FrontendAPIClient, *, query: str, limit: int) -> None:
    if not query.strip():
        set_feedback(
            st.session_state,
            level="warning",
            message="Wpisz zapytanie, aby rozpocząć wyszukiwanie.",
        )
        st.session_state["search_response"] = None
        st.session_state["compare_response"] = None
        return

    clear_feedback(st.session_state)
    st.session_state["search_response"] = None
    st.session_state["compare_response"] = None

    with st.spinner("Wyszukuję produkty i buduję odpowiedź asystenta..."):
        try:
            search_response = api_client.search_products(query=query.strip(), limit=limit)
        except ValidationAPIError as exc:
            set_feedback(st.session_state, level="warning", message=exc.user_message)
            return
        except (ConnectionAPIError, ServiceUnavailableAPIError, UnexpectedAPIError) as exc:
            set_feedback(st.session_state, level="error", message=exc.user_message)
            return

    set_search_response(st.session_state, search_response)


def _render_search_results(api_client: FrontendAPIClient) -> None:
    search_response = st.session_state.get("search_response")
    if search_response is None:
        st.subheader("Gotowe do demo")
        st.write(
            "Zadaj pytanie w języku naturalnym, a potem użyj kart produktów, aby otworzyć "
            "szczegóły lub dodać dwa modele do porównania."
        )
        return

    _render_assistant_answer(search_response)
    _render_parsed_query(search_response)
    _render_product_results(api_client=api_client, hits=search_response.hits)
    _render_comparison_section(st.session_state.get("compare_response"))


def _render_assistant_answer(search_response) -> None:
    assistant_answer = search_response.assistant_answer
    if assistant_answer is None:
        return

    st.subheader("Odpowiedź asystenta")
    st.markdown(
        f"""
        <div class="assistant-panel">
            <div class="assistant-kicker">Rekomendacja oparta na katalogu</div>
            <p class="assistant-message">{html.escape(assistant_answer.message)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cited_labels = get_cited_product_labels(search_response)
    if cited_labels:
        st.caption("Oparte na: " + " • ".join(cited_labels))


def _render_parsed_query(search_response) -> None:
    with st.expander("Jak system zrozumiał zapytanie", expanded=False):
        st.json(search_response.parsed_query.model_dump(mode="json"))


def _render_product_results(
    api_client: FrontendAPIClient,
    *,
    hits: list[ProductSearchHit],
) -> None:
    st.subheader(f"Wyniki ({len(hits)})")
    if not hits:
        st.info("W aktualnym katalogu nie ma produktów spełniających to zapytanie.")
        return

    cited_ids = set()
    search_response = st.session_state.get("search_response")
    if search_response is not None and search_response.assistant_answer is not None:
        cited_ids = set(search_response.assistant_answer.cited_source_ids)

    for hit in hits:
        with st.container(border=True):
            media_column, content_column, actions_column = st.columns([1.15, 2.15, 1.1])

            with media_column:
                if hit.image_url:
                    st.image(hit.image_url, use_container_width=True)
                else:
                    st.markdown(
                        f'<div class="image-placeholder">{html.escape(hit.name)}</div>',
                        unsafe_allow_html=True,
                    )

            with content_column:
                _render_product_badges(hit=hit, is_cited=hit.source_id in cited_ids)
                st.markdown(
                    f'<h3 class="card-title">{html.escape(hit.name)}</h3>',
                    unsafe_allow_html=True,
                )
                if hit.brand:
                    st.caption(f"Marka: {hit.brand}")
                st.markdown(
                    (
                        '<div class="product-description">'
                        f"{html.escape(_truncate_text(hit.description, 180))}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
                _render_key_specs(hit.specs)
                if hit.url:
                    st.markdown(f"[Zobacz źródło produktu]({hit.url})")

            with actions_column:
                st.metric("Cena", _format_price(hit.price_usd))
                is_selected = hit.source_id in st.session_state["selected_compare_ids"]
                compare_disabled = (
                    len(st.session_state["selected_compare_ids"]) >= 2 and not is_selected
                )

                if st.button(
                    "Szczegóły",
                    key=f"details_{hit.source_id}",
                    use_container_width=True,
                ):
                    _open_product_details(api_client=api_client, product_id=hit.source_id)

                compare_label = "Usuń z porównania" if is_selected else "Dodaj do porównania"
                if st.button(
                    compare_label,
                    key=f"compare_{hit.source_id}",
                    use_container_width=True,
                    disabled=compare_disabled,
                ):
                    _toggle_compare_selection(hit.source_id)

                if compare_disabled:
                    st.caption("Koszyk porównania jest pełny.")


def _render_product_badges(*, hit: ProductSearchHit, is_cited: bool) -> None:
    category_label = html.escape(_format_category(hit.internal_category))
    availability_label = html.escape(_format_availability(hit.availability))
    availability_class = _availability_badge_class(hit.availability)
    badges = [
        f'<span class="badge badge-category">{category_label}</span>',
        f'<span class="badge {availability_class}">{availability_label}</span>',
    ]
    if is_cited:
        badges.append('<span class="badge badge-cited">W rekomendacji asystenta</span>')

    st.markdown(
        f'<div class="badge-row">{"".join(badges)}</div>',
        unsafe_allow_html=True,
    )


def _render_key_specs(specs: dict[str, str], *, limit: int = 4) -> None:
    if not specs:
        st.caption("Brak dodatkowych parametrów technicznych w katalogu.")
        return

    top_specs = list(specs.items())[:limit]
    items = "".join(
        f"<li><strong>{html.escape(key)}:</strong> {html.escape(str(value))}</li>"
        for key, value in top_specs
    )
    st.markdown(f'<ul class="spec-list">{items}</ul>', unsafe_allow_html=True)


def _open_product_details(api_client: FrontendAPIClient, *, product_id: str) -> None:
    cached_product = get_cached_product_details(st.session_state, product_id)
    if cached_product is not None:
        set_selected_product(st.session_state, product_id)
        clear_feedback(st.session_state)
        return

    with st.spinner("Pobieram szczegóły produktu..."):
        try:
            product = api_client.get_product(product_id)
        except NotFoundAPIError as exc:
            clear_stale_product_selection(st.session_state, [product_id])
            set_feedback(st.session_state, level="warning", message=exc.user_message)
            return
        except ValidationAPIError as exc:
            set_feedback(st.session_state, level="warning", message=exc.user_message)
            return
        except (ConnectionAPIError, ServiceUnavailableAPIError, UnexpectedAPIError) as exc:
            set_feedback(st.session_state, level="error", message=exc.user_message)
            return

    cache_product_details(st.session_state, product)
    set_selected_product(st.session_state, product_id)
    clear_feedback(st.session_state)


def _toggle_compare_selection(product_id: str) -> None:
    if product_id in st.session_state["selected_compare_ids"]:
        remove_compare_product(st.session_state, product_id)
        clear_feedback(st.session_state)
        return

    added, warning_message = add_compare_product(st.session_state, product_id)
    if not added and warning_message:
        set_feedback(st.session_state, level="warning", message=warning_message)
        return

    clear_feedback(st.session_state)


def _render_comparison_section(compare_response: CompareResponse | None) -> None:
    if compare_response is None:
        return

    st.subheader("Porównanie")
    st.markdown(
        f"""
        <div class="comparison-shell">
            <div class="assistant-kicker">Wniosek porównawczy</div>
            <p class="assistant-message">
                {html.escape(compare_response.assistant_answer.message)}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Oparte na: "
        + " • ".join(product.name for product in compare_response.products)
    )

    columns = st.columns(2)
    for column, product in zip(columns, compare_response.products, strict=False):
        with column:
            with st.container(border=True):
                st.markdown(f"### {product.name}")
                st.caption(
                    f"{_format_category(product.internal_category)} "
                    f"• {product.brand or 'Brak marki'}"
                )
                if product.image_url:
                    st.image(product.image_url, use_container_width=True)
                else:
                    st.markdown(
                        f'<div class="image-placeholder">{html.escape(product.name)}</div>',
                        unsafe_allow_html=True,
                    )
                _render_product_badges(
                    hit=ProductSearchHit(
                        source_id=product.source_id,
                        sku=product.sku,
                        name=product.name,
                        brand=product.brand,
                        internal_category=product.internal_category,
                        source_category_id=product.source_category_id,
                        price_usd=product.price_usd,
                        availability=product.availability,
                        url=product.url,
                        image_url=product.image_url,
                        description=product.description,
                        specs=product.specs,
                        score=1.0,
                    ),
                    is_cited=(
                        product.source_id in compare_response.assistant_answer.cited_source_ids
                    ),
                )
                st.metric("Cena", _format_price(product.price_usd))
                st.markdown(
                    (
                        '<div class="product-description">'
                        f"{html.escape(_truncate_text(product.description, 220))}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
                _render_key_specs(product.specs, limit=6)
                if product.url:
                    st.markdown(f"[Zobacz źródło produktu]({product.url})")


def _render_sidebar(*, api_client: FrontendAPIClient, qdrant_url: str) -> None:
    with st.sidebar:
        st.markdown("## Koszyk compare")
        selected_ids = st.session_state["selected_compare_ids"]
        st.markdown(
            f'<span class="sidebar-chip">{len(selected_ids)}/2 wybrane produkty</span>',
            unsafe_allow_html=True,
        )

        if not selected_ids:
            st.markdown(
                (
                    '<p class="sidebar-note">'
                    "Dodaj dwa produkty z listy wyników, aby uruchomić porównanie."
                    "</p>"
                ),
                unsafe_allow_html=True,
            )
        else:
            for product_id in selected_ids:
                label = get_known_product_label(st.session_state, product_id)
                row_left, row_right = st.columns([4, 1])
                with row_left:
                    st.write(label)
                with row_right:
                    if st.button("✕", key=f"sidebar_remove_{product_id}", use_container_width=True):
                        remove_compare_product(st.session_state, product_id)
                        clear_feedback(st.session_state)
                        st.rerun()

        compare_context = st.text_input(
            "Kontekst porównania (opcjonalnie)",
            key="compare_context_input",
            placeholder="Np. do programowania po 8h dziennie",
        )
        if st.button(
            "Porównaj",
            use_container_width=True,
            disabled=len(selected_ids) != 2,
        ):
            _run_compare(
                api_client=api_client,
                product_ids=selected_ids,
                compare_context=compare_context,
            )
            st.rerun()

        if st.button(
            "Wyczyść",
            use_container_width=True,
            disabled=not selected_ids,
        ):
            clear_compare_selection(st.session_state)
            clear_feedback(st.session_state)
            st.rerun()

        st.divider()
        st.markdown("## Szczegóły produktu")
        _render_sidebar_product_details()

        st.divider()
        st.markdown("## Status usług")
        st.write(f"API: `{api_client.base_url}`")
        st.write(f"Qdrant: `{qdrant_url}`")
        st.markdown(
            '<p class="sidebar-note">Źródło danych: Best Buy API</p>',
            unsafe_allow_html=True,
        )


def _run_compare(
    *,
    api_client: FrontendAPIClient,
    product_ids: list[str],
    compare_context: str,
) -> None:
    try:
        compare_response = api_client.compare_products(
            product_ids=product_ids,
            query=compare_context.strip() or None,
        )
    except NotFoundAPIError as exc:
        missing_ids = _extract_stale_product_ids(exc.user_message, product_ids)
        clear_stale_product_selection(st.session_state, missing_ids)
        set_feedback(st.session_state, level="warning", message=exc.user_message)
        return
    except ValidationAPIError as exc:
        set_feedback(st.session_state, level="warning", message=exc.user_message)
        return
    except (ConnectionAPIError, ServiceUnavailableAPIError, UnexpectedAPIError) as exc:
        set_feedback(st.session_state, level="error", message=exc.user_message)
        return

    for product in compare_response.products:
        cache_product_details(st.session_state, product)
    set_compare_response(st.session_state, compare_response)
    clear_feedback(st.session_state)


def _render_sidebar_product_details() -> None:
    selected_product_id = st.session_state.get("selected_product_id")
    if selected_product_id is None:
        st.markdown(
            (
                '<p class="sidebar-note">'
                "Wybierz produkt z listy wyników, aby zobaczyć pełniejsze dane."
                "</p>"
            ),
            unsafe_allow_html=True,
        )
        return

    product = get_cached_product_details(st.session_state, selected_product_id)
    if product is None:
        st.markdown(
            '<p class="sidebar-note">Brak danych szczegółowych dla wybranego produktu.</p>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(f"### {product.name}")
    st.caption(f"{_format_category(product.internal_category)} • {product.brand or 'Brak marki'}")
    if product.image_url:
        st.image(product.image_url, use_container_width=True)
    else:
        st.markdown(
            f'<div class="image-placeholder">{html.escape(product.name)}</div>',
            unsafe_allow_html=True,
        )
    st.metric("Cena", _format_price(product.price_usd))
    st.write(f"Dostępność: {_format_availability(product.availability)}")
    st.write(product.description or "Brak opisu produktu.")

    if product.specs:
        spec_lines = "\n".join(
            f"- **{html.escape(key)}:** {html.escape(str(value))}"
            for key, value in product.specs.items()
        )
        st.markdown(spec_lines)
    else:
        st.caption("Brak dodatkowych parametrów technicznych.")

    if product.url:
        st.markdown(f"[Zobacz źródło produktu]({product.url})")


def _format_category(category: str) -> str:
    return _CATEGORY_LABELS.get(category, category.replace("_", " ").title())


def _format_availability(availability: str) -> str:
    return "Dostępny" if availability == "available" else "Niedostępny"


def _availability_badge_class(availability: str) -> str:
    return "badge-available" if availability == "available" else "badge-unavailable"


def _format_price(price_usd: float | None) -> str:
    if price_usd is None:
        return "Brak ceny"
    return f"{price_usd:.2f} USD"


def _truncate_text(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _extract_stale_product_ids(message: str, product_ids: list[str]) -> list[str]:
    stale_ids = [product_id for product_id in product_ids if product_id in message]
    return stale_ids or product_ids


main()
