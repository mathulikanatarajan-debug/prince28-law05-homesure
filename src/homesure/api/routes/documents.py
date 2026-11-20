"""Document API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from homesure.api.deps import get_repo
from homesure.db.repository import DocumentRepository

router = APIRouter(prefix="/v1/documents", tags=["documents"])


@router.get("")
async def list_documents(
    request: Request,
    repo: Annotated[DocumentRepository, Depends(get_repo)],
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """Return documents with search, filters and pagination."""
    filters = {
        key: value
        for key, value in request.query_params.items()
        if key not in {"q", "limit", "offset"}
    }

    for key in filters:
        if not key.replace("_", "").isalnum() or not key[0].isalpha():
            raise HTTPException(status_code=400, detail="Invalid filter name")

    total, items = await repo.list(
        q=q,
        filters=filters,
        limit=limit,
        offset=offset,
    )

    return {"total": total, "items": items, "filters": filters}


@router.get("/{document_id}")
async def read_document(
    document_id: str,
    repo: Annotated[DocumentRepository, Depends(get_repo)],
) -> dict:
    """Return one document by ID."""
    document = await repo.get(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' was not found.",
        )

    return document
