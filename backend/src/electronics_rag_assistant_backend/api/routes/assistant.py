"""Assistant routes for semantic product retrieval."""

from fastapi import APIRouter, Depends, HTTPException, status

from electronics_rag_assistant_backend.dependencies import get_catalog_search_service
from electronics_rag_assistant_backend.services.catalog_search import CatalogSearchService
from electronics_rag_assistant_shared.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


@router.post("/search", response_model=SearchResponse)
def search_products(
    request: SearchRequest,
    service: CatalogSearchService = Depends(get_catalog_search_service),
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
