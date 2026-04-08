"""Normalization from Best Buy product payloads into canonical catalog records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from electronics_rag_assistant_shared.catalog import ProductRecord, ResolvedSourceCategory


def normalize_bestbuy_product(
    raw_product: dict[str, Any],
    category: ResolvedSourceCategory,
    *,
    synced_at: datetime | None = None,
) -> ProductRecord:
    """Map a Best Buy product payload into the canonical catalog model."""

    sku = str(raw_product["sku"])
    timestamp = synced_at or datetime.now(UTC)

    return ProductRecord(
        source_id=f"bestbuy:{sku}",
        sku=sku,
        name=str(raw_product["name"]).strip(),
        brand=_optional_string(raw_product.get("manufacturer")),
        internal_category=category.internal_category,
        source_category_id=category.source_category_id,
        price_usd=_extract_price(raw_product),
        availability=_derive_availability(raw_product),
        url=_optional_string(raw_product.get("url")),
        image_url=_optional_string(raw_product.get("image")),
        description=_extract_description(raw_product),
        specs=_extract_specs(raw_product),
        last_synced_at=timestamp,
    )


def _extract_price(raw_product: dict[str, Any]) -> float | None:
    for field_name in ("salePrice", "regularPrice"):
        value = raw_product.get(field_name)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _derive_availability(raw_product: dict[str, Any]) -> str:
    if raw_product.get("onlineAvailability") is True or raw_product.get("orderable") is True:
        return "available"
    if raw_product.get("onlineAvailability") is False or raw_product.get("orderable") is False:
        return "unavailable"
    return "unknown"


def _extract_description(raw_product: dict[str, Any]) -> str:
    for field_name in ("longDescription", "shortDescription", "name"):
        value = _optional_string(raw_product.get(field_name))
        if value:
            return value
    return "No description available."


def _extract_specs(raw_product: dict[str, Any]) -> dict[str, str]:
    specs: dict[str, str] = {}

    model_number = _optional_string(raw_product.get("modelNumber"))
    if model_number:
        specs["model_number"] = model_number

    details = raw_product.get("details", [])
    if isinstance(details, list):
        for detail in details:
            if not isinstance(detail, dict):
                continue
            key = _optional_string(detail.get("name"))
            value = _optional_string(detail.get("value"))
            if key and value:
                specs[key] = value

    return specs


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
