from datetime import UTC, datetime

from electronics_rag_assistant_backend.catalog.categories import (
    BESTBUY_CATEGORY_SEEDS,
    build_category_search_expression,
    resolve_bestbuy_category,
)
from electronics_rag_assistant_backend.catalog.normalization import normalize_bestbuy_product
from electronics_rag_assistant_shared.catalog import InternalCategory


def test_build_category_search_expression_uses_exact_name_match() -> None:
    seed = next(seed for seed in BESTBUY_CATEGORY_SEEDS if seed.internal_category == "laptops")

    assert build_category_search_expression(seed) == 'name="Laptops"'


def test_resolve_bestbuy_category_prefers_exact_name_and_path() -> None:
    seed = next(seed for seed in BESTBUY_CATEGORY_SEEDS if seed.internal_category == "monitors")

    resolved = resolve_bestbuy_category(
        seed,
        [
            {
                "id": "audio123",
                "name": "Monitors",
                "path": [{"name": "Audio"}],
                "url": "https://example.com/audio-monitors",
            },
            {
                "id": "monitor456",
                "name": "Monitors",
                "path": [{"name": "Computers & Tablets"}, {"name": "Monitors"}],
                "url": "https://example.com/computer-monitors",
            },
        ],
    )

    assert resolved.internal_category == InternalCategory.MONITORS
    assert resolved.source_category_id == "monitor456"
    assert resolved.source_category_path == ["Computers & Tablets", "Monitors"]


def test_normalize_bestbuy_product_maps_bestbuy_payload_to_canonical_record() -> None:
    synced_at = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    category = resolve_bestbuy_category(
        next(seed for seed in BESTBUY_CATEGORY_SEEDS if seed.internal_category == "laptops"),
        [
            {
                "id": "pcmcat1",
                "name": "Laptops",
                "path": [{"name": "Computers & Tablets"}, {"name": "Laptops"}],
                "url": "https://example.com/laptops",
            }
        ],
    )

    record = normalize_bestbuy_product(
        {
            "sku": 1234567,
            "name": "Example Laptop 14",
            "manufacturer": "Lenovo",
            "salePrice": 799.99,
            "onlineAvailability": True,
            "url": "https://example.com/product",
            "image": "https://example.com/image.jpg",
            "longDescription": "Solid laptop for study and work.",
            "modelNumber": "ABC-123",
            "details": [
                {"name": "Screen Size", "value": "14 inches"},
                {"name": "RAM", "value": "16 GB"},
            ],
        },
        category,
        synced_at=synced_at,
    )

    assert record.source_id == "bestbuy:1234567"
    assert record.sku == "1234567"
    assert record.name == "Example Laptop 14"
    assert record.brand == "Lenovo"
    assert record.internal_category == InternalCategory.LAPTOPS
    assert record.source_category_id == "pcmcat1"
    assert record.price_usd == 799.99
    assert record.availability == "available"
    assert record.description == "Solid laptop for study and work."
    assert record.specs == {
        "model_number": "ABC-123",
        "Screen Size": "14 inches",
        "RAM": "16 GB",
    }
    assert record.last_synced_at == synced_at
