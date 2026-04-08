"""Qdrant collection management and payload mapping for products."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.http import models

from electronics_rag_assistant_shared.catalog import ProductRecord


@dataclass(slots=True)
class EmbeddedProduct:
    """Canonical product record paired with its embedding vector."""

    record: ProductRecord
    vector: Sequence[float]
    document_text: str


class QdrantProductIndex:
    """Manages the Qdrant collection used for product retrieval."""

    def __init__(
        self,
        client: QdrantClient,
        *,
        collection_name: str,
        vector_size: int,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._vector_size = vector_size

    @property
    def collection_name(self) -> str:
        """Return the configured collection name."""

        return self._collection_name

    def ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""

        if self._client.collection_exists(self._collection_name):
            collection = self._client.get_collection(self._collection_name)
            configured_size = collection.config.params.vectors.size
            if configured_size != self._vector_size:
                raise ValueError(
                    "Existing Qdrant collection uses a different vector size: "
                    f"{configured_size} != {self._vector_size}"
                )
            return

        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=models.VectorParams(
                size=self._vector_size,
                distance=models.Distance.COSINE,
            ),
        )
        for field_name, schema in (
            ("internal_category", models.PayloadSchemaType.KEYWORD),
            ("source_category_id", models.PayloadSchemaType.KEYWORD),
            ("brand", models.PayloadSchemaType.KEYWORD),
            ("availability", models.PayloadSchemaType.KEYWORD),
            ("price_usd", models.PayloadSchemaType.FLOAT),
            ("sku", models.PayloadSchemaType.KEYWORD),
        ):
            self._client.create_payload_index(
                collection_name=self._collection_name,
                field_name=field_name,
                field_schema=schema,
            )

    def upsert_products(self, embedded_products: Iterable[EmbeddedProduct]) -> int:
        """Upsert embedded products into Qdrant."""

        points = [
            models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, embedded_product.record.source_id)),
                vector=list(embedded_product.vector),
                payload=self._build_payload(embedded_product),
            )
            for embedded_product in embedded_products
        ]
        if not points:
            return 0

        self._client.upsert(
            collection_name=self._collection_name,
            points=points,
            wait=True,
        )
        return len(points)

    def count(self) -> int:
        """Return the number of indexed points."""

        return self._client.count(
            collection_name=self._collection_name,
            exact=True,
        ).count

    def _build_payload(self, embedded_product: EmbeddedProduct) -> dict[str, Any]:
        record = embedded_product.record
        return {
            "source_id": record.source_id,
            "sku": record.sku,
            "name": record.name,
            "brand": record.brand,
            "internal_category": record.internal_category,
            "source_category_id": record.source_category_id,
            "price_usd": record.price_usd,
            "availability": record.availability,
            "url": record.url,
            "image_url": record.image_url,
            "description": record.description,
            "specs": record.specs,
            "last_synced_at": record.last_synced_at.isoformat(),
            "document_text": embedded_product.document_text,
        }
