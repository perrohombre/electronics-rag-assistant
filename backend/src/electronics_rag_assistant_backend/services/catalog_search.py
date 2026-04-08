"""Semantic search orchestration over indexed catalog products."""

from __future__ import annotations

from qdrant_client import QdrantClient

from electronics_rag_assistant_backend.indexing.openai_embedder import Embedder
from electronics_rag_assistant_backend.query.parser import parse_search_query
from electronics_rag_assistant_backend.retrieval.filter_builder import build_qdrant_filter
from electronics_rag_assistant_shared.search import ProductSearchHit, SearchRequest, SearchResponse


class CatalogSearchService:
    """Parse a search query, build filters, and query Qdrant."""

    def __init__(
        self,
        *,
        qdrant_client: QdrantClient,
        embedder: Embedder,
        collection_name: str,
    ) -> None:
        self._qdrant_client = qdrant_client
        self._embedder = embedder
        self._collection_name = collection_name

    def search(self, request: SearchRequest) -> SearchResponse:
        """Execute semantic retrieval over the indexed product catalog."""

        parsed_query = parse_search_query(request.query)
        query_filter = build_qdrant_filter(parsed_query)

        if not self._qdrant_client.collection_exists(self._collection_name):
            raise RuntimeError(
                "Indeks katalogu nie jest gotowy. "
                "Uruchom /api/v1/catalog/index przed wyszukiwaniem."
            )

        query_vector = self._embedder.embed_texts([parsed_query.semantic_query])[0]
        response = self._qdrant_client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=request.limit,
            with_payload=True,
            with_vectors=False,
        )
        hits = [self._map_hit(point) for point in response.points]

        return SearchResponse(
            query=request.query,
            parsed_query=parsed_query,
            total_hits=len(hits),
            hits=hits,
        )

    def _map_hit(self, point) -> ProductSearchHit:
        payload = point.payload or {}
        return ProductSearchHit(
            source_id=payload["source_id"],
            sku=payload["sku"],
            name=payload["name"],
            brand=payload.get("brand"),
            internal_category=payload["internal_category"],
            source_category_id=payload["source_category_id"],
            price_usd=payload.get("price_usd"),
            availability=payload["availability"],
            url=payload.get("url"),
            image_url=payload.get("image_url"),
            description=payload["description"],
            specs=payload.get("specs", {}),
            score=float(point.score),
        )
