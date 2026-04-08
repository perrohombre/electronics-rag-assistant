"""SQLite persistence for the local product catalog."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from electronics_rag_assistant_shared.catalog import CatalogStatus, CategorySnapshot, ProductRecord


class SQLiteCatalogRepository:
    """SQLite-backed catalog repository."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self.initialize()

    def initialize(self) -> None:
        """Create the database schema if it does not already exist."""

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog_categories (
                    internal_category TEXT PRIMARY KEY,
                    source_category_id TEXT NOT NULL,
                    source_category_name TEXT NOT NULL,
                    source_category_path_json TEXT NOT NULL,
                    source_category_url TEXT,
                    product_count INTEGER NOT NULL,
                    last_synced_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    source_id TEXT PRIMARY KEY,
                    sku TEXT NOT NULL,
                    name TEXT NOT NULL,
                    brand TEXT,
                    internal_category TEXT NOT NULL,
                    source_category_id TEXT NOT NULL,
                    price_usd REAL,
                    availability TEXT NOT NULL,
                    url TEXT,
                    image_url TEXT,
                    description TEXT NOT NULL,
                    specs_json TEXT NOT NULL,
                    last_synced_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_products_internal_category "
                "ON products (internal_category)"
            )

    def replace_category_snapshot(
        self,
        snapshot: CategorySnapshot,
        products: Iterable[ProductRecord],
    ) -> None:
        """Replace all products for one internal category with a fresh snapshot."""

        products = list(products)
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM products WHERE internal_category = ?",
                (snapshot.internal_category,),
            )
            connection.executemany(
                """
                INSERT INTO products (
                    source_id,
                    sku,
                    name,
                    brand,
                    internal_category,
                    source_category_id,
                    price_usd,
                    availability,
                    url,
                    image_url,
                    description,
                    specs_json,
                    last_synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        product.source_id,
                        product.sku,
                        product.name,
                        product.brand,
                        product.internal_category,
                        product.source_category_id,
                        product.price_usd,
                        product.availability,
                        product.url,
                        product.image_url,
                        product.description,
                        json.dumps(product.specs, sort_keys=True),
                        product.last_synced_at.isoformat(),
                    )
                    for product in products
                ],
            )
            connection.execute(
                """
                INSERT INTO catalog_categories (
                    internal_category,
                    source_category_id,
                    source_category_name,
                    source_category_path_json,
                    source_category_url,
                    product_count,
                    last_synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(internal_category) DO UPDATE SET
                    source_category_id = excluded.source_category_id,
                    source_category_name = excluded.source_category_name,
                    source_category_path_json = excluded.source_category_path_json,
                    source_category_url = excluded.source_category_url,
                    product_count = excluded.product_count,
                    last_synced_at = excluded.last_synced_at
                """,
                (
                    snapshot.internal_category,
                    snapshot.source_category_id,
                    snapshot.source_category_name,
                    json.dumps(snapshot.source_category_path),
                    snapshot.source_category_url,
                    snapshot.product_count,
                    snapshot.last_synced_at.isoformat(),
                ),
            )

    def get_catalog_status(self) -> CatalogStatus:
        """Return the current catalog status derived from persisted snapshots."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    internal_category,
                    source_category_id,
                    source_category_name,
                    source_category_path_json,
                    source_category_url,
                    product_count,
                    last_synced_at
                FROM catalog_categories
                ORDER BY internal_category
                """
            ).fetchall()

        categories = [
            CategorySnapshot(
                internal_category=row["internal_category"],
                source_category_id=row["source_category_id"],
                source_category_name=row["source_category_name"],
                source_category_path=json.loads(row["source_category_path_json"]),
                source_category_url=row["source_category_url"],
                product_count=row["product_count"],
                last_synced_at=row["last_synced_at"],
            )
            for row in rows
        ]
        last_synced_at = max((snapshot.last_synced_at for snapshot in categories), default=None)

        return CatalogStatus(
            total_products=sum(snapshot.product_count for snapshot in categories),
            categories=categories,
            last_synced_at=last_synced_at,
        )

    def list_products(self) -> list[ProductRecord]:
        """Return all locally persisted products."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    source_id,
                    sku,
                    name,
                    brand,
                    internal_category,
                    source_category_id,
                    price_usd,
                    availability,
                    url,
                    image_url,
                    description,
                    specs_json,
                    last_synced_at
                FROM products
                ORDER BY internal_category, sku
                """
            ).fetchall()

        return [self._map_product_row(row) for row in rows]

    def get_product(self, source_id: str) -> ProductRecord | None:
        """Return one locally persisted product by source identifier."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    source_id,
                    sku,
                    name,
                    brand,
                    internal_category,
                    source_category_id,
                    price_usd,
                    availability,
                    url,
                    image_url,
                    description,
                    specs_json,
                    last_synced_at
                FROM products
                WHERE source_id = ?
                """,
                (source_id,),
            ).fetchone()

        return self._map_product_row(row) if row is not None else None

    def get_products_by_source_ids(self, source_ids: list[str]) -> list[ProductRecord]:
        """Return locally persisted products for the requested source IDs in input order."""

        if not source_ids:
            return []

        placeholders = ", ".join("?" for _ in source_ids)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    source_id,
                    sku,
                    name,
                    brand,
                    internal_category,
                    source_category_id,
                    price_usd,
                    availability,
                    url,
                    image_url,
                    description,
                    specs_json,
                    last_synced_at
                FROM products
                WHERE source_id IN ({placeholders})
                """,
                source_ids,
            ).fetchall()

        products_by_id = {row["source_id"]: self._map_product_row(row) for row in rows}
        return [
            products_by_id[source_id]
            for source_id in source_ids
            if source_id in products_by_id
        ]

    def list_distinct_brands(self, limit: int) -> list[str]:
        """Return distinct non-empty brands sorted case-insensitively."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT brand
                FROM products
                WHERE brand IS NOT NULL AND TRIM(brand) != ''
                ORDER BY LOWER(TRIM(brand)), TRIM(brand)
                """
            ).fetchall()

        brands: list[str] = []
        seen: set[str] = set()
        for row in rows:
            brand = str(row["brand"]).strip()
            brand_key = brand.casefold()
            if not brand or brand_key in seen:
                continue
            seen.add(brand_key)
            brands.append(brand)
            if len(brands) >= limit:
                break

        return brands

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _map_product_row(self, row: sqlite3.Row) -> ProductRecord:
        return ProductRecord(
            source_id=row["source_id"],
            sku=row["sku"],
            name=row["name"],
            brand=row["brand"],
            internal_category=row["internal_category"],
            source_category_id=row["source_category_id"],
            price_usd=row["price_usd"],
            availability=row["availability"],
            url=row["url"],
            image_url=row["image_url"],
            description=row["description"],
            specs=json.loads(row["specs_json"]),
            last_synced_at=row["last_synced_at"],
        )
