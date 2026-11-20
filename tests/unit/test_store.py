"""Tests for the retained JSON store helpers."""

import json
from types import SimpleNamespace

from homesure import store


def test_load_and_find_documents(tmp_path, monkeypatch):
    records = [{"id": "001", "title": "Sample"}]
    data_file = tmp_path / "records.json"
    data_file.write_text(json.dumps(records), encoding="utf-8")
    monkeypatch.setattr(
        store,
        "get_settings",
        lambda: SimpleNamespace(data_file=data_file),
    )
    store.load_documents.cache_clear()

    try:
        loaded = store.load_documents()

        assert loaded == records
        assert store.load_documents() is loaded
        assert store.get_document("001") == records[0]
        assert store.get_document("missing") is None
    finally:
        store.load_documents.cache_clear()
