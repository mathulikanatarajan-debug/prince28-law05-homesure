"""Shared fixtures for API tests."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from homesure.api.deps import check_db, get_repo
from homesure.api.main import create_app
from homesure.config import Settings

SAMPLE = [
    {"id": "001", "title": "Alpha guideline", "year": 2023, "kind": "guideline"},
    {"id": "002", "title": "Beta circular", "year": 2024, "kind": "circular"},
    {"id": "003", "title": "Gamma notice", "year": 2025, "kind": "circular"},
]


class FakeRepo:
    """Behaves like DocumentRepository, using an in-memory list."""

    def __init__(self, rows):
        self.rows = rows

    async def list(self, *, q, filters, limit, offset):
        rows = [
            row
            for row in self.rows
            if (not q or q.lower() in str(row).lower())
            and all(str(row.get(key)) == value for key, value in filters.items())
        ]
        return len(rows), rows[offset : offset + limit]

    async def get(self, external_id):
        return next(
            (row for row in self.rows if row["id"] == external_id),
            None,
        )


@pytest.fixture
def settings():
    """Use test settings without reading the local .env file."""
    return Settings(
        app_env="ci",
        database_url="postgresql://localhost:5432/unused",
        _env_file=None,
    )


@pytest.fixture
def db_state():
    return {"up": True}


@pytest.fixture
def client(settings, db_state):
    app = create_app(settings)
    app.dependency_overrides[get_repo] = lambda: FakeRepo(SAMPLE)

    async def fake_check_db():
        if not db_state["up"]:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return True

    app.dependency_overrides[check_db] = fake_check_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
