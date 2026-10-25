#!/usr/bin/env python3
"""Reproducible meta-analysis for human-based versus bovine/cow milk fortifier/diet trials.

Analysis choices mirror the latest agreed analysis in this project:
- Risk ratio (human-based / bovine-cow comparator) as the relative effect.
- DerSimonian-Laird random-effects model on log(RR), with normal 95% CIs and z tests.
- 0.5 continuity correction added to all four cells only for single-zero studies.
- Double-zero NEC trial (Hagelberg 1990) listed descriptively but excluded from log-RR pooling.
- Hagelberg sepsis is included using narrative-derived post-fortification event counts (1/10 vs 2/10).
- Absolute effects are translated from pooled RR using aggregate comparator risk from all eligible
  arms for that comparison; uncertainty in the comparator baseline risk is not propagated.

Outputs are written under ./results and ./figures relative to this script.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from scipy.stats import chi2, norm

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "study_data.csv"
RESULTS_DIR = BASE / "results"
FIGURES_DIR = BASE / "figures"
RESULTS_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(exist_ok=True)

ANALYSES = [
    ("primary_direct_NEC", "Primary direct fortifier-only — NEC", "A", "Necrotizing enterocolitis (NEC)"),
    ("primary_direct_sepsis", "Primary direct fortifier-only — sepsis", "B", "Sepsis"),
    ("broader_diet_NEC", "Secondary broader human-milk diet strategy — NEC", "A", "Necrotizing enterocolitis (NEC)"),
    ("broader_diet_sepsis", "Secondary broader human-milk diet strategy — sepsis", "B", "Sepsis"),
]


def truthy(x: Any) -> bool:
    return str(x).strip().lower() in {"yes", "y", "true", "1"}


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for col in ("year", "human_events", "human_total", "comparator_events", "comparator_total"):
            row[col] = int(row[col])
        row["include_in_logrr_pool_bool"] = truthy(row["include_in_logrr_pool"])
    return rows


DATA = read_csv_rows(DATA_PATH)


def observed_cell_counts(row: dict[str, Any]) -> tuple[int, int, int, int]:
    a = int(row["human_events"])
    n1 = int(row["human_total"])
    c = int(row["comparator_events"])
    n0 = int(row["comparator_total"])
    if not (0 <= a <= n1 and 0 <= c <= n0):
        raise ValueError(f"Invalid binomial counts in {row['study']}: {a}/{n1} vs {c}/{n0}")
    return a, n1 - a, c, n0 - c


def study_effect(row: dict[str, Any]) -> dict[str, Any]:
    """Calculate study-level log RR, variance, RR and Wald CI, using only0 correction."""
    a, b, c, d = observed_cell_counts(row)
    if a == 0 and c == 0:
        return {
            **row, "estimable": False, "continuity_correction": False,
            "corrected_human_events": None, "corrected_human_total": None,
            "corrected_comparator_events": None, "corrected_comparator_total": None,
            "yi_log_rr": None, "vi_log_rr": None, "se_log_rr": None,
            "study_rr": None, "study_ci_lower": None, "study_ci_upper": None,
        }
    add_cc = any(v == 0 for v in (a, b, c, d))
    if add_cc:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    n1c = a + b
    n0c = c + d
    rr = (a / n1c) / (c / n0c)
    yi = math.log(rr)
    vi = (1.0 / a) - (1.0 / n1c) + (1.0 / c) - (1.0 / n0c)
    if vi <= 0 or not math.isfinite(vi):
        raise ValueError(f"Non-positive/non-finite variance for {row['study']}: {vi}")
    se = math.sqrt(vi)
    return {
        **row,
        "estimable": True,
        "continuity_correction": add_cc,
        "corrected_human_events": a,
        "corrected_human_total": n1c,
        "corrected_comparator_events": c,
        "corrected_comparator_total": n0c,
        "yi_log_rr": yi,
        "vi_log_rr": vi,
        "se_log_rr": se,
        "study_rr": rr,
        "study_ci_lower": math.exp(yi - 1.96 * se),
        "study_ci_upper": math.exp(yi + 1.96 * se),
    }


def dl_meta_analysis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """DerSimonian-Laird random-effects analysis of study log risk ratios."""
    effects = [study_effect(row) for row in rows]
    effects = [e for e in effects if e["estimable"]]
    k = len(effects)
    if k < 2:
        raise ValueError(f"At least two estimable studies are required; found {k}")
    yi = [float(e["yi_log_rr"]) for e in effects]
    vi = [float(e["vi_log_rr"]) for e in effects]
    wi = [1.0 / v for v in vi]
    sum_w = sum(wi)
    mu_fixed = sum(w * y for w, y in zip(wi, yi)) / sum_w
    Q = sum(w * (y - mu_fixed) ** 2 for w, y in zip(wi, yi))
    df = k - 1
    C = sum_w - sum(w * w for w in wi) / sum_w
    tau2 = max(0.0, (Q - df) / C) if C > 0 else 0.0
    w_re = [1.0 / (v + tau2) for v in vi]
    mu_re = sum(w * y for w, y in zip(w_re, yi)) / sum(w_re)
    se_re = math.sqrt(1.0 / sum(w_re))
    z = mu_re / se_re
    rr = math.exp(mu_re)
    ci_lower = math.exp(mu_re - 1.96 * se_re)
    ci_upper = math.exp(mu_re + 1.96 * se_re)
    p_effect = 2.0 * norm.sf(abs(z))
    p_heterogeneity = float(chi2.sf(Q, df)) if df > 0 else float("nan")
    I2 = max(0.0, (Q - df) / Q * 100.0) if Q > 0 else 0.0
    total_re_weight = sum(w_re)
    for effect, w in zip(effects, w_re):
        effect["weight_re_pct"] = 100.0 * w / total_re_weight
        effect["model_tau2"] = tau2
    return {
        "k_studies_pooled": k,
        "pooled_log_rr": mu_re,
        "pooled_se_log_rr": se_re,
        "pooled_rr": rr,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_effect": p_effect,
        "Q": Q,
        "Q_df": df,
        "p_heterogeneity": p_heterogeneity,
        "I2_pct": I2,
        "tau2": tau2,
        "study_effects": effects,
    }


def sum_arm(rows: list[dict[str, Any]], arm: str) -> tuple[int, int]:
    if arm == "human":
        return sum(int(r["human_events"]) for r in rows), sum(int(r["human_total"]) for r in rows)
    return sum(int(r["comparator_events"]) for r in rows), sum(int(r["comparator_total"]) for r in rows)


def fmt_events(events: int, total: int) -> str:
    return f"{events}/{total}"


def build_pooled_outputs() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    pooled_rows: list[dict[str, Any]] = []
    absolute_rows: list[dict[str, Any]] = []
    study_effect_rows: list[dict[str, Any]] = []
    results_by_id: dict[str, dict[str, Any]] = {}

    for analysis_id, label, panel, outcome_label in ANALYSES:
        eligible = [r for r in DATA if r["analysis_id"] == analysis_id]
        pool_inputs = [r for r in eligible if r["include_in_logrr_pool_bool"]]
        model = dl_meta_analysis(pool_inputs)
        results_by_id[analysis_id] = {**model, "eligible_rows": eligible, "pool_inputs": pool_inputs,
                                     "label": label, "outcome_label": outcome_label, "panel": panel}
        all_h_ev, all_h_n = sum_arm(eligible, "human")
        all_c_ev, all_c_n = sum_arm(eligible, "comparator")
        pool_h_ev, pool_h_n = sum_arm(pool_inputs, "human")
        pool_c_ev, pool_c_n = sum_arm(pool_inputs, "comparator")
        double_zero = sum(1 for r in eligible if int(r["human_events"]) == 0 and int(r["comparator_events"]) == 0)
        pooled_rows.append({
            "analysis_id": analysis_id,
            "analysis": label,
            "outcome": outcome_label,
            "eligible_studies": len(eligible),
            "studies_contributing_to_log_rr": model["k_studies_pooled"],
            "double_zero_studies_not_estimable": double_zero,
            "all_eligible_human_events_total": fmt_events(all_h_ev, all_h_n),
            "all_eligible_comparator_events_total": fmt_events(all_c_ev, all_c_n),
            "log_rr_pool_human_events_total": fmt_events(pool_h_ev, pool_h_n),
            "log_rr_pool_comparator_events_total": fmt_events(pool_c_ev, pool_c_n),
            "pooled_rr": model["pooled_rr"], "ci_lower": model["ci_lower"], "ci_upper": model["ci_upper"],
            "p_pooled_effect_z": model["p_effect"], "Q": model["Q"], "Q_df": model["Q_df"],
            "p_Q_heterogeneity": model["p_heterogeneity"], "I2_pct": model["I2_pct"], "tau2": model["tau2"],
            "model": "DerSimonian-Laird random effects on log RR; normal 95% CI; z test",
            "notes": "RR < 1 favors human-based intervention. All eligible-arm totals include double-zero NEC trial; log-RR pool excludes it."
                   if double_zero else "RR < 1 favors human-based intervention."
        })

        # Individual study effects for the pool and a non-estimable row for excluded double-zero study.
        effects_by_study = {e["study"]: e for e in model["study_effects"]}
        for row in eligible:
            e = effects_by_study.get(row["study"], study_effect(row))
            study_effect_rows.append({
                "analysis_id": analysis_id, "analysis": label, "outcome": outcome_label,
                "study": row["study"], "PMID": row["pmid"],
                "human_events_total": fmt_events(row["human_events"], row["human_total"]),
                "comparator_events_total": fmt_events(row["comparator_events"], row["comparator_total"]),
                "in_log_rr_pool": row["include_in_logrr_pool"],
                "estimable_effect": e.get("estimable", False),
                "continuity_correction_0_5_all_cells": e.get("continuity_correction", False),
                "study_rr": e.get("study_rr"), "study_ci_lower": e.get("study_ci_lower"),
                "study_ci_upper": e.get("study_ci_upper"), "log_rr": e.get("yi_log_rr"),
                "variance_log_rr": e.get("vi_log_rr"), "random_effects_weight_pct": e.get("weight_re_pct"),
                "outcome_definition": row["outcome_definition"], "notes": row["extraction_notes"],
                "source_url": row["source_url"],
            })

        # Main absolute effects: aggregate comparator baseline risk across all extractable trial arms.
        # This deliberately includes double-zero trial arms for direct NEC so it matches the previously
        # reported absolute-effect calculation. The pooled RR itself still excludes that trial.
        comp_baseline = all_c_ev / all_c_n
        obs_h_risk = all_h_ev / all_h_n
        obs_c_risk = all_c_ev / all_c_n
        model_h_risk = model["pooled_rr"] * comp_baseline
        model_h_low = model["ci_lower"] * comp_baseline
        model_h_high = model["ci_upper"] * comp_baseline
        absolute_rows.append({
            "analysis_id": analysis_id, "analysis": label, "outcome": outcome_label,
            "human_observed_events_total": fmt_events(all_h_ev, all_h_n),
            "comparator_observed_events_total": fmt_events(all_c_ev, all_c_n),
            "observed_human_risk_per_1000": obs_h_risk * 1000,
            "observed_comparator_risk_per_1000": obs_c_risk * 1000,
            "observed_crude_risk_difference_per_1000_human_minus_comparator": (obs_h_risk - obs_c_risk) * 1000,
            "pooled_rr": model["pooled_rr"], "pooled_rr_ci_lower": model["ci_lower"], "pooled_rr_ci_upper": model["ci_upper"],
            "comparator_baseline_risk_source": "Observed comparator-arm event rate aggregated across all eligible study arms for this analysis",
            "comparator_baseline_events_total": fmt_events(all_c_ev, all_c_n),
            "comparator_baseline_risk_per_1000": comp_baseline * 1000,
            "model_translated_human_risk_per_1000": model_h_risk * 1000,
            "model_translated_human_risk_ci_lower_per_1000": model_h_low * 1000,
            "model_translated_human_risk_ci_upper_per_1000": model_h_high * 1000,
            "model_translated_risk_difference_per_1000_human_minus_comparator": (model["pooled_rr"] - 1) * comp_baseline * 1000,
            "model_translated_rd_ci_lower_per_1000": (model["ci_lower"] - 1) * comp_baseline * 1000,
            "model_translated_rd_ci_upper_per_1000": (model["ci_upper"] - 1) * comp_baseline * 1000,
            "p_pooled_effect_z": model["p_effect"],
            "interpretation": "Negative risk difference favors human-based intervention; positive favors comparator.",
            "caveat": "Translates pooled RR using fixed observed comparator baseline risk; uncertainty in baseline risk is not propagated. Outcome definitions differ across studies. Broader diet analyses are not fortifier-only."
        })

    return pooled_rows, absolute_rows, study_effect_rows, results_by_id


def ci_excludes_null(ci_lower: float, ci_upper: float, null_value: float = 1.0) -> bool:
    """Return whether a confidence interval excludes the null RR value."""
    return bool(ci_lower > null_value or ci_upper < null_value)


def effect_direction(rr: float, null_value: float = 1.0) -> str:
    """Describe point-estimate direction relative to RR=1; not significance."""
    if math.isclose(rr, null_value, rel_tol=0.0, abs_tol=1e-12):
        return "at null"
    return "point estimate favours human-based intervention" if rr < null_value else "point estimate favours comparator"


def build_loo_outputs(results_by_id: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run LOO analyses and compare each iteration with its full-analysis model.

    No analysis-specific conclusion is hard-coded. Stability is assessed for the CI-based
    significance classification, direction of the point estimate, pooled-RR magnitude,
    and overlap of the full and leave-one-out confidence intervals.
    """
    loo_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    absolute_by_id: dict[str, float] = {}
    for analysis_id, _, _, _ in ANALYSES:
        eligible = results_by_id[analysis_id]["eligible_rows"]
        comp_events, comp_total = sum_arm(eligible, "comparator")
        absolute_by_id[analysis_id] = comp_events / comp_total

    for analysis_id, label, _, outcome_label in ANALYSES:
        res = results_by_id[analysis_id]
        pool_inputs = res["pool_inputs"]
        full = res
        full_sig = ci_excludes_null(full["ci_lower"], full["ci_upper"])
        full_direction = effect_direction(full["pooled_rr"])
        per_analysis_rows: list[dict[str, Any]] = []

        for omitted in pool_inputs:
            remain = [r for r in pool_inputs if r["study"] != omitted["study"]]
            if len(remain) < 2:
                continue
            loo = dl_meta_analysis(remain)
            h_ev, h_n = sum_arm(remain, "human")
            c_ev, c_n = sum_arm(remain, "comparator")
            base_risk = absolute_by_id[analysis_id]  # full-analysis comparator baseline held fixed
            rd = (loo["pooled_rr"] - 1) * base_risk * 1000
            rd_low = (loo["ci_lower"] - 1) * base_risk * 1000
            rd_high = (loo["ci_upper"] - 1) * base_risk * 1000
            loo_sig = ci_excludes_null(loo["ci_lower"], loo["ci_upper"])
            loo_direction = effect_direction(loo["pooled_rr"])
            sig_matches_full = loo_sig == full_sig
            direction_matches_full = loo_direction == full_direction
            ci_overlaps_full = bool(loo["ci_lower"] <= full["ci_upper"] and loo["ci_upper"] >= full["ci_lower"])
            relative_change_pct = (loo["pooled_rr"] / full["pooled_rr"] - 1.0) * 100.0
            item = {
                "analysis_id": analysis_id, "analysis": label, "outcome": outcome_label,
                "study_omitted": omitted["study"], "omitted_PMID": omitted["pmid"],
                "remaining_studies_k": loo["k_studies_pooled"],
                "remaining_study_names": "; ".join(r["study"] for r in remain),
                "remaining_human_events_total": fmt_events(h_ev, h_n),
                "remaining_comparator_events_total": fmt_events(c_ev, c_n),
                "full_pooled_rr": full["pooled_rr"], "full_ci_lower": full["ci_lower"], "full_ci_upper": full["ci_upper"],
                "full_p_pooled_effect_z": full["p_effect"], "full_ci_excludes_1": full_sig,
                "full_effect_direction": full_direction,
                "pooled_rr": loo["pooled_rr"], "ci_lower": loo["ci_lower"], "ci_upper": loo["ci_upper"],
                "p_pooled_effect_z": loo["p_effect"], "Q": loo["Q"], "Q_df": loo["Q_df"],
                "p_Q_heterogeneity": loo["p_heterogeneity"], "I2_pct": loo["I2_pct"], "tau2": loo["tau2"],
                "pooled_rr_delta_vs_full": loo["pooled_rr"] - full["pooled_rr"],
                "pooled_rr_relative_change_pct_vs_full": relative_change_pct,
                "ci_lower_delta_vs_full": loo["ci_lower"] - full["ci_lower"],
                "ci_upper_delta_vs_full": loo["ci_upper"] - full["ci_upper"],
                "loo_ci_overlaps_full_ci": ci_overlaps_full,
                "fixed_comparator_baseline_risk_per_1000": base_risk * 1000,
                "model_translated_rd_per_1000": rd, "model_translated_rd_ci_lower_per_1000": rd_low,
                "model_translated_rd_ci_upper_per_1000": rd_high,
                "pooled_ci_excludes_1": loo_sig, "loo_effect_direction": loo_direction,
                "significance_status_matches_full": sig_matches_full,
                "effect_direction_matches_full": direction_matches_full,
                "interpretation": (
                    "LOO significance classification matches full analysis" if sig_matches_full
                    else "LOO significance classification differs from full analysis"
                ) + "; " + (
                    "point-estimate direction matches full analysis" if direction_matches_full
                    else "point-estimate direction differs from full analysis"
                ),
                "notes": "Absolute RD uses the full-analysis comparator baseline risk held fixed across iterations."
                       + (" Double-zero Hagelberg 1990 is not part of the NEC effect pool." if analysis_id == "primary_direct_NEC" else "")
                       + (" Hagelberg sepsis counts are narrative-derived 1/10 vs 2/10 and include a recurrent HMP episode." if analysis_id == "primary_direct_sepsis" else "")
            }
            loo_rows.append(item)
            per_analysis_rows.append(item)

        n_loo = len(per_analysis_rows)
        n_loo_sig = sum(1 for r in per_analysis_rows if r["pooled_ci_excludes_1"])
        n_sig_match = sum(1 for r in per_analysis_rows if r["significance_status_matches_full"])
        n_dir_match = sum(1 for r in per_analysis_rows if r["effect_direction_matches_full"])
        sig_changed = [r["study_omitted"] for r in per_analysis_rows if not r["significance_status_matches_full"]]
        dir_changed = [r["study_omitted"] for r in per_analysis_rows if not r["effect_direction_matches_full"]]
        pct_changes = [abs(r["pooled_rr_relative_change_pct_vs_full"]) for r in per_analysis_rows]
        log_changes = [abs(math.log(r["pooled_rr"] / full["pooled_rr"])) for r in per_analysis_rows]
        summary_rows.append({
            "analysis_id": analysis_id, "analysis": label, "full_k_studies": full["k_studies_pooled"],
            "full_rr": full["pooled_rr"], "full_ci_lower": full["ci_lower"], "full_ci_upper": full["ci_upper"],
            "full_p_effect": full["p_effect"], "full_Q": full["Q"], "full_Q_df": full["Q_df"],
            "full_p_heterogeneity": full["p_heterogeneity"], "full_I2_pct": full["I2_pct"], "full_tau2": full["tau2"],
            "full_ci_excludes_1": full_sig, "full_effect_direction": full_direction,
            "loo_iterations": n_loo,
            "loo_rr_min": min((r["pooled_rr"] for r in per_analysis_rows), default=float("nan")),
            "loo_rr_max": max((r["pooled_rr"] for r in per_analysis_rows), default=float("nan")),
            "loo_iterations_ci_excludes_1": f"{n_loo_sig}/{n_loo}",
            "loo_iterations_matching_full_significance": f"{n_sig_match}/{n_loo}",
            "omissions_changing_significance_vs_full": "; ".join(sig_changed) if sig_changed else "None",
            "conclusion_stable_for_significance": n_sig_match == n_loo,
            "loo_iterations_matching_full_direction": f"{n_dir_match}/{n_loo}",
            "omissions_changing_direction_vs_full": "; ".join(dir_changed) if dir_changed else "None",
            "effect_direction_stable_vs_full": n_dir_match == n_loo,
            "max_absolute_relative_change_in_rr_pct": max(pct_changes, default=float("nan")),
            "max_absolute_change_in_log_rr": max(log_changes, default=float("nan")),
            "interpretation": loo_interpretation(full, per_analysis_rows),
        })
    return loo_rows, summary_rows


def loo_interpretation(full: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """Create an interpretation from actual results, comparing LOO with full analysis."""
    if not rows:
        return "No valid leave-one-out iterations were available."
    full_sig = ci_excludes_null(full["ci_lower"], full["ci_upper"])
    full_direction = effect_direction(full["pooled_rr"])
    sig_matches = sum(bool(r["significance_status_matches_full"]) for r in rows)
    dir_matches = sum(bool(r["effect_direction_matches_full"]) for r in rows)
    sig_changed = [r["study_omitted"] for r in rows if not r["significance_status_matches_full"]]
    dir_changed = [r["study_omitted"] for r in rows if not r["effect_direction_matches_full"]]
    full_sig_text = "95% CI excludes RR=1" if full_sig else "95% CI includes RR=1"
    message = (
        f"Full analysis: RR={full['pooled_rr']:.3f} (95% CI {full['ci_lower']:.3f} to {full['ci_upper']:.3f}; "
        f"{full_sig_text}). LOO significance classification matched the full analysis in {sig_matches}/{len(rows)} iterations."
    )
    if sig_changed:
        message += " Significance status changed when omitting: " + "; ".join(sig_changed) + "."
    else:
        message += " No omission changed the significance classification."
    message += f" Point-estimate direction in the full analysis ({full_direction}) matched {dir_matches}/{len(rows)} LOO iterations."
    if dir_changed:
        message += " Point-estimate direction changed when omitting: " + "; ".join(dir_changed) + "."
    rr_values = [r["pooled_rr"] for r in rows]
    message += f" LOO pooled RR ranged from {min(rr_values):.3f} to {max(rr_values):.3f}."
    return message

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    # stable, first-seen column order
    fields = list(dict.fromkeys(k for row in rows for k in row.keys()))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fields})



def write_publication_absolute_table(absolute_rows: list[dict[str, Any]]) -> None:
    """Write a compact, manuscript-friendly absolute-effect table."""
    concise = []
    for r in absolute_rows:
        human_ci = (f"{r['model_translated_human_risk_per_1000']:.1f} "
                    f"({r['model_translated_human_risk_ci_lower_per_1000']:.1f} to "
                    f"{r['model_translated_human_risk_ci_upper_per_1000']:.1f})")
        rd_ci = (f"{r['model_translated_risk_difference_per_1000_human_minus_comparator']:+.1f} "
                 f"({r['model_translated_rd_ci_lower_per_1000']:+.1f} to "
                 f"{r['model_translated_rd_ci_upper_per_1000']:+.1f})")
        concise.append({
            "Analysis": r["analysis"],
            "Human-based events/total": r["human_observed_events_total"],
            "Comparator events/total": r["comparator_observed_events_total"],
            "Observed comparator risk per 1000": f"{r['observed_comparator_risk_per_1000']:.1f}",
            "Model-translated human risk per 1000 (95% CI)": human_ci,
            "Model-translated risk difference per 1000 (95% CI)": rd_ci,
            "Pooled RR (95% CI)": (f"{r['pooled_rr']:.3f} "
                                  f"({r['pooled_rr_ci_lower']:.3f} to {r['pooled_rr_ci_upper']:.3f})"),
            "P for pooled effect": f"{r['p_pooled_effect_z']:.3f}",
            "Notes": r["caveat"],
        })
    write_csv(RESULTS_DIR / "absolute_effects_publication_table.csv", concise)

def fmt_rr(rr: float | None, lo: float | None, hi: float | None) -> str:
    if rr is None or lo is None or hi is None:
        return "Not estimable"
    return f"{rr:.2f} ({lo:.2f}–{hi:.2f})"


def draw_table_axis(ax, rows, model, full_eligible_rows, panel_letter, title):
    ax.set_axis_off()
    n = len(full_eligible_rows)
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.25, n + 3.15)
    ax.text(0.01, n + 2.75, f"{panel_letter}  {title}", fontsize=12.5, fontweight="bold", va="center")
    y_header = n + 2.0
    headers = [
        (0.015, "Study", "left"),
        (0.405, "Human-based\nEvents/Total", "center"),
        (0.565, "Bovine/cow\nEvents/Total", "center"),
        (0.805, "Risk ratio (95% CI)", "center"),
        (0.985, "Weight, %", "right"),
    ]
    for x, label, ha in headers:
        ax.text(x, y_header, label, fontsize=8.4, fontweight="bold", ha=ha, va="center")
    ax.plot([0.01, 0.99], [y_header - 0.40, y_header - 0.40], color="#4B5563", lw=0.8)
    effects = {e["study"]: e for e in model["study_effects"]}
    for i, row in enumerate(full_eligible_rows):
        y = n + 1.25 - i
        e = effects.get(row["study"])
        rr_txt = fmt_rr(e.get("study_rr"), e.get("study_ci_lower"), e.get("study_ci_upper")) if e else "Not estimable"
        weight_txt = f"{e['weight_re_pct']:.1f}" if e and e.get("weight_re_pct") is not None else "—"
        ax.text(0.015, y, row["study"], fontsize=8.8, ha="left", va="center")
        ax.text(0.405, y, fmt_events(row["human_events"], row["human_total"]), fontsize=8.8, ha="center", va="center")
        ax.text(0.565, y, fmt_events(row["comparator_events"], row["comparator_total"]), fontsize=8.8, ha="center", va="center")
        ax.text(0.805, y, rr_txt, fontsize=8.4, ha="center", va="center")
        ax.text(0.985, y, weight_txt, fontsize=8.8, ha="right", va="center")
        ax.plot([0.01, 0.99], [y - 0.43, y - 0.43], color="#D1D5DB", lw=0.45)
    # Descriptive totals use all eligible trial arms; double-zero study is not in the log-RR fit.
    h_ev, h_n = sum_arm(full_eligible_rows, "human")
    c_ev, c_n = sum_arm(full_eligible_rows, "comparator")
    y_sum = 0.72
    ax.plot([0.01, 0.99], [1.20, 1.20], color="#374151", lw=0.8)
    ax.text(0.015, y_sum, "Random-effects model", fontsize=9.0, fontweight="bold", ha="left", va="center")
    ax.text(0.405, y_sum, fmt_events(h_ev, h_n), fontsize=8.8, fontweight="bold", ha="center", va="center")
    ax.text(0.565, y_sum, fmt_events(c_ev, c_n), fontsize=8.8, fontweight="bold", ha="center", va="center")
    ax.text(0.805, y_sum, fmt_rr(model["pooled_rr"], model["ci_lower"], model["ci_upper"]), fontsize=8.7, fontweight="bold", ha="center", va="center")
    ax.text(0.985, y_sum, "100.0", fontsize=8.8, fontweight="bold", ha="right", va="center")
    het = f"Heterogeneity: I² = {model['I2_pct']:.1f}%, τ² = {model['tau2']:.3f}; Q = {model['Q']:.3f}, df = {model['Q_df']}, P = {model['p_heterogeneity']:.3f}"
    ax.text(0.015, 0.20, het, fontsize=7.8, ha="left", va="center")


def draw_forest_axis(ax, full_eligible_rows, model, outcome, analysis_id):
    effects = {e["study"]: e for e in model["study_effects"]}
    n = len(full_eligible_rows)
    ax.set_xscale("log")
    ax.set_xlim(0.01, 100)
    ax.set_ylim(-0.25, n + 3.15)
    ax.set_yticks([])
    ax.axvline(1, color="#6B7280", lw=0.9, linestyle=(0, (3, 2)))
    ax.set_xticks([0.01, 0.1, 1, 10, 100])
    ax.set_xticklabels(["0.01", "0.1", "1", "10", "100"], fontsize=8.5)
    ax.tick_params(axis="x", length=3, color="#4B5563")
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#6B7280")
    ax.set_xlabel("Risk ratio (human-based / bovine-cow-based)", fontsize=9, labelpad=7)
    if analysis_id.startswith("broader"):
        left_favor = "Favors human-milk\ndiet strategy"
        right_favor = "Favors bovine-containing\ndiet"
    else:
        left_favor = "Favors human-based\nfortifier"
        right_favor = "Favors bovine/cow\nfortifier"
    ax.text(0.025, n + 2.45, left_favor, ha="left", va="center", fontsize=8.6, color="#174A5B")
    ax.text(4.0, n + 2.45, right_favor, ha="left", va="center", fontsize=8.6, color="#174A5B")
    for i, row in enumerate(full_eligible_rows):
        y = n + 1.25 - i
        e = effects.get(row["study"])
        if not e or not e.get("estimable"):
            continue
        rr, lo, hi = e["study_rr"], e["study_ci_lower"], e["study_ci_upper"]
        low_vis, high_vis = max(lo, 0.01), min(hi, 100)
        ax.plot([low_vis, high_vis], [y, y], color="#4B5563", lw=1.0, solid_capstyle="butt", zorder=2)
        if lo < 0.01:
            ax.annotate("", xy=(0.0105, y), xytext=(0.018, y), arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "#4B5563"})
        if hi > 100:
            ax.annotate("", xy=(98, y), xytext=(80, y), arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "#4B5563"})
        weight = e.get("weight_re_pct", 0.0)
        marker_size = 22 + 2.4 * math.sqrt(max(weight, 0.0))
        ax.scatter([rr], [y], s=marker_size, marker="s", color="#0F6674", edgecolor="#0B4550", linewidth=0.45, zorder=3)
    # Summary diamond; the x values are the pooled RR and its CI.
    y_sum = 0.72
    diamond = Polygon([[model["ci_lower"], y_sum], [model["pooled_rr"], y_sum + 0.22],
                       [model["ci_upper"], y_sum], [model["pooled_rr"], y_sum - 0.22]],
                      closed=True, facecolor="#2B8798", edgecolor="#0B4550", linewidth=0.8, zorder=4)
    ax.add_patch(diamond)


def make_combined_forest(output_name: str, title: str, analysis_ids: list[str], panel_titles: list[str]) -> None:
    fig = plt.figure(figsize=(15.5, 10.0), facecolor="white")
    gs = fig.add_gridspec(2, 2, width_ratios=[2.20, 1.20], height_ratios=[1, 1], hspace=0.27, wspace=0.025)
    fig.suptitle(title, fontsize=15.0, fontweight="bold", x=0.5, y=0.985)
    for idx, (analysis_id, panel_title) in enumerate(zip(analysis_ids, panel_titles)):
        r = idx
        eligible = [row for row in DATA if row["analysis_id"] == analysis_id]
        pool = [row for row in eligible if row["include_in_logrr_pool_bool"]]
        model = dl_meta_analysis(pool)
        ax_table = fig.add_subplot(gs[r, 0])
        ax_forest = fig.add_subplot(gs[r, 1])
        draw_table_axis(ax_table, eligible, model, eligible, "A" if r == 0 else "B", panel_title)
        draw_forest_axis(ax_forest, eligible, model, panel_title, analysis_id)
    if "primary" in output_name:
        footer = ("RR < 1 favors the human-based fortifier. Hagelberg 1990 NEC was double-zero (0/10 vs 0/10), "
                  "is listed as not estimable, and is excluded from log-RR pooling.")
    else:
        footer = ("RR < 1 favors the human-milk diet strategy. This is a broader diet-strategy comparison, "
                  "not an isolated fortifier-source effect.")
    fig.text(0.015, 0.012, footer, fontsize=8.1, ha="left", va="bottom", color="#374151")
    pdf = FIGURES_DIR / output_name
    png = FIGURES_DIR / output_name.replace(".pdf", ".png")
    fig.savefig(pdf, format="pdf", bbox_inches="tight")
    fig.savefig(png, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    pooled, absolute, study_effects, results_by_id = build_pooled_outputs()
    loo, loo_summary = build_loo_outputs(results_by_id)
    write_csv(RESULTS_DIR / "pooled_results.csv", pooled)
    write_csv(RESULTS_DIR / "absolute_effects.csv", absolute)
    write_publication_absolute_table(absolute)
    write_csv(RESULTS_DIR / "leave_one_out_detailed.csv", loo)
    write_csv(RESULTS_DIR / "leave_one_out_summary.csv", loo_summary)
    write_csv(RESULTS_DIR / "study_level_effects.csv", study_effects)
    data_for_export = [{k: v for k, v in row.items() if k != "include_in_logrr_pool_bool"} for row in DATA]
    write_csv(RESULTS_DIR / "analysis_dataset_used.csv", data_for_export)

    make_combined_forest(
        "Figure_1_primary_direct_fortifier.pdf",
        "Random-effects meta-analysis: direct human-based vs bovine/cow milk-based fortifier",
        ["primary_direct_NEC", "primary_direct_sepsis"],
        ["Necrotizing enterocolitis (NEC)", "Sepsis"],
    )
    make_combined_forest(
        "Figure_S1_broader_diet_strategy.pdf",
        "Random-effects meta-analysis: broader human-milk diet strategy vs bovine-containing diet",
        ["broader_diet_NEC", "broader_diet_sepsis"],
        ["Necrotizing enterocolitis (NEC)", "Sepsis"],
    )

    # Compact terminal summary useful for audit/reproduction.
    print("Analysis complete. Main pooled estimates:")
    for row in pooled:
        print(f"- {row['analysis']}: RR {row['pooled_rr']:.3f} "
              f"(95% CI {row['ci_lower']:.3f}-{row['ci_upper']:.3f}); "
              f"P(effect)={row['p_pooled_effect_z']:.3f}; I2={row['I2_pct']:.1f}%; "
              f"tau2={row['tau2']:.3f}; P(Q)={row['p_Q_heterogeneity']:.3f}")
    print(f"Wrote tables to: {RESULTS_DIR}")
    print(f"Wrote forest-plot PDFs/PNGs to: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
