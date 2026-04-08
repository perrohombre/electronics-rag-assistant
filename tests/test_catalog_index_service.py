from datetime import UTC, datetime

from qdrant_client import QdrantClient

from electronics_rag_assistant_backend.indexing.qdrant_product_index import QdrantProductIndex
from electronics_rag_assistant_backend.services.catalog_index import CatalogIndexService
from electronics_rag_assistant_backend.storage.sqlite_catalog_repository import (
    SQLiteCatalogRepository,
)
from electronics_rag_assistant_shared.catalog import (
    CategorySnapshot,
    InternalCategory,
    ProductRecord,
)


class FakeEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            [float(index), float(index) + 0.25, float(index) + 0.5]
            for index, _ in enumerate(texts)
        ]


def test_catalog_index_service_indexes_local_products_into_qdrant(tmp_path) -> None:
    repository = SQLiteCatalogRepository(tmp_path / "catalog.db")
    synced_at = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    repository.replace_category_snapshot(
        CategorySnapshot(
            internal_category=InternalCategory.MONITORS,
            source_category_id="monitor-cat",
            source_category_name="Monitors",
            source_category_path=["Computers & Tablets", "Monitors"],
            source_category_url="https://example.com/monitors",
            product_count=1,
            last_synced_at=synced_at,
        ),
        [
            ProductRecord(
                source_id="bestbuy:321",
                sku="321",
                name="Developer Monitor",
                brand="Dell",
                internal_category=InternalCategory.MONITORS,
                source_category_id="monitor-cat",
                price_usd=399.0,
                availability="available",
                url="https://example.com/321",
                image_url=None,
                description="27-inch IPS display.",
                specs={"Refresh Rate": "144 Hz"},
                last_synced_at=synced_at,
            )
        ],
    )

    qdrant_client = QdrantClient(location=":memory:")
    product_index = QdrantProductIndex(
        qdrant_client,
        collection_name="products",
        vector_size=3,
    )
    service = CatalogIndexService(
        repository=repository,
        product_index=product_index,
        embedder=FakeEmbedder(),
        embedding_model="test-model",
    )

    report = service.index_catalog()
    points, _ = qdrant_client.scroll(collection_name="products", limit=1, with_vectors=False)

    assert report.collection_name == "products"
    assert report.embedding_model == "test-model"
    assert report.indexed_products == 1
    assert len(points) == 1
    assert points[0].payload["source_id"] == "bestbuy:321"
    assert "Developer Monitor" in points[0].payload["document_text"]
