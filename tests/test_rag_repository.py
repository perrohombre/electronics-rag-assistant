from pathlib import Path

from mediaexpert_laptops.rag.models import ParsedLaptopQuery
from mediaexpert_laptops.rag.repository import LaptopRepository


def test_import_csv_loads_current_dataset(tmp_path) -> None:
    repository = LaptopRepository(tmp_path / "catalog.db")

    report = repository.import_csv(Path("data/raw/mediaexpert_laptops.csv"))
    laptops = repository.list_laptops()

    assert report.imported == 150
    assert len(laptops) == 150
    assert laptops[0].semantic_description
    assert laptops[0].price_pln > 0
    assert laptops[0].ram_gb is not None


def test_repository_counts_laptops_matching_hard_filters(tmp_path) -> None:
    repository = LaptopRepository(tmp_path / "catalog.db")
    repository.import_csv(Path("data/raw/mediaexpert_laptops.csv"))

    all_laptops = repository.count_laptops()
    filtered = repository.count_matching_filters(
        ParsedLaptopQuery(max_price_pln=4000, min_ram_gb=16)
    )

    assert all_laptops == 150
    assert 0 < filtered < all_laptops
