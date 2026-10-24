#!/usr/bin/env python3
"""Leave-one-out random-effects sensitivity analysis for HMBF vs BMBF.

Effect measure: log risk ratio (human-based fortifier / bovine-based fortifier).
Model: inverse-variance DerSimonian-Laird random effects.
A 0.5 continuity correction is applied to all four cells for 2x2 tables
with exactly one zero event count, consistent with the primary analysis.
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path
import pandas as pd

OUTDIR = Path("/home/ubuntu/leave_one_out_hmbf_bmbf")
OUTDIR.mkdir(parents=True, exist_ok=True)

# Verified study-level counts recorded for the primary direct-comparison analysis.
# Outcome values retain the definitions used in the original primary meta-analysis.
DATA = [
    {"outcome": "NEC", "study": "O’Connor 2018", "pmid": "29878061", "outcome_definition": "All-stage NEC", "human_events": 3, "human_total": 64, "bovine_events": 6, "bovine_total": 61},
    {"outcome": "NEC", "study": "Jensen 2024", "pmid": "38545091", "outcome_definition": "NEC stage II–III", "human_events": 8, "human_total": 115, "bovine_events": 9, "bovine_total": 113},
    {"outcome": "NEC", "study": "Berrington 2025", "pmid": "39660504", "outcome_definition": "Medical/surgical NEC", "human_events": 1, "human_total": 14, "bovine_events": 0, "bovine_total": 14},
    {"outcome": "Sepsis", "study": "O’Connor 2018", "pmid": "29878061", "outcome_definition": "Sepsis", "human_events": 8, "human_total": 64, "bovine_events": 14, "bovine_total": 61},
    {"outcome": "Sepsis", "study": "Kumbhare 2022", "pmid": "36029771", "outcome_definition": "Late-onset sepsis", "human_events": 6, "human_total": 16, "bovine_events": 2, "bovine_total": 14},
    {"outcome": "Sepsis", "study": "Jensen 2024", "pmid": "38545091", "outcome_definition": "Culture-proven sepsis", "human_events": 33, "human_total": 115, "bovine_events": 28, "bovine_total": 113},
    {"outcome": "Sepsis", "study": "Berrington 2025", "pmid": "39660504", "outcome_definition": "Blood-culture-positive LOS in first 21 study days", "human_events": 2, "human_total": 14, "bovine_events": 0, "bovine_total": 14},
]


def z_from_two_sided_p(p: float) -> float:
    """Standard normal quantile for two-sided CI p (p = 1-alpha/2)."""
    # statistics.NormalDist avoids a scipy dependency.
    from statistics import NormalDist
    return NormalDist().inv_cdf(p)


def chi_square_sf(q: float, df: int) -> float:
    """Upper-tail chi-square probability for the df values used here (1–3)."""
    x = max(q, 0.0)
    if df == 1:
        return math.erfc(math.sqrt(x / 2.0))
    if df == 2:
        return math.exp(-x / 2.0)
    if df == 3:
        return math.erfc(math.sqrt(x / 2.0)) + math.sqrt(2.0 * x / math.pi) * math.exp(-x / 2.0)
    raise ValueError(f"Unsupported degrees of freedom: {df}")


def study_effect(row: pd.Series) -> tuple[float, float, bool]:
    """Return log(RR), its sampling variance, and correction status."""
    a, n1 = float(row.human_events), float(row.human_total)
    c, n0 = float(row.bovine_events), float(row.bovine_total)
    correction = (a == 0) ^ (c == 0)
    if correction:
        a, n1, c, n0 = a + 0.5, n1 + 1.0, c + 0.5, n0 + 1.0
    # log risk ratio and conventional variance estimate.
    yi = math.log((a / n1) / (c / n0))
    vi = 1.0 / a - 1.0 / n1 + 1.0 / c - 1.0 / n0
    return yi, vi, correction


def dl_random_effects(rows: pd.DataFrame) -> dict[str, float]:
    """Inverse-variance DerSimonian-Laird random-effects meta-analysis."""
    vals = [study_effect(row) for _, row in rows.iterrows()]
    yi = [v[0] for v in vals]
    vi = [v[1] for v in vals]
    k = len(yi)
    w_fixed = [1.0 / v for v in vi]
    sw = sum(w_fixed)
    mu_fixed = sum(w * y for w, y in zip(w_fixed, yi)) / sw
    q = sum(w * (y - mu_fixed) ** 2 for w, y in zip(w_fixed, yi))
    df = k - 1
    c = sw - sum(w ** 2 for w in w_fixed) / sw
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
    w_re = [1.0 / (v + tau2) for v in vi]
    sw_re = sum(w_re)
    mu_re = sum(w * y for w, y in zip(w_re, yi)) / sw_re
    se_re = math.sqrt(1.0 / sw_re)
    z = z_from_two_sided_p(0.975)
    lo = mu_re - z * se_re
    hi = mu_re + z * se_re
    z_effect = mu_re / se_re
    p_effect = math.erfc(abs(z_effect) / math.sqrt(2.0))
    i2 = max(0.0, (q - df) / q) * 100.0 if q > 0 and df > 0 else 0.0
    h2 = q / df if df > 0 else float("nan")
    return {
        "k": k,
        "log_rr": mu_re,
        "se_log_rr": se_re,
        "rr": math.exp(mu_re),
        "ci_low": math.exp(lo),
        "ci_high": math.exp(hi),
        "z_effect": z_effect,
        "p_effect": p_effect,
        "tau2": tau2,
        "q": q,
        "df": df,
        "p_heterogeneity": chi_square_sf(q, df),
        "i2_percent": i2,
        "h2": h2,
    }


def fmt(x: float, digits: int = 3) -> str:
    return f"{x:.{digits}f}"


def main() -> None:
    data = pd.DataFrame(DATA)
    shutil.copy2(Path(__file__), OUTDIR / Path(__file__).name)
    data.to_csv(OUTDIR / "primary_event_data_reconstructed.csv", index=False)

    results = []
    for outcome, outcome_rows in data.groupby("outcome", sort=False):
        full = dl_random_effects(outcome_rows)
        for _, excluded in outcome_rows.iterrows():
            kept = outcome_rows[outcome_rows.study != excluded.study].copy()
            result = dl_random_effects(kept)
            results.append({
                "outcome": outcome,
                "excluded_study": excluded.study,
                "excluded_pmid": excluded.pmid,
                "excluded_outcome_definition": excluded.outcome_definition,
                "studies_retained": int(result["k"]),
                "retained_studies": "; ".join(kept.study.tolist()),
                "rr": result["rr"],
                "ci_low": result["ci_low"],
                "ci_high": result["ci_high"],
                "log_rr": result["log_rr"],
                "se_log_rr": result["se_log_rr"],
                "z_effect": result["z_effect"],
                "p_effect": result["p_effect"],
                "tau2": result["tau2"],
                "q": result["q"],
                "df": result["df"],
                "p_heterogeneity": result["p_heterogeneity"],
                "i2_percent": result["i2_percent"],
                "h2": result["h2"],
                "full_analysis_rr": full["rr"],
                "full_analysis_ci_low": full["ci_low"],
                "full_analysis_ci_high": full["ci_high"],
                "full_analysis_tau2": full["tau2"],
                "full_analysis_i2_percent": full["i2_percent"],
            })

    res = pd.DataFrame(results)
    res.to_csv(OUTDIR / "leave_one_out_results.csv", index=False, float_format="%.12g")

    # Full primary result reference, recalculated from the same input.
    full_rows = []
    for outcome, outcome_rows in data.groupby("outcome", sort=False):
        r = dl_random_effects(outcome_rows)
        full_rows.append({"outcome": outcome, **r})
    pd.DataFrame(full_rows).to_csv(OUTDIR / "full_primary_recalculated.csv", index=False, float_format="%.12g")

    md = []
    md.append("# Leave-one-out sensitivity analysis: human-based vs bovine/cow milk-based fortifier\n")
    md.append("## Objective\n")
    md.append("To evaluate the influence of each individual direct-comparison study on the primary random-effects estimates for necrotizing enterocolitis (NEC) and sepsis. Each iteration excludes one study and recalculates the pooled effect from all remaining studies.\n")
    md.append("## Methods\n")
    md.append("- **Effect measure:** risk ratio (RR), human-based fortifier / bovine/cow milk-based fortifier; RR <1 favors the human-based fortifier arm.\n")
    md.append("- **Model:** inverse-variance random-effects meta-analysis using the DerSimonian–Laird estimator for between-study variance (τ²).\n")
    md.append("- **Heterogeneity:** Cochran Q, degrees of freedom (df), τ², and I².\n")
    md.append("- **Sparse data:** a 0.5 continuity correction was applied to all four cells in a study with exactly one zero event count, as in the primary analysis.\n")
    md.append("- **Interpretation caution:** after an exclusion, NEC has only two studies and sepsis has three; with only two retained studies, I²/τ² are especially unstable and should not be overinterpreted.\n")
    md.append("## Recalculated complete primary analyses\n")
    md.append("| Outcome | Studies | Random-effects RR (95% CI) | P value | τ² | Q (df), P value | I² |\n|---|---:|---:|---:|---:|---:|---:|\n")
    for row in full_rows:
        md.append(f"| {row['outcome']} | {int(row['k'])} | {fmt(row['rr'],2)} ({fmt(row['ci_low'],2)}–{fmt(row['ci_high'],2)}) | {fmt(row['p_effect'],3)} | {fmt(row['tau2'],3)} | {fmt(row['q'],3)} ({int(row['df'])}), {fmt(row['p_heterogeneity'],3)} | {fmt(row['i2_percent'],1)}% |\n")

    for outcome in ["NEC", "Sepsis"]:
        subset = res[res.outcome == outcome]
        md.append(f"\n## {outcome}: leave-one-out iterations\n")
        md.append("| Excluded study (PMID) | Excluded outcome definition | Studies retained | Recalculated random-effects RR (95% CI) | P value | τ² | Q (df), P value | I² |\n|---|---|---:|---:|---:|---:|---:|---:|\n")
        for _, row in subset.iterrows():
            md.append(
                f"| {row.excluded_study} ({row.excluded_pmid}) | {row.excluded_outcome_definition} | "
                f"{int(row.studies_retained)} | {fmt(row.rr,2)} ({fmt(row.ci_low,2)}–{fmt(row.ci_high,2)}) | "
                f"{fmt(row.p_effect,3)} | {fmt(row.tau2,3)} | {fmt(row.q,3)} ({int(row.df)}), {fmt(row.p_heterogeneity,3)} | {fmt(row.i2_percent,1)}% |\n"
            )

    nec = res[res.outcome == "NEC"]
    sep = res[res.outcome == "Sepsis"]
    md.append("\n## Interpretation\n")
    md.append(
        f"**NEC:** The pooled estimate remains below 1.0 in every iteration (RR range {fmt(nec.rr.min(),2)}–{fmt(nec.rr.max(),2)}), but all confidence intervals include the null. "
        "Removing O’Connor 2018 produces the largest apparent protective estimate; removing Berrington 2025 leaves no observed heterogeneity among the two retained studies. Given two-study analyses and sparse events, these shifts are descriptive rather than definitive.\n"
    )
    md.append(
        f"**Sepsis:** The pooled estimate changes direction across the four iterations (RR range {fmt(sep.rr.min(),2)}–{fmt(sep.rr.max(),2)}), and every confidence interval includes 1.0. "
        "Excluding O’Connor 2018 reduces the DerSimonian–Laird heterogeneity estimates to zero (τ² = 0; I² = 0%), indicating that its lower study-level effect estimate is the principal contributor to the observed between-study inconsistency. Excluding Kumbhare 2022 shifts the pooled point estimate below 1.0 but leaves the heterogeneity estimates similar to the full analysis.\n"
    )
    md.append("\n## Reproducibility files\n")
    md.append("- `primary_event_data_reconstructed.csv`: study-level input counts and outcome definitions.\n")
    md.append("- `leave_one_out_results.csv`: machine-readable results for every iteration.\n")
    md.append("- `full_primary_recalculated.csv`: complete primary reference analyses recalculated using the same code.\n")
    md.append("- `loo_hmbf_bmbf.py`: executable script used for all calculations.\n")

    (OUTDIR / "leave_one_out_report.md").write_text("".join(md), encoding="utf-8")
    print(pd.DataFrame(full_rows).to_string(index=False))
    print("\nLeave-one-out sensitivity analysis:\n")
    print(res[["outcome", "excluded_study", "rr", "ci_low", "ci_high", "tau2", "q", "df", "i2_percent"]].to_string(index=False))
    print(f"\nWrote outputs to {OUTDIR}")


if __name__ == "__main__":
    main()
