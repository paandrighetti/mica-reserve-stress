"""Downloads the files listed in sources/MANIFEST.json and compares them with the recorded SHA-256.

The examination reports (PDF) must match: they are fixed documents. The two web pages and the DefiLlama series
change every day, so a difference there is reported, not an error. Usage: python scripts/fetch_sources.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROWSER = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}


def main() -> None:
    src = ROOT / "sources"
    bad = 0
    for item in json.loads((src / "MANIFEST.json").read_text()):
        path = src / item["file"]
        if not path.exists():
            with urllib.request.urlopen(urllib.request.Request(item["url"], headers=BROWSER), timeout=90) as r:
                path.write_bytes(r.read())
        same = hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        if not same:
            fixed = item["file"].endswith(".pdf")
            bad += fixed
            print(("ERROR" if fixed else "changed since"), item["fetched"], item["file"])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
