"""Heuristic parser for Polish shopping queries."""

from __future__ import annotations

import re
import unicodedata

from electronics_rag_assistant_shared.catalog import InternalCategory
from electronics_rag_assistant_shared.search import CurrencyCode, ParsedSearchQuery, SearchIntent

_POLISH_CHAR_REPLACEMENTS = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "a",
        "Ć": "c",
        "Ę": "e",
        "Ł": "l",
        "Ń": "n",
        "Ó": "o",
        "Ś": "s",
        "Ź": "z",
        "Ż": "z",
    }
)

_CATEGORY_PATTERNS: tuple[tuple[InternalCategory, tuple[str, ...]], ...] = (
    (InternalCategory.LAPTOPS, ("laptop", "laptopy", "notebook", "notebooki")),
    (InternalCategory.MONITORS, ("monitor", "monitory")),
    (InternalCategory.TELEVISIONS, ("telewizor", "telewizory", "tv")),
    (InternalCategory.MICE, ("mysz", "myszka", "myszki", "mouse")),
    (InternalCategory.KEYBOARDS, ("klawiatura", "klawiatury", "keyboard", "keyboards")),
    (InternalCategory.HEADPHONES, ("sluchawki", "sluchawka", "headphones", "headset")),
)

_KNOWN_BRANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Apple", ("apple",)),
    ("Asus", ("asus",)),
    ("Acer", ("acer",)),
    ("Bose", ("bose",)),
    ("Dell", ("dell",)),
    ("HP", ("hp", "hewlett packard")),
    ("JBL", ("jbl",)),
    ("Keychron", ("keychron",)),
    ("LG", ("lg",)),
    ("Lenovo", ("lenovo",)),
    ("Logitech", ("logitech",)),
    ("MSI", ("msi",)),
    ("Philips", ("philips",)),
    ("Razer", ("razer",)),
    ("Samsung", ("samsung",)),
    ("Sennheiser", ("sennheiser",)),
    ("Sony", ("sony",)),
    ("SteelSeries", ("steelseries",)),
    ("Xiaomi", ("xiaomi",)),
)

_PLN_PATTERN = re.compile(
    r"(?:(?:do|ponizej|maksymalnie|max)\s+)?(\d+(?:[.,]\d+)?)\s*(pln|zl|zł)\b"
)
_USD_PATTERN = re.compile(
    r"(?:(?:do|ponizej|maksymalnie|max)\s+)?(\d+(?:[.,]\d+)?)\s*(usd|dolary|dolarow|dolarów|dolar)\b"
)
_USD_PREFIX_PATTERN = re.compile(r"\$\s*(\d+(?:[.,]\d+)?)")
_BUDGET_WITHOUT_CURRENCY_PATTERN = re.compile(
    r"(?:do|ponizej|maksymalnie|max)\s+(\d+(?:[.,]\d+)?)\b"
)


def parse_search_query(raw_query: str) -> ParsedSearchQuery:
    """Extract intent and hard constraints from a user query."""

    normalized_query = _normalize_query(raw_query)
    budget_value, budget_currency = _extract_budget(normalized_query)

    return ParsedSearchQuery(
        raw_query=raw_query.strip(),
        normalized_query=normalized_query,
        intent=_extract_intent(normalized_query),
        category=_extract_category(normalized_query),
        brand=_extract_brand(normalized_query),
        budget_value=budget_value,
        budget_currency=budget_currency,
        availability=_extract_availability(normalized_query),
        semantic_query=raw_query.strip(),
    )


def _extract_intent(normalized_query: str) -> SearchIntent:
    if any(token in normalized_query for token in ("porownaj", "versus", " vs ", "compare")):
        return SearchIntent.COMPARISON
    return SearchIntent.SEARCH


def _extract_category(normalized_query: str) -> InternalCategory | None:
    for category, patterns in _CATEGORY_PATTERNS:
        if any(
            re.search(rf"(?<!\w){re.escape(pattern)}(?!\w)", normalized_query)
            for pattern in patterns
        ):
            return category
    return None


def _extract_brand(normalized_query: str) -> str | None:
    for canonical_brand, aliases in _KNOWN_BRANDS:
        if any(
            re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized_query)
            for alias in aliases
        ):
            return canonical_brand
    return None


def _extract_budget(normalized_query: str) -> tuple[float | None, CurrencyCode | None]:
    for pattern, currency in (
        (_PLN_PATTERN, CurrencyCode.PLN),
        (_USD_PATTERN, CurrencyCode.USD),
        (_USD_PREFIX_PATTERN, CurrencyCode.USD),
        (_BUDGET_WITHOUT_CURRENCY_PATTERN, CurrencyCode.USD),
    ):
        match = pattern.search(normalized_query)
        if match is None:
            continue
        amount = float(match.group(1).replace(",", "."))
        return amount, currency
    return None, None


def _extract_availability(normalized_query: str) -> str:
    if any(token in normalized_query for token in ("niedostepn", "brak dostepnosci")):
        return "unavailable"
    if any(
        token in normalized_query
        for token in ("na stanie", "w magazynie", "dostepn", "od reki")
    ):
        return "available"
    return "available"


def _normalize_query(raw_query: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw_query.translate(_POLISH_CHAR_REPLACEMENTS))
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    collapsed = re.sub(r"[^a-z0-9$ ]+", " ", ascii_only)
    return re.sub(r"\s+", " ", collapsed).strip()
