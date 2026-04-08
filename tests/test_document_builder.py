from datetime import UTC, datetime

from electronics_rag_assistant_backend.indexing.document_builder import build_product_document
from electronics_rag_assistant_shared.catalog import InternalCategory, ProductRecord


def test_build_product_document_includes_core_fields_and_sorted_specs() -> None:
    record = ProductRecord(
        source_id="bestbuy:123",
        sku="123",
        name="Example Keyboard",
        brand="Keychron",
        internal_category=InternalCategory.KEYBOARDS,
        source_category_id="keyboard-cat",
        price_usd=129.99,
        availability="available",
        url=None,
        image_url=None,
        description="Mechanical keyboard with hot-swappable switches.",
        specs={"Layout": "ANSI", "Switch Type": "Brown"},
        last_synced_at=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
    )

    document = build_product_document(record)

    assert document.record == record
    assert document.text == (
        "Product name: Example Keyboard\n"
        "Category: keyboards\n"
        "Brand: Keychron\n"
        "Price USD: 129.99\n"
        "Availability: available\n"
        "Description: Mechanical keyboard with hot-swappable switches.\n"
        "Specifications:\n"
        "- Layout: ANSI\n"
        "- Switch Type: Brown"
    )


def test_build_product_document_skips_optional_empty_fields() -> None:
    record = ProductRecord(
        source_id="bestbuy:456",
        sku="456",
        name="Basic Mouse",
        brand=None,
        internal_category=InternalCategory.MICE,
        source_category_id="mouse-cat",
        price_usd=None,
        availability="unknown",
        url=None,
        image_url=None,
        description="Simple mouse.",
        specs={},
        last_synced_at=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
    )

    document = build_product_document(record)

    assert document.text == (
        "Product name: Basic Mouse\n"
        "Category: mice\n"
        "Availability: unknown\n"
        "Description: Simple mouse."
    )
