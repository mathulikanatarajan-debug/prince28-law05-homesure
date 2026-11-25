import csv
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin


class RegisterParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = {"text": [], "href": ""}
        elif tag == "a" and self.cell is not None:
            self.cell["href"] = attrs.get("href", "")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            text = " ".join(" ".join(self.cell["text"]).split())
            self.row.append((text, self.cell["href"]))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


columns = [
    "SerialNumber",
    "CaseNumber",
    "Complainant",
    "Respondent",
    "Project",
    "OrderDate",
    "OfficialPDFLink",
]

for year in (2023, 2024):
    source = Path.home() / "AppData" / "Local" / "Temp" / f"tnrera_orders_{year}.html"
    if not source.exists():
        print(f"{year}: SOURCE FILE MISSING: {source}")
        continue

    parser = RegisterParser()
    parser.feed(source.read_text(encoding="utf-8", errors="replace"))

    records = []
    for row in parser.rows:
        if len(row) < 7:
            continue

        values = [cell[0] for cell in row[:7]]
        href = row[6][1]

        if not values[0].isdigit() or not values[1] or not href:
            continue

        values[6] = urljoin("https://rera.tn.gov.in/", href)
        records.append(dict(zip(columns, values, strict=True)))

    output = Path("data") / "metadata" / f"official_tnrera_bench1_{year}.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)

    print(f"{year}: {len(records)} register rows extracted")
    print(f"Created: {output}")
    if records:
        print("First record:", records[0])
