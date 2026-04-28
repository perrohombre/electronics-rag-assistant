"""LLM-backed extraction of explicit hard filters."""

from __future__ import annotations

import re

from mediaexpert_laptops.rag.models import ParsedLaptopQuery, QueryDecision


class QueryAnalysisService:
    """Extract explicit filters from Polish laptop queries."""

    def __init__(self, *, api_key: str, model: str, known_brands: list[str]) -> None:
        self._api_key = api_key
        self._model = model
        self._known_brands = sorted({brand.upper() for brand in known_brands})

    def analyze(self, query: str) -> QueryDecision:
        """Return dialog decision and explicit filters."""

        if not self._api_key:
            return self._fallback(query)

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._api_key)
            response = client.responses.parse(
                model=self._model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Wyciągasz tylko jawne, twarde filtry z polskich zapytań o laptopy. "
                            "Nie zgaduj zastosowania, kategorii ani parametrów. Jeśli warunek nie "
                            "jest jasno podany, ustaw null. Marka musi być jedną z: "
                            f"{', '.join(self._known_brands)}. "
                            "Dodatkowo wybierasz action: search, search_with_assumption, "
                            "ask_clarification albo unsupported. Użyj unsupported, gdy użytkownik "
                            "szuka produktu spoza katalogu laptopów, np. klawiatury, myszy, "
                            "monitora albo zasilacza. Nie pytaj o doprecyzowanie, jeśli "
                            "zapytanie ma wystarczający sens semantyczny, np. laptop gamingowy "
                            "albo do nauki. "
                            "Zapytaj tylko wtedy, gdy brak informacji blokuje sensowną "
                            "rekomendację albo użytkownik używa pojęcia wymagającego progu, "
                            "np. tani, budżetowy, niedrogi, bez podania kwoty. Jeśli da się "
                            "szukać z założeniem, wybierz "
                            "search_with_assumption i opisz założenie. Zadawaj maksymalnie jedno "
                            "krótkie pytanie po polsku."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                text_format=QueryDecision,
            )
            decision = response.output_parsed
        except Exception:
            decision = self._fallback(query)

        return self._validate(decision, query)

    def _fallback(self, query: str) -> QueryDecision:
        text = query.casefold()
        parsed = ParsedLaptopQuery()

        max_price = re.search(
            r"(?:do|poniżej|ponizej|max(?:imum)?)\s*(\d[\d\s]*)\s*(?:zł|zl|pln)",
            text,
        )
        if max_price:
            parsed.max_price_pln = float(max_price.group(1).replace(" ", ""))

        min_price = re.search(
            r"(?:od|powyżej|powyzej|min(?:imum)?)\s*(\d[\d\s]*)\s*(?:zł|zl|pln)",
            text,
        )
        if min_price:
            parsed.min_price_pln = float(min_price.group(1).replace(" ", ""))

        ram = re.search(r"(?:minimum|min\.?|co najmniej|od)\s*(\d+)\s*gb\s*ram", text)
        if ram:
            parsed.min_ram_gb = int(ram.group(1))

        ssd = re.search(
            r"(?:minimum|min\.?|co najmniej|od)\s*(\d+)\s*(gb|tb)\s*(?:ssd|dysku)",
            text,
        )
        if ssd:
            value = int(ssd.group(1))
            parsed.min_ssd_gb = value * 1000 if ssd.group(2) == "tb" else value

        for brand in self._known_brands:
            if brand.casefold() in text or (brand == "APPLE" and "macbook" in text):
                parsed.brand = brand
                break

        if "windows" in text:
            parsed.operating_system = "Windows"
        elif "macos" in text or "macbook" in text:
            parsed.operating_system = "macOS"
        elif "chrome os" in text or "chromebook" in text:
            parsed.operating_system = "Chrome OS"

        if "dedykowan" in text or "rtx" in text or "geforce" in text:
            parsed.requires_dedicated_gpu = True

        screen_max = re.search(r'(?:do|max)\s*(\d+(?:[,.]\d+)?)\s*(?:cali|cal|")', text)
        if screen_max:
            parsed.screen_size_max = float(screen_max.group(1).replace(",", "."))

        screen_min = re.search(r'(?:od|min)\s*(\d+(?:[,.]\d+)?)\s*(?:cali|cal|")', text)
        if screen_min:
            parsed.screen_size_min = float(screen_min.group(1).replace(",", "."))

        action = "search"
        clarifying_question = None
        assumptions: list[str] = []
        unsupported_words = (
            "klawiatura",
            "klawiaturę",
            "klawiature",
            "mysz",
            "myszka",
            "monitor",
            "słuchawki",
            "sluchawki",
            "telefon",
            "smartfon",
            "zasilacz",
            "torba",
            "plecak",
        )
        budget_words = ("budżetowy", "budzetowy", "tani", "taniego", "niedrogi", "niedrogiego")
        broad_queries = {
            "laptop",
            "jaki laptop",
            "dobry laptop",
            "poleć laptop",
            "polec laptop",
        }
        has_budget_word = any(word in text for word in budget_words)
        has_clear_budget = parsed.max_price_pln is not None or parsed.min_price_pln is not None
        has_any_filter = any(value is not None for value in parsed.model_dump().values())
        has_semantic_signal = any(
            token in text
            for token in (
                "gaming",
                "gamingowy",
                "programowania",
                "programowanie",
                "nauki",
                "studia",
                "biura",
                "pracy",
                "mobilny",
                "lekki",
            )
        )

        if any(word in text for word in unsupported_words):
            action = "unsupported"
            clarifying_question = (
                "Obecny katalog obejmuje tylko laptopy. Nie mogę wyszukać tego typu produktu."
            )
        elif has_budget_word and not has_clear_budget:
            action = "search_with_assumption" if has_semantic_signal else "ask_clarification"
            clarifying_question = "Jaki maksymalny budżet w złotówkach mam przyjąć?"
            assumptions.append("Nie ustawiono filtra ceny, bo użytkownik nie podał kwoty.")
        elif text.strip() in broad_queries or (not has_any_filter and not has_semantic_signal):
            action = "ask_clarification"
            clarifying_question = (
                "Do czego laptop ma być używany i jaki maksymalny budżet mam przyjąć?"
            )

        return QueryDecision(
            action=action,
            filters=parsed,
            semantic_query=query,
            clarifying_question=clarifying_question,
            assumptions=assumptions,
        )

    def _validate(self, decision: QueryDecision, query: str) -> QueryDecision:
        parsed = decision.filters
        if parsed.brand and parsed.brand.upper() not in self._known_brands:
            parsed.brand = None
        elif parsed.brand:
            parsed.brand = parsed.brand.upper()
        if decision.action not in {"ask_clarification", "unsupported"}:
            decision.clarifying_question = decision.clarifying_question or None
        if not decision.semantic_query:
            decision.semantic_query = query
        decision.filters = parsed
        return decision
