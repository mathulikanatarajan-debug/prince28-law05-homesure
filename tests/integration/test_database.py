"""Integration tests against a fresh PostgreSQL database."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from homesure.api.main import create_app
from homesure.config import Settings
from homesure.db.models import Document
from homesure.db.repository import DocumentRepository
from homesure.db.url import to_asyncpg_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
async def db_session(integration_database_url):
    engine = create_async_engine(to_asyncpg_url(integration_database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture
async def sample_document(db_session):
    document = Document(
        external_id=f"test-{uuid4().hex}",
        title="Integration test document",
        doc_type="guideline",
        sha256=uuid4().hex * 2,
        metadata_={"project_reg_no": f"TEST-{uuid4().hex}", "year": 2026},
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    try:
        yield document
    finally:
        await db_session.delete(document)
        await db_session.commit()


@pytest.mark.asyncio
async def test_migrations_created_schema_at_head(db_session):
    revision = await db_session.scalar(text("SELECT version_num FROM alembic_version"))
    documents_table = await db_session.scalar(text("SELECT to_regclass('public.documents')"))
    pages_table = await db_session.scalar(text("SELECT to_regclass('public.pages')"))

    assert revision == "8127537c4076"
    assert documents_table == "documents"
    assert pages_table == "pages"


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
        filters={"project_reg_no": sample_document.metadata_["project_reg_no"]},
        limit=10,
        offset=0,
    )

    assert total == 1
    assert [item["id"] for item in items] == [sample_document.external_id]


@pytest.mark.asyncio
async def test_repository_search_and_pagination(db_session):
    search_token = f"integration-{uuid4().hex}"
    documents = [
        Document(
            external_id=f"test-{uuid4().hex}",
            title=f"{search_token} result {index}",
            doc_type="guideline",
            sha256=uuid4().hex * 2,
        )
        for index in range(3)
    ]
    db_session.add_all(documents)
    await db_session.commit()

    try:
        repository = DocumentRepository(db_session)
        total, items = await repository.list(
            q=search_token,
            filters={},
            limit=1,
            offset=1,
        )

        assert total == 3
        assert len(items) == 1
        assert items[0]["id"] == sorted(document.external_id for document in documents)[1]
    finally:
        for document in documents:
            await db_session.delete(document)
        await db_session.commit()


@pytest.mark.asyncio
async def test_repository_supports_typed_metadata_filters(db_session):
    document = Document(
        external_id=f"test-{uuid4().hex}",
        title="Typed metadata filter",
        doc_type="record",
        sha256=uuid4().hex * 2,
        metadata_={"active": True, "score": 1.5, "tags": ["approved"], "year": 2026},
    )
    db_session.add(document)
    await db_session.commit()

    try:
        repository = DocumentRepository(db_session)
        for filters in (
            {"active": "true"},
            {"score": "1.5"},
            {"tags": "approved"},
            {"year": "2026"},
        ):
            total, items = await repository.list(
                q=None,
                filters=filters,
                limit=10,
                offset=0,
            )
            assert total == 1
            assert [item["id"] for item in items] == [document.external_id]
    finally:
        await db_session.delete(document)
        await db_session.commit()


@pytest.mark.asyncio
async def test_database_backed_api_health_readiness_and_documents(
    db_session,
    integration_database_url,
):
    external_id = f"api-{uuid4().hex}"
    search_token = f"homesure-{uuid4().hex}"
    document = Document(
        external_id=external_id,
        title=f"{search_token} integration record",
        doc_type="record",
        sha256=uuid4().hex * 2,
        metadata_={"project_reg_no": f"TEST-{uuid4().hex}"},
    )
    db_session.add(document)
    await db_session.commit()

    settings = Settings(
        app_env="ci",
        database_url=integration_database_url,
        data_file=PROJECT_ROOT / "data" / "sample_records.json",
        _env_file=None,
    )

    try:
        with TestClient(create_app(settings)) as client:
            assert client.get("/health").json()["status"] == "ok"

            assert client.get("/ready").json() == {
                "status": "ready",
                "checks": {"database": True},
            }

            listing = client.get(
                "/v1/documents",
                params={"q": search_token, "limit": 1, "offset": 0},
            )
            assert listing.status_code == 200
            assert listing.json()["total"] == 1
            assert listing.json()["items"][0]["id"] == external_id

            detail = client.get(f"/v1/documents/{external_id}")
            assert detail.status_code == 200
            assert detail.json()["id"] == external_id
    finally:
        await db_session.delete(document)
        await db_session.commit()


@pytest.mark.asyncio
async def test_missing_document_returns_none(db_session):
    repository = DocumentRepository(db_session)

    result = await repository.get(f"does-not-exist-{uuid4().hex}")

    assert result is None


def test_data_loader_is_idempotent(integration_database_url):
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV": "ci",
            "DATABASE_URL": integration_database_url,
            "DATA_FILE": str(PROJECT_ROOT / "data" / "sample_records.json"),
        }
    )

    def run_loader() -> str:
        result = subprocess.run(
            [sys.executable, "scripts/load_db.py"],
            cwd=PROJECT_ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    expected_records = len(
        json.loads((PROJECT_ROOT / "data" / "sample_records.json").read_text(encoding="utf-8"))
    )
    first_run = run_loader()
    second_run = run_loader()

    first_counts = re.search(r"inserted=(\d+) updated=(\d+) unchanged=(\d+)", first_run)
    second_counts = re.search(r"inserted=(\d+) updated=(\d+) unchanged=(\d+)", second_run)

    assert first_counts is not None
    assert second_counts is not None
    assert tuple(map(int, first_counts.groups())) == (expected_records, 0, 0)
    assert tuple(map(int, second_counts.groups())) == (0, 0, expected_records)
