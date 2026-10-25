#!/usr/bin/env python3
"""Validate a dual-reviewer screening ledger before study-level synthesis.

Run without --final to obtain a completeness report during active screening.
Run with --final only after all canonical records have dual decisions, all
conflicts are resolved, and every include/exclude/linked decision has the
required controlled code and study linkage.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set

ALLOWED_DECISIONS = {"include", "exclude", "linked", "awaiting"}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def nonempty(value: str | None) -> bool:
    return bool((value or "").strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--canonical-records", required=True, type=Path)
    parser.add_argument("--decision-codes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--final", action="store_true", help="Fail if any screening action is incomplete")
    args = parser.parse_args()
    for path in (args.ledger, args.canonical_records, args.decision_codes):
        if not path.is_file():
            raise SystemExit(f"Missing required file: {path}")

    ledger = read_csv(args.ledger)
    records = read_csv(args.canonical_records)
    codes = {row["code"] for row in read_csv(args.decision_codes)}
    canonical_ids = {row["record_id"] for row in records}
    ledger_ids = [row.get("record_id", "") for row in ledger]
    errors: List[str] = []

    if len(ledger) != len(canonical_ids):
        errors.append(f"Ledger has {len(ledger)} rows; canonical input has {len(canonical_ids)} records")
    if len(set(ledger_ids)) != len(ledger_ids):
        errors.append("Ledger record_id values are not unique")
    missing_ids = canonical_ids - set(ledger_ids)
    extra_ids = set(ledger_ids) - canonical_ids
    if missing_ids:
        errors.append(f"Ledger lacks {len(missing_ids)} canonical record_id(s)")
    if extra_ids:
        errors.append(f"Ledger contains {len(extra_ids)} noncanonical record_id(s)")

    decision_counts: Counter[str] = Counter()
    reviewer_1_missing = reviewer_2_missing = conflicts = unresolved = 0
    for row in ledger:
        for key in ("reviewer_1_decision", "reviewer_2_decision", "consensus_decision"):
            value = (row.get(key) or "").strip().lower()
            if value and value not in ALLOWED_DECISIONS:
                errors.append(f"{row.get('record_id')}: invalid {key}={value!r}")
        r1 = (row.get("reviewer_1_decision") or "").strip().lower()
        r2 = (row.get("reviewer_2_decision") or "").strip().lower()
        consensus = (row.get("consensus_decision") or "").strip().lower()
        if not r1:
            reviewer_1_missing += 1
        if not r2:
            reviewer_2_missing += 1
        if r1 and r2 and r1 != r2:
            conflicts += 1
        final = consensus or (r1 if r1 and r1 == r2 else "")
        if not final:
            unresolved += 1
            continue
        decision_counts[final] += 1
        code = (row.get("consensus_reason_code") or row.get("reviewer_1_reason_code") or "").strip()
        if final in {"include", "exclude", "linked"} and not code:
            errors.append(f"{row.get('record_id')}: {final} lacks a controlled reason code")
        if code and code not in codes:
            errors.append(f"{row.get('record_id')}: unrecognized decision code {code!r}")
        if final == "include":
            if not nonempty(row.get("study_id")):
                errors.append(f"{row.get('record_id')}: included report lacks study_id")
            if not nonempty(row.get("analytic_stratum")):
                errors.append(f"{row.get('record_id')}: included report lacks analytic_stratum")
            if not nonempty(row.get("report_id")):
                errors.append(f"{row.get('record_id')}: included report lacks report_id")

    report = {
        "canonical_records": len(canonical_ids),
        "ledger_rows": len(ledger),
        "reviewer_1_missing": reviewer_1_missing,
        "reviewer_2_missing": reviewer_2_missing,
        "reviewer_disagreements": conflicts,
        "unresolved_final_decisions": unresolved,
        "final_decision_counts": dict(decision_counts),
        "validation_errors": errors,
        "ready_for_final_screening": not (errors or reviewer_1_missing or reviewer_2_missing or conflicts or unresolved),
        "final_mode": args.final,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    final_errors = list(errors)
    if args.final:
        if reviewer_1_missing:
            final_errors.append(f"{reviewer_1_missing} records lack reviewer 1 decision")
        if reviewer_2_missing:
            final_errors.append(f"{reviewer_2_missing} records lack reviewer 2 decision")
        if conflicts:
            final_errors.append(f"{conflicts} reviewer conflicts remain unresolved")
        if unresolved:
            final_errors.append(f"{unresolved} records lack a final decision")
    if final_errors:
        raise SystemExit("SCREENING VALIDATION FAILED:\n- " + "\n- ".join(final_errors))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
