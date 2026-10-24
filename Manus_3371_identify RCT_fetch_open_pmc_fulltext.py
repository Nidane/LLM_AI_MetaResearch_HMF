#!/usr/bin/env python3
"""Archive open PubMed Central full text with a reproducible retrieval log.

This optional helper replaces the lost temporary fetch script at a transparent,
limited level. It downloads only explicitly supplied PMCID records from PMC,
saves source HTML without altering it, and records URL, retrieval time, HTTP
status, response type, byte size, and SHA-256. It does not bypass paywalls,
CAPTCHAs, robots restrictions, or access controls; publisher-only full texts
must be retrieved lawfully by the reviewer.

It also does not extract outcome counts automatically. NEC and sepsis events
must be verified manually from the actual report/table and recorded with a
source location in the review's outcome-extraction sheet.

Examples
--------
# Fetch one open PMC article
python src/fetch_open_pmc_fulltext.py --pmcid PMC10965410 --output-dir fulltext

# Fetch every nonblank PMCID in the exported retained eligible-RCT source data
python src/fetch_open_pmc_fulltext.py \
  --eligible-csv output/eligible_rcts_full.csv \
  --output-dir fulltext
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

import requests


def normalise_pmcid(value: str) -> str:
    value = value.strip().upper()
    if not value.startswith("PMC") or not value[3:].isdigit():
        raise ValueError(f"Invalid PMCID: {value!r}; expected form PMC1234567")
    return value


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def pmcids_from_csv(path: Path) -> List[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if "pmcid" not in (reader.fieldnames or []):
            raise ValueError(f"{path} has no 'pmcid' column")
        ids: Set[str] = set()
        for row in reader:
            if row.get("pmcid", "").strip():
                ids.add(normalise_pmcid(row["pmcid"]))
    return sorted(ids)


def fetch_one(session: requests.Session, pmcid: str, destination: Path, timeout: int) -> Dict[str, object]:
    url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    retrieved_at = datetime.now(timezone.utc).isoformat()
    row: Dict[str, object] = {
        "pmcid": pmcid,
        "url": url,
        "retrieved_utc": retrieved_at,
        "http_status": "",
        "content_type": "",
        "bytes": "",
        "sha256": "",
        "saved_file": "",
        "error": "",
    }
    try:
        response = session.get(url, timeout=timeout)
        row["http_status"] = response.status_code
        row["content_type"] = response.headers.get("content-type", "")
        row["bytes"] = len(response.content)
        if response.ok and response.content:
            output_file = destination / f"{pmcid}.html"
            output_file.write_bytes(response.content)
            row["sha256"] = sha256_bytes(response.content)
            row["saved_file"] = str(output_file)
        else:
            row["error"] = f"HTTP {response.status_code}; content not saved"
    except requests.RequestException as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pmcid", action="append", help="PMCID to fetch; may be specified more than once")
    group.add_argument("--eligible-csv", type=Path, help="Exported eligible_rcts_full.csv containing a pmcid column")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    if args.eligible_csv:
        if not args.eligible_csv.is_file():
            raise SystemExit(f"CSV does not exist: {args.eligible_csv}")
        pmcids = pmcids_from_csv(args.eligible_csv)
    else:
        pmcids = sorted({normalise_pmcid(x) for x in (args.pmcid or [])})
    if not pmcids:
        raise SystemExit("No nonblank PMCID values to fetch")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "HMF-systematic-review-reproducibility/1.0 (open-access retrieval)"})
    rows = [fetch_one(session, pmcid, args.output_dir, args.timeout) for pmcid in pmcids]

    log_path = args.output_dir / "pmc_retrieval_log.json"
    log_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    successful = sum(bool(row["saved_file"]) for row in rows)
    print(f"Requested {len(rows)} PMC record(s); saved {successful}; audit log: {log_path}")


if __name__ == "__main__":
    main()
