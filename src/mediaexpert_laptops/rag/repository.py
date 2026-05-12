"""SQLite catalog repository for laptop records."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from mediaexpert_laptops.rag.models import ImportReport, LaptopRecord, ParsedLaptopQuery
from mediaexpert_laptops.rag.normalization import normalize_laptop_row


class LaptopRepository:
    """SQLite-backed local laptop catalog."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        """Create schema if needed."""

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS laptops (
                    source_id TEXT PRIMARY KEY,
                    sku TEXT NOT NULL,
                    name TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    price_pln REAL NOT NULL,
                    availability TEXT NOT NULL,
                    url TEXT NOT NULL,
                    processor TEXT NOT NULL,
                    ram TEXT NOT NULL,
                    ssd TEXT NOT NULL,
                    hdd TEXT NOT NULL,
                    gpu TEXT NOT NULL,
                    screen TEXT NOT NULL,
                    operating_system TEXT NOT NULL,
                    description TEXT NOT NULL,
                    semantic_description TEXT NOT NULL,
                    scraped_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    ram_gb INTEGER,
                    ssd_gb INTEGER,
                    screen_inches REAL,
                    refresh_hz INTEGER,
                    has_dedicated_gpu INTEGER NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_laptops_brand ON laptops (brand)")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_laptops_price ON laptops (price_pln)"
            )

    def import_csv(self, csv_path: str | Path) -> ImportReport:
        """Replace local catalog with records from CSV."""

        csv_path = Path(csv_path)
        with csv_path.open(encoding="utf-8", newline="") as file:
            records = [normalize_laptop_row(row) for row in csv.DictReader(file)]

        with self._connect() as connection:
            connection.execute("DELETE FROM laptops")
            connection.executemany(
                """
                INSERT INTO laptops (
                    source_id, sku, name, brand, price_pln, availability, url, processor,
                    ram, ssd, hdd, gpu, screen, operating_system, description,
                    semantic_description, scraped_at, source, ram_gb, ssd_gb, screen_inches,
                    refresh_hz, has_dedicated_gpu
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self._to_row(record) for record in records],
            )

        return ImportReport(
            imported=len(records),
            source_csv=str(csv_path),
            database_path=str(self.database_path),
        )

    def list_laptops(self) -> list[LaptopRecord]:
        """Return all laptops."""

        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM laptops ORDER BY source_id").fetchall()
        return [self._from_row(row) for row in rows]

    def list_brands(self) -> list[str]:
        """Return available brands."""

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT brand FROM laptops ORDER BY brand"
            ).fetchall()
        return [row["brand"] for row in rows]

    def count_laptops(self) -> int:
        """Return total number of laptops in the catalog."""

        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM laptops").fetchone()
        return int(row["count"])

    def count_matching_filters(self, parsed_query: ParsedLaptopQuery) -> int:
        """Return how many laptops satisfy explicit hard filters."""

        where_clauses, values = self._filter_sql(parsed_query)
        query = "SELECT COUNT(*) AS count FROM laptops"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        with self._connect() as connection:
            row = connection.execute(query, values).fetchone()
        return int(row["count"])

    def get_by_source_ids(self, source_ids: list[str]) -> list[LaptopRecord]:
        """Return laptops in the input source ID order."""

        if not source_ids:
            return []
        placeholders = ",".join("?" for _ in source_ids)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM laptops WHERE source_id IN ({placeholders})",
                source_ids,
            ).fetchall()
        by_id = {row["source_id"]: self._from_row(row) for row in rows}
        return [by_id[source_id] for source_id in source_ids if source_id in by_id]

    def _filter_sql(self, parsed_query: ParsedLaptopQuery) -> tuple[list[str], list]:
        where_clauses: list[str] = []
        values: list = []

        if parsed_query.min_price_pln is not None:
            where_clauses.append("price_pln >= ?")
            values.append(parsed_query.min_price_pln)
        if parsed_query.max_price_pln is not None:
            where_clauses.append("price_pln <= ?")
            values.append(parsed_query.max_price_pln)
        if parsed_query.brand:
            where_clauses.append("brand = ?")
            values.append(parsed_query.brand)
        if parsed_query.operating_system:
            where_clauses.append("LOWER(operating_system) LIKE ?")
            values.append(f"%{parsed_query.operating_system.casefold()}%")
        if parsed_query.min_ram_gb is not None:
            where_clauses.append("ram_gb >= ?")
            values.append(parsed_query.min_ram_gb)
        if parsed_query.min_ssd_gb is not None:
            where_clauses.append("ssd_gb >= ?")
            values.append(parsed_query.min_ssd_gb)
        if parsed_query.requires_dedicated_gpu is True:
            where_clauses.append("has_dedicated_gpu = 1")
        if parsed_query.screen_size_min is not None:
            where_clauses.append("screen_inches >= ?")
            values.append(parsed_query.screen_size_min)
        if parsed_query.screen_size_max is not None:
            where_clauses.append("screen_inches <= ?")
            values.append(parsed_query.screen_size_max)

        return where_clauses, values

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _to_row(self, record: LaptopRecord) -> tuple:
        return (
            record.source_id,
            record.sku,
            record.name,
            record.brand,
            record.price_pln,
            record.availability,
            record.url,
            record.processor,
            record.ram,
            record.ssd,
            record.hdd,
            record.gpu,
            record.screen,
            record.operating_system,
            record.description,
            record.semantic_description,
            record.scraped_at,
            record.source,
            record.ram_gb,
            record.ssd_gb,
            record.screen_inches,
            record.refresh_hz,
            int(record.has_dedicated_gpu),
        )

    def _from_row(self, row: sqlite3.Row) -> LaptopRecord:
        return LaptopRecord(
            source_id=row["source_id"],
            sku=row["sku"],
            name=row["name"],
            brand=row["brand"],
            price_pln=row["price_pln"],
            availability=row["availability"],
            url=row["url"],
            processor=row["processor"],
            ram=row["ram"],
            ssd=row["ssd"],
            hdd=row["hdd"],
            gpu=row["gpu"],
            screen=row["screen"],
            operating_system=row["operating_system"],
            description=row["description"],
            semantic_description=row["semantic_description"],
            scraped_at=row["scraped_at"],
            source=row["source"],
            ram_gb=row["ram_gb"],
            ssd_gb=row["ssd_gb"],
            screen_inches=row["screen_inches"],
            refresh_hz=row["refresh_hz"],
            has_dedicated_gpu=bool(row["has_dedicated_gpu"]),
        )
