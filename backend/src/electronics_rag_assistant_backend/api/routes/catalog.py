"""Catalog sync and status routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from electronics_rag_assistant_backend.dependencies import (
    get_catalog_index_service,
    get_catalog_sync_service,
)
from electronics_rag_assistant_backend.services.catalog_index import CatalogIndexService
from electronics_rag_assistant_backend.services.catalog_sync import CatalogSyncService
from electronics_rag_assistant_backend.source.bestbuy_client import (
    BestBuyAPIError,
    BestBuyAuthenticationError,
)
from electronics_rag_assistant_shared.catalog import (
    CatalogIndexReport,
    CatalogStatus,
    CatalogSyncReport,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.post("/sync", response_model=CatalogSyncReport)
def sync_catalog(
    service: CatalogSyncService = Depends(get_catalog_sync_service),
) -> CatalogSyncReport:
    """Trigger a full catalog sync from Best Buy into local storage."""

    try:
        return service.sync_catalog()
    except BestBuyAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except BestBuyAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/index", response_model=CatalogIndexReport)
def index_catalog(
    service: CatalogIndexService = Depends(get_catalog_index_service),
) -> CatalogIndexReport:
    """Build embeddings for locally stored products and upsert them into Qdrant."""

    try:
        return service.index_catalog()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get("/status", response_model=CatalogStatus)
def get_catalog_status(
    service: CatalogSyncService = Depends(get_catalog_sync_service),
) -> CatalogStatus:
    """Return the current local catalog status."""

    return service.get_catalog_status()
