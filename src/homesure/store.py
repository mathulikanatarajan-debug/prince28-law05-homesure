"""Load and access HomeSure document records."""

import json
from functools import lru_cache

from homesure.config import get_settings


@lru_cache
def load_documents() -> list[dict]:
    """Load document records from the configured JSON file."""
    settings = get_settings()

    with settings.data_file.open(encoding="utf-8") as file:
        return json.load(file)


def get_document(document_id: str) -> dict | None:
    """Find one document by its ID."""
    for document in load_documents():
        if str(document.get("id")) == document_id:
            return document

    return None
