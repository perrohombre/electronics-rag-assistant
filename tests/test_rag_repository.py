from pathlib import Path

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

