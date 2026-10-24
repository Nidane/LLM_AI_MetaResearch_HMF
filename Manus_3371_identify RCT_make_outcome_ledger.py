#!/usr/bin/env python3
"""Create a long-form NEC/sepsis extraction ledger from retained workbook data.

This is a *provenance ledger*, not a new evidence extraction. It carries forward
only numerators/denominators and definitions already present in the retained
workbook and explicitly labels whether counts were reported in the abstract,
verified outside the abstract, inferred from abstract percentages, or unavailable.

The ledger deliberately leaves source table/page blank where that information
was not retained after the original sandbox reset. Do not use rows marked
"needs full-text verification" for a publication-grade meta-analysis until the
source table/page and analysis denominator have been checked.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List


OUTCOMES = (
    ("nec", "NEC"),
    ("sepsis", "Sepsis"),
    ("composite", "Composite outcome"),
)


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def provenance_for(row: Dict[str, str], outcome_key: str, has_events: bool) -> str:
    """Assign only a conservative status supported by retained wording."""
    definition = row.get(f"{outcome_key}_definition", "").lower()
    caveat = row.get("caveat", "").lower()
    if not has_events:
        return "events unavailable in retained workbook; needs full-text/registry/author verification"
    if "verified from accessible pmc" in definition:
        return "verified outside PubMed abstract; source table/page was not retained in package"
    if "from accessible article/snippet" in definition or "blocked" in caveat:
        return "provisional external article/snippet count; needs full-text table verification"
    if "derived from abstract percentages" in definition:
        return "integer reconstructed from retained abstract percentages; needs full-text verification"
    if "in abstract" in definition:
        return "reported in PubMed abstract; confirm full-text definition/denominator before pooling"
    return "retained workbook count; needs source-location verification before pooling"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eligible-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.eligible_csv.is_file():
        raise SystemExit(f"Source CSV does not exist: {args.eligible_csv}")

    source_rows = read_csv(args.eligible_csv)
    fields = [
        "report_pmid", "short_citation", "record_no", "doi", "analytic_stratum",
        "outcome", "outcome_definition", "human_events", "human_denominator",
        "bovine_events", "bovine_denominator", "analysis_population_or_denominator_note",
        "source_type", "source_table_page_section", "verification_status", "retained_caveat",
    ]
    output_rows: List[Dict[str, str]] = []
    for row in source_rows:
        directness = row.get("directness", "")
        low = directness.lower()
        if "pure fortifier-source" in low:
            stratum = "strict_direct_fortifier_source"
        elif "borderline" in low:
            stratum = "borderline_out_of_scope"
        else:
            stratum = "broader_ehmd_or_bovine_product_strategy"
        for key, label in OUTCOMES:
            human_events = row.get(f"{key}_human", "")
            bovine_events = row.get(f"{key}_bovine", "")
            definition = row.get(f"{key}_definition", "")
            has_events = bool(human_events or bovine_events)
            output_rows.append(
                {
                    "report_pmid": row.get("pmid", ""),
                    "short_citation": row.get("short_citation", ""),
                    "record_no": row.get("record_no", ""),
                    "doi": row.get("doi", ""),
                    "analytic_stratum": stratum,
                    "outcome": label,
                    "outcome_definition": definition,
                    "human_events": human_events,
                    "human_denominator": row.get("human_n", ""),
                    "bovine_events": bovine_events,
                    "bovine_denominator": row.get("bovine_n", ""),
                    "analysis_population_or_denominator_note": (
                        "Denominators reproduced from retained workbook; verify ITT vs analyzed population in full text."
                    ),
                    "source_type": "retained Excel workbook / prior screening notes",
                    "source_table_page_section": "Not retained after sandbox reset",
                    "verification_status": provenance_for(row, key, has_events),
                    "retained_caveat": row.get("caveat", ""),
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Wrote {len(output_rows)} retained-data outcome ledger rows -> {args.output}")


if __name__ == "__main__":
    main()
