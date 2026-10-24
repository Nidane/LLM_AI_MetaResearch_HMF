#!/usr/bin/env python3
"""RECONSTRUCTED primary direct-comparison meta-analysis: HMBF vs BMBF.

This standalone script was rebuilt after the sandbox reset from the verified
study-level event data and the documented original analysis specification.
It reproduces the PRIMARY direct-comparison RR meta-analyses for NEC and sepsis.

Effect measure: risk ratio (RR), HMBF / BMBF; RR < 1 favours HMBF.
Model: inverse-variance fixed and DerSimonian-Laird random effects on log(RR).
Sparse data: a 0.5 continuity correction is applied to all four 2x2 cells when
exactly one event cell is zero.

This is not represented as the byte-identical original file, which was lost in
the sandbox reset. It is a verified reconstruction of the primary RR analysis.
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path
from statistics import NormalDist

import pandas as pd

OUTDIR = Path("/home/ubuntu/primary_hmbf_bmbf_meta_analysis")
OUTDIR.mkdir(parents=True, exist_ok=True)

# Verified final primary direct-comparison event counts.  Outcome definitions are
# deliberately retained because definitions were not completely identical across trials.
DATA = [
    {"outcome": "NEC", "study": "O’Connor 2018", "pmid": "29878061", "outcome_definition": "All-stage NEC", "human_events": 3, "human_total": 64, "bovine_events": 6, "bovine_total": 61},
    {"outcome": "NEC", "study": "Jensen 2024", "pmid": "38545091", "outcome_definition": "NEC stage II–III", "human_events": 8, "human_total": 115, "bovine_events": 9, "bovine_total": 113},
    {"outcome": "NEC", "study": "Berrington 2025", "pmid": "39660504", "outcome_definition": "Medical/surgical NEC", "human_events": 1, "human_total": 14, "bovine_events": 0, "bovine_total": 14},
    {"outcome": "Sepsis", "study": "O’Connor 2018", "pmid": "29878061", "outcome_definition": "Sepsis", "human_events": 8, "human_total": 64, "bovine_events": 14, "bovine_total": 61},
    {"outcome": "Sepsis", "study": "Kumbhare 2022", "pmid": "36029771", "outcome_definition": "Late-onset sepsis", "human_events": 6, "human_total": 16, "bovine_events": 2, "bovine_total": 14},
    {"outcome": "Sepsis", "study": "Jensen 2024", "pmid": "38545091", "outcome_definition": "Culture-proven sepsis", "human_events": 33, "human_total": 115, "bovine_events": 28, "bovine_total": 113},
    {"outcome": "Sepsis", "study": "Berrington 2025", "pmid": "39660504", "outcome_definition": "Blood-culture-positive late-onset sepsis in first 21 study days", "human_events": 2, "human_total": 14, "bovine_events": 0, "bovine_total": 14},
]

# Key eligibility decisions, included to preserve the primary-comparison scope.
SCREENING = [
    {"study": "O’Connor 2018", "pmid": "29878061", "primary_direct_comparison": "Included", "reason": "Direct HMBF vs BMBF comparison; NEC and sepsis data available."},
    {"study": "Kumbhare 2022", "pmid": "36029771", "primary_direct_comparison": "Included for sepsis only", "reason": "Direct H2MF vs BHMF comparison; late-onset sepsis data available; NEC data not included in primary dataset."},
    {"study": "Jensen 2024", "pmid": "38545091", "primary_direct_comparison": "Included", "reason": "Direct HMBF vs BMBF comparison; NEC and culture-proven sepsis data available."},
    {"study": "Berrington 2025", "pmid": "39660504", "primary_direct_comparison": "Included", "reason": "Direct PHMF vs PBMF comparison; medical/surgical NEC and first-21-day culture-positive LOS data available."},
    {"study": "Uthaya 2022", "pmid": "35809401", "primary_direct_comparison": "Sensitivity only", "reason": "Randomised diet differed in donor milk/formula exposure as well as fortifier source."},
    {"study": "Embleton 2023", "pmid": "36857051", "primary_direct_comparison": "Sensitivity only", "reason": "Randomised diet differed in donor milk/formula exposure as well as fortifier source."},
]


def norm_ppf(probability: float) -> float:
    return NormalDist().inv_cdf(probability)


def chi_square_sf(q: float, df: int) -> float:
    """Chi-square upper-tail probability for the degrees of freedom here (1–3)."""
    x = max(float(q), 0.0)
    if df == 1:
        return math.erfc(math.sqrt(x / 2.0))
    if df == 2:
        return math.exp(-x / 2.0)
    if df == 3:
        return math.erfc(math.sqrt(x / 2.0)) + math.sqrt(2.0 * x / math.pi) * math.exp(-x / 2.0)
    raise ValueError(f"Unsupported degrees of freedom: {df}")


def study_log_rr(row: pd.Series) -> dict[str, float | bool]:
    """Calculate a study log-RR, sampling variance, and correction indicator."""
    a, n_h = float(row.human_events), float(row.human_total)
    c, n_b = float(row.bovine_events), float(row.bovine_total)
    continuity_correction = (a == 0) ^ (c == 0)
    if continuity_correction:
        # Haldane-Anscombe-style correction used in the original primary analysis.
        a, n_h, c, n_b = a + 0.5, n_h + 1.0, c + 0.5, n_b + 1.0
    log_rr = math.log((a / n_h) / (c / n_b))
    variance = 1.0 / a - 1.0 / n_h + 1.0 / c - 1.0 / n_b
    se = math.sqrt(variance)
    z = norm_ppf(0.975)
    return {
        "log_rr": log_rr,
        "variance_log_rr": variance,
        "se_log_rr": se,
        "study_rr": math.exp(log_rr),
        "study_rr_ci_low": math.exp(log_rr - z * se),
        "study_rr_ci_high": math.exp(log_rr + z * se),
        "continuity_correction": continuity_correction,
    }


def pool_meta_analysis(rows: pd.DataFrame) -> tuple[dict[str, float], pd.DataFrame]:
    """Calculate fixed- and DerSimonian-Laird random-effects results."""
    work = rows.copy()
    effect_rows = [study_log_rr(r) for _, r in work.iterrows()]
    effects = pd.DataFrame(effect_rows)
    work = pd.concat([work.reset_index(drop=True), effects], axis=1)

    yi = work.log_rr.tolist()
    vi = work.variance_log_rr.tolist()
    w_fixed = [1.0 / v for v in vi]
    sw_fixed = sum(w_fixed)
    mu_fixed = sum(w * y for w, y in zip(w_fixed, yi)) / sw_fixed
    se_fixed = math.sqrt(1.0 / sw_fixed)
    z_critical = norm_ppf(0.975)
    q = sum(w * (y - mu_fixed) ** 2 for w, y in zip(w_fixed, yi))
    df = len(yi) - 1
    c = sw_fixed - sum(w * w for w in w_fixed) / sw_fixed
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0

    w_random = [1.0 / (v + tau2) for v in vi]
    sw_random = sum(w_random)
    mu_random = sum(w * y for w, y in zip(w_random, yi)) / sw_random
    se_random = math.sqrt(1.0 / sw_random)
    i2 = max(0.0, (q - df) / q) * 100.0 if q > 0 and df > 0 else 0.0
    p_heterogeneity = chi_square_sf(q, df)

    def row_for_model(model: str, log_effect: float, se: float) -> dict[str, float | str]:
        z_effect = log_effect / se
        return {
            "model": model,
            "k": len(yi),
            "log_rr": log_effect,
            "se_log_rr": se,
            "rr": math.exp(log_effect),
            "ci_low": math.exp(log_effect - z_critical * se),
            "ci_high": math.exp(log_effect + z_critical * se),
            "z_effect": z_effect,
            "p_effect": math.erfc(abs(z_effect) / math.sqrt(2.0)),
            "tau2": 0.0 if model == "Fixed effect" else tau2,
            "q": q,
            "df": df,
            "p_heterogeneity": p_heterogeneity,
            "i2_percent": i2,
            "h2": q / df if df > 0 else float("nan"),
        }

    work["fixed_effect_weight_percent"] = [100.0 * w / sw_fixed for w in w_fixed]
    work["random_effects_weight_percent"] = [100.0 * w / sw_random for w in w_random]
    return {"fixed": row_for_model("Fixed effect", mu_fixed, se_fixed), "random": row_for_model("Random effects (DerSimonian-Laird)", mu_random, se_random)}, work


def f(x: float, digits: int = 3) -> str:
    return f"{x:.{digits}f}"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), OUTDIR / Path(__file__).name)
    data = pd.DataFrame(DATA)
    screening = pd.DataFrame(SCREENING)
    data.to_csv(OUTDIR / "primary_event_data.csv", index=False)
    screening.to_csv(OUTDIR / "screening_scope_summary.csv", index=False)

    pooled_rows, study_rows = [], []
    for outcome, outcome_data in data.groupby("outcome", sort=False):
        models, individual = pool_meta_analysis(outcome_data)
        study_rows.append(individual)
        for model in [models["fixed"], models["random"]]:
            pooled_rows.append({"outcome": outcome, **model})

    study_effects = pd.concat(study_rows, ignore_index=True)
    pooled = pd.DataFrame(pooled_rows)
    study_effects.to_csv(OUTDIR / "study_level_rr_effects.csv", index=False, float_format="%.12g")
    pooled.to_csv(OUTDIR / "pooled_results.csv", index=False, float_format="%.12g")

    random_rows = pooled[pooled.model == "Random effects (DerSimonian-Laird)"].copy()
    report = []
    report.append("# Reconstructed primary direct-comparison meta-analysis: human-based vs bovine/cow milk-based fortifier\n\n")
    report.append("> **Reconstruction note:** The byte-identical original `run_hmbf_bmbf_meta.py` was lost in the sandbox reset. This script was rebuilt from the final verified event data and recorded method specification, and its primary random-effects results have been checked against the original reported results.\n\n")
    report.append("## Scope\n\n")
    report.append("This program reproduces the **primary direct-comparison** meta-analysis, not the broader diet-package sensitivity analysis. The primary comparison includes only trials in which the randomised comparison sufficiently isolates human-based/human-derived versus bovine/cow milk-based fortifier.\n\n")
    report.append("## Methods\n\n")
    report.append("- **Effect measure:** risk ratio (RR), human-based fortifier / bovine/cow milk-based fortifier; RR <1 favours human-based fortifier.\n")
    report.append("- **Pooling:** inverse-variance fixed-effect and DerSimonian–Laird random-effects meta-analysis on the log-RR scale.\n")
    report.append("- **Heterogeneity:** Cochran Q, degrees of freedom, P value for heterogeneity, I², H², and τ².\n")
    report.append("- **Sparse data:** a 0.5 continuity correction is applied to all four 2×2 cells where exactly one event cell is zero.\n\n")
    report.append("## Primary random-effects results\n\n")
    report.append("| Outcome | Studies | RR (95% CI) | P value | τ² | Q (df), P value | I² |\n|---|---:|---:|---:|---:|---:|---:|\n")
    for _, r in random_rows.iterrows():
        report.append(f"| {r.outcome} | {int(r.k)} | {f(r.rr,2)} ({f(r.ci_low,2)}–{f(r.ci_high,2)}) | {f(r.p_effect,3)} | {f(r.tau2,3)} | {f(r.q,3)} ({int(r.df)}), {f(r.p_heterogeneity,3)} | {f(r.i2_percent,1)}% |\n")
    report.append("\n## Included study-level data and effects\n\n")
    report.append("| Outcome | Study (PMID) | Human events/total | Bovine events/total | Definition | Study RR (95% CI) | Continuity correction |\n|---|---|---:|---:|---|---:|---:|\n")
    for _, r in study_effects.iterrows():
        cc = "Yes" if r.continuity_correction else "No"
        report.append(f"| {r.outcome} | {r.study} ({r.pmid}) | {int(r.human_events)}/{int(r.human_total)} | {int(r.bovine_events)}/{int(r.bovine_total)} | {r.outcome_definition} | {f(r.study_rr,2)} ({f(r.study_rr_ci_low,2)}–{f(r.study_rr_ci_high,2)}) | {cc} |\n")
    report.append("\n## Files\n\n")
    report.append("- `run_hmbf_bmbf_meta.py`: executable reconstructed primary-analysis script.\n")
    report.append("- `primary_event_data.csv`: verified input counts and outcome definitions.\n")
    report.append("- `study_level_rr_effects.csv`: individual study log-RRs, CIs, correction flags, and weights.\n")
    report.append("- `pooled_results.csv`: fixed-effect and random-effects pooled results.\n")
    report.append("- `screening_scope_summary.csv`: primary-analysis inclusion/sensitivity scope.\n")
    (OUTDIR / "primary_meta_analysis_report.md").write_text("".join(report), encoding="utf-8")

    print("Primary direct-comparison meta-analysis results")
    print(random_rows[["outcome", "k", "rr", "ci_low", "ci_high", "p_effect", "tau2", "q", "df", "p_heterogeneity", "i2_percent"]].to_string(index=False))
    print(f"\nOutputs written to {OUTDIR}")


if __name__ == "__main__":
    main()
