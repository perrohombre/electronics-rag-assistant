"""Product lookup routes for UI-driven product inspection flows."""

from fastapi import APIRouter, Depends, HTTPException, status

from electronics_rag_assistant_backend.dependencies import get_assistant_service
from electronics_rag_assistant_backend.services.assistant_service import AssistantService
from electronics_rag_assistant_shared.search import ProductSummary

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("/{product_id}", response_model=ProductSummary)
def get_product(
    product_id: str,
    service: AssistantService = Depends(get_assistant_service),
) -> ProductSummary:
    """Return one locally stored product for detail and comparison views."""

    try:
        return service.get_product(product_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
