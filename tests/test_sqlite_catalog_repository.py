from datetime import UTC, datetime

from electronics_rag_assistant_backend.storage.sqlite_catalog_repository import (
    SQLiteCatalogRepository,
)
from electronics_rag_assistant_shared.catalog import (
    CategorySnapshot,
    InternalCategory,
    ProductRecord,
)


def test_repository_replaces_snapshot_and_returns_catalog_status(tmp_path) -> None:
    repository = SQLiteCatalogRepository(tmp_path / "catalog.db")
    synced_at = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    snapshot = CategorySnapshot(
        internal_category=InternalCategory.LAPTOPS,
        source_category_id="pcmcat1",
        source_category_name="Laptops",
        source_category_path=["Computers & Tablets", "Laptops"],
        source_category_url="https://example.com/laptops",
        product_count=2,
        last_synced_at=synced_at,
    )
    products = [
        ProductRecord(
            source_id="bestbuy:1",
            sku="1",
            name="Laptop 1",
            brand="Brand A",
            internal_category=InternalCategory.LAPTOPS,
            source_category_id="pcmcat1",
            price_usd=999.0,
            availability="available",
            url="https://example.com/1",
            image_url="https://example.com/1.jpg",
            description="Laptop",
            specs={"RAM": "16 GB"},
            last_synced_at=synced_at,
        ),
        ProductRecord(
            source_id="bestbuy:2",
            sku="2",
            name="Laptop 2",
            brand="Brand B",
            internal_category=InternalCategory.LAPTOPS,
            source_category_id="pcmcat1",
            price_usd=1299.0,
            availability="available",
            url="https://example.com/2",
            image_url="https://example.com/2.jpg",
            description="Laptop",
            specs={"RAM": "32 GB"},
            last_synced_at=synced_at,
        ),
    ]

    repository.replace_category_snapshot(snapshot, products)
    status = repository.get_catalog_status()

    assert status.total_products == 2
    assert status.last_synced_at == synced_at
    assert len(status.categories) == 1
    assert status.categories[0].internal_category == InternalCategory.LAPTOPS
    assert status.categories[0].product_count == 2


def test_repository_replaces_existing_products_for_category(tmp_path) -> None:
    repository = SQLiteCatalogRepository(tmp_path / "catalog.db")
    first_synced_at = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    second_synced_at = datetime(2026, 4, 8, 13, 0, tzinfo=UTC)

    repository.replace_category_snapshot(
        CategorySnapshot(
            internal_category=InternalCategory.HEADPHONES,
            source_category_id="cat-1",
            source_category_name="Headphones",
            source_category_path=["Audio", "Headphones"],
            source_category_url="https://example.com/headphones",
            product_count=2,
            last_synced_at=first_synced_at,
        ),
        [
            ProductRecord(
                source_id="bestbuy:11",
                sku="11",
                name="Headphones 11",
                brand="Brand A",
                internal_category=InternalCategory.HEADPHONES,
                source_category_id="cat-1",
                price_usd=199.0,
                availability="available",
                url="https://example.com/11",
                image_url=None,
                description="Headphones",
                specs={},
                last_synced_at=first_synced_at,
            ),
            ProductRecord(
                source_id="bestbuy:12",
                sku="12",
                name="Headphones 12",
                brand="Brand B",
                internal_category=InternalCategory.HEADPHONES,
                source_category_id="cat-1",
                price_usd=249.0,
                availability="available",
                url="https://example.com/12",
                image_url=None,
                description="Headphones",
                specs={},
                last_synced_at=first_synced_at,
            ),
        ],
    )

    repository.replace_category_snapshot(
        CategorySnapshot(
            internal_category=InternalCategory.HEADPHONES,
            source_category_id="cat-1",
            source_category_name="Headphones",
            source_category_path=["Audio", "Headphones"],
            source_category_url="https://example.com/headphones",
            product_count=1,
            last_synced_at=second_synced_at,
        ),
        [
            ProductRecord(
                source_id="bestbuy:13",
                sku="13",
                name="Headphones 13",
                brand="Brand C",
                internal_category=InternalCategory.HEADPHONES,
                source_category_id="cat-1",
                price_usd=299.0,
                availability="available",
                url="https://example.com/13",
                image_url=None,
                description="Headphones",
                specs={},
                last_synced_at=second_synced_at,
            )
        ],
    )

    status = repository.get_catalog_status()

    assert status.total_products == 1
    assert status.last_synced_at == second_synced_at
    assert status.categories[0].product_count == 1


def test_repository_lists_distinct_brands_case_insensitively(tmp_path) -> None:
    repository = SQLiteCatalogRepository(tmp_path / "catalog.db")
    synced_at = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)

    repository.replace_category_snapshot(
        CategorySnapshot(
            internal_category=InternalCategory.MONITORS,
            source_category_id="cat-2",
            source_category_name="Monitors",
            source_category_path=["Displays", "Monitors"],
            source_category_url="https://example.com/monitors",
            product_count=4,
            last_synced_at=synced_at,
        ),
        [
            ProductRecord(
                source_id="bestbuy:21",
                sku="21",
                name="Monitor 21",
                brand="Dell",
                internal_category=InternalCategory.MONITORS,
                source_category_id="cat-2",
                price_usd=299.0,
                availability="available",
                url="https://example.com/21",
                image_url=None,
                description="Monitor",
                specs={},
                last_synced_at=synced_at,
            ),
            ProductRecord(
                source_id="bestbuy:22",
                sku="22",
                name="Monitor 22",
                brand="dell",
                internal_category=InternalCategory.MONITORS,
                source_category_id="cat-2",
                price_usd=319.0,
                availability="available",
                url="https://example.com/22",
                image_url=None,
                description="Monitor",
                specs={},
                last_synced_at=synced_at,
            ),
            ProductRecord(
                source_id="bestbuy:23",
                sku="23",
                name="Monitor 23",
                brand=" LG ",
                internal_category=InternalCategory.MONITORS,
                source_category_id="cat-2",
                price_usd=349.0,
                availability="available",
                url="https://example.com/23",
                image_url=None,
                description="Monitor",
                specs={},
                last_synced_at=synced_at,
            ),
            ProductRecord(
                source_id="bestbuy:24",
                sku="24",
                name="Monitor 24",
                brand="",
                internal_category=InternalCategory.MONITORS,
                source_category_id="cat-2",
                price_usd=359.0,
                availability="available",
                url="https://example.com/24",
                image_url=None,
                description="Monitor",
                specs={},
                last_synced_at=synced_at,
            ),
        ],
    )

    assert repository.list_distinct_brands(limit=10) == ["Dell", "LG"]
    assert repository.list_distinct_brands(limit=1) == ["Dell"]


def test_repository_returns_products_by_source_id_in_requested_order(tmp_path) -> None:
    repository = SQLiteCatalogRepository(tmp_path / "catalog.db")
    synced_at = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    repository.replace_category_snapshot(
        CategorySnapshot(
            internal_category=InternalCategory.MONITORS,
            source_category_id="cat-3",
            source_category_name="Monitors",
            source_category_path=["Displays", "Monitors"],
            source_category_url="https://example.com/monitors",
            product_count=2,
            last_synced_at=synced_at,
        ),
        [
            ProductRecord(
                source_id="bestbuy:31",
                sku="31",
                name="Monitor 31",
                brand="Dell",
                internal_category=InternalCategory.MONITORS,
                source_category_id="cat-3",
                price_usd=299.0,
                availability="available",
                url="https://example.com/31",
                image_url=None,
                description="Monitor",
                specs={},
                last_synced_at=synced_at,
            ),
            ProductRecord(
                source_id="bestbuy:32",
                sku="32",
                name="Monitor 32",
                brand="LG",
                internal_category=InternalCategory.MONITORS,
                source_category_id="cat-3",
                price_usd=349.0,
                availability="available",
                url="https://example.com/32",
                image_url=None,
                description="Monitor",
                specs={},
                last_synced_at=synced_at,
            ),
        ],
    )

    assert repository.get_product("bestbuy:31") is not None
    assert repository.get_product("bestbuy:404") is None
    assert [
        product.source_id
        for product in repository.get_products_by_source_ids(
            ["bestbuy:32", "bestbuy:404", "bestbuy:31"]
        )
    ] == ["bestbuy:32", "bestbuy:31"]
