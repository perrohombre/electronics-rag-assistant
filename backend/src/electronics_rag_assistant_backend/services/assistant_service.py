"""Application-facing assistant service orchestrating retrieval and grounded answers."""

from __future__ import annotations

from electronics_rag_assistant_backend.services.catalog_search import CatalogSearchService
from electronics_rag_assistant_backend.services.grounded_answer import GroundedAnswerService
from electronics_rag_assistant_backend.storage.sqlite_catalog_repository import (
    SQLiteCatalogRepository,
)
from electronics_rag_assistant_shared.catalog import ProductRecord
from electronics_rag_assistant_shared.search import (
    CompareRequest,
    CompareResponse,
    ProductSummary,
    SearchRequest,
    SearchResponse,
)


class AssistantService:
    """Compose retrieval, product lookup, and grounded answer generation."""

    def __init__(
        self,
        *,
        catalog_search_service: CatalogSearchService,
        answer_service: GroundedAnswerService,
        repository: SQLiteCatalogRepository,
    ) -> None:
        self._catalog_search_service = catalog_search_service
        self._answer_service = answer_service
        self._repository = repository

    def search(self, request: SearchRequest) -> SearchResponse:
        """Return retrieved products together with a grounded recommendation answer."""

        search_response = self._catalog_search_service.search(request)
        assistant_answer = self._answer_service.generate_search_answer(
            query=request.query,
            parsed_query=search_response.parsed_query,
            hits=search_response.hits,
        )
        return search_response.model_copy(update={"assistant_answer": assistant_answer})

    def compare(self, request: CompareRequest) -> CompareResponse:
        """Compare exactly two stored products and return a grounded answer."""

        if len(set(request.product_ids)) != 2:
            raise ValueError("Porównanie wymaga wskazania dokładnie dwóch różnych produktów.")

        products = self._repository.get_products_by_source_ids(request.product_ids)
        if len(products) != 2:
            missing_ids = [product_id for product_id in request.product_ids if product_id not in {
                product.source_id for product in products
            }]
            raise LookupError(
                "Nie znaleziono wszystkich produktów do porównania: "
                + ", ".join(sorted(missing_ids))
            )

        product_summaries = [self._to_product_summary(product) for product in products]
        assistant_answer = self._answer_service.generate_comparison_answer(
            query=request.query,
            products=product_summaries,
        )
        return CompareResponse(
            query=request.query,
            product_ids=request.product_ids,
            products=product_summaries,
            assistant_answer=assistant_answer,
        )

    def get_product(self, product_id: str) -> ProductSummary:
        """Return one locally stored product as API-ready summary data."""

        product = self._repository.get_product(product_id)
        if product is None:
            raise LookupError(f"Nie znaleziono produktu: {product_id}")
        return self._to_product_summary(product)

    def _to_product_summary(self, product: ProductRecord) -> ProductSummary:
        return ProductSummary(
            source_id=product.source_id,
            sku=product.sku,
            name=product.name,
            brand=product.brand,
            internal_category=product.internal_category,
            source_category_id=product.source_category_id,
            price_usd=product.price_usd,
            availability=product.availability,
            url=product.url,
            image_url=product.image_url,
            description=product.description,
            specs=product.specs,
        )
