"""Application-specific API errors."""

from fastapi import HTTPException, status


class DocumentNotFoundError(HTTPException):
    """Raised when a requested document does not exist."""

    def __init__(self, document_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' was not found.",
        )
