from datetime import UTC, datetime

from mediaexpert_laptops.scraper import (
    CSV_FIELDS,
    build_page_url,
    discover_last_page,
    parse_laptop_offers,
    parse_price_pln,
)

SAMPLE_HTML = """
<html>
  <body>
    <a href="/komputery-i-tablety/laptopy-i-ultrabooki/laptopy/laptop-hp-15">
      Laptop HP 15-FC0001NW 15.6" IPS R7 16GB RAM 512GB SSD Windows 11 Home
    </a>
    <p>Kod: 2127389</p>
    <p>Procesor: AMD Ryzen 7 7730U</p>
    <p>RAM: 16GB, DDR4, 3200MHz</p>
    <p>Dysk SSD: 512GB PCIe NVMe</p>
    <p>Karta graficzna: AMD Radeon Graphics</p>
    <p>Ekran: 15.6", 1920 x 1080px, Matryca IPS</p>
    <p>System operacyjny: Windows 11 Home</p>
    <p>2 599 97 zl</p>
    <button>Do koszyka</button>

    <a href="/komputery-i-tablety/laptopy-i-ultrabooki/laptopy/laptop-apple-air">
      Laptop APPLE MacBook Air 15.3" Retina M5 16GB RAM 512GB SSD macOS
    </a>
    <p>Procesor: Apple M5</p>
    <p>RAM: 16GB</p>
    <p>Dysk SSD: 512GB</p>
    <p>Karta graficzna: Apple M5 (10 rdzeni)</p>
    <p>Ekran: 15.3", 2880 x 1864px, Retina</p>
    <p>System operacyjny: macOS</p>
    <p>Taniej o 200,00 zl</p>
    <p>5 799 00 zl</p>
    <button>Do koszyka</button>
  </body>
</html>
"""


def test_parse_price_pln_supports_mediaexpert_formats() -> None:
    assert parse_price_pln("2 999 99 zl") == 2999.99
    assert parse_price_pln("3 699,00 zl") == 3699.0
    assert parse_price_pln("Taniej o 700,00 zl") is None


def test_parse_laptop_offers_extracts_listing_fields() -> None:
    offers = parse_laptop_offers(
        SAMPLE_HTML,
        page_url="https://www.mediaexpert.pl/komputery-i-tablety/laptopy-i-ultrabooki/laptopy",
        scraped_at=datetime(2026, 4, 27, 12, 0, tzinfo=UTC),
    )

    assert len(offers) == 2
    assert offers[0].source_id == "mediaexpert:2127389"
    assert offers[0].brand == "HP"
    assert offers[0].processor == "AMD Ryzen 7 7730U"
    assert offers[0].price_pln == 2599.97
    assert offers[0].availability == "dostepny"
    assert offers[0].url.endswith("/laptop-hp-15")
    assert offers[1].brand == "APPLE"
    assert offers[1].price_pln == 5799.0
    assert offers[1].description.startswith("Laptop APPLE")
    assert "Procesor: Apple M5" in offers[1].description


def test_csv_row_uses_polish_dataset_columns() -> None:
    offer = parse_laptop_offers(
        SAMPLE_HTML,
        page_url="https://www.mediaexpert.pl/komputery-i-tablety/laptopy-i-ultrabooki/laptopy",
        scraped_at=datetime(2026, 4, 27, 12, 0, tzinfo=UTC),
    )[0]

    row = offer.to_csv_row()

    assert list(row) == CSV_FIELDS
    assert row["identyfikator_zrodla"] == "mediaexpert:2127389"
    assert row["nazwa"].startswith("Laptop HP")
    assert row["marka"] == "HP"
    assert row["cena_pln"] == "2599.97"
    assert row["dostepnosc"] == "dostepny"
    assert row["zrodlo"] == "Media Expert"


def test_discover_last_page_reads_pagination_links() -> None:
    html = '<a href="?page=2">2</a><a href="?page=55">55</a>'

    assert discover_last_page(html) == 55


def test_build_page_url_replaces_existing_page_query() -> None:
    assert build_page_url("https://example.test/laptopy?sort=price&page=2", 3) == (
        "https://example.test/laptopy?sort=price&page=3"
    )
