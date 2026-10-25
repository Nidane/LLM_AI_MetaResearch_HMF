#!/usr/bin/env python3
"""Apply publication-level gates to linked reports, arms, and outcome data.

This script is intentionally strict: it fails if proposed meta-analysis rows
lack two-reviewer reconciliation, exact source location, verified event counts,
valid denominators, or an eligible strict-fortifier analytic stratum.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def required_columns(rows: List[Dict[str, str]], columns: Set[str], path: Path) -> None:
    if not rows:
        return
    missing = columns - set(rows[0])
    if missing:
        raise SystemExit(f"{path} lacks required columns: {sorted(missing)}")


def integer(value: str, field: str, row_id: str, errors: List[str]) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        errors.append(f"{row_id}: {field} is not an integer: {value!r}")
        return None
    if result < 0:
        errors.append(f"{row_id}: {field} is negative")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screening-report", required=True, type=Path)
    parser.add_argument("--linkage", required=True, type=Path)
    parser.add_argument("--arms", required=True, type=Path)
    parser.add_argument("--outcomes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    for path in (args.screening_report, args.linkage, args.arms, args.outcomes):
        if not path.is_file():
            raise SystemExit(f"Missing required file: {path}")

    errors: List[str] = []
    screening = json.loads(args.screening_report.read_text(encoding="utf-8"))
    if not screening.get("ready_for_final_screening"):
        errors.append("Screening ledger is not complete and dual-reviewer resolved")

    linkage = read_csv(args.linkage)
    arms = read_csv(args.arms)
    outcomes = read_csv(args.outcomes)
    required_columns(linkage, {"study_id", "report_id", "relationship", "adjudication_status"}, args.linkage)
    required_columns(arms, {"study_id", "report_id", "arm_id", "arm_category", "randomized_n", "analyzed_n", "table_page_or_section", "reconciliation_status"}, args.arms)
    required_columns(outcomes, {"study_id", "report_id", "outcome_name", "arm_id", "events", "denominator", "source_document_hash", "table_figure_page_section", "reconciliation_status", "verification_status"}, args.outcomes)

    primary_by_study: Counter[str] = Counter()
    report_to_study: Dict[str, str] = {}
    for row in linkage:
        study = row.get("study_id", "").strip()
        report = row.get("report_id", "").strip()
        if not study or not report:
            errors.append("Linkage row lacks study_id or report_id")
            continue
        if report in report_to_study and report_to_study[report] != study:
            errors.append(f"Report {report} links to multiple studies")
        report_to_study[report] = study
        if row.get("relationship", "").strip() == "primary_report":
            primary_by_study[study] += 1
        if row.get("adjudication_status", "").strip().lower() not in {"resolved", "not_applicable"}:
            errors.append(f"Linkage for report {report} is not resolved")
    for study, count in primary_by_study.items():
        if count != 1:
            errors.append(f"Study {study} has {count} primary reports; expected exactly one")

    arm_keys: Set[tuple[str, str]] = set()
    for row in arms:
        row_id = f"arm {row.get('study_id')}/{row.get('arm_id')}"
        if not row.get("study_id") or not row.get("arm_id"):
            errors.append(f"{row_id}: missing study_id or arm_id")
            continue
        arm_keys.add((row["study_id"], row["arm_id"]))
        for field in ("randomized_n", "analyzed_n"):
            if row.get(field, "").strip():
                integer(row[field], field, row_id, errors)
        if row.get("reconciliation_status", "").strip().lower() != "resolved":
            errors.append(f"{row_id}: arm extraction is not reconciled")
        if not row.get("table_page_or_section", "").strip():
            errors.append(f"{row_id}: missing exact source location")

    poolable = 0
    for row in outcomes:
        row_id = f"outcome {row.get('study_id')}/{row.get('outcome_name')}/{row.get('arm_id')}"
        key = (row.get("study_id", ""), row.get("arm_id", ""))
        if key not in arm_keys:
            errors.append(f"{row_id}: no linked arm row")
        event = integer(row.get("events", ""), "events", row_id, errors)
        denominator = integer(row.get("denominator", ""), "denominator", row_id, errors)
        if event is not None and denominator is not None and event > denominator:
            errors.append(f"{row_id}: events exceed denominator")
        if not row.get("source_document_hash", "").strip():
            errors.append(f"{row_id}: missing source document hash")
        if not row.get("table_figure_page_section", "").strip():
            errors.append(f"{row_id}: missing exact table/figure/page/section")
        if row.get("reconciliation_status", "").strip().lower() != "resolved":
            errors.append(f"{row_id}: extraction is not reconciled")
        if row.get("verification_status", "").strip().lower() != "verified":
            errors.append(f"{row_id}: outcome is not verified")
        # Strict meta-analysis eligibility is determined from the linked arms.
        categories = {a.get("arm_category", "") for a in arms if a.get("study_id") == row.get("study_id")}
        if categories and "strict_direct_fortifier_source" not in categories:
            errors.append(f"{row_id}: study does not have strict direct-fortifier arm category")
        poolable += 1

    report = {
        "linked_reports": len(linkage),
        "arms": len(arms),
        "outcome_rows": len(outcomes),
        "candidate_poolable_outcome_rows": poolable,
        "validation_errors": errors,
        "publication_ready_for_strict_meta_analysis": not errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise SystemExit("ANALYSIS-DATA VALIDATION FAILED:\n- " + "\n- ".join(errors))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
