#!/usr/bin/env python3
"""Capture explicitly requested open PMC article HTML with an audit trail.

The script uses public PMC URLs only. It neither bypasses publisher paywalls nor
solves CAPTCHAs. It records every request, including failures, in a source
manifest suitable for later outcome source-location verification. It does not
perform outcome extraction or eligibility decisions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def normalise_pmcid(value: str) -> str:
    value = value.strip().upper()
    if not value.startswith("PMC") or not value[3:].isdigit():
        raise ValueError(f"Invalid PMCID {value!r}; expected PMC followed by digits")
    return value


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pmcid", action="append", required=True, help="May be repeated")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    args.source_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, str]] = []
    for requested in sorted({normalise_pmcid(value) for value in args.pmcid}):
        url = f"https://pmc.ncbi.nlm.nih.gov/articles/{requested}/"
        row = {
            "report_id": "",
            "record_id": "",
            "pmid": "",
            "source_type": "PMC HTML",
            "stable_url_or_identifier": url,
            "retrieval_date": datetime.now(timezone.utc).isoformat(),
            "access_status": "",
            "local_filename": "",
            "sha256": "",
            "copyright_or_access_note": "Open PMC page requested; preserve citation/copyright terms.",
            "reviewer": "",
            "notes": "",
        }
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "HMF-RCT-review-source-archiver/1.0"})
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                content = response.read()
                if not content:
                    raise ValueError("Empty response")
                filename = f"{requested}.html"
                destination = args.source_dir / filename
                destination.write_bytes(content)
                row.update(
                    {
                        "access_status": f"HTTP {response.status}",
                        "local_filename": str(destination),
                        "sha256": sha256(content),
                    }
                )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
            row["access_status"] = "not captured"
            row["notes"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)

    fields = list(rows[0]) if rows else []
    write_header = not args.manifest.exists() or args.manifest.stat().st_size == 0
    with args.manifest.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
