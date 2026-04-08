from datetime import UTC, datetime

from fastapi.testclient import TestClient

from electronics_rag_assistant_backend.dependencies import get_catalog_sync_service
from electronics_rag_assistant_backend.main import app
from electronics_rag_assistant_backend.source.bestbuy_client import BestBuyAuthenticationError
from electronics_rag_assistant_shared.catalog import (
    CatalogStatus,
    CatalogSyncReport,
    CategorySnapshot,
    CategorySyncResult,
    InternalCategory,
)


class StubCatalogSyncService:
    def __init__(self) -> None:
        synced_at = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
        self._report = CatalogSyncReport(
            source="bestbuy",
            total_products=1,
            categories=[
                CategorySyncResult(
                    internal_category=InternalCategory.LAPTOPS,
                    source_category_id="pcmcat1",
                    source_category_name="Laptops",
                    product_count=1,
                    last_synced_at=synced_at,
                )
            ],
            started_at=synced_at,
            finished_at=synced_at,
        )
        self._status = CatalogStatus(
            total_products=1,
            categories=[
                CategorySnapshot(
                    internal_category=InternalCategory.LAPTOPS,
                    source_category_id="pcmcat1",
                    source_category_name="Laptops",
                    source_category_path=["Computers & Tablets", "Laptops"],
                    source_category_url="https://example.com/laptops",
                    product_count=1,
                    last_synced_at=synced_at,
                )
            ],
            last_synced_at=synced_at,
        )

    def sync_catalog(self) -> CatalogSyncReport:
        return self._report

    def get_catalog_status(self) -> CatalogStatus:
        return self._status


class FailingCatalogSyncService:
    def sync_catalog(self) -> CatalogSyncReport:
        raise BestBuyAuthenticationError("BESTBUY_API_KEY is required")

    def get_catalog_status(self) -> CatalogStatus:
        return CatalogStatus()


def test_catalog_sync_endpoint_returns_report() -> None:
    app.dependency_overrides[get_catalog_sync_service] = lambda: StubCatalogSyncService()
    client = TestClient(app)

    response = client.post("/api/v1/catalog/sync")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["source"] == "bestbuy"
    assert response.json()["total_products"] == 1


def test_catalog_status_endpoint_returns_current_status() -> None:
    app.dependency_overrides[get_catalog_sync_service] = lambda: StubCatalogSyncService()
    client = TestClient(app)

    response = client.get("/api/v1/catalog/status")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["total_products"] == 1
    assert response.json()["categories"][0]["internal_category"] == "laptops"


def test_catalog_sync_endpoint_maps_bestbuy_auth_errors_to_503() -> None:
    app.dependency_overrides[get_catalog_sync_service] = lambda: FailingCatalogSyncService()
    client = TestClient(app)

    response = client.post("/api/v1/catalog/sync")

    app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["detail"] == "BESTBUY_API_KEY is required"
