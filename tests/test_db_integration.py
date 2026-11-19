"""Optional integration tests against a real PostgreSQL database."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from homesure.db.models import Document
from homesure.db.repository import DocumentRepository
from homesure.db.url import to_asyncpg_url

DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="TEST_DATABASE_URL is not configured",
)


@pytest.fixture
async def db_session():
    """Create a session connected to the integration-test database."""
    engine = create_async_engine(to_asyncpg_url(DATABASE_URL))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def sample_document(db_session):
    """Insert a temporary document for integration tests."""
    document = Document(
        external_id=f"test-{uuid4().hex}",
        title="Integration test document",
        doc_type="guideline",
        sha256=uuid4().hex * 2,
        metadata_={"project_reg_no": "TEST-123", "year": 2026},
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    yield document

    await db_session.delete(document)
    await db_session.commit()


@pytest.mark.asyncio
async def test_insert_and_retrieve_document(db_session, sample_document):
    result = await db_session.scalar(
        select(Document).where(Document.external_id == sample_document.external_id)
    )
    assert result is not None
    assert result.title == "Integration test document"


@pytest.mark.asyncio
async def test_repository_metadata_filter(db_session, sample_document):
    repository = DocumentRepository(db_session)

    total, items = await repository.list(
        q=None,
        filters={"project_reg_no": "TEST-123"},
        limit=10,
        offset=0,
    )

    assert total >= 1
    assert any(item["id"] == sample_document.external_id for item in items)


@pytest.mark.asyncio
async def test_missing_document_returns_none(db_session):
    repository = DocumentRepository(db_session)

    result = await repository.get("does-not-exist-12345")

    assert result is None
