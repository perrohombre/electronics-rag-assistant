"""Search orchestration for explicit filters plus semantic retrieval."""

from __future__ import annotations

from mediaexpert_laptops.rag.embedding import Embedder
from mediaexpert_laptops.rag.index import LaptopIndex
from mediaexpert_laptops.rag.models import (
    RetrievalTrace,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from mediaexpert_laptops.rag.query_analysis import QueryAnalysisService
from mediaexpert_laptops.rag.repository import LaptopRepository


class SearchService:
    """Analyze query, filter Qdrant payloads, and return semantic matches."""

    def __init__(
        self,
        *,
        repository: LaptopRepository,
        index: LaptopIndex,
        embedder: Embedder,
        query_analysis: QueryAnalysisService,
    ) -> None:
        self._repository = repository
        self._index = index
        self._embedder = embedder
        self._query_analysis = query_analysis

    def search(self, request: SearchRequest) -> SearchResponse:
        """Search laptops."""

        parsed = self._query_analysis.analyze(request.query)
        candidates_before = self._repository.count_laptops()
        candidates_after = self._repository.count_matching_filters(parsed)
        query_vector = self._embedder.embed_query(request.query)
        matches = self._index.search(
            query_vector=query_vector,
            parsed_query=parsed,
            limit=request.limit,
        )
        laptops = self._repository.get_by_source_ids([hit.source_id for hit in matches])
        by_id = {laptop.source_id: laptop for laptop in laptops}
        results = [
            SearchResult(score=hit.score, laptop=by_id[hit.source_id])
            for hit in matches
            if hit.source_id in by_id
        ]
        return SearchResponse(
            query=request.query,
            parsed_query=parsed,
            total_candidates=len(results),
            results=results,
            trace=RetrievalTrace(
                parsed_filters=parsed,
                candidates_before_filtering=candidates_before,
                candidates_after_filtering=candidates_after,
                qdrant_hits=matches,
            ),
        )
