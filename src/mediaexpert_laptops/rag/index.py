"""Qdrant laptop index."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http import models

from mediaexpert_laptops.rag.embedding import Embedder
from mediaexpert_laptops.rag.models import IndexReport, LaptopRecord, ParsedLaptopQuery


class LaptopIndex:
    """Qdrant-backed vector index for laptop descriptions."""

    def __init__(
        self,
        *,
        client: QdrantClient,
        collection_name: str,
        vector_size: int,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._vector_size = vector_size

    def ensure_collection(self) -> None:
        """Create collection if needed."""

        if self._client.collection_exists(self._collection_name):
            return
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=models.VectorParams(
                size=self._vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def index_laptops(
        self,
        *,
        laptops: list[LaptopRecord],
        embedder: Embedder,
        embedding_model: str,
    ) -> IndexReport:
        """Embed and upsert laptops into Qdrant."""

        self.ensure_collection()
        vectors = embedder.embed_documents([laptop.embedding_text() for laptop in laptops])
        points = [
            models.PointStruct(
                id=index + 1,
                vector=vector,
                payload=_payload(laptop),
            )
            for index, (laptop, vector) in enumerate(zip(laptops, vectors, strict=True))
        ]
        if points:
            self._client.upsert(collection_name=self._collection_name, points=points)
        return IndexReport(
            indexed=len(points),
            collection_name=self._collection_name,
            embedding_model=embedding_model,
        )

    def search(
        self,
        *,
        query_vector: list[float],
        parsed_query: ParsedLaptopQuery,
        limit: int,
    ) -> list[tuple[str, float]]:
        """Search Qdrant with metadata filters."""

        results = self._client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            query_filter=build_qdrant_filter(parsed_query),
            limit=limit,
            with_payload=True,
        )
        return [
            (str(point.payload["source_id"]), float(point.score))
            for point in results.points
            if point.payload and point.payload.get("source_id")
        ]


def build_qdrant_filter(parsed_query: ParsedLaptopQuery) -> models.Filter | None:
    """Build Qdrant metadata filter from explicit query constraints."""

    must: list[models.Condition] = []

    if parsed_query.max_price_pln is not None or parsed_query.min_price_pln is not None:
        must.append(
            models.FieldCondition(
                key="cena_pln",
                range=models.Range(
                    gte=parsed_query.min_price_pln,
                    lte=parsed_query.max_price_pln,
                ),
            )
        )
    if parsed_query.brand:
        must.append(
            models.FieldCondition(
                key="marka",
                match=models.MatchValue(value=parsed_query.brand),
            )
        )
    if parsed_query.operating_system:
        must.append(
            models.FieldCondition(
                key="system_operacyjny",
                match=models.MatchText(text=parsed_query.operating_system),
            )
        )
    if parsed_query.min_ram_gb is not None:
        must.append(
            models.FieldCondition(
                key="ram_gb",
                range=models.Range(gte=parsed_query.min_ram_gb),
            )
        )
    if parsed_query.min_ssd_gb is not None:
        must.append(
            models.FieldCondition(
                key="ssd_gb",
                range=models.Range(gte=parsed_query.min_ssd_gb),
            )
        )
    if parsed_query.requires_dedicated_gpu is True:
        must.append(
            models.FieldCondition(key="has_dedicated_gpu", match=models.MatchValue(value=True))
        )
    if parsed_query.screen_size_min is not None or parsed_query.screen_size_max is not None:
        must.append(
            models.FieldCondition(
                key="screen_inches",
                range=models.Range(
                    gte=parsed_query.screen_size_min,
                    lte=parsed_query.screen_size_max,
                ),
            )
        )

    return models.Filter(must=must) if must else None


def _payload(laptop: LaptopRecord) -> dict:
    return {
        "source_id": laptop.source_id,
        "nazwa": laptop.name,
        "marka": laptop.brand,
        "cena_pln": laptop.price_pln,
        "ram_gb": laptop.ram_gb,
        "ssd_gb": laptop.ssd_gb,
        "gpu": laptop.gpu,
        "screen_inches": laptop.screen_inches,
        "refresh_hz": laptop.refresh_hz,
        "system_operacyjny": laptop.operating_system,
        "url": laptop.url,
        "opis_semantyczny": laptop.semantic_description,
        "has_dedicated_gpu": laptop.has_dedicated_gpu,
    }
