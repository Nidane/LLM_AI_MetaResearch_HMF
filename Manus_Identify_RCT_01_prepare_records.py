#!/usr/bin/env python3
"""Create immutable canonical records and reviewer screening files from a PubMed export.

This script is the entry point for a new prospective review workflow. It parses
only sequential 1..N top-level record starts, so numbered reference lines within
an article remain inside that article. It creates one canonical record for every
record in the supplied export and a blank dual-reviewer ledger for all records.

It performs no eligibility decisions. Automated term flags determine a review
priority tier only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

RECORD_START_RE = re.compile(r"(?m)^(\d+)\.\s+")
PMID_RE = re.compile(r"\bPMID:\s*(\d+)", re.IGNORECASE)
PMCID_RE = re.compile(r"\bPMCID:\s*(PMC\d+)", re.IGNORECASE)
DOI_RE = re.compile(r"\bdoi:\s*([^\s;]+)", re.IGNORECASE)
ABSTRACT_LABEL_RE = re.compile(
    r"^(?:abstract|background|objective|objectives|design|methods?|results?|conclusions?|"
    r"aim|introduction|purpose|setting|participants?|intervention|main outcome measures):",
    re.IGNORECASE,
)

LEDGER_FIELDS = [
    "record_id", "export_record_no", "pmid", "doi_normalized", "title", "priority_tier",
    "stage", "reviewer_1", "reviewer_1_date", "reviewer_1_decision", "reviewer_1_reason_code",
    "reviewer_1_rationale", "reviewer_2", "reviewer_2_date", "reviewer_2_decision",
    "reviewer_2_reason_code", "reviewer_2_rationale", "consensus_decision", "consensus_reason_code",
    "consensus_rationale", "adjudicator", "adjudication_date", "requires_full_text", "report_id",
    "study_id", "analytic_stratum", "source_document_or_url", "record_version",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalise_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def split_paragraphs(raw_without_number: str) -> List[str]:
    return [normalise_space(x) for x in re.split(r"\n\s*\n", raw_without_number) if x.strip()]


def is_citation_like(text: str) -> bool:
    low = text.lower()
    return bool(re.search(r"\b(?:doi|pmid|pmcid):", low) or re.search(r"\b\d{4}\b", text) and len(text) < 350)


def extract_title_and_authors(raw_without_number: str) -> Tuple[str, str]:
    """Extract best-effort title/authors while retaining raw text as authority."""
    paragraphs = split_paragraphs(raw_without_number)
    title_index = None
    for idx, paragraph in enumerate(paragraphs[:8]):
        if idx == 0 or is_citation_like(paragraph) or paragraph.lower().startswith("author information"):
            continue
        if ABSTRACT_LABEL_RE.match(paragraph):
            continue
        if paragraph.startswith("[") and "article" in paragraph.lower():
            continue
        title_index = idx
        break
    if title_index is None:
        return "", ""
    title = paragraphs[title_index]
    authors = ""
    for paragraph in paragraphs[title_index + 1:title_index + 4]:
        if paragraph.lower().startswith("author information") or ABSTRACT_LABEL_RE.match(paragraph):
            break
        if len(paragraph) < 700:
            authors = paragraph
            break
    return title, authors


def sequential_starts(text: str) -> Tuple[List[re.Match[str]], int]:
    """Return record starts numbered 1..N in order and count all apparent starts."""
    all_starts = list(RECORD_START_RE.finditer(text))
    canonical: List[re.Match[str]] = []
    expected = 1
    for match in all_starts:
        if int(match.group(1)) == expected:
            canonical.append(match)
            expected += 1
    if not canonical or int(canonical[0].group(1)) != 1:
        raise ValueError("Input does not begin with sequential record number 1")
    return canonical, len(all_starts)


def compile_terms(dictionary: Dict[str, Any]) -> Dict[str, List[re.Pattern[str]]]:
    terms = dictionary.get("terms", {})
    required = {
        "randomization", "human_fortifier_or_ehmd", "bovine_or_cow_comparator",
        "fortification", "population", "outcomes",
    }
    missing = required - set(terms)
    if missing:
        raise ValueError(f"Term dictionary missing categories: {sorted(missing)}")
    return {category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns] for category, patterns in terms.items()}


def matches(text: str, patterns: Sequence[re.Pattern[str]]) -> List[str]:
    values: List[str] = []
    for pattern in patterns:
        found = pattern.search(text)
        if found and found.group(0) not in values:
            values.append(found.group(0))
    return values


def priority_tier(flags: Dict[str, bool]) -> str:
    if flags["randomization"] and flags["human_fortifier_or_ehmd"] and flags["fortification"] and flags["bovine_or_cow_comparator"]:
        return "tier_1_explicit_rct_and_bovine_comparator_signal"
    if flags["randomization"] and flags["human_fortifier_or_ehmd"] and flags["fortification"]:
        return "tier_2_rct_and_human_fortifier_signal"
    if flags["human_fortifier_or_ehmd"] and flags["fortification"]:
        return "tier_3_human_fortifier_or_ehmd_signal"
    return "tier_4_no_automated_priority_signal"


def record_rows(text: str, compiled: Dict[str, List[re.Pattern[str]]], input_hash: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    starts, apparent_starts = sequential_starts(text)
    rows: List[Dict[str, Any]] = []
    for index, start in enumerate(starts, start=1):
        end = starts[index].start() if index < len(starts) else len(text)
        raw = text[start.start():end].strip()
        raw_without_number = RECORD_START_RE.sub("", raw, count=1)
        normalised = normalise_space(raw_without_number)
        term_matches = {category: matches(normalised, patterns) for category, patterns in compiled.items()}
        flags = {category: bool(values) for category, values in term_matches.items()}
        pmid = PMID_RE.search(normalised)
        pmcid = PMCID_RE.search(normalised)
        doi = DOI_RE.search(normalised)
        title, authors = extract_title_and_authors(raw_without_number)
        record_no = int(start.group(1))
        rows.append(
            {
                "record_id": f"HMF3371-{record_no:06d}",
                "parser_index": index,
                "export_record_no": record_no,
                "pmid": pmid.group(1) if pmid else "",
                "pmcid": pmcid.group(1) if pmcid else "",
                "doi": doi.group(1).rstrip(".").lower() if doi else "",
                "title": title,
                "authors": authors,
                "priority_tier": priority_tier(flags),
                "term_flags": flags,
                "term_matches": term_matches,
                "input_sha256": input_hash,
                "raw_text": raw,
                "parse_warnings": [],
            }
        )
    parsing = {
        "canonical_record_count": len(rows),
        "apparent_numbered_line_starts": apparent_starts,
        "embedded_reference_like_numbered_lines": apparent_starts - len(rows),
        "first_record_no": rows[0]["export_record_no"] if rows else None,
        "last_record_no": rows[-1]["export_record_no"] if rows else None,
    }
    return rows, parsing


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--term-dictionary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--expected-record-count", type=int, default=3371)
    args = parser.parse_args()
    if not args.input.is_file() or not args.term_dictionary.is_file():
        raise SystemExit("Input export or term dictionary does not exist")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    input_hash = sha256_file(args.input)
    dictionary_hash = sha256_file(args.term_dictionary)
    dictionary = json.loads(args.term_dictionary.read_text(encoding="utf-8"))
    compiled = compile_terms(dictionary)
    rows, parsing = record_rows(args.input.read_text(encoding="utf-8", errors="replace"), compiled, input_hash)
    if parsing["canonical_record_count"] != args.expected_record_count:
        raise SystemExit(
            f"Expected {args.expected_record_count} canonical records, found {parsing['canonical_record_count']}"
        )

    write_jsonl(args.output_dir / "canonical_records.jsonl", rows)
    record_fields = [
        "record_id", "parser_index", "export_record_no", "pmid", "pmcid", "doi", "title", "authors",
        "priority_tier", "input_sha256", "parse_warnings",
    ]
    flat_rows = []
    for row in rows:
        flat = {key: row[key] for key in record_fields}
        flat["term_flags"] = json.dumps(row["term_flags"], sort_keys=True)
        flat["term_matches"] = json.dumps(row["term_matches"], ensure_ascii=False, sort_keys=True)
        flat_rows.append(flat)
    write_csv(args.output_dir / "canonical_records.csv", record_fields + ["term_flags", "term_matches"], flat_rows)

    queue_rows = [row for row in flat_rows if row["priority_tier"] != "tier_4_no_automated_priority_signal"]
    write_csv(args.output_dir / "automated_screening_queue.csv", record_fields + ["term_flags", "term_matches"], queue_rows)

    ledger_rows = []
    for row in flat_rows:
        ledger_rows.append(
            {
                "record_id": row["record_id"],
                "export_record_no": row["export_record_no"],
                "pmid": row["pmid"],
                "doi_normalized": row["doi"],
                "title": row["title"],
                "priority_tier": row["priority_tier"],
                "stage": "title_abstract",
                "record_version": "v1.0",
            }
        )
    write_csv(args.output_dir / "screening_ledger_template.csv", LEDGER_FIELDS, ledger_rows)

    counts = {tier: sum(row["priority_tier"] == tier for row in rows) for tier in sorted({row["priority_tier"] for row in rows})}
    manifest = {
        "workflow": "HMF_RCT_PublicationWorkflow_v1",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "command": " ".join(sys.argv),
        "python": sys.version,
        "platform": platform.platform(),
        "input_path": str(args.input),
        "input_sha256": input_hash,
        "term_dictionary_path": str(args.term_dictionary),
        "term_dictionary_sha256": dictionary_hash,
        "term_dictionary_version": dictionary.get("dictionary_version"),
        "parsing": parsing,
        "priority_tier_counts": counts,
        "automated_decisions_made": 0,
        "manual_screening_required_for_all_canonical_records": True,
    }
    (args.output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(rows)} canonical records and {len(queue_rows)} automated-priority records")
    print(f"Run output: {args.output_dir}")


if __name__ == "__main__":
    main()
