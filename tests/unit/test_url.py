"""Tests for PostgreSQL URL normalization."""

from sqlalchemy.engine import make_url

from homesure.db.url import to_asyncpg_url


def test_sync_postgres_url_is_converted_and_ssl_parameters_normalized():
    url = make_url(
        to_asyncpg_url("postgresql://localhost/homesure?sslmode=require&channel_binding=require")
    )

    assert url.drivername == "postgresql+asyncpg"
    assert url.query == {"ssl": "require"}


def test_asyncpg_url_with_disabled_ssl_drops_driver_specific_parameters():
    url = make_url(
        to_asyncpg_url(
            "postgresql+asyncpg://localhost/homesure?sslmode=disable&channel_binding=require"
        )
    )

    assert url.drivername == "postgresql+asyncpg"
    assert url.query == {}
