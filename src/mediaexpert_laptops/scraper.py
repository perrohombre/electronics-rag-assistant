"""Scrape Media Expert laptop listings into a local CSV snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup, NavigableString, Tag

DEFAULT_LISTING_URL = "https://www.mediaexpert.pl/komputery-i-tablety/laptopy-i-ultrabooki/laptopy"
DEFAULT_OUTPUT_PATH = Path("data/raw/mediaexpert_laptops.csv")
SOURCE_SLUG = "mediaexpert"
SOURCE_NAME = "Media Expert"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

SPEC_LABELS = {
    "Procesor": "processor",
    "RAM": "ram",
    "Dysk SSD": "ssd",
    "Dysk HDD": "hdd",
    "Karta graficzna": "gpu",
    "Ekran": "screen",
    "System operacyjny": "operating_system",
}

CSV_FIELDS = [
    "identyfikator_zrodla",
    "sku",
    "nazwa",
    "marka",
    "cena_pln",
    "dostepnosc",
    "url",
    "procesor",
    "ram",
    "dysk_ssd",
    "dysk_hdd",
    "karta_graficzna",
    "ekran",
    "system_operacyjny",
    "opis",
    "data_pobrania",
    "zrodlo",
]


@dataclass(frozen=True)
class LaptopOffer:
    """Normalized laptop offer captured from a listing page."""

    source_id: str
    sku: str
    name: str
    brand: str
    price_pln: float | None
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
    scraped_at: str
    source: str = SOURCE_NAME

    def to_csv_row(self) -> dict[str, str]:
        """Return a CSV-safe mapping."""

        return {
            "identyfikator_zrodla": self.source_id,
            "sku": self.sku,
            "nazwa": self.name,
            "marka": self.brand,
            "cena_pln": "" if self.price_pln is None else f"{self.price_pln:.2f}",
            "dostepnosc": self.availability,
            "url": self.url,
            "procesor": self.processor,
            "ram": self.ram,
            "dysk_ssd": self.ssd,
            "dysk_hdd": self.hdd,
            "karta_graficzna": self.gpu,
            "ekran": self.screen,
            "system_operacyjny": self.operating_system,
            "opis": self.description,
            "data_pobrania": self.scraped_at,
            "zrodlo": self.source,
        }


def fetch_html(url: str, *, timeout_seconds: float) -> str:
    """Fetch a listing page."""

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_laptop_offers(
    html: str,
    *,
    page_url: str,
    scraped_at: datetime | None = None,
) -> list[LaptopOffer]:
    """Parse laptop offers from one listing page."""

    soup = BeautifulSoup(html, "html.parser")
    listing_links = _find_product_links(soup, page_url)
    timestamp = (scraped_at or datetime.now(UTC)).isoformat()
    offers: list[LaptopOffer] = []

    for index, link in enumerate(listing_links):
        next_link = listing_links[index + 1].tag if index + 1 < len(listing_links) else None
        block_texts = _extract_texts_until_next_product(link.tag, next_link)
        offers.append(
            _build_offer(
                name=link.name,
                url=link.url,
                block_texts=block_texts,
                scraped_at=timestamp,
            )
        )

    return _deduplicate_offers(offers)


def discover_last_page(html: str) -> int:
    """Return the largest listing page number found in the HTML."""

    soup = BeautifulSoup(html, "html.parser")
    candidates: list[int] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        candidates.extend(int(match) for match in re.findall(r"[?&]page=(\d+)", href))
        text = _clean_text(anchor.get_text(" "))
        if text.isdigit():
            candidates.append(int(text))
    return max(candidates, default=1)


def scrape_laptops(
    *,
    listing_url: str = DEFAULT_LISTING_URL,
    pages: int | Literal["all"] = 1,
    delay_seconds: float = 1.0,
    timeout_seconds: float = 20.0,
) -> list[LaptopOffer]:
    """Fetch listing pages and return parsed laptop offers."""

    first_html = fetch_html(listing_url, timeout_seconds=timeout_seconds)
    page_count = discover_last_page(first_html) if pages == "all" else pages
    page_count = max(1, int(page_count))

    collected = parse_laptop_offers(first_html, page_url=listing_url)
    for page_number in range(2, page_count + 1):
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        page_url = build_page_url(listing_url, page_number)
        html = fetch_html(page_url, timeout_seconds=timeout_seconds)
        collected.extend(parse_laptop_offers(html, page_url=page_url))

    return _deduplicate_offers(collected)


def write_products_csv(products: list[LaptopOffer], output_path: Path) -> None:
    """Write offers to CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for product in products:
            writer.writerow(product.to_csv_row())


def build_page_url(listing_url: str, page_number: int) -> str:
    """Build a Media Expert listing URL for the requested page."""

    if page_number <= 1:
        return listing_url

    parsed = urlparse(listing_url)
    query_parts = [
        part
        for part in parsed.query.split("&")
        if part and not part.startswith("page=")
    ]
    query_parts.append(f"page={page_number}")
    return urlunparse(parsed._replace(query="&".join(query_parts)))


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Scrape Media Expert laptop listings to CSV.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--base-url", default=DEFAULT_LISTING_URL)
    parser.add_argument(
        "--input-html",
        type=Path,
        help="Parse a saved Media Expert listing HTML file instead of fetching the page.",
    )
    parser.add_argument("--pages", default="1", help="Number of pages to scrape or 'all'.")
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds.",
    )
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds.")
    args = parser.parse_args()

    pages: int | Literal["all"]
    if args.pages == "all":
        pages = "all"
    else:
        pages = int(args.pages)

    if args.input_html:
        html = args.input_html.read_text(encoding="utf-8")
        products = parse_laptop_offers(html, page_url=args.base_url)
    else:
        products = scrape_laptops(
            listing_url=args.base_url,
            pages=pages,
            delay_seconds=args.delay,
            timeout_seconds=args.timeout,
        )
    write_products_csv(products, args.output)
    print(f"Saved {len(products)} laptop offers to {args.output}")


@dataclass(frozen=True)
class ProductLink:
    """Product anchor found on a listing page."""

    tag: Tag
    name: str
    url: str


def _find_product_links(soup: BeautifulSoup, page_url: str) -> list[ProductLink]:
    links: list[ProductLink] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        name = _clean_product_name(anchor.get_text(" "))
        if not name.startswith("Laptop "):
            continue
        url = urljoin(page_url, str(anchor["href"]))
        if "/komputery-i-tablety/laptopy-i-ultrabooki/laptopy" not in url:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        links.append(ProductLink(tag=anchor, name=name, url=url))

    return links


def _extract_texts_until_next_product(anchor: Tag, next_product_anchor: Tag | None) -> list[str]:
    texts: list[str] = []
    for element in anchor.next_elements:
        if element is next_product_anchor:
            break
        if not isinstance(element, NavigableString):
            continue
        if _is_inside(anchor, element):
            continue
        if _is_inside_ignored_tag(element):
            continue
        clean = _clean_text(str(element))
        if clean:
            texts.append(clean)
    return texts


def _is_inside(parent: Tag, element: NavigableString) -> bool:
    return any(ancestor is parent for ancestor in element.parents)


def _is_inside_ignored_tag(element: NavigableString) -> bool:
    return any(
        isinstance(ancestor, Tag) and ancestor.name in {"script", "style", "noscript"}
        for ancestor in element.parents
    )


def _build_offer(name: str, url: str, block_texts: list[str], scraped_at: str) -> LaptopOffer:
    specs = _extract_specs(block_texts)
    sku = _extract_sku(block_texts) or _stable_fallback_sku(url, name)
    price_pln = _extract_price_pln(block_texts)
    brand = _extract_brand(name)
    description = _build_description(name, specs)

    return LaptopOffer(
        source_id=f"{SOURCE_SLUG}:{sku}",
        sku=sku,
        name=name,
        brand=brand,
        price_pln=price_pln,
        availability=_extract_availability(block_texts),
        url=url,
        processor=specs.get("processor", ""),
        ram=specs.get("ram", ""),
        ssd=specs.get("ssd", ""),
        hdd=specs.get("hdd", ""),
        gpu=specs.get("gpu", ""),
        screen=specs.get("screen", ""),
        operating_system=specs.get("operating_system", ""),
        description=description,
        scraped_at=scraped_at,
    )


def _extract_specs(block_texts: list[str]) -> dict[str, str]:
    specs: dict[str, str] = {}
    for text in block_texts:
        for source_label, target_key in SPEC_LABELS.items():
            prefix = f"{source_label}:"
            if text.startswith(prefix):
                specs[target_key] = text.removeprefix(prefix).strip()
    return specs


def _extract_sku(block_texts: list[str]) -> str | None:
    for text in block_texts:
        match = re.fullmatch(r"Kod:\s*(\d+)", text)
        if match:
            return match.group(1)
    return None


def _extract_price_pln(block_texts: list[str]) -> float | None:
    for text in block_texts:
        value = parse_price_pln(text)
        if value is not None:
            return value
    return None


def parse_price_pln(text: str) -> float | None:
    """Parse Media Expert price text such as '2 999 99 zl'."""

    normalized = _clean_text(text).replace("zł", "zl")
    if not re.fullmatch(r"\d{1,3}(?: \d{3})*(?:,\d{2}| \d{2}) zl", normalized):
        return None

    raw = normalized.removesuffix(" zl").strip()
    if "," in raw:
        return float(raw.replace(" ", "").replace(",", "."))

    parts = raw.split()
    if len(parts) >= 2 and len(parts[-1]) == 2:
        integer_part = "".join(parts[:-1])
        return float(f"{integer_part}.{parts[-1]}")

    return float(raw.replace(" ", ""))


def _extract_availability(block_texts: list[str]) -> str:
    joined = " ".join(block_texts).casefold()
    if "do koszyka" in joined:
        return "dostepny"
    if "powiadom" in joined or "niedostep" in joined or "niedostęp" in joined:
        return "niedostepny"
    return "nieznana"


def _extract_brand(name: str) -> str:
    without_prefix = name.removeprefix("Laptop ").strip()
    return without_prefix.split(maxsplit=1)[0].upper() if without_prefix else ""


def _build_description(name: str, specs: dict[str, str]) -> str:
    labels = {
        "processor": "Procesor",
        "ram": "RAM",
        "ssd": "Dysk SSD",
        "hdd": "Dysk HDD",
        "gpu": "Karta graficzna",
        "screen": "Ekran",
        "operating_system": "System operacyjny",
    }
    parts = [name]
    for key in ("processor", "ram", "ssd", "hdd", "gpu", "screen", "operating_system"):
        value = specs.get(key)
        if value:
            parts.append(f"{labels[key]}: {value}")
    return " | ".join(parts)


def _stable_fallback_sku(url: str, name: str) -> str:
    digest = hashlib.sha1(f"{url}|{name}".encode()).hexdigest()[:12]
    return f"generated-{digest}"


def _deduplicate_offers(offers: list[LaptopOffer]) -> list[LaptopOffer]:
    deduplicated: list[LaptopOffer] = []
    seen: set[str] = set()
    for offer in offers:
        if offer.source_id in seen:
            continue
        seen.add(offer.source_id)
        deduplicated.append(offer)
    return deduplicated


def _clean_product_name(text: str) -> str:
    return _clean_text(text).removesuffix(" Porównaj").strip()


def _clean_text(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


if __name__ == "__main__":
    main()
