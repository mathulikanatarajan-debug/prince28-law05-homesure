"""Unit tests for the HomeSure API."""

from fastapi.testclient import TestClient

from homesure.api.main import create_app
from homesure.config import Settings


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_database_up(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": True},
    }


def test_ready_database_unavailable(client, db_state):
    db_state["up"] = False

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == 503


def test_list_documents(client):
    response = client.get("/v1/documents")
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 3


def test_list_document_ids(client):
    response = client.get("/v1/documents")
    assert [doc["id"] for doc in response.json()["items"]] == ["001", "002", "003"]


def test_limit_documents(client):
    response = client.get("/v1/documents?limit=2")
    assert len(response.json()["items"]) == 2


def test_offset_documents(client):
    response = client.get("/v1/documents?offset=1")
    assert [doc["id"] for doc in response.json()["items"]] == ["002", "003"]


def test_search_documents(client):
    response = client.get("/v1/documents?q=Alpha")
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == "001"


def test_search_case_insensitive(client):
    response = client.get("/v1/documents?q=alpha")
    assert response.json()["total"] == 1


def test_filter_by_year(client):
    response = client.get("/v1/documents?year=2024")
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == "002"


def test_filter_by_kind(client):
    response = client.get("/v1/documents?kind=circular")
    assert response.json()["total"] == 2


def test_filters_are_returned(client):
    response = client.get("/v1/documents?kind=circular")
    assert response.json()["filters"] == {"kind": "circular"}


def test_get_document(client):
    response = client.get("/v1/documents/002")
    assert response.status_code == 200
    assert response.json()["title"] == "Beta circular"


def test_missing_document(client):
    response = client.get("/v1/documents/missing")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["status"] == 404


def test_invalid_filter_name(client):
    response = client.get("/v1/documents?Bad-Name=1")
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"


def test_invalid_limit(client):
    response = client.get("/v1/documents?limit=0")
    assert response.status_code == 422
    assert response.json()["status"] == 422


def test_request_id_is_echoed(client):
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"


def test_app_remains_available_when_json_file_is_missing(tmp_path, capsys):
    settings = Settings(
        app_env="ci",
        database_url="postgresql://localhost/unused",
        data_file=tmp_path / "missing.json",
        _env_file=None,
    )

    with TestClient(create_app(settings)) as test_client:
        assert test_client.get("/health").status_code == 200

    assert "Could not load records" in capsys.readouterr().err
