import json

import httpx
import pytest

from homesure.ingest.fetch import Source, fetch_all


async def no_sleep(_: float) -> None:
    pass


@pytest.mark.asyncio
async def test_fetch_all_retries_and_resumes_completed_downloads(tmp_path):
    source = Source("https://example.test/rules.pdf", "TNRERA", "public")
    requests: list[str] = []
    document_attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal document_attempts
        requests.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        document_attempts += 1
        if document_attempts == 1:
            return httpx.Response(503)
        return httpx.Response(
            200,
            content=b"sample law",
            headers={"Content-Type": "application/pdf"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        counts = await fetch_all(
            [source],
            root=tmp_path,
            per_host_delay=0,
            client=client,
            sleep=no_sleep,
        )
        resumed_counts = await fetch_all(
            [source],
            root=tmp_path,
            per_host_delay=0,
            client=client,
            sleep=no_sleep,
        )

    manifest_record = json.loads(
        (tmp_path / "data" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    saved_files = list((tmp_path / "data" / "raw").glob("*.pdf"))

    assert counts == {"downloaded": 1, "skipped": 0, "blocked": 0, "failed": 0}
    assert resumed_counts == {"downloaded": 0, "skipped": 1, "blocked": 0, "failed": 0}
    assert requests == ["/robots.txt", "/rules.pdf", "/rules.pdf"]
    assert manifest_record["attempts"] == 2
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == b"sample law"
    assert not list((tmp_path / "data" / "raw").glob("*.part"))


@pytest.mark.asyncio
async def test_fetch_all_does_not_request_url_disallowed_by_robots(tmp_path):
    source = Source("https://example.test/private.pdf", "TNRERA", "public")
    requests: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        return httpx.Response(
            200,
            text="User-agent: *\nDisallow: /private.pdf\n",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        counts = await fetch_all(
            [source],
            root=tmp_path,
            per_host_delay=0,
            client=client,
            sleep=no_sleep,
        )

    assert counts == {"downloaded": 0, "skipped": 0, "blocked": 1, "failed": 0}
    assert requests == ["/robots.txt"]
