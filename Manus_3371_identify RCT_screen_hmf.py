#!/usr/bin/env python3
"""High-sensitivity screening of a PubMed text export for HMF-vs-bovine RCT candidates.

This program is deliberately a candidate-identification tool, not an automated
systematic-review eligibility classifier. It flags records where the text
contains signals for randomisation, a human-milk intervention, a bovine/cow
comparator, and fortification. Final inclusion still requires manual review of
the title/abstract and, where needed, the full paper.

Input format
------------
PubMed's plain-text numbered export, where records begin at the start of a line
with '<integer>. '.  The provided HMF.3371.txt file contains citation-like
numbered references inside some records, so the parser deliberately preserves
all apparent boundaries for auditability.  It does not assume that a record
number is unique.

Outputs
-------
parsed_records.jsonl     all parsed chunks and extracted fields
rct_candidate_flags.tsv  high-sensitivity candidate table for manual screening
screening_summary.json   counts, search terms, and run metadata

Run example
-----------
python src/screen_hmf.py \
  --input /path/to/HMF.3371.txt \
  --output-dir output
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Pattern

# Each list is intentionally broad.  Terms are applied to the complete parsed
# record, not only the title, to minimise false negatives at the initial screen.
TERM_PATTERNS: Dict[str, List[str]] = {
    "rct": [
        r"\brandomi[sz](?:ed|ation|ing)?\b",
        r"\brandomised\b",
        r"\brandomized controlled trial\b",
        r"\brandomised controlled trial\b",
        r"\bcontrolled clinical trial\b",
        r"\bclinical trial\b",
        r"\btrial\b",
    ],
    "human": [
        r"\bhuman[ -]milk(?:[ -](?:based|derived))?[ -](?:fortifier|fortification)\b",
        r"\b(?:human[ -]milk|milk)[ -]derived[ -](?:fortifier|fortification)\b",
        r"\b(?:donor|donor[ -]milk)[ -]derived[ -](?:fortifier|fortification)\b",
        r"\bHMBF\b",
        r"\bHMDF\b",
        r"\bexclusive human milk diet\b",
        r"\bEHMD\b",
        r"\bhuman milk based diet\b",
    ],
    "bovine": [
        r"\bbovine(?:[ -]milk)?[ -](?:based|derived)?[ -]?(?:fortifier|fortification|product|products)\b",
        r"\b(?:cow'?s?|cow)[ -]milk(?:[ -](?:based|derived))?[ -](?:fortifier|fortification|product|products)\b",
        r"\bBMBF\b",
        r"\bCMDF\b",
        r"\bbovine products?\b",
        r"\bcow'?s? milk products?\b",
        r"\bpreterm formula\b",
        r"\bformula\b",
    ],
    "fortifier": [
        r"\bfortif(?:ier|iers|ication|ied|y)\b",
        r"\bmilk enrichment\b",
        r"\benrich(?:ed|ment) (?:human |breast )?milk\b",
    ],
    "outcome": [
        r"\bnecrotiz(?:ing|ed) enterocolitis\b",
        r"\bNEC\b",
        r"\bsepsis\b",
        r"\bsepticaemia\b",
        r"\bsepticemia\b",
        r"\bbloodstream infection\b",
        r"\blate[ -]onset infection\b",
        r"\blate[ -]onset sepsis\b",
    ],
    "population": [
        r"\bpreterm\b",
        r"\bpremature\b",
        r"\bvery low birth weight\b",
        r"\bVLBW\b",
        r"\bextremely low birth weight\b",
        r"\bELBW\b",
        r"\bneonat(?:e|al)\b",
    ],
}

PMID_RE = re.compile(r"\bPMID:\s*(\d+)", re.IGNORECASE)
PMCID_RE = re.compile(r"\bPMCID:\s*(PMC\d+)", re.IGNORECASE)
DOI_RE = re.compile(r"\bdoi:\s*([^\s;]+)", re.IGNORECASE)
RECORD_START_RE = re.compile(r"(?m)^(\d+)\.\s+")


def normalise_whitespace(value: str) -> str:
    """Collapse whitespace so snippets work consistently across line wrapping."""
    return re.sub(r"\s+", " ", value).strip()


def compile_patterns(patterns: Iterable[str]) -> List[Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


COMPILED_TERMS = {name: compile_patterns(patterns) for name, patterns in TERM_PATTERNS.items()}


def matched_terms(text: str, patterns: Iterable[Pattern[str]]) -> List[str]:
    """Return one normalized text match for each matched pattern."""
    matches: List[str] = []
    for pattern in patterns:
        found = pattern.search(text)
        if found:
            matches.append(found.group(0))
    return matches


def split_numbered_export(text: str) -> List[Dict[str, object]]:
    """Split the export on apparent start-of-line numbered record boundaries.

    This intentionally mirrors the original broad parser approach: the export
    can include numbered references that look like new records.  Those chunks
    remain in the all-record audit file, then are naturally eliminated by
    screening or manual review.  This is safer than silently discarding text.
    """
    starts = list(RECORD_START_RE.finditer(text))
    records: List[Dict[str, object]] = []
    for parser_index, match in enumerate(starts, start=1):
        end = starts[parser_index].start() if parser_index < len(starts) else len(text)
        raw = text[match.start():end].strip()
        records.append(
            {
                "parser_index": parser_index,
                "export_record_no": int(match.group(1)),
                "raw": raw,
            }
        )
    return records


def infer_title(raw_without_number: str) -> str:
    """Extract the first title-like paragraph after the citation paragraph.

    Plain PubMed exports do not expose a formal title field.  In this export,
    the first non-empty paragraph after the journal/citation block is typically
    the title.  This conservative heuristic is for manual triage only; the raw
    record remains the authoritative audit trail.
    """
    paragraphs = [normalise_whitespace(x) for x in re.split(r"\n\s*\n", raw_without_number) if x.strip()]
    if len(paragraphs) < 2:
        return ""
    candidates = paragraphs[1:5]
    for candidate in candidates:
        lower = candidate.lower()
        if lower.startswith("author information"):
            continue
        if lower in {"online ahead of print.", "epub ahead of print."}:
            continue
        if re.match(r"^[A-Z][A-Za-z'’\-]+\s+[A-Z]", candidate) and len(candidate) < 250:
            # likely an author line rather than a title
            continue
        return candidate
    return ""


def record_to_row(record: Dict[str, object]) -> Dict[str, object]:
    raw = str(record["raw"])
    raw_without_number = RECORD_START_RE.sub("", raw, count=1)
    text = normalise_whitespace(raw_without_number)
    pmid = PMID_RE.search(text)
    pmcid = PMCID_RE.search(text)
    doi = DOI_RE.search(text)

    term_matches = {name: matched_terms(text, patterns) for name, patterns in COMPILED_TERMS.items()}
    flags = {name: bool(matches) for name, matches in term_matches.items()}

    # Purposefully high sensitivity.  'outcome' is recorded but not required,
    # because a relevant RCT can omit NEC/sepsis from the abstract yet report it
    # in the paper's morbidity table.
    is_candidate = all(flags[key] for key in ("rct", "human", "bovine", "fortifier"))
    candidate_reason = "; ".join(
        f"{group}={', '.join(values[:3])}" for group, values in term_matches.items() if values
    )

    return {
        "parser_index": record["parser_index"],
        "export_record_no": record["export_record_no"],
        "pmid": pmid.group(1) if pmid else "",
        "pmcid": pmcid.group(1) if pmcid else "",
        "doi": doi.group(1).rstrip(".") if doi else "",
        "title_heuristic": infer_title(raw_without_number),
        "flags": flags,
        "term_matches": term_matches,
        "candidate_for_manual_rct_screen": is_candidate,
        "candidate_reason": candidate_reason,
        "raw": raw,
    }


def write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_candidates(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    fields = [
        "parser_index",
        "export_record_no",
        "pmid",
        "pmcid",
        "doi",
        "title_heuristic",
        "rct_signal",
        "human_signal",
        "bovine_signal",
        "fortifier_signal",
        "outcome_signal",
        "population_signal",
        "flags_json",
        "candidate_reason",
        "snippet",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in rows:
            flags = row["flags"]
            assert isinstance(flags, dict)
            raw = str(row["raw"])
            writer.writerow(
                {
                    "parser_index": row["parser_index"],
                    "export_record_no": row["export_record_no"],
                    "pmid": row["pmid"],
                    "pmcid": row["pmcid"],
                    "doi": row["doi"],
                    "title_heuristic": row["title_heuristic"],
                    "rct_signal": flags["rct"],
                    "human_signal": flags["human"],
                    "bovine_signal": flags["bovine"],
                    "fortifier_signal": flags["fortifier"],
                    "outcome_signal": flags["outcome"],
                    "population_signal": flags["population"],
                    "flags_json": json.dumps(flags),
                    "candidate_reason": row["candidate_reason"],
                    "snippet": normalise_whitespace(raw)[:1600],
                }
            )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="PubMed numbered plain-text export")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for TSV/JSONL outputs")
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input file does not exist: {args.input}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source = args.input.read_text(encoding="utf-8", errors="replace")
    parsed = split_numbered_export(source)
    rows = [record_to_row(record) for record in parsed]
    candidates = [row for row in rows if row["candidate_for_manual_rct_screen"]]

    write_jsonl(args.output_dir / "parsed_records.jsonl", rows)
    write_candidates(args.output_dir / "rct_candidate_flags.tsv", candidates)

    flag_counts = Counter()
    for row in rows:
        flags = row["flags"]
        assert isinstance(flags, dict)
        for key, value in flags.items():
            if value:
                flag_counts[key] += 1

    run_info = {
        "script": "screen_hmf.py",
        "script_purpose": "High-sensitivity candidate identification, not final eligibility adjudication",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(args.input),
        "input_sha256": sha256_file(args.input),
        "numbered_chunks_parsed": len(rows),
        "unique_export_record_numbers": len({row["export_record_no"] for row in rows}),
        "candidate_rule": "rct AND human AND bovine AND fortifier; outcome is not required",
        "candidate_count": len(candidates),
        "flag_counts": dict(flag_counts),
        "term_patterns": TERM_PATTERNS,
        "manual_review_required": [
            "Confirm actual random allocation and concurrent randomized comparison.",
            "Confirm preterm/VLBW population and comparator eligibility.",
            "Distinguish pure fortifier-source trials from broader EHMD/bovine-product diet trials.",
            "Identify protocols, follow-ups, reanalyses, reviews, and duplicate reports.",
            "Extract NEC/sepsis outcomes only from an appropriate primary report/full text.",
        ],
    }
    (args.output_dir / "screening_summary.json").write_text(
        json.dumps(run_info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"Parsed numbered chunks: {len(rows):,}")
    print(f"Candidate records requiring manual RCT review: {len(candidates):,}")
    print(f"Wrote: {args.output_dir / 'parsed_records.jsonl'}")
    print(f"Wrote: {args.output_dir / 'rct_candidate_flags.tsv'}")
    print(f"Wrote: {args.output_dir / 'screening_summary.json'}")


if __name__ == "__main__":
    main()
