"""Document API routes."""

from fastapi import APIRouter, HTTPException, Query

from homesure.store import get_document, load_documents

router = APIRouter(prefix="/v1/documents", tags=["documents"])


@router.get("")
def list_documents(
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict]:
    """Return a limited list of documents."""
    return load_documents()[:limit]


@router.get("/{document_id}")
def read_document(document_id: str) -> dict:
    """Return one document by ID."""
    document = get_document(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' was not found.",
        )

    return document
