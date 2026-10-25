r"""
================================================================================
HMBF vs BMBF for NEC and Sepsis — Screening of PubMed Meta-Analyses / SRs
================================================================================

Purpose
-------
Reproducibly screen a user-supplied set of PubMed records (meta-analyses,
network meta-analyses and systematic reviews on human-milk fortification) and
extract those that **directly compare a human-based milk fortifier against a
bovine / cow-based milk fortifier** on the outcomes of **necrotising
enterocolitis (NEC, any stage)** and/or **sepsis** in preterm / low-birthweight
infants. Produce a publication-ready Excel workbook summarising the included
studies.

Workflow (two stages with hard preconditions)
---------------------------------------------
Stage 1 — AUTOMATED KEYWORD SCREENING
    The PubMed plain-text file is split into individual records. Unicode dashes
    are normalised to hyphen-minus so that 'milk–derived' is treated the same
    as 'milk-derived'. Each record is tested against three regex panels:
        (a) human-based fortifier terms (HMBF, HMF, HMDF, EHMD, 'human milk-
            based/derived fortifier', 'human-based fortifier', Prolacta, etc.)
        (b) bovine / cow-based fortifier terms (BMBF, BMF, CMBF, 'bovine/cow
            milk-based/derived fortifier', 'bovine-based fortifier', etc.)
        (c) outcomes of interest (NEC, necroti[sz]ing enterocolitis, sepsis,
            infection)
    A fourth panel of 'coordinated phrases' such as 'human versus bovine milk-
    derived fortifier' and 'human or bovine milk-based fortifier' counts as a
    match for BOTH the human and the bovine panels, since those constructions
    name the two arms as a single coordinated noun phrase. A record must also
    self-identify as a systematic review, meta-analysis, umbrella review,
    network meta-analysis or Cochrane review.

Stage 2 — MANUAL CURATION, EXPRESSED AS A PMID-KEYED DECISION REGISTRY
    DECISIONS is a dict keyed by **PMID** (the stable identifier). Each entry
    has decision in {'include', 'exclude', 'borderline'} and the full extracted
    fields (for 'include' and 'borderline') or an exclusion reason (for
    'exclude'). Workbook rows are built from DECISIONS *filtered by what the
    parser actually found in the input*; the 'entry #' column shows the
    position in the input the user supplied (not a stored value), so a
    reordered export shows the new order.

Hard preconditions enforced by main() — a failure aborts with a non-zero
exit code and NO workbook is written:
    P1. Input file exists.
    P2. If EXPECTED_INPUT_SHA256 is set and the computed hash of the input
        differs, abort. If EXPECTED_INPUT_SHA256 is None, the hash is only
        printed, not enforced.
    P3. Every PMID in DECISIONS with decision='include' or 'borderline'
        must be present in the parsed input. Missing-input articles mean
        either the input is incomplete or the decision registry is stale.
    P4. Every Stage-1 candidate PMID must have a documented decision in
        DECISIONS. An undocumented candidate is reported as 'AWAITING
        REVIEW' and the run aborts — the maintainer must add a decision
        before the workbook can be regenerated.

Reproducibility notes
---------------------
- Stage 1 is fully deterministic.
- Stage 2 is a human judgment layer; its content lives in the DECISIONS
  dict near the top of this file. Change-control the DECISIONS dict and
  re-run.
- Numerical results (RRs, ORs, CIs, sample sizes) in DECISIONS were
  transcribed verbatim from the abstracts in the input file; nothing is
  computed or imputed by this script.

Input
-----
    INPUT_FILE
        PubMed plain-text export, one record per numbered block starting
        with '<n>. <journal citation>'. Expected SHA-256 for the published
        version of this analysis is EXPECTED_INPUT_SHA256.

Output
------
    OUTPUT_FILE  (only written when all preconditions pass)
        Three sheets:
          1. 'Included MA_SR'    — included records with extracted fields
          2. 'Methods & Criteria' — search strategy and inclusion rule
          3. 'Borderline'        — records set aside for user judgment

Change log
----------
v1  Initial run. Flagged 9 included records.
v2  Added entry 70 (Bührer 2020, PMID 31645057) after user feedback — v1
    keyword panel missed the connector 'or' in 'human OR bovine milk-based
    fortifiers'.
v3  Rewrote script with Stage-1 automation, record parser, and reconciliation.
    Fixed two parser issues: wrapped citation 'Epub 2025 Jul 29.' creating a
    false boundary, and shared-head construction 'human milk-based versus cow
    milk-based fortifiers' (entry 94). All 10 included entries then flagged
    by Stage 1.
v4  (this version) After adversarial testing by the user, two class-of-bug
    fixes:
      • Decision model. Previously, main() always wrote the hard-coded
        INCLUDED_RECORDS list regardless of parse — so an empty input still
        produced the full workbook. Workbook content is now built from a
        PMID-keyed DECISIONS registry filtered by what the parser found in
        the input, and three hard preconditions must pass before any file
        is written (see 'Hard preconditions' above). Identity is checked
        by PMID, not by entry number; undocumented Stage-1 candidates are
        reported as 'awaiting review' and abort the run. A SHA-256 check
        of the input file is available for historical regeneration.
      • Keyword panel. Added Unicode-dash normalisation ('milk–derived' is
        treated as 'milk-derived') and new patterns for: 'human-based
        fortifier' / 'bovine-based fortifier' with no 'milk' token; the
        coordinated construction 'human versus bovine milk-derived fortifier'
        where the head noun is shared; and the nested compound 'human milk-
        derived human milk fortifier'.
================================================================================
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


# ============================================================================
# 1. Configuration
# ============================================================================

INPUT_FILE = Path("/mnt/user-data/uploads/130_Meta_SystematicR_abstract.txt")
OUTPUT_FILE = Path("/mnt/user-data/outputs/HMBF_vs_BMBF_NEC_Sepsis_MA_SR.xlsx")

# SHA-256 of the input file as it was when the DECISIONS registry below was
# curated. Set to None to disable enforcement (the hash will still be printed).
# Re-run against a different input will abort if a value is set here and does
# not match. Compute the hash of a new input with:
#   python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" FILE
EXPECTED_INPUT_SHA256: str | None = (
    "56c331bf6eb62c0ae1527e690f0b29c9b559d99dff9657162a6816a6c797712c"
)


# --- Keyword panels for Stage 1 automated screening -------------------------
# Each panel is a list of case-insensitive regular expressions. A record
# matches a panel if ANY of its regexes match. Unicode dashes in the input
# are normalised to hyphen-minus by normalise_text() before matching, so the
# character class ``[\s\-]`` suffices.

HUMAN_BASED_FORTIFIER_PATTERNS: list[str] = [
    # Direct names: human milk-based / human milk-derived fortifier.
    r"human[\s\-]+milk[\s\-]+based[\s\-]+fortifier",
    r"human[\s\-]+milk[\s\-]+derived[\s\-]+fortifier",
    # No-'milk' variants: 'human-based fortifier' / 'human-derived fortifier'.
    r"human[\s\-]+(based|derived)[\s\-]+fortifier",
    # Donor variants.
    r"donor[\s\-]+milk[\s\-]+(based|derived)[\s\-]+fortifier",
    r"donor[\s\-]+(based|derived)[\s\-]+fortifier",
    r"donor\s+human\s+milk[\s\-]+(based|derived)\s+fortifier",
    # Nested compounds: 'human milk-based human milk fortifier'.
    r"human[\s\-]+milk[\s\-]+(based|derived)[\s\-]+human[\s\-]+milk[\s\-]+fortifier",
    # 'human milk-based' / 'human milk-derived' as a modifier, with 'fortifier'
    # appearing anywhere within the next 120 characters.
    r"human[\s\-]+milk[\s\-]+(based|derived)[\s\S]{0,120}?fortifier",
    # Acronyms.
    r"\bHMBF\b",
    r"\bHMF\b",
    r"\bHMDF\b",
    r"\bHBMF\b",
    r"\bEHMD\b",
    # Diet names and brand names.
    r"exclusive\s+human\s+milk\s+diet",
    r"exclusive\s+human\s+milk[\s\-]+based\s+diet",
    r"Prolacta",
]

BOVINE_BASED_FORTIFIER_PATTERNS: list[str] = [
    # Direct names: bovine milk-based / bovine milk-derived fortifier.
    r"bovine[\s\-]+milk[\s\-]+based[\s\-]+fortifier",
    r"bovine[\s\-]+milk[\s\-]+derived[\s\-]+fortifier",
    # No-'milk' variants: 'bovine-based fortifier' / 'bovine-derived fortifier'.
    r"bovine[\s\-]+(based|derived)[\s\-]+fortifier",
    r"\bbovine\s+fortifier\b",
    # Cow / cow's variants.
    r"cow(?:'s|s)?[\s\-]+milk[\s\-]+based[\s\-]+fortifier",
    r"cow(?:'s|s)?[\s\-]+milk[\s\-]+derived[\s\-]+fortifier",
    r"cow(?:'s|s)?[\s\-]+(based|derived)[\s\-]+fortifier",
    r"\bcow[\s\-]+fortifier\b",
    r"cow[\s\-]+milk[\s\-]+derived\s+diet",
    # Nested compounds: 'bovine milk-based human milk fortifier'.
    r"bovine[\s\-]+milk[\s\-]+(based|derived)[\s\-]+human[\s\-]+milk[\s\-]+fortifier",
    # 'bovine milk-based/-derived' as modifier, 'fortifier' within 120 chars.
    r"bovine[\s\-]+milk[\s\-]+(based|derived)[\s\S]{0,120}?fortifier",
    r"cow(?:'s|s)?[\s\-]+milk[\s\-]+(based|derived)[\s\S]{0,120}?fortifier",
    # Acronyms.
    r"\bBMBF\b",
    r"\bBMF\b",
    r"\bCMBF\b",
]

# A 'coordinated phrase' names both arms as one coordinated noun phrase and
# counts as a match for BOTH the human and the bovine panels. These capture
# constructions where the head noun ('fortifier') is shared between the two
# arms, e.g. 'human versus bovine milk-derived fortifier', 'human or bovine
# milk-based fortifiers'. The pattern requires 'fortifier' to appear within
# 150 characters of the coordination point so that unrelated 'human vs
# bovine' prose elsewhere in the record does not trigger a match.
COORDINATED_FORTIFIER_PATTERNS: list[str] = [
    r"human\s+(versus|vs\.?|or|and|compared\s+(?:with|to))\s+(cow(?:'s|s)?|bovine)[\s\S]{0,150}?fortifier",
    r"(cow(?:'s|s)?|bovine)\s+(versus|vs\.?|or|and|compared\s+(?:with|to))\s+human[\s\S]{0,150}?fortifier",
]

NEC_OR_SEPSIS_PATTERNS: list[str] = [
    r"necroti[sz]ing\s+enterocolitis",
    r"\bNEC\b",
    r"\bsepsis\b",
    r"late[\s\-]onset\s+(sepsis|infection)",
    r"\binfection(s)?\b",
]

REVIEW_TYPE_PATTERNS: list[str] = [
    r"systematic\s+review",
    r"meta[\s\-]?analysis",
    r"network\s+meta[\s\-]?analysis",
    r"umbrella\s+review",
    r"Cochrane",
    r"Bayesian\s+model[\s\-]averaged",
]


# ============================================================================
# 2. Data structures
# ============================================================================

@dataclass
class PubmedRecord:
    """One record parsed from the PubMed plain-text export."""
    number: int
    header: str
    text: str
    pmid: str | None = None
    doi: str | None = None


@dataclass
class ScreeningResult:
    record: PubmedRecord
    has_human_fortifier: bool
    has_bovine_fortifier: bool
    has_nec_or_sepsis: bool
    is_review: bool

    @property
    def is_candidate(self) -> bool:
        return (
            self.has_human_fortifier
            and self.has_bovine_fortifier
            and self.has_nec_or_sepsis
            and self.is_review
        )


# ============================================================================
# 3. Text normalisation and record parsing
# ============================================================================

# Unicode dash code points that routinely appear in copy-edited text and
# should all be treated as a hyphen-minus for pattern matching.
_UNICODE_DASHES = (
    "\u00AD"   # soft hyphen
    "\u2010"   # hyphen
    "\u2011"   # non-breaking hyphen
    "\u2012"   # figure dash
    "\u2013"   # en dash
    "\u2014"   # em dash
    "\u2015"   # horizontal bar
    "\u2212"   # minus sign
)
_DASH_TRANSLATION = {ord(ch): "-" for ch in _UNICODE_DASHES}


def normalise_text(text: str) -> str:
    """Map all Unicode dashes to hyphen-minus and collapse whitespace.

    This ensures that 'milk–derived' (en dash) and 'milk-derived' (hyphen) are
    indistinguishable to the regex panels, and that line wrapping inside the
    PubMed export does not break phrase matching.
    """
    text = text.translate(_DASH_TRANSLATION)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def read_records(path: Path) -> list[PubmedRecord]:
    """Split the PubMed plain-text file into individual records.

    Record boundary: a line starting with ``<digits>.`` followed on the SAME
    line by at least one space/tab and then a capital letter (the first letter
    of a journal citation). This rejects wrapped citation fragments such as
    'Epub 2025 Jul 29.' sitting alone on a line.
    """
    raw = path.read_text(encoding="utf-8").replace("\r", "")
    boundary = re.compile(r"(?m)^(\d+)\.[ \t]+[A-Z]")
    hits = list(boundary.finditer(raw))
    records: list[PubmedRecord] = []
    for i, m in enumerate(hits):
        start = m.start()
        end = hits[i + 1].start() if i + 1 < len(hits) else len(raw)
        block = raw[start:end]
        header_end = block.find("\n")
        header = block[:header_end].strip() if header_end != -1 else block.strip()
        body = normalise_text(block)
        pmid_match = re.search(r"PMID:\s*(\d+)", body)
        doi_match = re.search(r"DOI:\s*(\S+)", body)
        records.append(
            PubmedRecord(
                number=int(m.group(1)),
                header=header,
                text=body,
                pmid=pmid_match.group(1) if pmid_match else None,
                doi=doi_match.group(1) if doi_match else None,
            )
        )
    return records


# ============================================================================
# 4. Stage 1 — automated keyword screening
# ============================================================================

def _any_match(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def screen(records: Iterable[PubmedRecord]) -> list[ScreeningResult]:
    """Run every record through the keyword panels.

    A coordinated-phrase match counts as a hit for both the human and the
    bovine panels, so that constructions where the two arms share a head
    noun (e.g. 'human versus bovine milk-derived fortifier') are not missed
    by requiring 'fortifier' to be adjacent to each arm name separately.
    """
    results: list[ScreeningResult] = []
    for r in records:
        has_coord = _any_match(r.text, COORDINATED_FORTIFIER_PATTERNS)
        results.append(
            ScreeningResult(
                record=r,
                has_human_fortifier=has_coord or _any_match(r.text, HUMAN_BASED_FORTIFIER_PATTERNS),
                has_bovine_fortifier=has_coord or _any_match(r.text, BOVINE_BASED_FORTIFIER_PATTERNS),
                has_nec_or_sepsis=_any_match(r.text, NEC_OR_SEPSIS_PATTERNS),
                is_review=_any_match(r.text, REVIEW_TYPE_PATTERNS),
            )
        )
    return results


# ============================================================================
# 5. Stage 2 — DECISIONS registry (PMID-keyed)
# ============================================================================
#
# Workbook content is built from this registry filtered by what the parser
# actually finds in the input. Identity is PMID. The 'entry' field is a
# convenience locator; the output workbook shows the entry number from the
# parsed input, not from here, so a reordered export shows the new order.
#
# decision in {'include', 'exclude', 'borderline'}:
#   - 'include'    → row on the 'Included MA_SR' sheet, with all fields.
#   - 'borderline' → row on the 'Borderline' sheet with the 'reason' field.
#   - 'exclude'    → not written to any sheet; records why a Stage-1 candidate
#                    was rejected during Stage-2 manual review, so a re-run
#                    does not report it as 'awaiting review'.
#
# ============================================================================

COLUMN_ORDER = [
    "entry",
    "author",
    "year",
    "journal",
    "title",
    "study_type",
    "intervention",
    "comparator",
    "population",
    "n_studies",
    "n_participants",
    "nec_definition",
    "nec_result",
    "sepsis_definition",
    "sepsis_result",
    "other_outcomes",
    "conclusion",
    "doi",
    "pmid",
    "notes",
]

COLUMN_HEADERS = {
    "entry":             "Entry # in\nparsed input",
    "author":            "First Author",
    "year":              "Year",
    "journal":           "Journal",
    "title":             "Title",
    "study_type":        "Study Type",
    "intervention":      "Intervention (Human-based)",
    "comparator":        "Comparator (Bovine/Cow-based)",
    "population":        "Population",
    "n_studies":         "No. of included studies",
    "n_participants":    "No. of participants",
    "nec_definition":    "NEC definition / stage",
    "nec_result":        "NEC result\n(effect size, 95% CI, p / certainty)",
    "sepsis_definition": "Sepsis definition",
    "sepsis_result":     "Sepsis result\n(effect size, 95% CI, p / certainty)",
    "other_outcomes":    "Other key outcomes reported",
    "conclusion":        "Authors' conclusion (brief)",
    "doi":               "DOI",
    "pmid":              "PMID",
    "notes":             "Notes / Comments",
}

DECISIONS: dict[str, dict] = {
    # ---------- INCLUDED ----------
    "41449441": {
        "decision": "include",
        "entry": 6,
        "author": "Feng Y",
        "year": 2025,
        "journal": "Int Breastfeed J",
        "title": "Impact of three mammalian milk-derived fortifiers on morbidity and mortality in preterm infants: a systematic review and network meta-analysis.",
        "study_type": "Systematic review and network meta-analysis",
        "intervention": "Human milk-derived fortifier (HMF)",
        "comparator": "Bovine milk-derived fortifier (BMF); also compared to donkey milk-derived fortifier (DMF)",
        "population": "Preterm infants in NICUs",
        "n_studies": "10 studies qualitative; 5 studies in NMA (3 fortifier types)",
        "n_participants": "545 preterm infants",
        "nec_definition": "Necrotizing enterocolitis (NEC) – stage not specified in abstract",
        "nec_result": "Compared with HMF, BMF was associated with an INCREASED risk of NEC: RR = 2.33, 95% CI 1.22–4.44. HMF ranked most favourable for reducing NEC incidence.",
        "sepsis_definition": "Neonatal sepsis",
        "sepsis_result": "DMF (not HMF vs BMF) ranked best for reducing sepsis in cumulative ranking; direct HMF vs BMF estimate for sepsis not reported in abstract.",
        "other_outcomes": "Mortality (HMF ranked most favourable), intraventricular haemorrhage (DMF best), time outcomes (abstract limited).",
        "conclusion": "HMF may be associated with a reduced incidence of NEC; DMF may offer potential anti-inflammatory benefits. Findings based on limited number of small studies; further RCTs are needed.",
        "doi": "10.1186/s13006-025-00801-w",
        "notes": "Three-arm network meta-analysis (BMF vs HMF vs DMF). Direct HMF-vs-BMF effect reported for NEC.",
    },
    "41228457": {
        "decision": "include",
        "entry": 9,
        "author": "Reyes SM",
        "year": 2025,
        "journal": "Nutrients",
        "title": "Human Milk Fortification and Necrotizing Enterocolitis in Very Low Birthweight Infants: State of Evidence and Systematic Review with Meta-Analysis.",
        "study_type": "Systematic review and meta-analysis (RCTs + observational cohorts)",
        "intervention": "Exclusive human milk diet (EHMD) including human milk-derived fortifier (HMF)",
        "comparator": "Cow milk-derived diets (incl. cow milk-derived fortifier)",
        "population": "Very low birthweight (VLBW) infants (most studies ≤1250 g)",
        "n_studies": "20 studies (5 RCTs + 15 observational)",
        "n_participants": "6,794 infants (4,625 for Bell ≥II NEC; 4,754 for surgical NEC; 2,102 and 1,659 for direct fortifier-type comparisons)",
        "nec_definition": "Bell Stage ≥II NEC; surgical NEC",
        "nec_result": "EHMD vs cow milk-containing diets: Bell ≥II NEC OR 0.59 (95% CI 0.42–0.81; p<0.001; n=4,625); surgical NEC OR 0.43 (95% CI 0.32–0.58; p<0.0001; n=4,754). DIRECT HMF vs BMF (base diet = human milk): Bell ≥II NEC OR 0.65 (95% CI 0.44–0.97; p=0.03; n=2,102); surgical NEC OR 0.51 (95% CI 0.26–0.98; p=0.04; n=1,659).",
        "sepsis_definition": "Not primary – sepsis not analysed in the fortifier-type sub-analysis in the abstract",
        "sepsis_result": "Not reported in abstract (study focus is NEC).",
        "other_outcomes": "Medical NEC, surgical NEC, consistency across RCTs vs observational studies.",
        "conclusion": "EHMD with human milk-derived fortifiers was associated with lower odds of medical and surgical NEC in VLBW infants, with most evidence from infants ≤1250 g. Consistency across RCTs and observational studies strengthens confidence.",
        "doi": "10.3390/nu17213384",
        "notes": "Primary focus on NEC (not sepsis). Includes BOTH an overall EHMD vs cow-milk-containing diet analysis AND a direct fortifier-type sub-analysis (HMF vs BMF with a HM base). COI: lead author is a Prolacta Bioscience consultant.",
    },
    "40729426": {
        "decision": "include",
        "entry": 10,
        "author": "Huizing MJ",
        "year": 2025,
        "journal": "Acta Paediatr",
        "title": "Absence of Evidence of Beneficial Effects of Human Milk-Based Fortifier: A Bayesian Model-Averaged Meta-Analysis.",
        "study_type": "Bayesian model-averaged meta-analysis of RCTs",
        "intervention": "Human milk-based fortifier (HMBF)",
        "comparator": "Bovine milk-based fortifier (BMBF)",
        "population": "Infants with gestational age <32 weeks or birthweight <1500 g",
        "n_studies": "3 RCTs",
        "n_participants": "405 infants",
        "nec_definition": "NEC stage II–III",
        "nec_result": "BF10 = 0.86 – inconclusive; evidence does NOT confirm or exclude a protective effect of HMBF vs BMBF on NEC.",
        "sepsis_definition": "Late onset sepsis",
        "sepsis_result": "BF10 = 0.69 – inconclusive; evidence does NOT confirm or exclude a protective effect of HMBF vs BMBF on late onset sepsis.",
        "other_outcomes": "All-cause mortality (BF10=1.07), BPD (BF10=0.92), severe ROP (BF10=0.75) – all inconclusive.",
        "conclusion": "The extant corpus of RCTs does not provide sufficient evidence to either confirm or exclude a potential effect of HMBF compared with BMBF on the risk of NEC, mortality, sepsis, BPD, or severe ROP.",
        "doi": "10.1111/apa.70260",
        "notes": "Bayesian re-analysis of the existing RCTs; BF10 >3 would favour an effect, BF10 <1/3 would favour no effect. All five outcomes fell between these thresholds (inconclusive).",
    },
    "40431391": {
        "decision": "include",
        "entry": 13,
        "author": "Campbell-Yeo M",
        "year": 2025,
        "journal": "Nutrients",
        "title": "Effect of Multi-Nutrient Milk Fortification on Preterm Neonate Outcomes: A Network Meta-Analysis.",
        "study_type": "Systematic review and network meta-analysis of RCTs",
        "intervention": "Treatment classes incl. 'mother's own milk + donor milk + human-milk-based fortifier'",
        "comparator": "Treatment classes incl. 'mother's own milk + donor milk + bovine fortifier' and 'mother's own milk + formula + bovine fortification'",
        "population": "Preterm infants (feeding regimens that include multi-nutrient fortification)",
        "n_studies": "59 studies included",
        "n_participants": "Not specified in abstract",
        "nec_definition": "NEC (stage not specified in abstract)",
        "nec_result": "For NEC: top-ranked treatment class = MOM + donor milk + HUMAN-milk-based fortifier (favourable ranking vs bovine-fortifier regimens). No pooled HMBF-vs-BMBF effect-size estimate reported in abstract.",
        "sepsis_definition": "Sepsis (not further defined in abstract)",
        "sepsis_result": "For sepsis: top-ranked treatment class = MOM + formula (NOT a human-milk-based fortifier regimen). No pooled HMBF-vs-BMBF effect-size estimate reported in abstract.",
        "other_outcomes": "Mortality, ROP, PVL (bovine-fortifier regimen ranked top in disconnected network), BPD, time to full enteral feeds, Bayley II MDI (MOM + formula + bovine fortification ranked top).",
        "conclusion": "Treatment rankings consistent with the hypothesis that increased MOM intake is associated with better outcomes. Insufficient high-quality evidence to support or refute one fortification feeding regimen over another.",
        "doi": "10.3390/nu17101651",
        "notes": "NMA of feeding regimens, not solely of fortifier type. Multiple treatment classes include both HMBF and BMBF regimens, so HMBF vs BMBF is embedded within a wider comparison. Direct HMBF-vs-BMBF pooled effect sizes NOT given in abstract.",
    },
    "38542821": {
        "decision": "include",
        "entry": 23,
        "author": "Galis R",
        "year": 2024,
        "journal": "Nutrients",
        "title": "Association of Fortification with Human Milk versus Bovine Milk-Based Fortifiers on Short-Term Outcomes in Preterm Infants-A Meta-Analysis.",
        "study_type": "Meta-analysis",
        "intervention": "Human milk-derived fortifier (HMF) added to exclusive human milk (MOM or DHM)",
        "comparator": "Bovine milk fortifier (BMF) added to exclusive human milk",
        "population": "Preterm infants ≤28 weeks gestation and/or birthweight ≤1500 g on exclusive human milk diet",
        "n_studies": "4 studies",
        "n_participants": "681 infants (663 for BPD; 671 for ROP)",
        "nec_definition": "NEC stage ≥2",
        "nec_result": "RR 0.48 (95% CI 0.20–1.17); p=0.11; I²=39%. NOT statistically significant.",
        "sepsis_definition": "Sepsis (not further specified in abstract)",
        "sepsis_result": "RR 0.97 (95% CI 0.66–1.42); p=0.96; I²=26%. NOT statistically significant – no difference.",
        "other_outcomes": "Mortality significantly lower with HM-HMFs (RR 0.50, 95% CI 0.26–0.94; p=0.03; I²=0%). BPD RR 0.83 (0.69–1.00; p=0.05) – borderline. Combined ROP RR 0.64 (0.53–1.07; p=0.28).",
        "conclusion": "An HM-HMFs diet could possibly be associated with decreased mortality with no association with NEC, BPD, sepsis, or ROP. Limited by small number of studies; results should prompt further RCTs.",
        "doi": "10.3390/nu16060910",
        "notes": "Primary outcomes: death and NEC (stage ≥2). Directly addresses HMF vs BMF in exclusively HM-fed preterm infants.",
    },
    "32943531": {
        "decision": "include",
        "entry": 52,
        "author": "Grace E",
        "year": 2021,
        "journal": "Arch Dis Child Fetal Neonatal Ed",
        "title": "Safety and efficacy of human milk-based fortifier in enterally fed preterm and/or low birthweight infants: a systematic review and meta-analysis.",
        "study_type": "Systematic review and meta-analysis of RCTs / quasi-RCTs",
        "intervention": "Human milk-based fortifier (HMBF)",
        "comparator": "Cow's milk-based fortifier (CMBF)",
        "population": "Infants <34 weeks' gestation and/or birthweight <1500 g",
        "n_studies": "2 trials (16 full-text trials screened, 2 included)",
        "n_participants": "334 infants (332 with primary outcome data)",
        "nec_definition": "Necrotising enterocolitis (Bell's stage II or higher)",
        "nec_result": "HMBF vs CMBF: RR 0.47 (95% CI 0.22–0.98) – HMBF reduced NEC risk. Low to very low quality evidence.",
        "sepsis_definition": "Late-onset sepsis",
        "sepsis_result": "No clear evidence of an effect on late-onset sepsis (specific estimate not reproduced in abstract). Low to very low quality evidence.",
        "other_outcomes": "No clear effect on other outcomes.",
        "conclusion": "Findings suggest a reduction in NEC with human milk-based fortifier compared with cow's milk-based fortifier. Overall quality of evidence is low. Further appropriately powered trials needed before routine recommendation.",
        "doi": "10.1136/archdischild-2020-319406",
        "notes": "Primary outcomes explicitly: Bell stage II+ NEC and late-onset sepsis. Direct HMBF vs CMBF comparison. Low to very low quality evidence due to imprecision and lack of blinding in one study.",
    },
    "32277813": {
        "decision": "include",
        "entry": 66,
        "author": "Ananthan A",
        "year": 2020,
        "journal": "Adv Nutr",
        "title": "Human Milk-Derived Fortifiers Compared with Bovine Milk-Derived Fortifiers in Preterm Infants: A Systematic Review and Meta-Analysis.",
        "study_type": "Systematic review and meta-analysis of RCTs",
        "intervention": "Human milk-derived fortifier (HMF)",
        "comparator": "Bovine milk-derived fortifier (BMF)",
        "population": "Preterm infants",
        "n_studies": "6 RCTs",
        "n_participants": "Up to 334 infants (NEC analysis n=334; mortality n=334; weight n=241)",
        "nec_definition": "NEC ≥Stage II; surgical NEC",
        "nec_result": "NEC ≥Stage II: RR 0.38 (95% CI 0.15–0.95); p=0.04; I²=9%; n=334, 4 RCTs – FAVOURS HMF. Surgical NEC: RR 0.13 (95% CI 0.02–0.67); p=0.02; I²=0%; n=209, 3 RCTs – FAVOURS HMF. Benefit for NEC was NO LONGER SIGNIFICANT after excluding studies at high risk of bias.",
        "sepsis_definition": "Late-onset sepsis",
        "sepsis_result": "RR 0.96 (95% CI 0.56–1.67); p=0.90; I²=63%; n=334, 4 RCTs. NO SIGNIFICANT DIFFERENCE.",
        "other_outcomes": "Mortality RR 0.40 (95% CI 0.14–1.15; p=0.09). Lower weight gain with HMF: MD −1.08 g/kg/d (−1.96 to −0.21; p=0.02). No difference in length (MD −0.11 cm/wk) or head circumference (MD −0.02 cm/wk).",
        "conclusion": "Fortification with HMF compared with BMF decreased the risk of NEC but was associated with lower weight gain. GRADE quality of evidence low to very low; adequately powered, well-designed RCTs without industry influence are required.",
        "doi": "10.1093/advances/nmaa039",
        "notes": "Reports BOTH NEC (stage ≥II and surgical) AND late-onset sepsis as outcomes. NEC benefit lost in sensitivity analysis excluding high-risk-of-bias studies.",
    },
    "31697857": {
        "decision": "include",
        "entry": 69,
        "author": "Premkumar MH",
        "year": 2019,
        "journal": "Cochrane Database Syst Rev",
        "title": "Human milk-derived fortifier versus bovine milk-derived fortifier for prevention of mortality and morbidity in preterm neonates.",
        "study_type": "Cochrane systematic review and meta-analysis",
        "intervention": "Human milk-derived fortifier added to breast milk",
        "comparator": "Bovine milk-derived fortifier added to breast milk",
        "population": "Preterm neonates exclusively fed breast milk",
        "n_studies": "1 RCT met eligibility (low risk of bias)",
        "n_participants": "127 infants (NEC analysis n=125)",
        "nec_definition": "Necrotising enterocolitis",
        "nec_result": "RR 0.95 (95% CI 0.2–4.54); 1 study, 125 infants. LOW CERTAINTY evidence. Human milk-based fortifier did NOT decrease the risk of NEC.",
        "sepsis_definition": "Late-onset sepsis",
        "sepsis_result": "Human milk-derived fortifiers did NOT improve late-onset sepsis (specific estimate not in abstract). Low certainty evidence.",
        "other_outcomes": "Mortality, feeding intolerance, growth – no improvement with HMF vs BMF.",
        "conclusion": "Insufficient evidence evaluating HM-derived vs bovine milk-derived fortifier. Low-certainty evidence from one study suggests HM-derived fortifiers may NOT change the risk of NEC, mortality, feeding intolerance, infection, or improve growth. Well-designed RCTs needed.",
        "doi": "10.1002/14651858.CD013145.pub2",
        "notes": "Cochrane review. Only 1 eligible RCT. Addresses both NEC and late-onset sepsis as outcomes.",
    },
    "31645057": {
        "decision": "include",
        "entry": 70,
        "author": "Bührer C",
        "year": 2020,
        "journal": "Pediatr Res",
        "title": "Nutritional interventions to reduce rates of infection, necrotizing enterocolitis and mortality in very preterm infants.",
        "study_type": "Systematic review of meta-analyses and RCTs (narrative synthesis; results reported as RRs with 95% CI per intervention)",
        "intervention": "Human milk-based fortifier (one of several nutritional interventions reviewed)",
        "comparator": "Bovine milk-based fortifier",
        "population": "Very preterm infants",
        "n_studies": "Not specified in abstract (umbrella-style SR over multiple meta-analyses and RCTs)",
        "n_participants": "Not specified in abstract",
        "nec_definition": "Necrotizing enterocolitis (NEC) – stage not specified in abstract",
        "nec_result": "'No differences emerged between infants receiving human or bovine milk-based fortifiers' – NO pooled effect size for the HMBF vs BMBF arm reported in the abstract (qualitative statement).",
        "sepsis_definition": "Infections (sepsis / fungal sepsis / other infections)",
        "sepsis_result": "'No differences emerged between infants receiving human or bovine milk-based fortifiers' – also applies to infections. NO pooled effect size for HMBF vs BMBF on sepsis in the abstract.",
        "other_outcomes": "Also reviewed: donor human milk vs formula (DHM reduced NEC but not infections/mortality); bovine lactoferrin (reduced fungal sepsis only); prebiotic oligosaccharides (reduced infection); L-glutamine (lower infection); L-arginine (reduced NEC); multiple-strain probiotics (reduced NEC and mortality).",
        "conclusion": "Selected food components may help improve outcomes in preterm infants. For fortifier source specifically, no differences between human and bovine milk-based fortifiers on NEC, infections or mortality in this review.",
        "doi": "10.1038/s41390-019-0630-2",
        "notes": "Umbrella-style systematic review of MAs and RCTs across many nutritional interventions; HMBF vs BMBF is ONE sub-question among several. Conclusion for the fortifier arm is qualitative (no numeric pooled estimate given in the abstract).",
    },
    "28159204": {
        "decision": "include",
        "entry": 94,
        "author": "Mimouni FB",
        "year": 2017,
        "journal": "Clin Perinatol",
        "title": "The Use of Multinutrient Human Milk Fortifiers in Preterm Infants: A Systematic Review of Unanswered Questions.",
        "study_type": "Systematic review (narrative, no pooled meta-analysis)",
        "intervention": "Human milk-based fortifier",
        "comparator": "Cow milk-based (bovine) fortifier",
        "population": "Preterm infants on multinutrient-fortified human milk",
        "n_studies": "Number of included studies not specified in abstract",
        "n_participants": "Not specified in abstract",
        "nec_definition": "Necrotising enterocolitis",
        "nec_result": "LIMITED evidence that a bovine fortifier places the infant at a HIGHER risk of NEC compared with human milk-based fortifier (narrative conclusion; no pooled estimate reported in abstract).",
        "sepsis_definition": "Not reported in abstract as a dedicated analysis",
        "sepsis_result": "Not reported in abstract.",
        "other_outcomes": "Also addressed early vs late introduction of fortifiers; little evidence that early introduction affects important outcomes.",
        "conclusion": "Little evidence that early introduction of human milk fortification affects important outcomes; limited evidence that a bovine fortifier places the infant at a higher risk of NEC.",
        "doi": "10.1016/j.clp.2016.11.011",
        "notes": "Narrative systematic review covering TWO questions: (a) early vs late fortifier introduction, and (b) HMBF vs cow-based fortifier. No pooled meta-analysis in abstract; conclusion is qualitative.",
    },

    # ---------- BORDERLINE ----------
    "34101248": {
        "decision": "borderline",
        "entry": 42,
        "author": "Bridges KM",
        "year": 2021,
        "journal": "Nutr Clin Pract",
        "title": "Comparative effectiveness of liquid human milk fortifiers: A systematic review and meta-analysis.",
        "doi": "10.1002/ncp.10663",
        "reason": (
            "Primary comparison is LIQUID human milk fortifiers (incl. exclusive-HM-"
            "derived AND whey/casein hydrolysate = bovine-sourced) vs POWDER HMF "
            "(control, typically bovine). It is thus a liquid-vs-powder question "
            "with mixed sources on the liquid arm – not a clean HMBF vs CMBF head-"
            "to-head. Does report NEC and late-onset sepsis (no differences across "
            "treatments). Listed here only for user judgment."
        ),
    },
    "32302511": {
        "decision": "borderline",
        "entry": 65,
        "author": "van Katwyk S",
        "year": 2020,
        "journal": "Breastfeed Med",
        "title": "Economic Analysis of Exclusive Human Milk Diets for High-Risk Neonates, a Canadian Hospital Perspective.",
        "doi": "10.1089/bfm.2019.0273",
        "reason": (
            "Primary paper is a cost analysis. States 'A meta-analysis was performed "
            "to derive input parameters' for the economic model (EHMD vs standard, "
            "where EHMD includes human milk-derived fortifier). Does not present a "
            "stand-alone clinical-outcomes meta-analysis of NEC/sepsis in its "
            "abstract. Listed here only for user judgment."
        ),
    },

    # ---------- STAGE-1 CANDIDATES REJECTED AT STAGE 2 ----------
    "32726863": {
        "decision": "exclude",
        "entry": 55,
        "author": "Thanigainathan S",
        "year": 2020,
        "journal": "Cochrane Database Syst Rev",
        "title": "Early fortification of human milk versus late fortification to promote growth in preterm infants.",
        "doi": "10.1002/14651858.CD013392.pub2",
        "reason": (
            "Comparison is early vs late TIMING of multi-component fortification, "
            "not fortifier source. One included trial used bovine milk-based "
            "fortifier and the other used human milk-based fortifier, but no "
            "head-to-head HMBF-vs-BMBF comparison was performed. The paper does "
            "list fortifier type as a planned subgroup moderator, which is why "
            "it is picked up by Stage 1."
        ),
    },
}


# ============================================================================
# 6. Methods & Criteria sheet content
# ============================================================================

METHODS_CONTENT: list[tuple[str, str]] = [
    ("", ""),
    (
        "User's objective",
        "Identify meta-analyses, network meta-analyses and systematic reviews "
        "that DIRECTLY compare human-based milk fortifier vs bovine/cow-based "
        "milk fortifier on the outcomes of necrotising enterocolitis (any stage) "
        "and sepsis in preterm / low-birthweight infants.",
    ),
    ("", ""),
    (
        "Synonyms searched for – human-based fortifier",
        "human milk-based fortifier (HMBF), human milk-derived fortifier "
        "(HMF / HMDF), human-derived fortifier, 'human-based fortifier' "
        "(no 'milk' token), donor milk-based / donor-derived fortifier, "
        "exclusive human milk diet (EHMD), nested compounds such as 'human "
        "milk-based human milk fortifier', Prolacta (brand) – all mapped to "
        "the 'human-based' arm. Coordinated constructions 'human versus/or/and "
        "bovine ... fortifier' count as matches for both arms simultaneously.",
    ),
    (
        "Synonyms searched for – bovine / cow-based fortifier",
        "bovine milk-based fortifier (BMBF), bovine milk-derived fortifier "
        "(BMF), 'bovine-based fortifier' (no 'milk' token), cow milk-based "
        "fortifier (CMBF), cow's milk-based fortifier, 'bovine fortifier', "
        "cow milk-derived diet, nested compounds – all mapped to the "
        "'bovine/cow-based' arm.",
    ),
    (
        "Text normalisation",
        "Before matching, Unicode dash variants (en dash '–', em dash '—', "
        "non-breaking hyphen, figure dash, minus sign, soft hyphen, etc.) "
        "are mapped to a single hyphen-minus, and runs of whitespace are "
        "collapsed to one space. This ensures 'milk–derived fortifier' "
        "(en dash) is treated as 'milk-derived fortifier' and that patterns "
        "are not broken by line wrapping.",
    ),
    ("", ""),
    (
        "Outcomes required",
        "Necrotizing enterocolitis (NEC) – ANY stage/definition acceptable "
        "(Bell stage ≥II, surgical NEC, stage II–III, 'necrotising "
        "enterocolitis' as reported) AND/OR sepsis (early-onset, late-onset, "
        "invasive infection, neonatal sepsis).",
    ),
    ("", ""),
    (
        "Inclusion rule",
        "Entry must (i) be a systematic review / meta-analysis / network meta-"
        "analysis (not a primary RCT, not a narrative overview, not a cost-"
        "effectiveness paper), AND (ii) explicitly report a comparison between "
        "a human-based fortifier arm and a bovine/cow-based fortifier arm, AND "
        "(iii) report NEC and/or sepsis as an outcome.",
    ),
    ("", ""),
    (
        "Decision registry",
        "All inclusion/exclusion/borderline decisions live in the PMID-keyed "
        "DECISIONS dict inside the script, together with the extracted fields "
        "and, for excluded candidates, the rejection reason. Workbook rows "
        "are built from DECISIONS filtered by what the parser actually found "
        "in the input. Identity is by PMID, not by entry number.",
    ),
    ("", ""),
    (
        "Hard preconditions",
        "Before any workbook is written, main() enforces: (P1) input file "
        "exists; (P2) if EXPECTED_INPUT_SHA256 is set, the computed hash of "
        "the input matches it; (P3) every PMID in DECISIONS with "
        "decision='include' or 'borderline' is present in the parsed input; "
        "(P4) every Stage-1 candidate PMID has a documented decision in "
        "DECISIONS. If any precondition fails, the run aborts with a non-"
        "zero exit code and no workbook is written.",
    ),
    ("", ""),
    (
        "Final yield",
        "10 included entries (sheet 'Included MA_SR'), 2 borderline entries "
        "(sheet 'Borderline').",
    ),
    ("", ""),
    (
        "Note on NEC-only vs NEC + sepsis",
        "Of the 10 included entries, 8 report BOTH NEC and sepsis/infection "
        "outcomes (PMIDs 40729426, 40431391, 38542821, 32943531, 32277813, "
        "31697857, 31645057 explicitly; 41449441 reports NEC directly and "
        "sepsis via NMA ranking). PMIDs 41228457 (Reyes 2025) and 28159204 "
        "(Mimouni 2017) focus on NEC and do not report sepsis as a dedicated "
        "analysis in the abstract.",
    ),
    ("", ""),
    (
        "Change log",
        "v1: 9 included (initial run).\n"
        "v2: added PMID 31645057 (Bührer 2020) – user flagged that 'human OR "
        "bovine milk-based fortifiers' phrasing was missed; connector 'or' "
        "added.\n"
        "v3: refactored script with record parser and reconciliation. Fixed "
        "wrapped-citation parser bug and shared-head compound pattern. All "
        "10 included entries then flagged by Stage 1.\n"
        "v4: after adversarial testing. (a) Workbook content now depends on "
        "the parsed input via a PMID-keyed DECISIONS registry and three hard "
        "preconditions; empty or irrelevant input now aborts rather than "
        "silently producing the standard workbook. (b) Keyword panel widened: "
        "Unicode-dash normalisation, 'human-based fortifier' / 'bovine-based "
        "fortifier' with no 'milk' token, 'human versus bovine ... fortifier' "
        "shared-head coordination, and nested compounds such as 'human milk-"
        "derived human milk fortifier'.",
    ),
]


# ============================================================================
# 7. Excel writer
# ============================================================================

@dataclass
class Style:
    header_font: Font = field(default_factory=lambda: Font(name="Arial", bold=True, color="FFFFFF", size=11))
    header_fill: PatternFill = field(default_factory=lambda: PatternFill("solid", fgColor="305496"))
    cell_font: Font = field(default_factory=lambda: Font(name="Arial", size=10))
    label_font: Font = field(default_factory=lambda: Font(name="Arial", bold=True, size=11))
    body_font: Font = field(default_factory=lambda: Font(name="Arial", size=11))
    thin_border: Border = field(default_factory=lambda: Border(
        left=Side(style="thin", color="BFBFBF"),
        right=Side(style="thin", color="BFBFBF"),
        top=Side(style="thin", color="BFBFBF"),
        bottom=Side(style="thin", color="BFBFBF"),
    ))
    wrap_top: Alignment = field(default_factory=lambda: Alignment(wrap_text=True, vertical="top", horizontal="left"))
    wrap_centre: Alignment = field(default_factory=lambda: Alignment(wrap_text=True, vertical="center", horizontal="center"))


COL_WIDTHS = {
    "entry": 10, "author": 15, "year": 7, "journal": 18, "title": 42,
    "study_type": 22, "intervention": 26, "comparator": 26, "population": 26,
    "n_studies": 20, "n_participants": 22, "nec_definition": 24,
    "nec_result": 46, "sepsis_definition": 22, "sepsis_result": 46,
    "other_outcomes": 36, "conclusion": 46, "doi": 24, "pmid": 12, "notes": 36,
}

BORDERLINE_COL_WIDTHS = [10, 15, 8, 20, 50, 70, 24, 12]
METHODS_COL_WIDTHS = [42, 110]


def _style_header_row(ws, n_columns: int, style: Style) -> None:
    for col_idx in range(1, n_columns + 1):
        c = ws.cell(row=1, column=col_idx)
        c.font = style.header_font
        c.fill = style.header_fill
        c.alignment = style.wrap_centre
        c.border = style.thin_border


def _style_data_cells(ws, n_rows: int, n_columns: int, style: Style) -> None:
    for row_idx in range(2, 2 + n_rows):
        for col_idx in range(1, n_columns + 1):
            c = ws.cell(row=row_idx, column=col_idx)
            c.font = style.cell_font
            c.alignment = style.wrap_top
            c.border = style.thin_border


def write_included_sheet(wb: Workbook, records: list[dict], style: Style):
    ws = wb.active
    ws.title = "Included MA_SR"
    ws.append([COLUMN_HEADERS[c] for c in COLUMN_ORDER])
    for rec in records:
        ws.append([rec[c] for c in COLUMN_ORDER])
    _style_header_row(ws, len(COLUMN_ORDER), style)
    _style_data_cells(ws, len(records), len(COLUMN_ORDER), style)
    ws.freeze_panes = "C2"
    for col_name, width in COL_WIDTHS.items():
        col_letter = chr(ord("A") + COLUMN_ORDER.index(col_name))
        ws.column_dimensions[col_letter].width = width
    ws.row_dimensions[1].height = 48
    for row_idx in range(2, 2 + len(records)):
        ws.row_dimensions[row_idx].height = 230


def write_methods_sheet(wb: Workbook, content: list[tuple[str, str]], style: Style):
    ws = wb.create_sheet("Methods & Criteria")
    title_cell = ws["A1"]
    title_cell.value = "Methods used to extract these entries from the PubMed set"
    title_cell.font = Font(name="Arial", bold=True, size=14, color="FFFFFF")
    title_cell.fill = style.header_fill
    title_cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 28
    for i, (lab, text) in enumerate(content, start=2):
        ws.cell(row=i, column=1, value=lab).font = style.label_font
        ws.cell(row=i, column=2, value=text).font = style.body_font
        ws.cell(row=i, column=1).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=i, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = METHODS_COL_WIDTHS[0]
    ws.column_dimensions["B"].width = METHODS_COL_WIDTHS[1]
    for i in range(2, 2 + len(content)):
        txt = ws.cell(row=i, column=2).value or ""
        lines = max(1, txt.count("\n") + 1 + len(txt) // 120)
        ws.row_dimensions[i].height = max(18, min(220, lines * 16))


def write_borderline_sheet(wb: Workbook, records: list[dict], style: Style):
    ws = wb.create_sheet("Borderline")
    headers = ["Entry #", "First Author", "Year", "Journal", "Title",
               "Why borderline / why excluded from main table", "DOI", "PMID"]
    ws.append(headers)
    for rec in records:
        ws.append([rec["entry"], rec["author"], rec["year"], rec["journal"],
                   rec["title"], rec["reason"], rec["doi"], rec["pmid"]])
    _style_header_row(ws, len(headers), style)
    _style_data_cells(ws, len(records), len(headers), style)
    for i, w in enumerate(BORDERLINE_COL_WIDTHS):
        ws.column_dimensions[chr(ord("A") + i)].width = w
    ws.row_dimensions[1].height = 36
    for row_idx in range(2, 2 + len(records)):
        ws.row_dimensions[row_idx].height = 120
    ws.freeze_panes = "A2"


def build_workbook(included: list[dict], borderline: list[dict],
                   methods: list[tuple[str, str]]) -> Workbook:
    wb = Workbook()
    style = Style()
    write_included_sheet(wb, included, style)
    write_methods_sheet(wb, methods, style)
    write_borderline_sheet(wb, borderline, style)
    return wb


# ============================================================================
# 8. Reconciliation and preconditions
# ============================================================================

def compute_sha256(path: Path) -> str:
    """Return the hex-encoded SHA-256 of the file at *path*."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Reconciliation:
    """Outcome of comparing DECISIONS against the parsed input and Stage-1
    screen. Non-empty error lists indicate a precondition failure.
    """
    parsed_pmids: set[str]
    candidate_pmids: set[str]
    missing_includes: list[str]            # P3 failures
    missing_borderlines: list[str]         # P3 failures (borderline not in input)
    awaiting_review: list[str]             # P4 failures
    stage2_excluded_hits: list[str]        # candidates correctly rejected at S2
    stage1_misses: list[str]               # included PMIDs not flagged by S1


def reconcile(records: list[PubmedRecord],
              candidates: list[ScreeningResult]) -> Reconciliation:
    parsed_pmids = {r.pmid for r in records if r.pmid}
    candidate_pmids = {c.record.pmid for c in candidates if c.record.pmid}
    included = {p for p, d in DECISIONS.items() if d["decision"] == "include"}
    borderline = {p for p, d in DECISIONS.items() if d["decision"] == "borderline"}
    excluded = {p for p, d in DECISIONS.items() if d["decision"] == "exclude"}
    documented = included | borderline | excluded
    return Reconciliation(
        parsed_pmids=parsed_pmids,
        candidate_pmids=candidate_pmids,
        missing_includes=sorted(included - parsed_pmids),
        missing_borderlines=sorted(borderline - parsed_pmids),
        awaiting_review=sorted(candidate_pmids - documented),
        stage2_excluded_hits=sorted(candidate_pmids & excluded),
        stage1_misses=sorted(included - candidate_pmids),
    )


def _format_candidate(pmid: str, records_by_pmid: dict[str, PubmedRecord]) -> str:
    r = records_by_pmid.get(pmid)
    if r is None:
        return f"PMID {pmid} (not in parsed input)"
    header = r.header[:80] + ("…" if len(r.header) > 80 else "")
    return f"PMID {pmid}  entry #{r.number:>3}  {header}"


# ============================================================================
# 9. Main
# ============================================================================

def main() -> int:
    # ---- P1: input exists -------------------------------------------------
    if not INPUT_FILE.exists():
        print(f"ERROR (P1): input file not found: {INPUT_FILE}", file=sys.stderr)
        return 1

    # ---- P2: optional file-identity check ---------------------------------
    actual_hash = compute_sha256(INPUT_FILE)
    print(f"Input file: {INPUT_FILE}")
    print(f"Input SHA-256: {actual_hash}")
    if EXPECTED_INPUT_SHA256 is None:
        print("EXPECTED_INPUT_SHA256 not set — hash check skipped.")
    elif actual_hash != EXPECTED_INPUT_SHA256:
        print("ERROR (P2): input file hash does not match expected hash.",
              file=sys.stderr)
        print(f"  Expected: {EXPECTED_INPUT_SHA256}", file=sys.stderr)
        print(f"  Actual:   {actual_hash}", file=sys.stderr)
        print("  Either you are running against a different input file, or "
              "the input has been edited since the DECISIONS registry was "
              "curated. Verify the input and update EXPECTED_INPUT_SHA256 "
              "if the new input is intentional.", file=sys.stderr)
        return 2
    else:
        print("Input identity confirmed (SHA-256 matches EXPECTED_INPUT_SHA256).")

    # ---- Parse and screen -------------------------------------------------
    records = read_records(INPUT_FILE)
    print(f"\nParsed {len(records)} PubMed records.")
    records_by_pmid = {r.pmid: r for r in records if r.pmid}

    screening = screen(records)
    candidates = [s for s in screening if s.is_candidate]
    print(f"Stage-1 automated screening flagged {len(candidates)} candidate records:")
    for s in candidates:
        print(f"  • " + _format_candidate(s.record.pmid or "—", records_by_pmid))

    # ---- Reconcile against DECISIONS --------------------------------------
    rec = reconcile(records, candidates)
    print()

    # ---- P3: every included and borderline PMID must be in input ----------
    if rec.missing_includes or rec.missing_borderlines:
        print("ERROR (P3): curated records missing from the parsed input:",
              file=sys.stderr)
        for pmid in rec.missing_includes:
            d = DECISIONS[pmid]
            print(f"  INCLUDE   PMID {pmid}  (expected entry #{d['entry']} — "
                  f"{d['author']} {d['year']})", file=sys.stderr)
        for pmid in rec.missing_borderlines:
            d = DECISIONS[pmid]
            print(f"  BORDER    PMID {pmid}  (expected entry #{d['entry']} — "
                  f"{d['author']} {d['year']})", file=sys.stderr)
        print("  The input file does not contain every article the "
              "DECISIONS registry references. Either the input is "
              "incomplete or the registry is stale. No workbook written.",
              file=sys.stderr)
        return 3

    # ---- P4: every Stage-1 candidate must have a documented decision ------
    if rec.awaiting_review:
        print("ERROR (P4): Stage-1 candidates with no documented decision "
              "(AWAITING REVIEW):", file=sys.stderr)
        for pmid in rec.awaiting_review:
            print(f"  • " + _format_candidate(pmid, records_by_pmid),
                  file=sys.stderr)
        print("  Add an entry for each to DECISIONS with decision set to "
              "'include', 'exclude' or 'borderline' before regenerating "
              "the workbook. No workbook written.", file=sys.stderr)
        return 4

    # ---- All preconditions passed. Report Stage-1/Stage-2 agreement -------
    if rec.stage1_misses:
        print(f"NOTE: {len(rec.stage1_misses)} included PMIDs were NOT "
              f"flagged by Stage 1 (manual curation would have been "
              f"required): {rec.stage1_misses}")
        print("  Consider widening the Stage-1 keyword panels if these "
              "should have been caught automatically.")
    if rec.stage2_excluded_hits:
        print(f"Stage-1 candidates correctly rejected at Stage 2: "
              f"{rec.stage2_excluded_hits}")

    # ---- Build workbook (DECISIONS filtered by parsed input) --------------
    included_rows = []
    borderline_rows = []
    for pmid, d in DECISIONS.items():
        if d["decision"] not in ("include", "borderline"):
            continue
        parsed = records_by_pmid.get(pmid)
        if parsed is None:
            # Already caught by P3 above; defensive.
            continue
        row = dict(d)
        row["pmid"] = pmid
        row["entry"] = parsed.number  # position in the parsed input
        if d["decision"] == "include":
            included_rows.append(row)
        else:
            borderline_rows.append(row)

    # Sort included rows by year descending, then by author.
    included_rows.sort(key=lambda r: (-int(r["year"]), str(r["author"])))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    wb = build_workbook(included_rows, borderline_rows, METHODS_CONTENT)
    wb.save(OUTPUT_FILE)
    print(f"\nSaved workbook: {OUTPUT_FILE}")
    print(f"  Included:   {len(included_rows)} entries")
    print(f"  Borderline: {len(borderline_rows)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
