"""Best Buy category mapping for the local catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from electronics_rag_assistant_shared.catalog import InternalCategory, ResolvedSourceCategory


@dataclass(frozen=True, slots=True)
class BestBuyCategorySeed:
    """Desired mapping between an internal category and a Best Buy category."""

    internal_category: InternalCategory
    expected_name: str
    preferred_path_terms: tuple[str, ...]


BESTBUY_CATEGORY_SEEDS: tuple[BestBuyCategorySeed, ...] = (
    BestBuyCategorySeed(
        internal_category=InternalCategory.LAPTOPS,
        expected_name="Laptops",
        preferred_path_terms=("Computers & Tablets",),
    ),
    BestBuyCategorySeed(
        internal_category=InternalCategory.MONITORS,
        expected_name="Monitors",
        preferred_path_terms=("Computers & Tablets",),
    ),
    BestBuyCategorySeed(
        internal_category=InternalCategory.TELEVISIONS,
        expected_name="All Flat-Panel TVs",
        preferred_path_terms=("TV & Home Theater",),
    ),
    BestBuyCategorySeed(
        internal_category=InternalCategory.MICE,
        expected_name="Mice",
        preferred_path_terms=("Computers & Tablets",),
    ),
    BestBuyCategorySeed(
        internal_category=InternalCategory.KEYBOARDS,
        expected_name="Keyboards",
        preferred_path_terms=("Computers & Tablets",),
    ),
    BestBuyCategorySeed(
        internal_category=InternalCategory.HEADPHONES,
        expected_name="Headphones",
        preferred_path_terms=("Audio",),
    ),
)


def build_category_search_expression(seed: BestBuyCategorySeed) -> str:
    """Build a Best Buy category search expression for an exact name match."""

    return f'name="{seed.expected_name}"'


def resolve_bestbuy_category(
    seed: BestBuyCategorySeed,
    categories: list[dict[str, Any]],
) -> ResolvedSourceCategory:
    """Resolve the best matching Best Buy category for the configured seed."""

    if not categories:
        raise ValueError(f"No Best Buy categories found for {seed.expected_name}")

    best_match = max(categories, key=lambda item: _score_candidate(seed, item))
    return ResolvedSourceCategory(
        internal_category=seed.internal_category,
        source_category_id=str(best_match["id"]),
        source_category_name=str(best_match["name"]),
        source_category_path=_extract_path_names(best_match),
        source_category_url=best_match.get("url"),
    )


def _score_candidate(seed: BestBuyCategorySeed, category: dict[str, Any]) -> int:
    expected_name = _normalize_text(seed.expected_name)
    actual_name = _normalize_text(str(category.get("name", "")))
    score = 0

    if actual_name == expected_name:
        score += 100

    if expected_name in actual_name:
        score += 25

    path_names = _extract_path_names(category)
    normalized_path_names = [_normalize_text(value) for value in path_names]
    for preferred_term in seed.preferred_path_terms:
        if _normalize_text(preferred_term) in normalized_path_names:
            score += 15

    score -= len(path_names)
    return score


def _extract_path_names(category: dict[str, Any]) -> list[str]:
    path_entries = category.get("path", [])
    names = [str(entry.get("name", "")).strip() for entry in path_entries if entry.get("name")]
    return [name for name in names if name]


def _normalize_text(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())
