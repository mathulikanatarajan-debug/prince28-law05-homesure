"""Shared API dependencies."""

from homesure.store import get_document, load_documents


def get_all_documents() -> list[dict]:
    """Return all available documents."""
    return load_documents()


def find_document(document_id: str) -> dict | None:
    """Find a document using its ID."""
    return get_document(document_id)
