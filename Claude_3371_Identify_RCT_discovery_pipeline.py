#!/usr/bin/env python3
"""
HMBF-vs-BMBF Discovery Pipeline
================================

Purpose
-------
Deterministic Python pipeline that reduces a PubMed .txt export of thousands of
records to a smaller candidate pool for MANUAL eligibility adjudication, in the
context of a systematic review comparing Human-Milk-Based Fortifier (HMBF)
versus Bovine/Cow-Milk-Based Fortifier (BMBF) on NEC and sepsis in preterm
infants.

The pipeline has five stages:

    STAGE 1  Parse the PubMed export into structured records, with explicit
             sanity checks (expected count, one PMID per record, no duplicates,
             no multi-PMID blocks).
    STAGE 2  Keyword screen for records that contain BOTH an RCT phrase AND
             an HMBF, BMBF, or direct-comparison phrase. Matching is done on a
             WHITESPACE-NORMALIZED, lowercased copy of each record so that
             line-wrapped phrases are not missed.
    STAGE 3  Author-name recovery probe for landmark authors identified
             during corpus screening (see provenance note below).
    STAGE 4  Title-field recovery probe for titles containing "human" +
             ("bovine" or "cow") + ("fortif" or "protein") + a comparison word.
    STAGE 5  Dump the FULL text of every unique candidate (no truncation) for
             manual review, together with a text file of the adjudication
             criteria to apply.

Provenance of the LANDMARK_AUTHORS list
---------------------------------------
This list was built DURING screening of this specific corpus. It was NOT
assembled from a priori expert knowledge independent of the corpus. Each
author token in the list was added because it corresponded to a record that
other stages had surfaced or that was found during manual browsing of the
corpus. The list is therefore corpus-specific; applying this script to a
different search set would require re-building the list from scratch.

What this script does NOT establish
-----------------------------------
This script is a deterministic Python program. It performs no LLM, browser,
or external API calls. The classifications in the Excel workbook produced by
the companion script `hmbf_vs_bmbf_pipeline.py` were decided by a human
reviewer reading each flagged abstract. The present script makes those
decisions AUDITABLE (anyone can re-run it and see the same candidate pool
emerge from the same corpus), but it does NOT, on its own, prove what
process was used to reach the final shortlist in any prior interactive
session. The adjudication criteria in `MANUAL_ADJUDICATION_CRITERIA` below
reflect judgments made after reading the corpus; the final shortlist
requires human application of those criteria to the stage-5 output.

Usage
-----
    python discovery_pipeline.py \\
        --input    /path/to/HMF_3371.txt \\
        --outdir   /path/to/output_folder \\
        [--expected-records 3371]

Outputs
-------
    stage1_parse_report.txt             Parser self-check report.
    stage2_keyword_screen_hits.txt      Records surfaced by keyword screen.
    stage3_author_probe_hits.txt        Records surfaced by author probe.
    stage4_title_probe_hits.txt         Records surfaced by title probe.
    stage5_candidate_pool_records.txt   FULL text of every unique candidate.
    adjudication_criteria.txt           The criteria to apply to stage 5.
    discovery_log.txt                   Per-stage counts.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple


# =============================================================================
# UTILITY — WHITESPACE-NORMALIZED LOWERCASE COPY
# =============================================================================
# Many PubMed abstract phrases wrap across newlines (e.g. "randomized\ncontrolled
# trial"). A naive substring search misses these. We therefore keep two copies
# of each record's text: `text` (original, for display) and `text_norm` (lower-
# cased, with ALL whitespace runs collapsed to a single space, for matching).

_WS_RUN = re.compile(r"\s+")


def normalize_for_match(text: str) -> str:
    """Lowercase, then collapse every run of whitespace (including newlines)
    to a single space. This is the form keyword/phrase patterns are matched
    against so that line-wrapped phrases still match."""
    return _WS_RUN.sub(" ", text.lower()).strip()


# =============================================================================
# STAGE 1 — PARSE THE PUBMED EXPORT (with explicit sanity checks)
# =============================================================================

def stage1_parse(
    input_path: Path,
    expected_records: int = None,
) -> Tuple[List[Dict], str]:
    """
    Parse the PubMed .txt export into a list of records.

    The parser is DEFENSIVE. It:
      - Normalizes CRLF/CR line endings to LF.
      - Finds all lines starting with "N. " where N is an integer. These are
        candidate record starts. Records in the file begin at 1 and increase
        by exactly 1 each time; year-numbers inside abstracts (e.g. "2024.")
        do not form a strictly increasing +1 sequence and are rejected.
      - Reports multiple sanity checks: expected record count match, number
        of "^N. " candidates NOT selected (likely year-numbers inside prose),
        number of PMID lines in the raw file vs the parsed records, number of
        records with zero PMIDs, number of records with MULTIPLE PMID lines
        (which signals the parser merged two records), and any duplicate PMIDs.
      - These checks are REPORTED in the returned string. For this task the
        caller prints them and continues; a stricter caller could abort on
        any mismatch.

    Parameters
    ----------
    input_path : Path
        PubMed export file (plain text).
    expected_records : int, optional
        If provided, the parse report flags any mismatch.

    Returns
    -------
    records : list of dict
        Each dict has: num (int), start (int), end (int), text (str, original
        with line breaks preserved), text_norm (str, lowercased + whitespace-
        normalized, used for substring matching), pmid (str or None).
    report : str
        Human-readable sanity-check report.
    """
    raw = input_path.read_text(encoding="utf-8", errors="replace")
    content = raw.replace("\r\n", "\n").replace("\r", "\n")

    # All raw PMIDs in the file (used to cross-check parsing)
    all_raw_pmids = re.findall(r"^PMID:\s*(\d+)", content, flags=re.MULTILINE)

    # All "^N. " candidate record starts
    candidate_pat = re.compile(r"(?m)^(\d+)\. ")
    candidates = [(m.start(), int(m.group(1))) for m in candidate_pat.finditer(content)]
    n_candidates_total = len(candidates)

    # Keep only strictly-increasing-by-1 candidates (reject year-numbers)
    records: List[Dict] = []
    expected_num = 1
    prev_pos, prev_num = None, None
    rejected = []
    for pos, num in candidates:
        if num == expected_num:
            if prev_pos is not None:
                records.append({"num": prev_num, "start": prev_pos, "end": pos})
            prev_pos, prev_num = pos, num
            expected_num += 1
        else:
            rejected.append((pos, num))
    if prev_pos is not None:
        records.append({"num": prev_num, "start": prev_pos, "end": len(content)})

    # Attach text + text_norm + pmid to each record and flag anomalies
    pmids_seen: List[str] = []
    no_pmid: List[int] = []
    multi_pmid: List[Tuple[int, int]] = []
    for r in records:
        r["text"] = content[r["start"]:r["end"]].strip()
        r["text_norm"] = normalize_for_match(r["text"])
        pmids_in_rec = re.findall(r"^PMID:\s*(\d+)", r["text"], flags=re.MULTILINE)
        if len(pmids_in_rec) == 0:
            r["pmid"] = None
            no_pmid.append(r["num"])
        elif len(pmids_in_rec) == 1:
            r["pmid"] = pmids_in_rec[0]
            pmids_seen.append(pmids_in_rec[0])
        else:
            # Multiple PMIDs in one parsed block => the parser probably merged
            # two records. Flag it; use the first PMID.
            r["pmid"] = pmids_in_rec[0]
            multi_pmid.append((r["num"], len(pmids_in_rec)))
            pmids_seen.extend(pmids_in_rec)

    # Duplicates
    pmid_counts = Counter(pmids_seen)
    duplicate_pmids = [p for p, c in pmid_counts.items() if c > 1]

    # Build the parse-report string
    lines: List[str] = []
    lines.append("STAGE 1 PARSE REPORT")
    lines.append("=" * 60)
    lines.append(f"Records parsed .......................... {len(records)}")
    if expected_records is not None:
        ok = "OK" if len(records) == expected_records else "MISMATCH"
        lines.append(f"Records expected ........................ {expected_records}   [{ok}]")
    lines.append(f"Raw '^N. ' line-start matches found ..... {n_candidates_total}")
    lines.append(f"Of those, rejected as year-numbers ...... {len(rejected)}")
    lines.append(f"Raw '^PMID:' lines in the file .......... {len(all_raw_pmids)}")
    one_pmid_rec = sum(1 for r in records if r['pmid'] is not None) - len(multi_pmid)
    lines.append(f"Records with exactly 1 PMID ............. {one_pmid_rec}")
    lines.append(f"Records with 0 PMIDs .................... {len(no_pmid)}")
    if no_pmid:
        lines.append(f"  Numbers: {no_pmid[:10]}{' ...' if len(no_pmid) > 10 else ''}")
    lines.append(f"Records with >1 PMID (parse merged?) .... {len(multi_pmid)}")
    if multi_pmid:
        lines.append(f"  (rec#, count): {multi_pmid[:10]}"
                     f"{' ...' if len(multi_pmid) > 10 else ''}")
    lines.append(f"Duplicate PMIDs across records .......... {len(duplicate_pmids)}")
    if duplicate_pmids:
        lines.append(f"  PMIDs: {duplicate_pmids[:10]}"
                     f"{' ...' if len(duplicate_pmids) > 10 else ''}")

    unique_parsed_pmids = len({r["pmid"] for r in records if r["pmid"]})
    lines.append(f"Unique parsed PMIDs ..................... {unique_parsed_pmids}")
    expected_unique = len(set(all_raw_pmids))
    if unique_parsed_pmids != expected_unique:
        lines.append(f"  WARNING: unique parsed PMIDs ({unique_parsed_pmids}) "
                     f"!= unique raw PMIDs ({expected_unique})")
    lines.append("")
    report = "\n".join(lines)
    return records, report


# =============================================================================
# STAGE 2 — KEYWORD SCREEN
# =============================================================================
# Flag records that contain (RCT phrase) AND (HMBF or BMBF or direct comparison).
# IMPORTANT: all substring matches run against r["text_norm"], which has
# whitespace runs collapsed, so phrases wrapped across newlines still match.

RCT_PHRASES = [
    "randomized controlled trial", "randomised controlled trial",
    "randomized control trial",    "randomised control trial",
    "randomized clinical trial",   "randomised clinical trial",
    "randomized trial",            "randomised trial",
    "randomly assigned",           "randomly allocated",
    "randomized to receive",       "randomised to receive",
    "randomized to",               "randomised to",
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
    "prolacta", "prolact",
    "h2mf", "hmbf", "hmdf", "phmf",
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


def _contains_any_norm(norm_text: str, terms: List[str]) -> List[str]:
    """Substring match on an already-lowercased + whitespace-normalized string."""
    return [t for t in terms if t in norm_text]


def stage2_keyword_screen(records: List[Dict]) -> List[Dict]:
    hits = []
    for r in records:
        tn = r["text_norm"]
        rct = _contains_any_norm(tn, RCT_PHRASES)
        hmbf = _contains_any_norm(tn, HMBF_TERMS)
        bmbf = _contains_any_norm(tn, BMBF_TERMS)
        direct = _contains_any_norm(tn, DIRECT_COMPARISON_PHRASES)
        if rct and (hmbf or bmbf or direct):
            r2 = dict(r)
            r2.update({"rct": rct, "hmbf": hmbf, "bmbf": bmbf, "direct": direct,
                       "surfaced_by": "stage2_keyword"})
            hits.append(r2)
    return hits


# =============================================================================
# STAGE 3 — AUTHOR-NAME RECOVERY PROBE
# =============================================================================
# Provenance note: this list was ASSEMBLED DURING screening of this corpus.
# Each token is here because it corresponded to a record that was either:
#   (a) already surfaced by stage 2 (in which case the author token is
#       redundant but kept for documentation), or
#   (b) found by manual browsing of records that stage 2 missed because the
#       abstract used local shorthand (e.g. "HM100/HM40/BOV" instead of
#       "human milk-based fortifier"), and was then entered here so the
#       pipeline would surface it on re-runs.
# The list is CORPUS-SPECIFIC. Applying this script to a different search
# set would require re-building the list from scratch.

LANDMARK_AUTHORS = [
    "sullivan s",   # Sullivan 2010
    "cristofalo",   # Cristofalo 2013
    "o'connor dl",  # O'Connor 2018 OptiMoM
    "embleton n",   # Embleton 2023
    "mizuno k",     # Mizuno 2026
    "jensen gb",    # Jensen 2024 N-forte
    "berrington j", # Berrington 2025
    "kumbhare",     # Kumbhare 2022
    "polberger",    # Polberger 1999
    "hagelberg",    # Hagelberg 1990
    "lucas a",      # Lucas 2020 subgroup re-analysis
    "ghandehari",   # Ghandehari 2012
    "hopperton",    # Hopperton 2019
    "asbury",       # Asbury 2022
    "yeung t",      # Yeung 2023
    "uthaya",       # Uthaya 2022
    "hair ab",      # Hair 2014/2016 cream studies (eventually excluded)
    "boehm g",      # Boehm 1993 (eventually excluded)
    "moro ge",      # Moro 1991 (eventually excluded)
    "salas aa",     # Salas trials (eventually excluded as different comparison)
]


def stage3_author_probe(records: List[Dict], already: Set[int]) -> List[Dict]:
    hits = []
    for r in records:
        if r["num"] in already:
            continue
        tn = r["text_norm"]
        matched = next((a for a in LANDMARK_AUTHORS if a in tn), None)
        if not matched:
            continue
        rct = _contains_any_norm(tn, RCT_PHRASES)
        if not rct:
            continue
        r2 = dict(r)
        r2.update({"author_matched": matched, "rct": rct,
                   "surfaced_by": "stage3_author_probe"})
        hits.append(r2)
    return hits


# =============================================================================
# STAGE 4 — TITLE-FIELD RECOVERY PROBE
# =============================================================================

def _extract_title_norm(text: str) -> str:
    """Return the record's title block in whitespace-normalized lowercase form.
    PubMed records look like: 'N. Journal cite...\\n\\nTitle line 1\\nTitle
    line 2...\\n\\nAuthors...'. We take the first paragraph after the citation
    line as the title."""
    paras = re.split(r"\n\s*\n", text)
    if len(paras) < 2:
        return ""
    return normalize_for_match(paras[1])


COMPARISON_WORDS = ["versus", " vs ", "vs.", "compared", "comparison",
                    " and ", " or "]


def stage4_title_probe(records: List[Dict], already: Set[int]) -> List[Dict]:
    hits = []
    for r in records:
        if r["num"] in already:
            continue
        title = _extract_title_norm(r["text"])
        if "human" not in title:
            continue
        if not ("bovine" in title or "cow" in title):
            continue
        if "fortif" not in title and "protein" not in title:
            continue
        if not any(cw in title for cw in COMPARISON_WORDS):
            continue
        r2 = dict(r)
        r2.update({"title_norm": title, "surfaced_by": "stage4_title_probe"})
        hits.append(r2)
    return hits


# =============================================================================
# STAGE 5 — DUMP THE CANDIDATE POOL (NO TRUNCATION)
# =============================================================================

def stage5_dump_candidates(all_candidates: List[Dict], out_path: Path) -> int:
    """Write the FULL text of every unique candidate (no character cap).
    Returns the number of unique candidates written."""
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
        f.write("Each record below is written in FULL (no truncation).\n")
        f.write("Read each one and apply the adjudication criteria in\n")
        f.write("adjudication_criteria.txt .\n")
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
            if c.get("title_norm"):
                f.write(f"  Title (norm)    : {c['title_norm']}\n")
            f.write("-" * 100 + "\n")
            f.write(c["text"])  # <<< FULL original text, no 4000-char cap
            f.write("\n\n")
    return len(unique)


# =============================================================================
# MANUAL ADJUDICATION CRITERIA (written to its own file at stage 5)
# =============================================================================

MANUAL_ADJUDICATION_CRITERIA = """\
MANUAL ADJUDICATION CRITERIA
============================

Apply these criteria, in order, to every candidate in
stage5_candidate_pool_records.txt . If the answer to any one is "no" or
"unclear in a disqualifying way", the record is EXCLUDED.

(1) Is this an original research report (not a review, meta-analysis,
    protocol-only paper, commentary, letter, erratum, or conference abstract)?
      - Reviews / meta-analyses       -> EXCLUDE (note for background).
      - Protocol-only papers          -> EXCLUDE (companion if main trial
                                                   is included).

(2) Is the study a Randomized Controlled Trial?
      - Must use "randomized/randomised" or equivalent allocation language.
      - Retrospective cohort, prospective cohort without randomization,
        quality-improvement project, historical-control study -> EXCLUDE.

(3) Does one arm receive a Human-Milk-Based (or human-milk-derived) Fortifier?
      - Prolacta / H2MF / HMDF / HMBF / "human milk-based human milk fortifier"
        all qualify.
      - "Exclusive human milk diet" qualifies IF the fortifier itself is
        human-milk-derived.
      - Donkey-milk-derived fortifier (e.g. Fortilat trials)    -> EXCLUDE.
      - Trials where BOTH arms get HMBF (e.g. HM-derived CREAM) -> EXCLUDE.

(4) Does the comparator arm receive a Bovine/Cow-Milk-Based Fortifier?
      - Standard commercial powdered/liquid HMFs qualify.
      - Bovine COLOSTRUM (intact) as comparator                 -> EXCLUDE.
      - "Unfortified" comparator                                -> EXCLUDE.
      - Different timing / different protein target of the same
        BMBF (dosing or timing question)                        -> EXCLUDE.

(5) Is this the MAIN report of the trial, or a sub-study / follow-up?
      - Main report              -> PRIMARY RCT.
      - Protocol, long-term follow-up, substudy, cost analysis,
        corrigendum, subgroup re-analysis of the same cohort
                                 -> COMPANION PUBLICATION (do not double-count).

(6) Does the trial report NEC and/or sepsis in the abstract, OR plausibly in
    the full text?
      - If reported in the abstract: CORE trial.
      - If plausibly recorded given design and population: INCLUDE and
        retrieve full text.
      - Older protein-only fortifier RCTs typically do NOT report NEC/sepsis;
        flag as "limited usefulness, may contribute zero events".

Borderline rules documented after reading this corpus
-----------------------------------------------------
  - Trials whose comparator arm receives preterm formula when MOM is
    insufficient (Sullivan 2010, Cristofalo 2013, Embleton 2023,
    Mizuno 2026) are INCLUDED, because published HMBF-vs-BMBF
    meta-analyses include them. The milk-base mismatch is a
    sensitivity-analysis issue, not an inclusion issue.
  - Trials where both arms share an identical human milk base and only
    the fortifier source differs (O'Connor 2018, Jensen 2024,
    Berrington 2025, Kumbhare 2022, Hagelberg 1990, Polberger 1999) are
    the "cleanest" HMBF-vs-BMBF comparisons.
"""


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--expected-records", type=int, default=None,
                    help="If supplied, parse report flags any mismatch.")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1
    args.outdir.mkdir(parents=True, exist_ok=True)

    log: List[str] = []

    # ---------- STAGE 1 ----------
    print("[Stage 1] Parsing records ...")
    records, parse_report = stage1_parse(args.input, expected_records=args.expected_records)
    (args.outdir / "stage1_parse_report.txt").write_text(parse_report)
    print(parse_report)
    log.append(f"[Stage 1] parsed {len(records)} records")

    # ---------- STAGE 2 ----------
    print("[Stage 2] Keyword screen ...")
    stage2 = stage2_keyword_screen(records)
    s2_nums = sorted(r["num"] for r in stage2)
    msg = f"  {len(stage2)} records flagged by keyword screen."
    print(msg); log.append(f"[Stage 2] {len(stage2)} hits")
    (args.outdir / "stage2_keyword_screen_hits.txt").write_text(
        f"{msg}\nRecord numbers:\n" + "\n".join(f"  #{n}" for n in s2_nums) + "\n"
    )

    # ---------- STAGE 3 ----------
    print("[Stage 3] Author-name recovery probe ...")
    already = {r["num"] for r in stage2}
    stage3 = stage3_author_probe(records, already)
    msg = f"  {len(stage3)} ADDITIONAL records recovered by author probe."
    print(msg); log.append(f"[Stage 3] {len(stage3)} hits")
    (args.outdir / "stage3_author_probe_hits.txt").write_text(
        f"{msg}\nRecord numbers (with the author token that matched):\n" +
        "\n".join(f"  #{r['num']}  <- '{r['author_matched']}'" for r in stage3) + "\n"
    )

    # ---------- STAGE 4 ----------
    print("[Stage 4] Title-field recovery probe ...")
    already |= {r["num"] for r in stage3}
    stage4 = stage4_title_probe(records, already)
    s4_nums = sorted(r["num"] for r in stage4)
    msg = f"  {len(stage4)} ADDITIONAL records recovered by title probe."
    print(msg); log.append(f"[Stage 4] {len(stage4)} hits")
    (args.outdir / "stage4_title_probe_hits.txt").write_text(
        f"{msg}\nRecord numbers:\n" + "\n".join(f"  #{n}" for n in s4_nums) + "\n"
    )

    # ---------- STAGE 5 ----------
    print("[Stage 5] Writing candidate pool (full text, no truncation) ...")
    all_candidates = stage2 + stage3 + stage4
    pool_path = args.outdir / "stage5_candidate_pool_records.txt"
    n_pool = stage5_dump_candidates(all_candidates, pool_path)
    (args.outdir / "adjudication_criteria.txt").write_text(MANUAL_ADJUDICATION_CRITERIA)
    msg = f"  {n_pool} unique candidates written to {pool_path.name}"
    print(msg); log.append(f"[Stage 5] {n_pool} unique candidates")

    # ---------- Log ----------
    with (args.outdir / "discovery_log.txt").open("w", encoding="utf-8") as f:
        f.write("Discovery pipeline log\n" + "=" * 60 + "\n\n")
        f.write("\n".join(log))
        f.write("\n\nNext step: open stage5_candidate_pool_records.txt and\n")
        f.write("apply adjudication_criteria.txt to classify each candidate.\n")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
