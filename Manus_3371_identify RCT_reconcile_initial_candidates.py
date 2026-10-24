#!/usr/bin/env python3
"""Reconcile every retained original candidate against retained decision evidence.

This script is deliberately conservative.  It labels a candidate as included or
known secondary/excluded only when a matching retained workbook entry or a
specified known linked report supports that label.  It does *not* invent
record-level exclusion reasons for the remaining candidates, whose original
manual notes were lost with the prior sandbox reset.

Run example
-----------
python src/reconcile_initial_candidates.py \
  --data-dir output_example \
  --output output_example/candidate_reconciliation.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Set


# Explicitly documented reports discussed in the retained task history but not
# necessarily itemized individually in the original workbook's short exclusion
# log. They are used only for transparent report-lineage labels.
KNOWN_LINKED_REPORTS: Dict[str, Dict[str, str]] = {
    "32239968": {
        "classification": "known linked secondary report; not an independent RCT",
        "evidence_source": "Retained user/assistant discussion after the original delivery",
        "rationale": (
            "Lucas et al. 2020 is a post hoc mother's-own-milk subgroup reanalysis "
            "of the Sullivan et al. 2010 randomized trial; do not count as a separate trial."
        ),
    },
}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def pmids_from_text(value: str) -> Set[str]:
    return set(re.findall(r"\b\d{6,9}\b", value or ""))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    initial_path = args.data_dir / "initial_keyword_candidates.csv"
    eligible_path = args.data_dir / "eligible_rcts_full.csv"
    excluded_path = args.data_dir / "excluded_or_secondary.csv"
    for path in (initial_path, eligible_path, excluded_path):
        if not path.is_file():
            raise SystemExit(f"Required input missing: {path}")

    initial = read_csv(initial_path)
    eligible = {row.get("pmid", ""): row for row in read_csv(eligible_path) if row.get("pmid", "")}
    excluded = read_csv(excluded_path)

    excluded_by_pmid: Dict[str, Dict[str, str]] = {}
    for row in excluded:
        text = " ".join(row.values())
        for pmid in pmids_from_text(text):
            # If a PMID occurs in a grouped log entry, retain that exact entry
            # instead of fabricating a more granular reason.
            excluded_by_pmid[pmid] = row

    fields = [
        "num",
        "pmid",
        "doi",
        "title",
        "flags",
        "reconciliation_status",
        "retained_evidence_source",
        "retained_rationale_or_decision",
        "action_for_reviewer",
    ]
    output_rows: List[Dict[str, str]] = []
    for row in initial:
        pmid = row.get("pmid", "")
        out = {name: row.get(name, "") for name in fields[:5]}
        if pmid in eligible:
            e = eligible[pmid]
            out.update(
                {
                    "reconciliation_status": "present in retained eligible/borderline workbook table",
                    "retained_evidence_source": "Eligible_RCTs sheet",
                    "retained_rationale_or_decision": e.get("inclusion_decision", ""),
                    "action_for_reviewer": "Use the full eligible_RCTs_full.csv row and source paper before meta-analysis.",
                }
            )
        elif pmid in KNOWN_LINKED_REPORTS:
            item = KNOWN_LINKED_REPORTS[pmid]
            out.update(
                {
                    "reconciliation_status": item["classification"],
                    "retained_evidence_source": item["evidence_source"],
                    "retained_rationale_or_decision": item["rationale"],
                    "action_for_reviewer": "Keep in linked-report log; do not add a separate study to the RCT count.",
                }
            )
        elif pmid in excluded_by_pmid:
            x = excluded_by_pmid[pmid]
            out.update(
                {
                    "reconciliation_status": "present in retained excluded/secondary workbook log",
                    "retained_evidence_source": "Excluded_or_secondary sheet",
                    "retained_rationale_or_decision": f"{x.get('status', '')}: {x.get('reason', '')}",
                    "action_for_reviewer": "Do not count as an independent eligible RCT unless full review changes the protocol decision.",
                }
            )
        else:
            out.update(
                {
                    "reconciliation_status": "no individual manual adjudication retained",
                    "retained_evidence_source": "None; original manual working notes/source scripts were lost after sandbox reset",
                    "retained_rationale_or_decision": (
                        "The final workbook did not retain a record-level disposition for this initial keyword candidate. "
                        "Its absence from the eligible table is not an adequate standalone exclusion reason."
                    ),
                    "action_for_reviewer": (
                        "Re-screen title/abstract/full text against the prespecified protocol and record a fresh reason for exclusion."
                    ),
                }
            )
        output_rows.append(out)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    counts: Dict[str, int] = {}
    for row in output_rows:
        status = row["reconciliation_status"]
        counts[status] = counts.get(status, 0) + 1
    print(f"Reconciled {len(output_rows)} original candidate records -> {args.output}")
    for status, count in sorted(counts.items()):
        print(f"{count:>3}  {status}")


if __name__ == "__main__":
    main()
