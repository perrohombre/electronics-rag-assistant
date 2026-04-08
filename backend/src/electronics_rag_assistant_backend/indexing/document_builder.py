"""Build text documents used for product embeddings."""

from __future__ import annotations

from dataclasses import dataclass

from electronics_rag_assistant_shared.catalog import ProductRecord


@dataclass(slots=True)
class ProductDocument:
    """Canonical product paired with the text sent to the embedding model."""

    record: ProductRecord
    text: str


def build_product_document(record: ProductRecord) -> ProductDocument:
    """Create a deterministic embedding document from a product record."""

    lines = [
        f"Product name: {record.name}",
        f"Category: {record.internal_category}",
    ]
    if record.brand:
        lines.append(f"Brand: {record.brand}")
    if record.price_usd is not None:
        lines.append(f"Price USD: {record.price_usd:.2f}")
    lines.append(f"Availability: {record.availability}")
    lines.append(f"Description: {record.description}")

    if record.specs:
        lines.append("Specifications:")
        for key, value in sorted(record.specs.items()):
            lines.append(f"- {key}: {value}")

    return ProductDocument(record=record, text="\n".join(lines))
