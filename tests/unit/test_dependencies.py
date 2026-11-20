"""Tests for shared API dependency behavior."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from starlette.requests import Request

from homesure.api import deps
from homesure.api.errors import DocumentNotFoundError
from homesure.db.repository import DocumentRepository


def make_request(engine=None):
    app = FastAPI()
    if engine is not None:
        app.state.engine = engine

    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
            "client": ("test", 1),
            "server": ("test", 80),
            "app": app,
        }
    )


@pytest.mark.asyncio
async def test_get_repo_yields_and_closes_request_session(monkeypatch):
    session = object()

    class SessionContext:
        closed = False

        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc_value, traceback):
            self.closed = True

    context = SessionContext()
    engine = object()
    monkeypatch.setattr(
        deps,
        "make_sessionmaker",
        lambda actual_engine: (
            (lambda: context)
            if actual_engine is engine
            else pytest.fail("get_repo used a different engine")
        ),
    )
    repository_generator = deps.get_repo(make_request(engine))

    try:
        repository = await anext(repository_generator)
        assert isinstance(repository, DocumentRepository)
        assert repository.session is session
    finally:
        await repository_generator.aclose()

    assert context.closed


@pytest.mark.asyncio
async def test_check_db_executes_select_one():
    connection = SimpleNamespace(statement=None)

    class ConnectionContext:
        async def __aenter__(self):
            return connection

        async def __aexit__(self, exc_type, exc_value, traceback):
            return None

    class Engine:
        def connect(self):
            return ConnectionContext()

    async def execute(statement):
        connection.statement = str(statement)

    connection.execute = execute

    assert await deps.check_db(make_request(Engine()))
    assert connection.statement == "SELECT 1"


@pytest.mark.asyncio
async def test_check_db_reports_missing_or_unavailable_database():
    with pytest.raises(HTTPException) as missing_engine:
        await deps.check_db(make_request())
    assert missing_engine.value.status_code == 503

    class BrokenEngine:
        def connect(self):
            raise RuntimeError("connection failed")

    with pytest.raises(HTTPException) as unavailable_engine:
        await deps.check_db(make_request(BrokenEngine()))
    assert unavailable_engine.value.status_code == 503


def test_json_compatibility_dependencies_delegate(monkeypatch):
    records = [{"id": "test-1"}]
    monkeypatch.setattr(deps, "load_documents", lambda: records)
    monkeypatch.setattr(deps, "get_document", lambda document_id: records[0])

    assert deps.get_all_documents() is records
    assert deps.find_document("test-1") is records[0]


def test_not_found_error_contains_document_id():
    error = DocumentNotFoundError("test-1")

    assert error.status_code == 404
    assert error.detail == "Document 'test-1' was not found."
