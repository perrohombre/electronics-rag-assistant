from mediaexpert_laptops.rag.index import build_qdrant_filter
from mediaexpert_laptops.rag.models import ParsedLaptopQuery


def test_build_qdrant_filter_contains_hard_constraints() -> None:
    qdrant_filter = build_qdrant_filter(
        ParsedLaptopQuery(
            max_price_pln=4000,
            brand="APPLE",
            min_ram_gb=16,
            requires_dedicated_gpu=True,
        )
    )

    assert qdrant_filter is not None
    assert len(qdrant_filter.must) == 4


def test_build_qdrant_filter_returns_none_without_constraints() -> None:
    assert build_qdrant_filter(ParsedLaptopQuery()) is None

