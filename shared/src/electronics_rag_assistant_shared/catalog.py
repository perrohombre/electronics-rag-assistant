"""Shared catalog models used across services and interfaces."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class InternalCategory(StrEnum):
    """Supported product categories for the first project version."""

    LAPTOPS = "laptops"
    MONITORS = "monitors"
    TELEVISIONS = "televisions"
    MICE = "mice"
    KEYBOARDS = "keyboards"
    HEADPHONES = "headphones"


class ResolvedSourceCategory(BaseModel):
    """Resolved Best Buy category for one internal catalog category."""

    model_config = ConfigDict(use_enum_values=True)

    internal_category: InternalCategory
    source_category_id: str
    source_category_name: str
    source_category_path: list[str] = Field(default_factory=list)
    source_category_url: str | None = None


class ProductRecord(BaseModel):
    """Canonical product shape persisted in the local catalog."""

    model_config = ConfigDict(use_enum_values=True)

    source_id: str
    sku: str
    name: str
    brand: str | None = None
    internal_category: InternalCategory
    source_category_id: str
    price_usd: float | None = None
    availability: str
    url: str | None = None
    image_url: str | None = None
    description: str
    specs: dict[str, str] = Field(default_factory=dict)
    last_synced_at: datetime


class CategorySnapshot(BaseModel):
    """Persisted sync summary for one internal catalog category."""

    model_config = ConfigDict(use_enum_values=True)

    internal_category: InternalCategory
    source_category_id: str
    source_category_name: str
    source_category_path: list[str] = Field(default_factory=list)
    source_category_url: str | None = None
    product_count: int
    last_synced_at: datetime


class CatalogStatus(BaseModel):
    """Aggregated state of the local product catalog."""

    total_products: int
    categories: list[CategorySnapshot] = Field(default_factory=list)
    last_synced_at: datetime | None = None


class CategorySyncResult(BaseModel):
    """Result summary for one synced category."""

    model_config = ConfigDict(use_enum_values=True)

    internal_category: InternalCategory
    source_category_id: str
    source_category_name: str
    product_count: int
    last_synced_at: datetime


class CatalogSyncReport(BaseModel):
    """Summary returned after a sync job completes."""

    source: str
    total_products: int
    categories: list[CategorySyncResult] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime
