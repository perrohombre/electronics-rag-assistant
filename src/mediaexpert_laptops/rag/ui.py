"""Streamlit UI for the transparent laptop RAG demo."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


def main() -> None:
    """Run Streamlit UI."""

    st.set_page_config(page_title="Transparent RAG Laptop Demo", layout="wide")
    _inject_css()
    _initialize_state()

    st.markdown(
        """
        <div class="hero">
            <p class="eyebrow">Retrieval-Augmented Generation dla e-commerce</p>
            <h1>Asystent zakupowy laptopów</h1>
            <p>
                Demo pokazuje cały przepływ: zapytanie użytkownika, ekstrakcję filtrów,
                filtrowanie katalogu, semantic search w Qdrant i kontekst przekazany do LLM.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("search_form"):
        query = st.text_area(
            "Zapytanie użytkownika",
            value=st.session_state.get("last_query", "laptop do 4000 zł do programowania"),
            height=90,
        )
        limit = st.select_slider("Liczba wyników", options=[3, 5, 10], value=5)
        submitted = st.form_submit_button("Uruchom RAG")

    if submitted:
        st.session_state["last_query"] = query
        st.session_state["last_limit"] = limit
        _run_search(query, limit)

    payload = st.session_state.get("payload")
    if not payload:
        _render_empty_state()
        return

    _render_answer(payload)
    _render_clarification(payload)
    _render_pipeline(payload)
    _render_results(payload)


def _initialize_state() -> None:
    if "payload" not in st.session_state:
        st.session_state["payload"] = None
    if "last_error" not in st.session_state:
        st.session_state["last_error"] = None
    if "last_limit" not in st.session_state:
        st.session_state["last_limit"] = 5


def _run_search(query: str, limit: int) -> None:
    if not query.strip():
        st.session_state["last_error"] = "Wpisz zapytanie przed uruchomieniem wyszukiwania."
        return

    with st.spinner("Analizuję zapytanie, filtruję katalog i odpytuję Qdrant..."):
        try:
            response = requests.post(
                f"{API_URL}/answer",
                json={"query": query, "limit": limit},
                timeout=90,
            )
        except requests.RequestException:
            st.session_state["last_error"] = (
                "Nie można połączyć się z API. Uruchom backend komendą: "
                "`uvicorn mediaexpert_laptops.rag.app:app --reload --host 127.0.0.1 --port 8000`."
            )
            return

    if response.status_code != 200:
        st.session_state["last_error"] = response.text
        return

    st.session_state["payload"] = response.json()
    st.session_state["last_error"] = None


def _render_empty_state() -> None:
    error = st.session_state.get("last_error")
    if error:
        st.error(error)
    st.info(
        "Wpisz zapytanie i uruchom RAG. Przykłady: `laptop gamingowy`, "
        "`Apple do 5000 zł do nauki`, `minimum 16 GB RAM do programowania`."
    )


def _render_answer(payload: dict[str, Any]) -> None:
    error = st.session_state.get("last_error")
    if error:
        st.warning(error)

    st.markdown("## Odpowiedź asystenta")
    st.markdown(f"<div class='answer'>{payload['answer']}</div>", unsafe_allow_html=True)


def _render_clarification(payload: dict[str, Any]) -> None:
    decision = payload["trace"]["decision"]
    action = decision["action"]
    question = decision.get("clarifying_question")

    if action == "search_with_assumption":
        assumptions = decision.get("assumptions") or []
        if assumptions:
            st.warning("Założenie systemu: " + " ".join(assumptions))
        if question:
            st.caption(f"Pytanie pomocnicze: {question}")
        return

    if action != "ask_clarification":
        return

    st.markdown("## Doprecyzowanie")
    st.info(question or "Doprecyzuj proszę, jakiego laptopa szukasz.")
    with st.form("clarification_form"):
        clarification = st.text_input(
            "Twoja odpowiedź",
            placeholder="np. do 3500 zł, do nauki i programowania",
        )
        submitted = st.form_submit_button("Kontynuuj rozmowę")

    if submitted and clarification.strip():
        combined_query = f"{payload['query']}. Doprecyzowanie użytkownika: {clarification.strip()}"
        st.session_state["last_query"] = combined_query
        _run_search(combined_query, st.session_state["last_limit"])
        st.rerun()


def _render_pipeline(payload: dict[str, Any]) -> None:
    trace = payload["trace"]
    decision = trace["decision"]
    parsed_filters = trace["parsed_filters"]
    qdrant_hits = trace["qdrant_hits"]
    context = trace.get("context_sent_to_answer_llm")

    st.markdown("## Transparentny przebieg retrievalu")
    steps = [
        (
            "1. Zapytanie użytkownika",
            payload["query"],
        ),
        (
            "2. Ekstrakcja jawnych filtrów przez LLM",
            _format_non_empty_filters(parsed_filters),
        ),
        (
            "3. Decyzja dialogowa",
            _format_decision(decision),
        ),
        (
            "4. Filtrowanie katalogu",
            (
                f"Przed filtrowaniem: {trace['candidates_before_filtering']} produktów. "
                f"Po filtrach twardych: {trace['candidates_after_filtering']} produktów."
            ),
        ),
        (
            "5. Semantic search w Qdrant",
            f"Qdrant zwrócił {len(qdrant_hits)} hitów dla embeddingu zapytania.",
        ),
        (
            "6. Kontekst dla LLM",
            "Top wyniki zostały zamienione na tekstowy kontekst z parametrami i opisami laptopów.",
        ),
        (
            "7. Odpowiedź końcowa",
            "Model odpowiada wyłącznie na podstawie kontekstu z poprzedniego kroku.",
        ),
    ]

    columns = st.columns(3)
    for index, (title, body) in enumerate(steps):
        with columns[index % 3]:
            st.markdown(
                f"""
                <div class="step-card">
                    <div class="step-title">{title}</div>
                    <div class="step-body">{body}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.expander("Szczegóły: parsed filters JSON", expanded=False):
        st.json(parsed_filters)

    with st.expander("Szczegóły: decision JSON", expanded=False):
        st.json(decision)

    with st.expander("Szczegóły: Qdrant hits", expanded=False):
        if qdrant_hits:
            st.dataframe(
                [
                    {
                        "rank": hit["rank"],
                        "source_id": hit["source_id"],
                        "score": round(hit["score"], 4),
                        "nazwa": hit.get("payload", {}).get("nazwa"),
                        "cena_pln": hit.get("payload", {}).get("cena_pln"),
                    }
                    for hit in qdrant_hits
                ],
                use_container_width=True,
            )
        else:
            st.write("Brak hitów Qdrant.")

    with st.expander("Szczegóły: kontekst wysłany do LLM", expanded=False):
        if context:
            st.code(context, language="text")
        else:
            st.write("Brak kontekstu, ponieważ retrieval nie zwrócił wyników.")


def _render_results(payload: dict[str, Any]) -> None:
    results = payload["results"]
    st.markdown(f"## Wyniki retrievalu ({len(results)})")
    if not results:
        st.info("Brak produktów spełniających twarde filtry z zapytania.")
        return

    for result in results:
        laptop = result["laptop"]
        st.markdown(
            f"""
            <div class="product-card">
                <div class="score">score: {result['score']:.4f}</div>
                <h3>{laptop['name']}</h3>
                <p class="meta">
                    {laptop['brand']} | {laptop['price_pln']:.2f} zł | {laptop['ram']} |
                    SSD: {laptop['ssd']} | {laptop['screen']}
                </p>
                <p>{laptop['semantic_description']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Parametry i źródło", expanded=False):
            left, right = st.columns(2)
            with left:
                st.write(f"**Procesor:** {laptop['processor']}")
                st.write(f"**GPU:** {laptop['gpu']}")
                st.write(f"**System:** {laptop['operating_system']}")
            with right:
                st.write(f"**RAM znormalizowany:** {laptop['ram_gb']} GB")
                st.write(f"**SSD znormalizowany:** {laptop['ssd_gb']} GB")
                st.write(f"**Ekran znormalizowany:** {laptop['screen_inches']} cala")
            st.link_button("Otwórz produkt w źródle", laptop["url"])


def _format_non_empty_filters(parsed_filters: dict[str, Any]) -> str:
    non_empty = {
        key: value for key, value in parsed_filters.items() if value is not None
    }
    if not non_empty:
        return "Brak jawnych filtrów. Retrieval działa tylko semantycznie."
    return ", ".join(f"{key}={value}" for key, value in non_empty.items())


def _format_decision(decision: dict[str, Any]) -> str:
    action_labels = {
        "search": "Szukaj od razu",
        "search_with_assumption": "Szukaj z miękkim założeniem",
        "ask_clarification": "Zadaj pytanie doprecyzowujące",
    }
    label = action_labels.get(decision["action"], decision["action"])
    if decision.get("clarifying_question"):
        return f"{label}. Pytanie: {decision['clarifying_question']}"
    return label


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at 10% 0%, rgba(255, 214, 102, 0.24), transparent 28rem),
                linear-gradient(135deg, #fffaf0 0%, #edf7f6 48%, #f7efe5 100%);
            color: #18211f;
        }
        .hero {
            padding: 2rem;
            border: 1px solid rgba(24, 33, 31, 0.12);
            border-radius: 28px;
            background: rgba(255, 255, 255, 0.72);
            box-shadow: 0 18px 55px rgba(31, 54, 48, 0.10);
            margin-bottom: 1.5rem;
        }
        .hero h1 {
            font-size: 3.2rem;
            letter-spacing: -0.06em;
            margin: 0.1rem 0 0.5rem;
        }
        .eyebrow {
            text-transform: uppercase;
            font-weight: 800;
            color: #87620f;
            letter-spacing: 0.08em;
            font-size: 0.8rem;
        }
        .answer, .step-card, .product-card {
            border: 1px solid rgba(24, 33, 31, 0.12);
            background: rgba(255, 255, 255, 0.82);
            border-radius: 22px;
            padding: 1.1rem 1.2rem;
            box-shadow: 0 10px 35px rgba(31, 54, 48, 0.08);
        }
        .answer {
            font-size: 1.08rem;
            line-height: 1.65;
            border-left: 6px solid #d7931f;
        }
        .step-card {
            min-height: 160px;
            margin-bottom: 1rem;
        }
        .step-title {
            font-weight: 800;
            color: #1f4f46;
            margin-bottom: 0.5rem;
        }
        .step-body {
            color: #3e4a47;
            line-height: 1.45;
        }
        .product-card {
            position: relative;
            margin: 1rem 0 0.35rem;
        }
        .product-card h3 {
            margin-right: 7rem;
            letter-spacing: -0.02em;
        }
        .meta {
            color: #50615d;
            font-weight: 700;
        }
        .score {
            position: absolute;
            top: 1rem;
            right: 1rem;
            border-radius: 999px;
            padding: 0.3rem 0.7rem;
            background: #163f38;
            color: #ffffff;
            font-size: 0.82rem;
            font-weight: 800;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
