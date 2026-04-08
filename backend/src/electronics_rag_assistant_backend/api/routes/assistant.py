"""Assistant routes for semantic product retrieval."""

from fastapi import APIRouter, Depends, HTTPException, status

from electronics_rag_assistant_backend.dependencies import get_assistant_service
from electronics_rag_assistant_backend.services.assistant_service import AssistantService
from electronics_rag_assistant_shared.search import (
    CompareRequest,
    CompareResponse,
    SearchRequest,
    SearchResponse,
)

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


@router.post("/search", response_model=SearchResponse)
def search_products(
    request: SearchRequest,
    service: AssistantService = Depends(get_assistant_service),
) -> SearchResponse:
    """Search indexed products using a natural language query."""

    try:
        return service.search(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/compare", response_model=CompareResponse)
def compare_products(
    request: CompareRequest,
    service: AssistantService = Depends(get_assistant_service),
) -> CompareResponse:
    """Compare exactly two selected products using grounded catalog data."""

    try:
        return service.compare(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
