from pathlib import Path

from mediaexpert_laptops.rag.models import ParsedLaptopQuery, SearchRequest
from mediaexpert_laptops.rag.repository import LaptopRepository
from mediaexpert_laptops.rag.search import SearchService


class FakeEmbedder:
    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeIndex:
    def __init__(self, source_ids: list[str]) -> None:
        self.source_ids = source_ids
        self.parsed_query = None

    def search(self, *, query_vector, parsed_query, limit: int):
        self.parsed_query = parsed_query
        return [
            (source_id, 0.9 - index * 0.01)
            for index, source_id in enumerate(self.source_ids[:limit])
        ]


class FakeQueryAnalysis:
    def __init__(self, parsed: ParsedLaptopQuery) -> None:
        self.parsed = parsed

    def analyze(self, query: str) -> ParsedLaptopQuery:
        return self.parsed


def test_search_service_returns_results_and_passes_hard_filters(tmp_path) -> None:
    repository = LaptopRepository(tmp_path / "catalog.db")
    repository.import_csv(Path("data/raw/mediaexpert_laptops.csv"))
    source_ids = [laptop.source_id for laptop in repository.list_laptops()[:3]]
    index = FakeIndex(source_ids)
    parsed = ParsedLaptopQuery(max_price_pln=4000, min_ram_gb=16)
    service = SearchService(
        repository=repository,
        index=index,
        embedder=FakeEmbedder(),
        query_analysis=FakeQueryAnalysis(parsed),
    )

    response = service.search(SearchRequest(query="laptop do 4000 zł do programowania", limit=3))

    assert response.parsed_query == parsed
    assert index.parsed_query == parsed
    assert len(response.results) == 3
    assert response.results[0].laptop.semantic_description
