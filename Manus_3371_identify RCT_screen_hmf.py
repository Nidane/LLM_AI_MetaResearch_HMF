#!/usr/bin/env python3
"""High-sensitivity screening of a PubMed text export for HMF-vs-bovine RCT candidates.

This program is a transparent *candidate-identification* tool, not an automated
systematic-review eligibility classifier. It flags records with randomisation,
human-milk intervention, bovine/cow comparator, fortification, preterm-population,
and NEC/sepsis signals. Final inclusion must be adjudicated from the report and,
where needed, its full text.

The supplied export is numbered sequentially from 1 to 3,371, but includes
citation-like numbered reference lines inside some records. By default the parser
uses the sequential numbering to extract exactly the 3,371 canonical records. A
legacy all-numbered mode is available only for comparison/audit and will split
such embedded references into extra chunks.

Outputs
-------
parsed_records.jsonl       one row per parsed record, raw text retained
rct_candidate_flags.tsv    broad RCT manual-screening queue, with priority signals
specific_term_hits.tsv     all records with a human-fortifier/EHMD term
screening_summary.json     terms, rules, input hash, parsing details, and counts

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
from typing import Dict, Iterable, List, Pattern, Tuple

# Lists are intentionally broad. Terms are evaluated against complete records,
# not titles only, to reduce false-negative risk at initial screening.
TERM_PATTERNS: Dict[str, List[str]] = {
    "rct": [
        r"\brandomi[sz](?:ed|ation|ing)?\b",
        r"\brandomly (?:assigned|allocated)\b",
        r"\brandom allocation\b",
        r"\brandomised controlled trial\b",
        r"\brandomized controlled trial\b",
        r"\bcontrolled clinical trial\b",
        r"\bclinical trial\b",
        r"\btrial\b",
    ],
    "human": [
        r"\bhuman[ -]milk(?:[ -](?:based|derived))?[ -](?:fortifier|fortification)\b",
        r"\bhuman[ -]derived[ -](?:fortifier|fortification)\b",
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
ABSTRACT_LABELS = re.compile(
    r"^(?:abstract|background|objective|objectives|design|methods?|results?|conclusions?|"
    r"aim|introduction|purpose|setting|participants?|intervention|main outcome measures?):",
    re.IGNORECASE,
)


def normalise_whitespace(value: str) -> str:
    """Collapse whitespace so textual snippets and comparisons remain stable."""
    return re.sub(r"\s+", " ", value).strip()


def compile_patterns(patterns: Iterable[str]) -> List[Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


COMPILED_TERMS = {name: compile_patterns(patterns) for name, patterns in TERM_PATTERNS.items()}


def matched_terms(text: str, patterns: Iterable[Pattern[str]]) -> List[str]:
    """Return a unique normalized match for each matching search pattern."""
    matches: List[str] = []
    for pattern in patterns:
        found = pattern.search(text)
        if found:
            value = found.group(0)
            if value not in matches:
                matches.append(value)
    return matches


def numbered_starts(text: str) -> List[re.Match[str]]:
    return list(RECORD_START_RE.finditer(text))


def split_canonical_export(text: str) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
    """Extract sequentially numbered canonical records while ignoring inner references.

    The input's true records run 1, 2, ..., N. A reference numbered '1.' within
    record 100 does not equal the next expected number (101), so it is safely
    retained inside record 100 rather than treated as a new record.
    """
    all_starts = numbered_starts(text)
    canonical_starts: List[re.Match[str]] = []
    expected = 1
    for match in all_starts:
        if int(match.group(1)) == expected:
            canonical_starts.append(match)
            expected += 1

    if not canonical_starts or int(canonical_starts[0].group(1)) != 1:
        raise ValueError("Could not find the required first canonical record '1.'")

    records: List[Dict[str, object]] = []
    for index, match in enumerate(canonical_starts, start=1):
        end = canonical_starts[index].start() if index < len(canonical_starts) else len(text)
        records.append(
            {
                "parser_index": index,
                "export_record_no": int(match.group(1)),
                "raw": text[match.start():end].strip(),
            }
        )
    info = {
        "apparent_numbered_starts": len(all_starts),
        "canonical_records": len(records),
        "embedded_reference_like_starts_ignored": len(all_starts) - len(records),
        "next_expected_record_number": expected,
    }
    return records, info


def split_all_numbered_chunks(text: str) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
    """Legacy audit mode that treats every start-of-line number as a boundary."""
    starts = numbered_starts(text)
    records: List[Dict[str, object]] = []
    for parser_index, match in enumerate(starts, start=1):
        end = starts[parser_index].start() if parser_index < len(starts) else len(text)
        records.append(
            {
                "parser_index": parser_index,
                "export_record_no": int(match.group(1)),
                "raw": text[match.start():end].strip(),
            }
        )
    return records, {
        "apparent_numbered_starts": len(starts),
        "canonical_records": None,
        "embedded_reference_like_starts_ignored": 0,
        "next_expected_record_number": None,
    }


def infer_title(raw_without_number: str) -> str:
    """Conservatively infer a title from plain PubMed export paragraphs.

    This is a triage convenience only. The raw record is preserved and is the
    audit source when title parsing is imperfect.
    """
    paragraphs = [normalise_whitespace(x) for x in re.split(r"\n\s*\n", raw_without_number) if x.strip()]
    if len(paragraphs) < 2:
        return ""
    for candidate in paragraphs[1:7]:
        lower = candidate.lower()
        if lower.startswith("author information") or ABSTRACT_LABELS.match(candidate):
            continue
        if lower in {"online ahead of print.", "epub ahead of print."}:
            continue
        # An author line generally begins "Surname X" and has no sentence-like
        # title ending. This check is intentionally narrow to avoid title loss.
        if re.match(r"^[A-Z][A-Za-z'’\-]+\s+[A-Z](?:\([^)]*\))?[,;]", candidate):
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

    # Broad queue: not requiring outcome (often omitted from abstracts) nor an
    # explicitly named bovine product (sometimes only in full text). Directness
    # is supplied as a separate priority variable instead of a hidden filter.
    candidate_for_manual_rct_screen = flags["rct"] and flags["human"] and flags["fortifier"]
    direct_comparator_signal = candidate_for_manual_rct_screen and flags["bovine"]
    outcome_signal = candidate_for_manual_rct_screen and flags["outcome"]
    high_priority_direct_candidate = direct_comparator_signal and flags["population"]

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
        "candidate_for_manual_rct_screen": candidate_for_manual_rct_screen,
        "direct_comparator_signal": direct_comparator_signal,
        "outcome_signal_in_abstract": outcome_signal,
        "high_priority_direct_candidate": high_priority_direct_candidate,
        "candidate_reason": candidate_reason,
        "raw": raw,
    }


def write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def triage_row(row: Dict[str, object]) -> Dict[str, object]:
    """Flatten a parsed row for a readable, auditable tab-separated table."""
    flags = row["flags"]
    assert isinstance(flags, dict)
    raw = str(row["raw"])
    return {
        "parser_index": row["parser_index"],
        "export_record_no": row["export_record_no"],
        "pmid": row["pmid"],
        "pmcid": row["pmcid"],
        "doi": row["doi"],
        "title_heuristic": row["title_heuristic"],
        "manual_rct_screen": row["candidate_for_manual_rct_screen"],
        "direct_comparator_signal": row["direct_comparator_signal"],
        "outcome_signal_in_abstract": row["outcome_signal_in_abstract"],
        "high_priority_direct_candidate": row["high_priority_direct_candidate"],
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


def write_tsv(path: Path, rows: Iterable[Dict[str, object]]) -> int:
    fields = [
        "parser_index", "export_record_no", "pmid", "pmcid", "doi", "title_heuristic",
        "manual_rct_screen", "direct_comparator_signal", "outcome_signal_in_abstract",
        "high_priority_direct_candidate", "rct_signal", "human_signal", "bovine_signal",
        "fortifier_signal", "outcome_signal", "population_signal", "flags_json",
        "candidate_reason", "snippet",
    ]
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(triage_row(row))
            count += 1
    return count


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
    parser.add_argument(
        "--parse-mode", choices=("canonical", "all-numbered"), default="canonical",
        help="canonical keeps sequential export records intact; all-numbered is legacy/audit mode",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input file does not exist: {args.input}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = args.input.read_text(encoding="utf-8", errors="replace")

    if args.parse_mode == "canonical":
        parsed, parsing_info = split_canonical_export(source)
    else:
        parsed, parsing_info = split_all_numbered_chunks(source)
    rows = [record_to_row(record) for record in parsed]

    broad_candidates = [row for row in rows if row["candidate_for_manual_rct_screen"]]
    direct_candidates = [row for row in broad_candidates if row["direct_comparator_signal"]]
    term_hits = [row for row in rows if row["flags"]["human"]]

    write_jsonl(args.output_dir / "parsed_records.jsonl", rows)
    candidate_count = write_tsv(args.output_dir / "rct_candidate_flags.tsv", broad_candidates)
    term_hit_count = write_tsv(args.output_dir / "specific_term_hits.tsv", term_hits)

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
        "parse_mode": args.parse_mode,
        "parsing": parsing_info,
        "candidate_rule": "broad manual RCT queue: rct AND human AND fortifier",
        "direct_comparator_priority_rule": "broad queue AND bovine",
        "outcome_is_not_required": True,
        "broad_manual_candidate_count": candidate_count,
        "direct_comparator_signal_count": len(direct_candidates),
        "human_term_hit_count": term_hit_count,
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

    print(f"Parsed canonical records: {len(rows):,}")
    print(f"Broad candidate records requiring manual RCT review: {candidate_count:,}")
    print(f"Of these, explicit bovine/cow comparator signal: {len(direct_candidates):,}")
    print(f"Human-fortifier/EHMD term hits: {term_hit_count:,}")
    print(f"Wrote: {args.output_dir / 'parsed_records.jsonl'}")
    print(f"Wrote: {args.output_dir / 'rct_candidate_flags.tsv'}")
    print(f"Wrote: {args.output_dir / 'specific_term_hits.tsv'}")
    print(f"Wrote: {args.output_dir / 'screening_summary.json'}")


if __name__ == "__main__":
    main()
