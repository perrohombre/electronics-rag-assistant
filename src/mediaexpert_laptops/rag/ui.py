"""Streamlit UI for the laptop RAG assistant."""

from __future__ import annotations

import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


def main() -> None:
    """Run Streamlit UI."""

    st.set_page_config(page_title="Asystent laptopowy RAG", layout="wide")
    st.title("Asystent laptopowy RAG")
    st.caption("Jawne filtry z LLM + semantyczne wyszukiwanie po opisach laptopów.")

    query = st.text_area("Zapytanie", value="laptop do 4000 zł do programowania")
    limit = st.slider("Liczba wyników", min_value=3, max_value=10, value=5)

    if st.button("Szukaj"):
        response = requests.post(
            f"{API_URL}/answer",
            json={"query": query, "limit": limit},
            timeout=60,
        )
        if response.status_code != 200:
            st.error(response.text)
            return
        payload = response.json()
        st.subheader("Odpowiedź")
        st.write(payload["answer"])
        st.subheader("Wykryte jawne filtry")
        st.json(payload["parsed_query"])
        st.subheader("Źródła")
        for result in payload["results"]:
            laptop = result["laptop"]
            st.markdown(f"### {laptop['name']}")
            st.write(f"**Cena:** {laptop['price_pln']:.2f} zł | **Marka:** {laptop['brand']}")
            st.write(laptop["semantic_description"])
            st.link_button("Otwórz produkt", laptop["url"])


if __name__ == "__main__":
    main()

