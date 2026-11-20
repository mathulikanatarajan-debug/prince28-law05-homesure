"""Provision an isolated PostgreSQL database for each integration test run."""

import asyncio
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from homesure.db.url import to_asyncpg_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]


async def _create_database(admin_url: URL, database_name: str) -> None:
    engine = create_async_engine(admin_url)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
    finally:
        await engine.dispose()


async def _drop_database(admin_url: URL, database_name: str) -> None:
    engine = create_async_engine(admin_url)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.exec_driver_sql(
                f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'
            )
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def integration_database_url() -> Iterator[str]:
    """Create and later remove a unique database; never reuse an existing test database."""
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.fail(
            "TEST_DATABASE_URL is required; run integration tests with "
            "`uv run poe test-integration`."
        )

    template_url = make_url(to_asyncpg_url(base_url))
    admin_url = template_url.set(database="postgres")
    database_name = f"homesure_test_{uuid4().hex}"
    test_url = template_url.set(database=database_name).render_as_string(hide_password=False)
    created = False

    try:
        asyncio.run(_create_database(admin_url, database_name))
        created = True

        environment = os.environ.copy()
        environment.update(
            {
                "APP_ENV": "ci",
                "DATABASE_URL": test_url,
                "DATA_FILE": str(PROJECT_ROOT / "data" / "sample_records.json"),
            }
        )
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=PROJECT_ROOT,
            env=environment,
            check=True,
        )
        yield test_url
    finally:
        if created:
            asyncio.run(_drop_database(admin_url, database_name))
