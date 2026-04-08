from datetime import UTC, datetime

from qdrant_client import QdrantClient

from electronics_rag_assistant_backend.indexing.qdrant_product_index import (
    EmbeddedProduct,
    QdrantProductIndex,
)
from electronics_rag_assistant_shared.catalog import InternalCategory, ProductRecord


def _product_record() -> ProductRecord:
    return ProductRecord(
        source_id="bestbuy:123",
        sku="123",
        name="Example Monitor",
        brand="Dell",
        internal_category=InternalCategory.MONITORS,
        source_category_id="monitor-cat",
        price_usd=349.99,
        availability="available",
        url="https://example.com/product",
        image_url="https://example.com/product.jpg",
        description="Good monitor for development work.",
        specs={"Resolution": "2560x1440", "Panel Type": "IPS"},
        last_synced_at=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
    )


def test_qdrant_index_upsert_is_idempotent() -> None:
    client = QdrantClient(location=":memory:")
    index = QdrantProductIndex(client, collection_name="products", vector_size=3)
    index.ensure_collection()

    embedded_product = EmbeddedProduct(
        record=_product_record(),
        vector=[0.1, 0.2, 0.3],
        document_text="monitor dell ips 1440p",
    )

    assert index.upsert_products([embedded_product]) == 1
    assert index.upsert_products([embedded_product]) == 1
    assert index.count() == 1


def test_qdrant_index_stores_filterable_payload_fields() -> None:
    client = QdrantClient(location=":memory:")
    index = QdrantProductIndex(client, collection_name="products", vector_size=3)
    index.ensure_collection()

    embedded_product = EmbeddedProduct(
        record=_product_record(),
        vector=[0.2, 0.4, 0.6],
        document_text="monitor dell ips 1440p",
    )
    index.upsert_products([embedded_product])

    points, _ = client.scroll(collection_name="products", limit=1, with_vectors=False)

    assert len(points) == 1
    assert points[0].payload["source_id"] == "bestbuy:123"
    assert points[0].payload["internal_category"] == "monitors"
    assert points[0].payload["price_usd"] == 349.99
    assert points[0].payload["document_text"] == "monitor dell ips 1440p"
