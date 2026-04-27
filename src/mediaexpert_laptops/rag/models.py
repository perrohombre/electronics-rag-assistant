"""Data contracts for the laptop RAG pipeline."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LaptopRecord(BaseModel):
    """Canonical laptop record imported from the local CSV dataset."""

    source_id: str
    sku: str
    name: str
    brand: str
    price_pln: float
    availability: str
    url: str
    processor: str
    ram: str
    ssd: str
    hdd: str
    gpu: str
    screen: str
    operating_system: str
    description: str
    semantic_description: str
    scraped_at: str
    source: str
    ram_gb: int | None = None
    ssd_gb: int | None = None
    screen_inches: float | None = None
    refresh_hz: int | None = None
    has_dedicated_gpu: bool = False

    def embedding_text(self) -> str:
        """Return the text used for semantic search."""

        return f"{self.name}. {self.semantic_description}"


class ParsedLaptopQuery(BaseModel):
    """Structured hard filters extracted from a natural-language query."""

    model_config = ConfigDict(extra="forbid")

    max_price_pln: float | None = None
    min_price_pln: float | None = None
    brand: str | None = None
    operating_system: str | None = None
    min_ram_gb: int | None = None
    min_ssd_gb: int | None = None
    requires_dedicated_gpu: bool | None = None
    screen_size_min: float | None = None
    screen_size_max: float | None = None


class SearchRequest(BaseModel):
    """Search request accepted by API and UI."""

    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    """One retrieved laptop result."""

    score: float
    laptop: LaptopRecord


class SearchResponse(BaseModel):
    """Search response with parsed filters and semantic matches."""

    query: str
    parsed_query: ParsedLaptopQuery
    total_candidates: int
    results: list[SearchResult]


class AnswerResponse(BaseModel):
    """Grounded answer generated from retrieved laptops."""

    query: str
    parsed_query: ParsedLaptopQuery
    answer: str
    results: list[SearchResult]


class ImportReport(BaseModel):
    """CSV import summary."""

    imported: int
    source_csv: str
    database_path: str


class IndexReport(BaseModel):
    """Qdrant indexing summary."""

    indexed: int
    collection_name: str
    embedding_model: str

