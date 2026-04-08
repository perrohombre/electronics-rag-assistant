"""Catalog indexing orchestration between local storage, embeddings, and Qdrant."""

from __future__ import annotations

from datetime import UTC, datetime

from electronics_rag_assistant_backend.indexing.document_builder import build_product_document
from electronics_rag_assistant_backend.indexing.openai_embedder import Embedder
from electronics_rag_assistant_backend.indexing.qdrant_product_index import (
    EmbeddedProduct,
    QdrantProductIndex,
)
from electronics_rag_assistant_backend.storage.sqlite_catalog_repository import (
    SQLiteCatalogRepository,
)
from electronics_rag_assistant_shared.catalog import CatalogIndexReport


class CatalogIndexService:
    """Index locally stored products into Qdrant."""

    def __init__(
        self,
        *,
        repository: SQLiteCatalogRepository,
        product_index: QdrantProductIndex,
        embedder: Embedder,
        embedding_model: str,
    ) -> None:
        self._repository = repository
        self._product_index = product_index
        self._embedder = embedder
        self._embedding_model = embedding_model

    def index_catalog(self) -> CatalogIndexReport:
        """Read products from SQLite, embed them, and upsert them into Qdrant."""

        indexed_at = datetime.now(UTC)
        products = self._repository.list_products()
        documents = [build_product_document(product) for product in products]

        self._product_index.ensure_collection()

        if not documents:
            return CatalogIndexReport(
                collection_name=self._product_index.collection_name,
                embedding_model=self._embedding_model,
                indexed_products=0,
                indexed_at=indexed_at,
            )

        vectors = self._embedder.embed_texts([document.text for document in documents])
        if len(vectors) != len(documents):
            raise ValueError(
                "Embedding provider returned a different number of vectors than input documents"
            )

        indexed_products = self._product_index.upsert_products(
            [
                EmbeddedProduct(
                    record=document.record,
                    vector=vector,
                    document_text=document.text,
                )
                for document, vector in zip(documents, vectors, strict=True)
            ]
        )

        return CatalogIndexReport(
            collection_name=self._product_index.collection_name,
            embedding_model=self._embedding_model,
            indexed_products=indexed_products,
            indexed_at=indexed_at,
        )
