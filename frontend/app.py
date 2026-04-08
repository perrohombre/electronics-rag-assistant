"""Streamlit shell for the Electronics RAG Assistant demo."""

import os

import streamlit as st

st.set_page_config(page_title="Electronics RAG Assistant", layout="wide")

api_host = os.getenv("API_HOST", "127.0.0.1")
api_port = os.getenv("API_PORT", "8000")
qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

st.title("Electronics RAG Assistant")
st.caption("Prototyp asystenta zakupowego RAG dla elektroniki użytkowej.")

left_column, right_column = st.columns([2, 1])

with left_column:
    query = st.text_input(
        "Zapytanie",
        placeholder="Np. jaki monitor do programowania do 500 USD",
    )
    if st.button("Szukaj", type="primary"):
        if query.strip():
            st.info("Obsługa wyszukiwania zostanie dodana w kolejnym PR-ze.")
        else:
            st.warning("Wpisz zapytanie, aby rozpocząć wyszukiwanie.")

with right_column:
    st.subheader("Usługi lokalne")
    st.write(f"API: `http://{api_host}:{api_port}`")
    st.write(f"Qdrant: `{qdrant_url}`")

st.subheader("Zakres v1")
st.write(
    "Kategorie startowe: laptopy, monitory, telewizory, myszki, klawiatury i słuchawki."
)
