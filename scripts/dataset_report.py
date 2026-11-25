import json
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifest.jsonl"
DOCS = ROOT / "docs"


def main():
    if not MANIFEST.exists():
        raise SystemExit("ERROR: data/manifest.jsonl not found.")

    records = []
    for line_number, line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON in manifest line {line_number}: {exc}") from exc

    status_counts = Counter(record.get("status", "unknown") for record in records)
    source_counts = Counter(record.get("source", "Unknown") for record in records)

    files = []
    total_bytes = 0
    total_pages = 0
    checksum_count = 0
    errors = []

    for record in records:
        relative_path = record.get("path")
        path = (ROOT / relative_path).resolve() if relative_path else None

        if path is None or not path.is_relative_to(ROOT):
            errors.append(f"Unsafe or missing path: {relative_path}")
            continue

        if not path.is_file():
            errors.append(f"File missing: {relative_path}")
            continue

        size = path.stat().st_size
        total_bytes += size

        pages = 0
        if path.suffix.lower() == ".pdf":
            try:
                pages = len(PdfReader(str(path)).pages)
                total_pages += pages
            except Exception as exc:
                errors.append(f"Could not read {relative_path}: {exc}")

        checksum = record.get("sha256", "")
        if checksum:
            checksum_count += 1

        files.append(
            {
                "title": record.get("title", path.name),
                "source": record.get("source", "Unknown"),
                "status": record.get("status", "unknown"),
                "path": relative_path,
                "bytes": size,
                "pages": pages,
                "sha256": checksum,
                "url": record.get("url", ""),
            }
        )

    DOCS.mkdir(parents=True, exist_ok=True)
    mb = total_bytes / (1024 * 1024)

    dataset = [
        "# HomeSure Dataset Report",
        "",
        "Generated from `data/manifest.jsonl` and the files present in `data/raw`.",
        "",
        "## Summary",
        "",
        f"- Manifest records: {len(records)}",
        f"- Downloaded files present: {len(files)}",
        f"- PDF files: {sum(1 for f in files if f['path'].lower().endswith('.pdf'))}",
        f"- Total PDF pages: {total_pages}",
        f"- Total corpus size: {total_bytes:,} bytes ({mb:.3f} MB)",
        f"- Files with SHA-256 recorded: {checksum_count}",
        "",
        "## Status counts",
        "",
    ]

    for status, count in sorted(status_counts.items()):
        dataset.append(f"- {status}: {count}")

    dataset += ["", "## Source counts", ""]
    for source, count in sorted(source_counts.items()):
        dataset.append(f"- {source}: {count}")

    dataset += ["", "## Files", ""]
    for file in files:
        dataset += [
            f"### {file['title']}",
            f"- Source: {file['source']}",
            f"- Status: {file['status']}",
            f"- File: `{file['path']}`",
            f"- Size: {file['bytes']:,} bytes",
            f"- PDF pages: {file['pages']}",
            f"- URL: {file['url']}",
            f"- SHA-256: `{file['sha256'] or 'Not recorded'}`",
            "",
        ]

    if errors:
        dataset += ["## Warnings", ""]
        dataset.extend(f"- {error}" for error in errors)
        dataset.append("")

    (ROOT / "DATASET.md").write_text("\n".join(dataset), encoding="utf-8")

    capacity = [
        "# HomeSure Corpus Capacity Report",
        "",
        "## Current measured corpus",
        "",
        f"- Files present: {len(files)}",
        f"- Total size: {total_bytes:,} bytes ({mb:.3f} MB)",
        f"- PDF pages: {total_pages}",
        f"- SHA-256 checksums recorded: {checksum_count}",
        "",
        "## Capacity notes",
        "",
        "- These figures describe the files currently present in `data/raw`.",
        "- They are not a performance benchmark or a prediction of final dataset size.",
        "- Additional circulars and individual orders must be collected",
        "  before the target corpus is complete.",
        "- Re-run `uv run python scripts/dataset_report.py` after adding",
        "  sources to refresh these reports.",
    ]

    (DOCS / "CAPACITY.md").write_text("\n".join(capacity), encoding="utf-8")

    print("Dataset reports generated successfully.")
    print(f"Manifest records: {len(records)}")
    print(f"Files present: {len(files)}")
    print(f"PDF pages: {total_pages}")
    print(f"Corpus size: {mb:.3f} MB")
    print(f"Warnings: {len(errors)}")
    print("Created: DATASET.md")
    print("Created: docs/CAPACITY.md")


if __name__ == "__main__":
    main()
