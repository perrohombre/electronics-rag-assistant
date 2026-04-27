"""LLM-backed extraction of explicit hard filters."""

from __future__ import annotations

import re

from mediaexpert_laptops.rag.models import ParsedLaptopQuery


class QueryAnalysisService:
    """Extract explicit filters from Polish laptop queries."""

    def __init__(self, *, api_key: str, model: str, known_brands: list[str]) -> None:
        self._api_key = api_key
        self._model = model
        self._known_brands = sorted({brand.upper() for brand in known_brands})

    def analyze(self, query: str) -> ParsedLaptopQuery:
        """Return explicit filters; use a deterministic fallback without API key."""

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
                            f"{', '.join(self._known_brands)}."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                text_format=ParsedLaptopQuery,
            )
            parsed = response.output_parsed
        except Exception:
            parsed = self._fallback(query)

        return self._validate(parsed)

    def _fallback(self, query: str) -> ParsedLaptopQuery:
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

        return parsed

    def _validate(self, parsed: ParsedLaptopQuery) -> ParsedLaptopQuery:
        if parsed.brand and parsed.brand.upper() not in self._known_brands:
            parsed.brand = None
        elif parsed.brand:
            parsed.brand = parsed.brand.upper()
        return parsed
