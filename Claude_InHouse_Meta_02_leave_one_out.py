#!/usr/bin/env python3
"""
================================================================================
Script 02 — LEAVE-ONE-OUT SENSITIVITY ANALYSIS
================================================================================
For each outcome (NEC, late-onset sepsis), re-run the DerSimonian-Laird
random-effects meta-analysis with ONE study removed at a time.

Purpose: assess whether any single study is unduly influential on the
pooled estimate, direction, or heterogeneity.

For each iteration (full + k individual removals), reports:
  - Pooled RR with 95% CI
  - Z and p for overall effect
  - Heterogeneity (Q, df, p_Q, I², tau²)
  - % change in pooled RR versus full-pool estimate

Data are identical to Script 01 (Berrington 2025 sepsis = 4/14 vs 1/14,
full-study counts).

Outputs:
  - Console summary (iteration-by-iteration + summary table)
  - loo_NEC.png / loo_sepsis.png  (one-panel-per-iteration forest plot)
  - loo_results.json (machine-readable per-iteration results)

Dependencies: numpy, scipy, matplotlib
================================================================================
"""

import os
import json
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

# Reuse data and statistical functions from Script 01
NEC_DATA = [
    ("O'Connor",    2018,  3,  64,  6,  61, "NEC any stage"),
    ("Embleton",    2023,  1,  63,  2,  63, "Surgical NEC"),
    ("Bach Jensen", 2024,  8, 115,  9, 113, "NEC Bell II-III"),
    ("Berrington",  2025,  1,  14,  0,  14, "Medical or surgical NEC"),
]
SEPSIS_DATA = [
    ("O'Connor",    2018,  8,  64, 14,  61, "Culture-proven LOS"),
    ("Kumbhare",    2022,  6,  16,  2,  14, "Culture-proven LOS"),
    ("Embleton",    2023,  6,  63,  8,  63, "Culture-proven LOS"),
    ("Bach Jensen", 2024, 33, 115, 28, 113, "Culture-proven LOS"),
    ("Berrington",  2025,  4,  14,  1,  14, "Culture-proven LOS (full study)"),
]
OUTPUT_DIR = "/mnt/user-data/outputs"


def study_rr(e1, n1, e2, n2, cc=0.5):
    if e1 == 0 or e2 == 0 or (n1 - e1) == 0 or (n2 - e2) == 0:
        e1a, n1a, e2a, n2a = e1 + cc, n1 + 2*cc, e2 + cc, n2 + 2*cc
    else:
        e1a, n1a, e2a, n2a = e1, n1, e2, n2
    rr = (e1a/n1a) / (e2a/n2a)
    log_rr = np.log(rr)
    se = np.sqrt(1/e1a - 1/n1a + 1/e2a - 1/n2a)
    return rr, float(np.exp(log_rr - 1.96*se)), float(np.exp(log_rr + 1.96*se)), log_rr, se


def dl_pool(data):
    """DL random-effects pool on log-RR scale (same engine as Script 01)."""
    log_eff, se_eff = [], []
    for item in data:
        _, _, _, log_rr, se = study_rr(item[2], item[3], item[4], item[5])
        log_eff.append(log_rr); se_eff.append(se)
    log_eff = np.array(log_eff); se_eff = np.array(se_eff)
    w_fe = 1.0 / se_eff**2
    pooled_fe = (w_fe * log_eff).sum() / w_fe.sum()
    Q = (w_fe * (log_eff - pooled_fe) ** 2).sum()
    df = len(log_eff) - 1
    c = w_fe.sum() - (w_fe**2).sum() / w_fe.sum()
    tau2 = max(0.0, (Q - df) / c) if c > 0 else 0.0
    w_re = 1.0 / (se_eff**2 + tau2)
    pooled_re = (w_re * log_eff).sum() / w_re.sum()
    se_pool = np.sqrt(1.0 / w_re.sum())
    I2 = max(0.0, (Q - df) / Q) * 100 if Q > 0 else 0.0
    p_Q = float(1 - stats.chi2.cdf(Q, df)) if df > 0 else float("nan")
    z = pooled_re / se_pool
    return {
        "k": len(data),
        "total_hmbf_events": sum(x[2] for x in data),
        "total_hmbf_n":      sum(x[3] for x in data),
        "total_bmbf_events": sum(x[4] for x in data),
        "total_bmbf_n":      sum(x[5] for x in data),
        "pooled_rr": float(np.exp(pooled_re)),
        "ci_low":    float(np.exp(pooled_re - 1.96 * se_pool)),
        "ci_high":   float(np.exp(pooled_re + 1.96 * se_pool)),
        "z":         float(z),
        "p_effect":  float(2 * (1 - stats.norm.cdf(abs(z)))),
        "Q":  float(Q), "df": df, "p_Q": p_Q,
        "I2": float(I2), "tau2": float(tau2),
    }


def leave_one_out(data, outcome_label):
    """Compute pooled estimates for the full pool and each k leave-one-out."""
    print("\n" + "=" * 90)
    print(f"LEAVE-ONE-OUT SENSITIVITY ANALYSIS: {outcome_label}")
    print("=" * 90)

    full = dl_pool(data)
    print(f"\nFULL ANALYSIS (k = {full['k']} studies):")
    print(f"  Totals: HMBF {full['total_hmbf_events']}/{full['total_hmbf_n']}, "
          f"BMBF {full['total_bmbf_events']}/{full['total_bmbf_n']}")
    print(f"  Pooled RR (DL): {full['pooled_rr']:.3f}  "
          f"[{full['ci_low']:.3f}, {full['ci_high']:.3f}]")
    print(f"  Z = {full['z']:+.2f}, p = {full['p_effect']:.3f}")
    print(f"  Heterogeneity: Q = {full['Q']:.2f} (df = {full['df']}, "
          f"p = {full['p_Q']:.3f}), I² = {full['I2']:.1f}%, tau² = {full['tau2']:.4f}")

    results = [{"removed": "- (full analysis)", **full}]
    for i, removed in enumerate(data):
        remaining = [x for j, x in enumerate(data) if j != i]
        pooled = dl_pool(remaining)
        label = f"{removed[0]} {removed[1]}"
        print("\n" + "-" * 90)
        print(f"ITERATION {i+1}: REMOVE {label}")
        print("-" * 90)
        print(f"  Removed study: HMBF {removed[2]}/{removed[3]} vs "
              f"BMBF {removed[4]}/{removed[5]}")
        print(f"  Remaining studies (k = {pooled['k']}):")
        for item in remaining:
            print(f"    - {item[0]} {item[1]}: HMBF {item[2]}/{item[3]} vs "
                  f"BMBF {item[4]}/{item[5]}")
        print(f"  Pooled RR: {pooled['pooled_rr']:.3f}  "
              f"[{pooled['ci_low']:.3f}, {pooled['ci_high']:.3f}]")
        print(f"  Z = {pooled['z']:+.2f}, p = {pooled['p_effect']:.3f}")
        print(f"  Heterogeneity: Q = {pooled['Q']:.2f} (df = {pooled['df']}, "
              f"p = {pooled['p_Q']:.3f}), I² = {pooled['I2']:.1f}%, "
              f"tau² = {pooled['tau2']:.4f}")
        change = (pooled['pooled_rr'] - full['pooled_rr']) / full['pooled_rr'] * 100
        print(f"  Change vs full pool: {full['pooled_rr']:.3f} -> "
              f"{pooled['pooled_rr']:.3f} ({change:+.1f}%)")
        results.append({"removed": label, **pooled})

    print("\n" + "=" * 90)
    print(f"SUMMARY TABLE - {outcome_label}")
    print("=" * 90)
    print(f"{'Analysis':<28}{'k':>4}  {'RR':>7}  {'[95% CI]':<22}"
          f"{'I²':>8}  {'p (effect)':>12}")
    print("-" * 90)
    for r in results:
        ci = f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]"
        print(f"{r['removed']:<28}{r['k']:>4}  {r['pooled_rr']:>7.3f}  "
              f"{ci:<22}{r['I2']:>7.1f}%  {r['p_effect']:>12.3f}")
    return results


# -----------------------------------------------------------------
# LOO plot (two-panel)
# -----------------------------------------------------------------
def loo_plot(results, outcome_name, save_path):
    n = len(results)
    fig = plt.figure(figsize=(16, 1.2 + 0.65 * n))
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(1, 2, width_ratios=[0.9, 1.4], wspace=0.02)
    ax_tbl = fig.add_subplot(gs[0, 0])
    ax_plot = fig.add_subplot(gs[0, 1])

    y_header, y_rule, y_start, row_h = 0.3, 0.75, 1.4, 0.75
    y_bot = y_start + n * row_h + 0.3
    for ax in (ax_tbl, ax_plot):
        ax.set_ylim(0, y_bot); ax.invert_yaxis()

    ax_tbl.set_xlim(0, 1); ax_tbl.axis("off")
    col = {"analysis": 0.00, "k": 0.74}
    ax_tbl.text(col["analysis"], y_header, "Analysis", fontsize=11,
                fontweight="bold", va="center")
    ax_tbl.text(col["k"], y_header, "k", fontsize=11,
                fontweight="bold", va="center", ha="center")
    ax_tbl.axhline(y=y_rule, color="black", linewidth=0.6)

    for i, r in enumerate(results):
        y = y_start + i * row_h
        is_full = (r['removed'] == "- (full analysis)")
        label = "FULL (all studies)" if is_full else f"- {r['removed']}"
        ax_tbl.text(col["analysis"], y, label, fontsize=11, va="center",
                    fontweight=("bold" if is_full else "normal"))
        ax_tbl.text(col["k"], y, str(r['k']), fontsize=11, va="center",
                    ha="center", fontweight=("bold" if is_full else "normal"))

    ax_plot.set_xscale("log")
    lows  = [r['ci_low']  for r in results]
    highs = [r['ci_high'] for r in results]
    xmin = min(0.1, min(lows) * 0.7)
    xmax = max(3.5, max(highs) * 1.3)
    ax_plot.set_xlim(xmin, xmax)
    ax_plot.axvline(x=1, color="black", linewidth=0.8)
    ax_plot.axhline(y=y_rule, color="black", linewidth=0.6)

    full = results[0]
    ax_plot.axvline(x=full['pooled_rr'], color="#888", linewidth=0.8,
                    linestyle="--", alpha=0.5)

    x_rr  = xmax * 1.25
    x_het = xmax * 4.3
    ax_plot.text(x_rr,  y_header, "Pooled RR [95% CI]",
                 fontsize=11, fontweight="bold", va="center", clip_on=False)
    ax_plot.text(x_het, y_header, "I²       p (effect)",
                 fontsize=11, fontweight="bold", va="center", clip_on=False)

    for i, r in enumerate(results):
        y = y_start + i * row_h
        is_full = (i == 0)
        color  = "#c53030" if is_full else "#2b6cb0"
        marker = "D" if is_full else "s"
        size   = 200 if is_full else 120
        ax_plot.plot([r['ci_low'], r['ci_high']], [y, y], color="black", linewidth=1.3)
        for xcap in (r['ci_low'], r['ci_high']):
            ax_plot.plot([xcap, xcap], [y - 0.15, y + 0.15],
                         color="black", linewidth=1.3)
        ax_plot.scatter([r['pooled_rr']], [y], s=size, marker=marker,
                        color=color, edgecolor="black", linewidth=0.8, zorder=5)
        ax_plot.text(x_rr, y,
                     f"{r['pooled_rr']:>5.3f}  [{r['ci_low']:>5.3f}, "
                     f"{r['ci_high']:>5.3f}]",
                     fontsize=10.5, va="center", family="monospace",
                     fontweight=("bold" if is_full else "normal"), clip_on=False)
        ax_plot.text(x_het, y,
                     f"{r['I2']:>5.1f}%   {r['p_effect']:>5.3f}",
                     fontsize=10.5, va="center", family="monospace",
                     color=("#222" if is_full else "#444"),
                     fontweight=("bold" if is_full else "normal"), clip_on=False)

    ax_plot.set_yticks([])
    for s in ("top", "right", "left"):
        ax_plot.spines[s].set_visible(False)
    ax_plot.set_xticks([0.1, 0.3, 0.5, 1, 2, 3, 5])
    ax_plot.set_xticklabels(["0.1", "0.3", "0.5", "1", "2", "3", "5"], fontsize=10)
    ax_plot.set_xlabel("Pooled risk ratio (HMBF vs BMBF, log scale)\n"
                       "← Favours HMBF        Favours BMBF →",
                       fontsize=11, labelpad=8)

    fig.suptitle(f"Leave-one-out sensitivity analysis - {outcome_name}",
                 fontsize=14, fontweight="bold", y=0.98)
    plt.subplots_adjust(left=0.02, right=0.80, top=0.90, bottom=0.15)
    plt.savefig(save_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"\nSaved: {save_path}")


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    nec_loo    = leave_one_out(NEC_DATA,    "NEC (any stage, as reported)")
    sepsis_loo = leave_one_out(SEPSIS_DATA, "Late-onset sepsis (culture-proven)")

    loo_plot(nec_loo,    "NEC (any stage)",
             os.path.join(OUTPUT_DIR, "loo_NEC.png"))
    loo_plot(sepsis_loo, "Late-onset sepsis (culture-proven)",
             os.path.join(OUTPUT_DIR, "loo_sepsis.png"))

    with open(os.path.join(OUTPUT_DIR, "loo_results.json"), "w") as f:
        json.dump({"NEC": nec_loo, "Sepsis": sepsis_loo}, f, indent=2)
    print(f"\nSaved: {os.path.join(OUTPUT_DIR, 'loo_results.json')}")
