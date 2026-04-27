"""Normalization helpers for laptop CSV values."""

from __future__ import annotations

import re
from typing import Any

from mediaexpert_laptops.rag.models import LaptopRecord


def normalize_laptop_row(row: dict[str, str]) -> LaptopRecord:
    """Convert one Polish CSV row into a canonical laptop record."""

    ram = row["ram"].strip()
    ssd = row["dysk_ssd"].strip()
    screen = row["ekran"].strip()
    gpu = row["karta_graficzna"].strip()

    return LaptopRecord(
        source_id=row["identyfikator_zrodla"].strip(),
        sku=row["sku"].strip(),
        name=row["nazwa"].strip(),
        brand=row["marka"].strip().upper(),
        price_pln=float(row["cena_pln"]),
        availability=row["dostepnosc"].strip(),
        url=row["url"].strip(),
        processor=row["procesor"].strip(),
        ram=ram,
        ssd=ssd,
        hdd=row["dysk_hdd"].strip(),
        gpu=gpu,
        screen=screen,
        operating_system=row["system_operacyjny"].strip(),
        description=row["opis"].strip(),
        semantic_description=row["opis_semantyczny"].strip(),
        scraped_at=row["data_pobrania"].strip(),
        source=row["zrodlo"].strip(),
        ram_gb=parse_capacity_gb(ram),
        ssd_gb=parse_capacity_gb(ssd),
        screen_inches=parse_screen_inches(screen),
        refresh_hz=parse_refresh_hz(screen),
        has_dedicated_gpu=has_dedicated_gpu(gpu),
    )


def parse_capacity_gb(value: str) -> int | None:
    """Parse first GB/TB capacity from text."""

    match = re.search(r"(\d+)\s*TB", value, flags=re.IGNORECASE)
    if match:
        return int(match.group(1)) * 1000
    match = re.search(r"(\d+)\s*GB", value, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def parse_screen_inches(value: str) -> float | None:
    """Parse screen size from text."""

    match = re.search(r"(\d+(?:\.\d+)?)\"", value)
    if match:
        return float(match.group(1))
    return None


def parse_refresh_hz(value: str) -> int | None:
    """Parse refresh rate from text."""

    match = re.search(r"(\d+)\s*Hz", value, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def has_dedicated_gpu(value: str) -> bool:
    """Return whether GPU text clearly describes a dedicated GPU."""

    normalized = value.casefold()
    dedicated_tokens = ("geforce", "rtx", "gtx", "radeon rx")
    integrated_only = ("intel uhd", "intel graphics", "intel iris", "amd radeon graphics")
    if any(token in normalized for token in dedicated_tokens):
        return True
    return not any(token in normalized for token in integrated_only) and "nvidia" in normalized


def normalize_optional_number(value: Any) -> float | None:
    """Normalize optional numeric values returned by external services."""

    if value is None or value == "":
        return None
    return float(value)

