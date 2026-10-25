#!/usr/bin/env python3
"""
HMBF-vs-BMBF Discovery Pipeline — how the 10 RCT shortlist was reached
======================================================================

This script documents, as runnable code, the exact process I used to narrow
3,371 PubMed records down to a candidate pool from which 10 RCTs were
hand-adjudicated as directly comparing Human-Milk-Based Fortifier (HMBF)
against Bovine/Cow-Milk-Based Fortifier (BMBF) for NEC and sepsis outcomes.

The pipeline has FIVE stages:

    STAGE 1  Parse the PubMed export into structured records.
    STAGE 2  Keyword screen for RCTs mentioning HMBF/BMBF/direct-comparison.
    STAGE 3  Author-name probe for landmark authors in the field (recovery).
    STAGE 4  Title-field probe for titles containing "human" vs "bovine/cow"
             + "fortifier" + a comparison word (recovery).
    STAGE 5  Dump the full abstract of every unique candidate for MANUAL
             adjudication by a human reviewer.

The script DOES NOT output "the 10 RCTs". It outputs the CANDIDATE POOL
(roughly 50 records) that a human must then read.

The final choice of 10 primary RCTs + 9 companion publications is a
judgment call made after reading each abstract. The adjudication criteria
are documented at the bottom of this file and in
HMBF_vs_BMBF_RCTs_Meta-analysis_Sources.xlsx .

Usage
-----
    python discovery_pipeline.py \\
        --input  /path/to/HMF_3371.txt \\
        --outdir /path/to/output_folder

Outputs
-------
    stage1_records_parsed.txt           N parsed / sanity checks
    stage2_keyword_screen_hits.txt      Record numbers surfaced by stage 2
    stage3_author_probe_hits.txt        Record numbers surfaced by stage 3
    stage4_title_probe_hits.txt         Record numbers surfaced by stage 4
    stage5_candidate_pool_abstracts.txt FULL abstracts of every unique
                                        candidate across stages 2–4,
                                        for manual review.
    discovery_log.txt                   Summary of counts per stage.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


# =============================================================================
# STAGE 1 — PARSE THE PUBMED EXPORT
# =============================================================================

def stage1_parse(input_path: Path) -> List[Dict]:
    """
    PubMed .txt exports have records separated by blank lines, each starting
    with "N. Journal..." where N is a sequential record number.

    Two traps I hit the first time and now handle:
      - Windows CRLF line endings — normalized to LF.
      - Year numbers like "2024." inside an abstract match a naive '^\\d+\\. '
        regex. Filter by requiring the number to equal the previous accepted
        number + 1, so year-numbers in prose are rejected.
    """
    raw = input_path.read_text(encoding="utf-8", errors="replace")
    content = raw.replace("\r\n", "\n").replace("\r", "\n")

    pat = re.compile(r"(?m)^(\d+)\. ")
    candidates = [(m.start(), int(m.group(1))) for m in pat.finditer(content)]

    records: List[Dict] = []
    expected = 1
    prev_pos, prev_num = None, None
    for pos, num in candidates:
        if num == expected:
            if prev_pos is not None:
                records.append({"num": prev_num, "start": prev_pos, "end": pos})
            prev_pos, prev_num = pos, num
            expected += 1
    if prev_pos is not None:
        records.append({"num": prev_num, "start": prev_pos, "end": len(content)})

    for r in records:
        r["text"] = content[r["start"]:r["end"]].strip()
        pmid_m = re.search(r"PMID:\s*(\d+)", r["text"])
        r["pmid"] = pmid_m.group(1) if pmid_m else None

    return records


# =============================================================================
# STAGE 2 — KEYWORD SCREEN
# =============================================================================
# Flag records that contain BOTH (a) an RCT-type phrase AND
# (b) at least one HMBF, BMBF, or direct-comparison phrase.

RCT_PHRASES = [
    "randomized controlled trial", "randomised controlled trial",
    "randomized control trial",    "randomised control trial",     # typo variant
    "randomized clinical trial",   "randomised clinical trial",
    "randomized trial",            "randomised trial",
    "randomly assigned",           "randomly allocated",
    "randomized to receive",       "randomised to receive",
    "randomized to",               "randomised to",                # catches Mizuno 2026
    "were randomized",             "were randomised",
    "pilot randomized",            "pilot randomised",
    "multicenter randomized",      "multicentre randomised",
    "randomization",               "randomisation",
    "random assignment",           "random allocation",
    "double-blind",                "double blind",
    "triple-blind",                "triple blind",
]

HMBF_TERMS = [
    "human milk-based fortifier",  "human-milk-based fortifier",
    "human milk based fortifier",
    "human milk-derived fortifier","human-milk-derived fortifier",
    "human milk derived fortifier",
    "human-based fortifier",       "human based fortifier",
    "human-derived fortifier",     "human derived fortifier",
    "donor milk-derived fortifier","donor-derived fortifier",
    "donor milk derived fortifier",
    "human milk-based human milk fortifier",
    "human-milk-based human milk fortifier",
    "donor human milk-based human milk fortifier",
    "donor human milk-derived fortifier",
    "exclusive human milk diet",   "exclusively human milk-based",
    "exclusive human milk-based diet",
    "prolacta", "prolact",          # brand
    "h2mf", "hmbf", "hmdf", "phmf", # common abbreviations
]

BMBF_TERMS = [
    "bovine milk-based fortifier", "bovine-milk-based fortifier",
    "bovine milk based fortifier",
    "bovine milk-derived fortifier","bovine-milk-derived fortifier",
    "bovine milk derived fortifier",
    "bovine-based fortifier",       "bovine based fortifier",
    "bovine-derived fortifier",     "bovine derived fortifier",
    "bovine fortifier",             "bovine human milk fortifier",
    "bovine-based human milk fortifier",
    "bovine milk-based human milk fortifier",
    "cow milk-based fortifier",     "cow's milk-based fortifier",
    "cow milk based fortifier",     "cow's milk based fortifier",
    "cow milk-derived fortifier",   "cow's milk-derived fortifier",
    "cow milk derived fortifier",   "cow's milk derived fortifier",
    "cow's milk fortifier",         "cow milk fortifier",
    "bovine whey protein fortifier","bovine whey fortifier",
    "bmbf", "bmdf", "cmdf", "pbmf", "bhmf",
]

DIRECT_COMPARISON_PHRASES = [
    "human milk-based fortifier vs",   "human milk-based fortifier versus",
    "human milk-derived fortifier vs", "human milk-derived fortifier versus",
    "human milk fortifier vs bovine",  "human milk fortifier versus bovine",
    "human and bovine milk-based fortifiers",
    "human or bovine milk-based fortifiers",
    "human versus bovine milk",        "human vs bovine milk",
    "human milk-derived versus bovine milk-derived",
    "human-derived breast milk fortifier",
    "exclusively human milk-based diet",
]


def _lc_contains_any(text_lc: str, terms: List[str]) -> List[str]:
    return [t for t in terms if t in text_lc]


def stage2_keyword_screen(records: List[Dict]) -> List[Dict]:
    """Return the subset of records flagged by the keyword screen."""
    hits = []
    for r in records:
        t = r["text"].lower()
        rct = _lc_contains_any(t, RCT_PHRASES)
        hmbf = _lc_contains_any(t, HMBF_TERMS)
        bmbf = _lc_contains_any(t, BMBF_TERMS)
        direct = _lc_contains_any(t, DIRECT_COMPARISON_PHRASES)
        if rct and (hmbf or bmbf or direct):
            r2 = dict(r)
            r2.update({"rct": rct, "hmbf": hmbf, "bmbf": bmbf, "direct": direct,
                       "surfaced_by": "stage2_keyword"})
            hits.append(r2)
    return hits


# =============================================================================
# STAGE 3 — AUTHOR-NAME RECOVERY PROBE
# =============================================================================
# The keyword screen can miss landmark trials when the abstract uses local
# shorthand (e.g. Sullivan 2010 uses "HM100/HM40/BOV" instead of the full
# phrase "human milk-based fortifier"). This probe searches for authors known
# in the field. A matching record is only treated as a candidate if it also
# contains SOME RCT signal — pure review/editorial hits are dropped.

LANDMARK_AUTHORS = [
    # Author-last-name tokens; case-insensitive substring match on text
    "sullivan s",      # Sullivan 2010 — landmark 3-arm RCT
    "cristofalo",      # Cristofalo 2013
    "o'connor dl",     # O'Connor 2018 OptiMoM
    "embleton n",      # Embleton 2023
    "mizuno k",        # Mizuno 2026
    "jensen gb",       # Jensen 2024 N-forte
    "berrington j",    # Berrington 2025
    "kumbhare",        # Kumbhare 2022
    "polberger",       # Polberger 1999
    "hagelberg",       # Hagelberg 1990
    "lucas a",         # Lucas 2020 subgroup re-analysis
    "ghandehari",      # Ghandehari 2012 re-analysis
    "hopperton",       # Hopperton 2019 OptiMoM 18-mo
    "asbury",          # Asbury 2022 OptiMoM microbiome
    "yeung t",         # Yeung 2023 OptiMoM cost
    "uthaya",          # Uthaya 2022 UK body composition
    "hair ab",         # Hair cream studies (ultimately excluded)
    "boehm g",         # Boehm 1993 (ultimately excluded)
    "moro ge",         # Moro 1991 (ultimately excluded)
    "salas aa",        # Salas trials (different comparison)
]


def stage3_author_probe(records: List[Dict], already: Set[int]) -> List[Dict]:
    """Return records that match a landmark-author token AND contain an RCT
    signal, excluding records already found by stage 2."""
    hits = []
    for r in records:
        if r["num"] in already:
            continue
        t = r["text"].lower()
        author_match = next((a for a in LANDMARK_AUTHORS if a in t), None)
        if not author_match:
            continue
        rct = _lc_contains_any(t, RCT_PHRASES)
        if not rct:
            continue
        r2 = dict(r)
        r2.update({"author_matched": author_match, "rct": rct,
                   "surfaced_by": "stage3_author_probe"})
        hits.append(r2)
    return hits


# =============================================================================
# STAGE 4 — TITLE-FIELD RECOVERY PROBE
# =============================================================================
# Some older trials (Hagelberg 1990, Boehm 1993, Moro 1991) describe
# "human milk protein" vs "cow's milk protein" or similar in the TITLE but
# never use the modern phrase "human milk-based fortifier" in the abstract.
# This probe scans titles only, looking for "human" AND ("bovine" OR "cow")
# AND "fortif" AND some comparison word, then returns those records.

def _extract_title(text: str) -> str:
    """A PubMed record's title typically sits on the lines after the journal
    citation line and before the first blank line. Grab a generous window."""
    lines = text.split("\n")
    title_lines = []
    seen_blank = False
    for i, line in enumerate(lines):
        if i == 0:  # journal citation line
            continue
        if not line.strip():
            if title_lines:
                break
            seen_blank = True
            continue
        if seen_blank:
            title_lines.append(line.strip())
    return " ".join(title_lines).lower()


COMPARISON_WORDS = ["versus", " vs ", "vs.", "compared", "comparison",
                    " and ", " or "]


def stage4_title_probe(records: List[Dict], already: Set[int]) -> List[Dict]:
    hits = []
    for r in records:
        if r["num"] in already:
            continue
        title = _extract_title(r["text"])
        if "human" not in title:
            continue
        if not ("bovine" in title or "cow" in title):
            continue
        if "fortif" not in title and "protein" not in title:
            continue
        if not any(cw in title for cw in COMPARISON_WORDS):
            continue
        r2 = dict(r)
        r2.update({"title": title, "surfaced_by": "stage4_title_probe"})
        hits.append(r2)
    return hits


# =============================================================================
# STAGE 5 — DUMP CANDIDATE POOL FOR MANUAL ADJUDICATION
# =============================================================================

MANUAL_ADJUDICATION_CRITERIA = """
MANUAL ADJUDICATION CRITERIA  (applied to every candidate in stage 5)
=====================================================================

For each candidate abstract, ask these questions in order. If the answer to
ANY is "no" or "unclear in a way that disqualifies the record", the record
is EXCLUDED.

(1) Is this an original research report (not a review, meta-analysis,
    protocol-only paper, commentary, letter, erratum, or conference abstract)?
    - Reviews / meta-analyses -> EXCLUDE (but note for background).
    - Protocols without results -> EXCLUDE (but keep as companion if the
      main trial is included).

(2) Is the study a Randomized Controlled Trial?
    - Must have "randomized/randomised" or equivalent allocation.
    - Retrospective cohort, prospective cohort without randomization,
      quality-improvement project, historical-control study -> EXCLUDE.

(3) Does one arm receive a Human-Milk-Based (or human-milk-derived) Fortifier?
    - Prolacta / H2MF / HMDF / HMBF / "human milk-based human milk fortifier"
      all qualify.
    - "Exclusive human milk diet" qualifies IF the fortifier used is itself
      human-milk-derived.
    - Donkey-milk-derived fortifier (Fortilat trials) -> EXCLUDE.
    - Human milk + HM-derived CREAM where both arms have HMBF -> EXCLUDE.

(4) Does the comparator arm receive a Bovine/Cow-Milk-Based Fortifier?
    - Standard commercial powdered or liquid HMFs qualify.
    - Bovine COLOSTRUM (intact) as a comparator -> EXCLUDE (different product).
    - "Unfortified" comparator -> EXCLUDE (fortified-vs-unfortified question).
    - "Different timing / different protein target" of the same BMBF
      -> EXCLUDE (dosing/timing question).

(5) Is this the MAIN report of the trial, or a sub-study / follow-up?
    - Main report -> primary RCT.
    - Protocol, long-term follow-up, substudy, cost analysis, corrigendum,
      subgroup re-analysis of the same cohort -> COMPANION PUBLICATION
      (do not double-count in the meta-analysis).

(6) Does the trial report NEC and/or sepsis in the abstract OR plausibly in
    the full text?
    - Core trial if abstract clearly reports NEC and/or sepsis.
    - Still include if the design and population plausibly recorded these
      outcomes (full-text retrieval needed).
    - Older protein-only fortifier RCTs (Hagelberg 1990, Polberger 1999,
      Boehm 1993, Moro 1991) typically do NOT report NEC/sepsis — flag as
      "limited usefulness, may contribute zero events".

Borderline rules I applied:
    - Trials where the comparator arm uses preterm formula WHEN MOM is
      insufficient (Sullivan 2010, Cristofalo 2013, Embleton 2023, Mizuno
      2026) are INCLUDED, because every published HMBF-vs-BMBF meta-analysis
      includes them. The milk-base mismatch is a sensitivity-analysis issue,
      not an inclusion issue.
    - Trials where BOTH arms have an identical human milk base and only the
      fortifier source differs (O'Connor 2018, Jensen 2024, Berrington 2025,
      Kumbhare 2022, Hagelberg 1990, Polberger 1999) are the "cleanest"
      HMBF-vs-BMBF comparisons.
"""


def stage5_dump_candidates(all_candidates: List[Dict], out_path: Path) -> None:
    """Write the full abstract of every unique candidate to a single file
    for human review. Sorted by record number, oldest-first."""
    seen = set()
    unique = []
    for c in all_candidates:
        if c["num"] in seen:
            continue
        seen.add(c["num"])
        unique.append(c)
    unique.sort(key=lambda r: r["num"])

    with out_path.open("w", encoding="utf-8") as f:
        f.write("CANDIDATE POOL FOR MANUAL ADJUDICATION\n")
        f.write("=" * 100 + "\n")
        f.write(f"Total unique candidates: {len(unique)}\n")
        f.write("Read each abstract. Apply the criteria in\n"
                "MANUAL_ADJUDICATION_CRITERIA (see discovery_pipeline.py).\n")
        f.write("=" * 100 + "\n\n")

        for c in unique:
            f.write("=" * 100 + "\n")
            f.write(f"Record #{c['num']} | PMID {c.get('pmid','?')} | "
                    f"surfaced by: {c['surfaced_by']}\n")
            if c.get("rct"):
                f.write(f"  RCT phrases     : {c['rct']}\n")
            if c.get("hmbf"):
                f.write(f"  HMBF terms      : {c['hmbf']}\n")
            if c.get("bmbf"):
                f.write(f"  BMBF terms      : {c['bmbf']}\n")
            if c.get("direct"):
                f.write(f"  Direct-comp.    : {c['direct']}\n")
            if c.get("author_matched"):
                f.write(f"  Author matched  : {c['author_matched']}\n")
            if c.get("title"):
                f.write(f"  Title (lower)   : {c['title']}\n")
            f.write("-" * 100 + "\n")
            f.write(c["text"][:4000])
            f.write("\n\n")


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    args = ap.parse_args()

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1
    args.outdir.mkdir(parents=True, exist_ok=True)

    log_lines = []

    # ---- STAGE 1 ----
    print("[Stage 1] Parsing records ...")
    records = stage1_parse(args.input)
    pmid_count = sum(1 for r in records if r["pmid"])
    msg = f"  Parsed {len(records)} records; {pmid_count} contain a PMID."
    print(msg); log_lines.append("[Stage 1] " + msg)
    (args.outdir / "stage1_records_parsed.txt").write_text(msg + "\n")

    # ---- STAGE 2 ----
    print("[Stage 2] Keyword screen (RCT + HMBF/BMBF/direct-comparison) ...")
    stage2 = stage2_keyword_screen(records)
    s2_nums = sorted(r["num"] for r in stage2)
    msg = f"  {len(stage2)} records flagged by keyword screen."
    print(msg); log_lines.append("[Stage 2] " + msg)
    (args.outdir / "stage2_keyword_screen_hits.txt").write_text(
        f"{msg}\nRecord numbers:\n" + "\n".join(f"  #{n}" for n in s2_nums) + "\n"
    )

    # ---- STAGE 3 ----
    print("[Stage 3] Author-name recovery probe ...")
    already = {r["num"] for r in stage2}
    stage3 = stage3_author_probe(records, already)
    s3_nums = sorted(r["num"] for r in stage3)
    msg = f"  {len(stage3)} ADDITIONAL records recovered by author-name probe."
    print(msg); log_lines.append("[Stage 3] " + msg)
    (args.outdir / "stage3_author_probe_hits.txt").write_text(
        f"{msg}\nRecord numbers:\n" + "\n".join(
            f"  #{r['num']}  (matched '{r['author_matched']}')" for r in stage3
        ) + "\n"
    )

    # ---- STAGE 4 ----
    print("[Stage 4] Title-field recovery probe ...")
    already |= {r["num"] for r in stage3}
    stage4 = stage4_title_probe(records, already)
    s4_nums = sorted(r["num"] for r in stage4)
    msg = f"  {len(stage4)} ADDITIONAL records recovered by title-field probe."
    print(msg); log_lines.append("[Stage 4] " + msg)
    (args.outdir / "stage4_title_probe_hits.txt").write_text(
        f"{msg}\nRecord numbers:\n" + "\n".join(f"  #{n}" for n in s4_nums) + "\n"
    )

    # ---- STAGE 5 ----
    print("[Stage 5] Writing candidate-pool abstracts for manual review ...")
    all_candidates = stage2 + stage3 + stage4
    pool_path = args.outdir / "stage5_candidate_pool_abstracts.txt"
    stage5_dump_candidates(all_candidates, pool_path)
    unique_pool_size = len({c["num"] for c in all_candidates})
    msg = f"  {unique_pool_size} unique candidates written to {pool_path.name}"
    print(msg); log_lines.append("[Stage 5] " + msg)

    # ---- Log ----
    log_path = args.outdir / "discovery_log.txt"
    with log_path.open("w", encoding="utf-8") as f:
        f.write("HMBF-vs-BMBF discovery pipeline log\n")
        f.write("=" * 60 + "\n\n")
        for line in log_lines:
            f.write(line + "\n")
        f.write("\n")
        f.write("=" * 60 + "\n")
        f.write("Next step: open stage5_candidate_pool_abstracts.txt and\n")
        f.write("apply the MANUAL_ADJUDICATION_CRITERIA documented in\n")
        f.write("discovery_pipeline.py to classify each candidate as:\n")
        f.write("  - PRIMARY RCT (comparing HMBF vs BMBF on NEC/sepsis)\n")
        f.write("  - COMPANION publication of a primary RCT\n")
        f.write("  - EXCLUDED (with reason)\n")

    print("\nDone. Open stage5_candidate_pool_abstracts.txt and apply the")
    print("MANUAL_ADJUDICATION_CRITERIA (see this script) to each candidate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
