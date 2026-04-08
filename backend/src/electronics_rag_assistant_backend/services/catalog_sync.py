"""Catalog sync orchestration between Best Buy and local storage."""

from __future__ import annotations

from datetime import UTC, datetime

from electronics_rag_assistant_backend.catalog.categories import (
    BESTBUY_CATEGORY_SEEDS,
    build_category_search_expression,
    resolve_bestbuy_category,
)
from electronics_rag_assistant_backend.catalog.normalization import normalize_bestbuy_product
from electronics_rag_assistant_backend.source.bestbuy_client import BestBuyClient
from electronics_rag_assistant_backend.storage.sqlite_catalog_repository import (
    SQLiteCatalogRepository,
)
from electronics_rag_assistant_shared.catalog import (
    CatalogStatus,
    CatalogSyncReport,
    CategorySnapshot,
    CategorySyncResult,
)


class CatalogSyncService:
    """Synchronize the local catalog with the configured Best Buy source."""

    def __init__(
        self,
        *,
        repository: SQLiteCatalogRepository,
        bestbuy_client: BestBuyClient,
        page_size: int,
        max_pages_per_category: int,
    ) -> None:
        self._repository = repository
        self._bestbuy_client = bestbuy_client
        self._page_size = page_size
        self._max_pages_per_category = max_pages_per_category

    def sync_catalog(self) -> CatalogSyncReport:
        """Fetch, normalize, and persist products for all configured categories."""

        started_at = datetime.now(UTC)
        category_results: list[CategorySyncResult] = []
        total_products = 0

        for seed in BESTBUY_CATEGORY_SEEDS:
            categories = self._bestbuy_client.get_categories(
                build_category_search_expression(seed),
                page_size=25,
            )
            resolved_category = resolve_bestbuy_category(seed, categories)
            raw_products = self._bestbuy_client.get_products_for_category(
                resolved_category.source_category_id,
                page_size=self._page_size,
                max_pages=self._max_pages_per_category,
            )
            normalized_products = [
                normalize_bestbuy_product(
                    raw_product,
                    resolved_category,
                    synced_at=started_at,
                )
                for raw_product in raw_products
            ]
            snapshot = CategorySnapshot(
                internal_category=resolved_category.internal_category,
                source_category_id=resolved_category.source_category_id,
                source_category_name=resolved_category.source_category_name,
                source_category_path=resolved_category.source_category_path,
                source_category_url=resolved_category.source_category_url,
                product_count=len(normalized_products),
                last_synced_at=started_at,
            )
            self._repository.replace_category_snapshot(snapshot, normalized_products)
            category_results.append(
                CategorySyncResult(
                    internal_category=resolved_category.internal_category,
                    source_category_id=resolved_category.source_category_id,
                    source_category_name=resolved_category.source_category_name,
                    product_count=len(normalized_products),
                    last_synced_at=started_at,
                )
            )
            total_products += len(normalized_products)

        finished_at = datetime.now(UTC)
        return CatalogSyncReport(
            source="bestbuy",
            total_products=total_products,
            categories=category_results,
            started_at=started_at,
            finished_at=finished_at,
        )

    def get_catalog_status(self) -> CatalogStatus:
        """Return the current local catalog status."""

        return self._repository.get_catalog_status()
