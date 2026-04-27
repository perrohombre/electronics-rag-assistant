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
from urllib.error import HTTPError, URLError
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
FetcherName = Literal["playwright", "urllib"]

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


class ScraperFetchError(RuntimeError):
    """Raised when listing HTML cannot be fetched."""


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
    """Fetch a listing page with urllib."""

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        if exc.code == 403:
            raise ScraperFetchError(
                "Media Expert zwrocil HTTP 403. Strona blokuje automatyczne pobranie HTML. "
                "Zapisz HTML listingu z przegladarki i uruchom scraper z --input-html."
            ) from exc
        raise ScraperFetchError(
            f"Nie udalo sie pobrac strony {url}. HTTP {exc.code}: {exc.reason}"
        ) from exc
    except URLError as exc:
        raise ScraperFetchError(f"Nie udalo sie pobrac strony {url}: {exc.reason}") from exc


def fetch_html_with_playwright(
    url: str,
    *,
    timeout_seconds: float,
    headless: bool,
    scroll_steps: int,
) -> str:
    """Fetch a rendered listing page with Playwright Chromium."""

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ScraperFetchError(
            "Brakuje pakietu playwright. Uruchom: python -m pip install -e \".[dev]\""
        ) from exc

    timeout_ms = int(timeout_seconds * 1000)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="pl-PL",
                timezone_id="Europe/Warsaw",
                viewport={"width": 1440, "height": 1200},
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            _accept_cookie_banner(page)
            _wait_for_listing_render(page, timeout_ms=timeout_ms)
            _scroll_listing(page, scroll_steps=scroll_steps)
            html = page.content()
            browser.close()
            return html
    except PlaywrightTimeoutError as exc:
        raise ScraperFetchError(
            f"Playwright przekroczyl limit czasu podczas pobierania {url}. "
            "Sprobuj trybu --headed albo zwieksz --timeout."
        ) from exc
    except PlaywrightError as exc:
        raise ScraperFetchError(
            f"Playwright nie mogl pobrac strony {url}: {exc}. "
            "Jesli Chromium nie jest zainstalowany, uruchom: python -m playwright install chromium"
        ) from exc


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
    fetcher: FetcherName = "playwright",
    headless: bool = True,
    scroll_steps: int = 4,
) -> list[LaptopOffer]:
    """Fetch listing pages and return parsed laptop offers."""

    fetch_page = _build_fetcher(
        fetcher=fetcher,
        timeout_seconds=timeout_seconds,
        headless=headless,
        scroll_steps=scroll_steps,
    )
    first_html = fetch_page(listing_url)
    page_count = discover_last_page(first_html) if pages == "all" else pages
    page_count = max(1, int(page_count))

    collected = parse_laptop_offers(first_html, page_url=listing_url)
    for page_number in range(2, page_count + 1):
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        page_url = build_page_url(listing_url, page_number)
        html = fetch_page(page_url)
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
    parser.add_argument(
        "--fetcher",
        choices=["playwright", "urllib"],
        default="playwright",
        help="HTML fetcher used for live scraping.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the Chromium window while Playwright fetches listing pages.",
    )
    parser.add_argument(
        "--scroll-steps",
        type=int,
        default=4,
        help="Number of scroll steps Playwright performs before reading HTML.",
    )
    args = parser.parse_args()

    pages: int | Literal["all"]
    if args.pages == "all":
        pages = "all"
    else:
        pages = int(args.pages)

    try:
        if args.input_html:
            html = args.input_html.read_text(encoding="utf-8")
            products = parse_laptop_offers(html, page_url=args.base_url)
        else:
            products = scrape_laptops(
                listing_url=args.base_url,
                pages=pages,
                delay_seconds=args.delay,
                timeout_seconds=args.timeout,
                fetcher=args.fetcher,
                headless=not args.headed,
                scroll_steps=args.scroll_steps,
            )
    except ScraperFetchError as exc:
        parser.exit(2, f"Error: {exc}\n")

    write_products_csv(products, args.output)
    print(f"Saved {len(products)} laptop offers to {args.output}")
    if len(products) < 20:
        print(
            "Warning: parsed fewer than 20 offers. "
            "Check whether the input HTML contains the full product listing."
        )


@dataclass(frozen=True)
class ProductLink:
    """Product anchor found on a listing page."""

    tag: Tag
    name: str
    url: str


def _build_fetcher(
    *,
    fetcher: FetcherName,
    timeout_seconds: float,
    headless: bool,
    scroll_steps: int,
):
    if fetcher == "urllib":
        return lambda url: fetch_html(url, timeout_seconds=timeout_seconds)
    return lambda url: fetch_html_with_playwright(
        url,
        timeout_seconds=timeout_seconds,
        headless=headless,
        scroll_steps=scroll_steps,
    )


def _accept_cookie_banner(page) -> None:
    for label in ("Akceptuje", "Akceptuję", "Zgadzam", "OK"):
        try:
            page.get_by_text(label, exact=False).first.click(timeout=1500)
            return
        except Exception:
            continue


def _wait_for_listing_render(page, *, timeout_ms: int) -> None:
    selectors = [
        'a[href*="/komputery-i-tablety/laptopy-i-ultrabooki/laptopy"]',
        "text=Laptop",
    ]
    for selector in selectors:
        try:
            page.wait_for_selector(selector, timeout=timeout_ms)
            return
        except Exception:
            continue


def _scroll_listing(page, *, scroll_steps: int) -> None:
    for _ in range(max(0, scroll_steps)):
        page.mouse.wheel(0, 1600)
        page.wait_for_timeout(500)


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
        if not _looks_like_product_url(url):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        links.append(ProductLink(tag=anchor, name=name, url=url))

    return links


def _looks_like_product_url(url: str) -> bool:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return slug.startswith(("laptop-", "notebook-"))


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
    for index, text in enumerate(block_texts):
        for source_label, target_key in SPEC_LABELS.items():
            prefix = f"{source_label}:"
            if text.startswith(prefix):
                value = text.removeprefix(prefix).strip()
                if not value and index + 1 < len(block_texts):
                    value = block_texts[index + 1]
                if value:
                    specs[target_key] = value
    return specs


def _extract_sku(block_texts: list[str]) -> str | None:
    for text in block_texts:
        match = re.fullmatch(r"Kod:\s*(\d+)", text)
        if match:
            return match.group(1)
    return None


def _extract_price_pln(block_texts: list[str]) -> float | None:
    for marker in ("Cena z kodem:", "Cena:", "Cena aktualna:"):
        price = _extract_split_price_after_marker(block_texts, marker)
        if price is not None:
            return price

    split_price = _extract_first_split_price(block_texts)
    if split_price is not None:
        return split_price

    for text in block_texts:
        value = parse_price_pln(text)
        if value is not None:
            return value
    return None


def _extract_split_price_after_marker(block_texts: list[str], marker: str) -> float | None:
    for index, text in enumerate(block_texts):
        if text == marker:
            return _extract_first_split_price(block_texts[index + 1 : index + 6])
    return None


def _extract_first_split_price(block_texts: list[str]) -> float | None:
    for index, text in enumerate(block_texts):
        if _clean_text(text).replace("zł", "zl") != "zl" or index < 2:
            continue
        integer_part = block_texts[index - 2]
        cents = block_texts[index - 1]
        if not re.fullmatch(r"\d{1,3}(?: \d{3})*", integer_part):
            continue
        if not re.fullmatch(r"\d{2}", cents):
            continue
        return float(f"{integer_part.replace(' ', '')}.{cents}")
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
