"""Document API routes."""

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/v1/documents", tags=["documents"])


@router.get("")
def list_documents(
    request: Request,
    q: str | None = None,
    limit: int = Query(default=10, ge=1, le=100),
) -> dict:
    """Return a limited list of documents."""
    documents = request.app.state.documents or []
    if q:
        query = q.casefold()
        documents = [
            document for document in documents if query in str(document.get("title", "")).casefold()
        ]
    return {"total": len(documents), "items": documents[:limit]}


@router.get("/{document_id}")
def read_document(document_id: str, request: Request) -> dict:
    """Return one document by ID."""
    document = next(
        (
            item
            for item in (request.app.state.documents or [])
            if str(item.get("id")) == document_id
        ),
        None,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' was not found.",
        )

    return document
