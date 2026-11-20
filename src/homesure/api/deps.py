"""Shared API dependencies."""

from collections.abc import AsyncIterator

from fastapi import HTTPException, Request
from sqlalchemy import text

from homesure.db.repository import DocumentRepository
from homesure.db.session import make_sessionmaker
from homesure.store import get_document, load_documents


async def get_repo(request: Request) -> AsyncIterator[DocumentRepository]:
    """Provide a database repository for one request."""
    session_factory = make_sessionmaker(request.app.state.engine)

    async with session_factory() as session:
        yield DocumentRepository(session)


def get_all_documents() -> list[dict]:
    """Return all available documents."""
    return load_documents()


def find_document(document_id: str) -> dict | None:
    """Find a document using its ID."""
    return get_document(document_id)


async def check_db(request: Request) -> bool:
    """Check whether PostgreSQL is reachable."""
    engine = getattr(request.app.state, "engine", None)

    if engine is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
