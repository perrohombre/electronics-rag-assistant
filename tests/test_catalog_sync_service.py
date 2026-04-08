from datetime import UTC, datetime

from electronics_rag_assistant_backend.catalog.categories import BESTBUY_CATEGORY_SEEDS
from electronics_rag_assistant_backend.services.catalog_sync import CatalogSyncService
from electronics_rag_assistant_backend.storage.sqlite_catalog_repository import (
    SQLiteCatalogRepository,
)


class FakeBestBuyClient:
    def get_categories(self, search_expression: str, *, page_size: int = 100) -> list[dict]:
        expected_name = search_expression.split('"')[1]
        return [
            {
                "id": f"{expected_name.lower().replace(' ', '-')}-id",
                "name": expected_name,
                "path": [{"name": "Computers & Tablets"}, {"name": expected_name}],
                "url": f"https://example.com/{expected_name.lower().replace(' ', '-')}",
            }
        ]

    def get_products_for_category(
        self,
        category_id: str,
        *,
        page_size: int,
        max_pages: int,
    ) -> list[dict]:
        return [
            {
                "sku": f"{category_id}-1",
                "name": f"Product for {category_id}",
                "manufacturer": "Brand A",
                "salePrice": 199.0,
                "onlineAvailability": True,
                "url": "https://example.com/product",
                "image": "https://example.com/product.jpg",
                "shortDescription": "Example description",
                "details": [{"name": "Spec", "value": "Value"}],
            }
        ]


def test_sync_service_persists_one_snapshot_per_seed(tmp_path, monkeypatch) -> None:
    fixed_time = datetime(2026, 4, 8, 15, 0, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return fixed_time

    monkeypatch.setattr(
        "electronics_rag_assistant_backend.services.catalog_sync.datetime",
        FrozenDateTime,
    )

    repository = SQLiteCatalogRepository(tmp_path / "catalog.db")
    service = CatalogSyncService(
        repository=repository,
        bestbuy_client=FakeBestBuyClient(),
        page_size=100,
        max_pages_per_category=1,
    )

    report = service.sync_catalog()
    status = repository.get_catalog_status()

    assert report.source == "bestbuy"
    assert report.total_products == len(BESTBUY_CATEGORY_SEEDS)
    assert len(report.categories) == len(BESTBUY_CATEGORY_SEEDS)
    assert status.total_products == len(BESTBUY_CATEGORY_SEEDS)
    assert len(status.categories) == len(BESTBUY_CATEGORY_SEEDS)
    assert status.last_synced_at == fixed_time
