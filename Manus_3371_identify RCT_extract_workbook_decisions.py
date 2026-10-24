#!/usr/bin/env python3
"""Export the retained manual screening decisions from the delivered workbook.

This produces CSV files that are easier to review in version control than a
binary .xlsx file.  It does not create new eligibility decisions: it preserves
what was manually entered into the reference workbook.

Run example
-----------
python src/extract_workbook_decisions.py \
  --workbook reference/HMF_RCT_extraction_for_NEC_sepsis.xlsx \
  --output-dir output
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List

from openpyxl import load_workbook


def as_text(value: Any) -> str:
    """Use a stable empty-string representation for blank Excel cells."""
    return "" if value is None else str(value).replace("\n", " ").strip()


def header_and_rows(workbook_path: Path, sheet: str) -> Iterable[Dict[str, str]]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    if sheet not in workbook.sheetnames:
        raise ValueError(f"Sheet '{sheet}' not present. Available: {workbook.sheetnames}")
    worksheet = workbook[sheet]
    header = [as_text(cell.value) for cell in next(worksheet.iter_rows(min_row=1, max_row=1))]
    for values in worksheet.iter_rows(min_row=2, values_only=True):
        row = {column: as_text(value) for column, value in zip(header, values)}
        if any(row.values()):
            yield row


def write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, str]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})
            count += 1
    return count


def classify_decision(text: str) -> str:
    low = text.lower()
    if "borderline/exclude" in low:
        return "borderline; exclude from strict preterm/VLBW fortifier-only primary analysis"
    if "direct fortifier-source" in low or "direct hmbf vs bmbf" in low:
        return "include; direct fortifier-source RCT"
    if "ehmd" in low or "human milk diet" in low:
        return "include only if protocol accepts broader EHMD/bovine-product diet comparison"
    if low.startswith("include"):
        return "include; requires outcome-table/full-text verification for quantitative pooling"
    return "see original manual decision"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.workbook.is_file():
        raise SystemExit(f"Workbook does not exist: {args.workbook}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    eligible_rows = list(header_and_rows(args.workbook, "Eligible_RCTs"))
    eligible_fields = [
        "screening_disposition",
        "inclusion_decision",
        "short_citation",
        "record_no",
        "pmid",
        "pmcid",
        "doi",
        "pubmed_title",
        "design",
        "population",
        "human_intervention",
        "comparator",
        "directness",
        "outcomes_in_abstract",
        "nec_human",
        "nec_bovine",
        "nec_definition",
        "sepsis_human",
        "sepsis_bovine",
        "sepsis_definition",
        "caveat",
    ]
    normalised_rows = []
    for row in eligible_rows:
        copied = dict(row)
        copied["screening_disposition"] = classify_decision(row.get("inclusion_decision", ""))
        normalised_rows.append(copied)

    excluded_rows = list(header_and_rows(args.workbook, "Excluded_or_secondary"))
    excluded_fields = ["status", "reason", "identifier"]

    # The underlying spreadsheet intentionally keeps exact extracted values in
    # its original wording.  These CSVs are transparent/auditable derivatives.
    n_eligible = write_csv(args.output_dir / "manual_eligible_or_borderline_decisions.csv", eligible_fields, normalised_rows)
    n_excluded = write_csv(args.output_dir / "manual_excluded_or_secondary_reports.csv", excluded_fields, excluded_rows)

    print(f"Exported {n_eligible} eligible/borderline records")
    print(f"Exported {n_excluded} excluded/secondary-report entries")


if __name__ == "__main__":
    main()
