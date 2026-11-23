"""Polite, resumable downloader for your corpus.

The rules it follows, in order:
1. Ask robots.txt first (RFC 9309). Not allowed means never requested.
2. At most `max_concurrency` downloads at once, and a pause between two requests to one site.
3. A timeout on every request. Only errors that can heal are retried (429, 5xx, network),
   with exponential backoff + jitter, and Retry-After is obeyed.
4. Write to <name>.part and rename when complete: a killed run never leaves a half file.
5. One line per file in data/manifest.jsonl, so the next run skips what is already there.
"""

import asyncio
import csv
import hashlib
import json
import random
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx
from protego import Protego

# Say who you are and where to complain. Site owners see this in their logs.
CONTACT = "https://github.com/mathulikanatarajan-debug/prince28-law05-homesure"
ROBOTS_TOKEN = "examate-student-bot"
USER_AGENT = f"{ROBOTS_TOKEN}/0.1 (student project; +{CONTACT})"

RETRYABLE = {408, 425, 429, 500, 502, 503, 504}
MAX_WAIT = 120.0
MAX_BYTES = 200 * 1024 * 1024
ATTEMPT_TIMEOUT = 300.0
KNOWN_EXT = {
    ".pdf",
    ".html",
    ".htm",
    ".json",
    ".txt",
    ".md",
    ".mdx",
    ".rst",
    ".adoc",
    ".csv",
    ".xml",
    ".yaml",
    ".yml",
    ".zip",
    ".docx",
    ".xlsx",
    ".xls",
}
EXT_BY_TYPE = {
    "application/pdf": ".pdf",
    "text/html": ".html",
    "application/json": ".json",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/xml": ".xml",
    "text/xml": ".xml",
    "application/zip": ".zip",
    "application/yaml": ".yaml",
}

Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class Source:
    url: str
    source: str
    licence: str
    title: str = ""


class DownloadError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        retry_after: float | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def slug(text: str, limit: int = 60) -> str:
    """Lowercase letters, digits and dashes only: safe on Windows, Mac and Linux."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit] or "file"


def file_stem(url: str) -> str:
    """A stable file name for a URL: a readable part + 8 characters of the URL's hash."""
    parts = urlsplit(url)
    last = unquote(parts.path.rstrip("/").rsplit("/", 1)[-1]) or parts.netloc
    name = last.rsplit(".", 1)[0] if "." in last else last
    return f"{slug(name)}-{hashlib.sha256(url.encode()).hexdigest()[:8]}"


def pick_ext(url: str, content_type: str) -> str:
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix in KNOWN_EXT:
        return suffix
    return EXT_BY_TYPE.get(content_type.split(";")[0].strip().lower(), ".bin")


def backoff_delay(attempt: int, *, base: float = 1.0, cap: float = 60.0) -> float:
    """Exponential backoff with full jitter."""
    return random.uniform(0, min(cap, base * 2**attempt))


def retry_after_seconds(value: str | None) -> float | None:
    """The Retry-After header is either seconds or an HTTP date."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def read_sources(path: Path) -> list[Source]:
    """Read data/sources.csv. Lines starting with # are notes."""
    sources: list[Source] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        lines = (line for line in handle if line.strip() and not line.lstrip().startswith("#"))
        for number, row in enumerate(csv.DictReader(lines), start=1):
            url = (row.get("url") or "").strip()
            name = (row.get("source") or "").strip()
            licence = (row.get("licence") or "").strip()
            if urlsplit(url).scheme not in {"http", "https"}:
                raise ValueError(f"sources row {number}: not an http(s) URL: {url!r}")
            if not name or not licence:
                raise ValueError(f"sources row {number}: source and licence are required: {url}")
            if url not in seen:
                seen.add(url)
                sources.append(Source(url, name, licence, (row.get("title") or "").strip()))
    return sources


class Manifest:
    """Append-only log: one JSON line per file. The newest line for a URL wins."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.records: dict[str, dict] = {}
        if path.exists():
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self.records[record["url"]] = record
            if text and not text.endswith("\n"):
                with path.open("a", encoding="utf-8") as handle:
                    handle.write("\n")

    def done(self, url: str, root: Path) -> bool:
        record = self.records.get(url)
        return bool(
            record and record["status"] == "downloaded" and (root / record["path"]).is_file()
        )

    def add(self, record: dict) -> None:
        self.records[record["url"]] = record
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


class Robots:
    """robots.txt for each site: fetched once per run, applied the RFC 9309 way."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._rules: dict[str, Protego | None] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def _load(self, origin: str) -> Protego | None:
        try:
            async with asyncio.timeout(ATTEMPT_TIMEOUT):
                response = await self._client.get(origin + "/robots.txt")
        except (httpx.HTTPError, TimeoutError):
            return None
        if response.status_code == 429 or response.status_code >= 500:
            return None
        if response.status_code >= 400:
            return Protego.parse("")
        return Protego.parse(response.text)

    async def check(self, url: str) -> tuple[bool, float]:
        """Return (allowed?, the crawl delay the site asks for in seconds)."""
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        async with self._locks.setdefault(origin, asyncio.Lock()):
            if origin not in self._rules:
                self._rules[origin] = await self._load(origin)
        rules = self._rules[origin]
        if rules is None:
            return False, 0.0
        return (
            rules.can_fetch(url, ROBOTS_TOKEN),
            float(rules.crawl_delay(ROBOTS_TOKEN) or 0.0),
        )


async def _download(
    client: httpx.AsyncClient,
    src: Source,
    root: Path,
    raw_dir: Path,
) -> dict:
    async with client.stream("GET", src.url) as response:
        if response.status_code >= 400:
            raise DownloadError(
                f"HTTP {response.status_code}",
                code=response.status_code,
                retry_after=retry_after_seconds(response.headers.get("Retry-After")),
            )

        content_type = response.headers.get("Content-Type", "")
        content_length = response.headers.get("Content-Length", "").strip()
        if content_length.isdigit() and int(content_length) > MAX_BYTES:
            raise DownloadError(
                f"response exceeds the {MAX_BYTES}-byte size limit",
                code=response.status_code,
            )

        raw_dir.mkdir(parents=True, exist_ok=True)
        destination = raw_dir / f"{file_stem(src.url)}{pick_ext(src.url, content_type)}"
        partial = destination.with_suffix(destination.suffix + ".part")
        digest = hashlib.sha256()
        size = 0
        try:
            with partial.open("wb") as handle:
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise DownloadError(
                            f"response exceeds the {MAX_BYTES}-byte size limit",
                            code=response.status_code,
                        )
                    handle.write(chunk)
                    digest.update(chunk)
            partial.replace(destination)
        finally:
            if partial.exists():
                partial.unlink()

    return {
        "path": destination.relative_to(root).as_posix(),
        "bytes": size,
        "sha256": digest.hexdigest(),
        "content_type": content_type,
    }


class HostGate:
    """Politeness: leave a gap between two requests to the same site."""

    def __init__(self, delay: float, sleep: Sleep) -> None:
        self._delay = delay
        self._sleep = sleep
        self._next_ok: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def wait(self, host: str, crawl_delay: float = 0.0) -> None:
        async with self._locks.setdefault(host, asyncio.Lock()):
            pause = self._next_ok.get(host, 0.0) - time.monotonic()

            if pause > 0:
                await self._sleep(pause)
            self._next_ok[host] = time.monotonic() + max(self._delay, crawl_delay)


def make_client(max_concurrency: int = 4) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(max_connections=max_concurrency),
        follow_redirects=True,
    )


async def fetch_one(
    client: httpx.AsyncClient,
    src: Source,
    *,
    root: Path,
    raw_dir: Path,
    robots: Robots,
    gate: HostGate,
    slots: asyncio.Semaphore,
    max_attempts: int,
    sleep: Sleep,
) -> dict:
    """Download one source with retries. Always returns a manifest record."""
    record = {
        "url": src.url,
        "source": src.source,
        "licence": src.licence,
        "title": src.title,
        "via": "http",
    }
    allowed, crawl_delay = await robots.check(src.url)
    if not allowed:
        return record | {
            "status": "blocked",
            "error": "robots.txt",
            "fetched_at": now_iso(),
        }
    host = urlsplit(src.url).netloc
    error, code, attempt = "", None, 0
    for attempt in range(1, max_attempts + 1):
        wait = backoff_delay(attempt - 1)
        async with slots:
            await gate.wait(host, crawl_delay)
            try:
                async with asyncio.timeout(ATTEMPT_TIMEOUT):
                    fields = await _download(client, src, root, raw_dir)
                done = {
                    "status": "downloaded",
                    "attempts": attempt,
                    "fetched_at": now_iso(),
                }
                return record | fields | done
            except DownloadError as exc:
                error, code = str(exc), exc.code
                if code not in RETRYABLE:
                    break
                if exc.retry_after is not None:
                    if exc.retry_after > MAX_WAIT:
                        error = f"{error}: asked to wait {exc.retry_after:.0f} s, run again later"
                        break
                    wait = max(wait, exc.retry_after)
            except (httpx.TransportError, TimeoutError) as exc:
                error, code = type(exc).__name__, None
            except httpx.HTTPError as exc:
                error, code = type(exc).__name__, None
                break
        if attempt < max_attempts:
            await sleep(min(wait, MAX_WAIT))
    failed = {
        "status": "failed",
        "http_status": code,
        "error": error,
        "attempts": attempt,
    }
    return record | failed | {"fetched_at": now_iso()}


async def fetch_all(
    sources: list[Source],
    *,
    root: Path = Path("."),
    max_concurrency: int = 4,
    per_host_delay: float = 0.5,
    max_attempts: int = 4,
    client: httpx.AsyncClient | None = None,
    sleep: Sleep = asyncio.sleep,
    on_result: Callable[[dict], None] | None = None,
) -> dict[str, int]:
    """Download every source that is not already done. Returns counts per status."""
    raw_dir = root / "data" / "raw"
    manifest = Manifest(root / "data" / "manifest.jsonl")
    todo = [src for src in sources if not manifest.done(src.url, root)]
    counts = {
        "downloaded": 0,
        "skipped": len(sources) - len(todo),
        "blocked": 0,
        "failed": 0,
    }
    own_client = client is None
    if client is None:
        client = make_client(max_concurrency)
    robots = Robots(client)
    gate = HostGate(per_host_delay, sleep)
    slots = asyncio.Semaphore(max_concurrency)
    tasks: list[asyncio.Task[dict]] = []
    try:
        tasks = [
            asyncio.create_task(
                fetch_one(
                    client,
                    src,
                    root=root,
                    raw_dir=raw_dir,
                    robots=robots,
                    gate=gate,
                    slots=slots,
                    max_attempts=max_attempts,
                    sleep=sleep,
                )
            )
            for src in todo
        ]
        for finished in asyncio.as_completed(tasks):
            record = await finished
            counts[record["status"]] += 1
            before = manifest.records.get(record["url"], {})
            same_problem = (before.get("status"), before.get("error")) == (
                record["status"],
                record.get("error"),
            )
            if record["status"] == "downloaded" or not same_problem:
                manifest.add(record)
            if on_result:
                on_result(record)
        return counts
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if own_client:
            await client.aclose()
