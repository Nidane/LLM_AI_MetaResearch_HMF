#!/usr/bin/env python3
"""
================================================================================
Script 03 — ABSOLUTE EFFECT MEASURES (risk difference & events per 1,000)
================================================================================
In response to a reviewer request for absolute-scale effect estimates alongside
the relative risk, this script computes TWO complementary absolute effects:

 (A) DIRECTLY POOLED RISK DIFFERENCE
     - Per-study RD = p_HMBF - p_BMBF, with 0.5 continuity correction applied
       to all four cells of any study with a zero cell.
     - Inverse-variance random-effects (DerSimonian-Laird) pooling on the RD
       scale.
     - Variance per study: p1(1-p1)/n1 + p2(1-p2)/n2.
     - Report as RD % and as events per 1,000.
     - NOTE: Q, Z, p from this analysis are on the RD scale, so they differ
       numerically from the log-RR scale Q, Z, p produced by Script 01 even
       though the overall clinical conclusion is the same. See accompanying
       note explaining why.

 (B) GRADE-STYLE ABSOLUTE EFFECT (from the pooled RR of Script 01)
     - Assumed baseline risk = overall event rate in the pooled BMBF arm.
     - Expected HMBF risk = baseline × pooled RR.
     - Absolute effect per 1,000 = (expected HMBF - baseline) × 1,000.
     - This is what Cochrane / GRADE Summary of Findings tables use.

Data are identical to Scripts 01 and 02 (Berrington 2025 sepsis = 4/14 vs 1/14,
full-study counts).

Outputs:
  - Console summary (per-study + both pooled methods for each outcome)
  - forest_NEC_RD.png / forest_sepsis_RD.png  (RD forest plots)
  - rd_results.json (machine-readable results of both methods)

Dependencies: numpy, scipy, matplotlib
================================================================================
"""

import os
import json
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

NEC_DATA = [
    ("O'Connor",    2018,  3,  64,  6,  61),
    ("Embleton",    2023,  1,  63,  2,  63),
    ("Bach Jensen", 2024,  8, 115,  9, 113),
    ("Berrington",  2025,  1,  14,  0,  14),
]
SEPSIS_DATA = [
    ("O'Connor",    2018,  8,  64, 14,  61),
    ("Kumbhare",    2022,  6,  16,  2,  14),
    ("Embleton",    2023,  6,  63,  8,  63),
    ("Bach Jensen", 2024, 33, 115, 28, 113),
    ("Berrington",  2025,  4,  14,  1,  14),
]
OUTPUT_DIR = "/mnt/user-data/outputs"


# ------------------------------------------------------------------------------
# Per-study RD and RR
# ------------------------------------------------------------------------------
def study_rd(e1, n1, e2, n2, cc=0.5):
    """Risk difference (p_HMBF - p_BMBF) with 95% CI. Returns proportion, not %."""
    if e1 == 0 or e2 == 0 or (n1 - e1) == 0 or (n2 - e2) == 0:
        e1a, n1a = e1 + cc, n1 + 2 * cc
        e2a, n2a = e2 + cc, n2 + 2 * cc
    else:
        e1a, n1a, e2a, n2a = e1, n1, e2, n2
    p1 = e1a / n1a
    p2 = e2a / n2a
    rd = p1 - p2
    se = np.sqrt(p1 * (1 - p1) / n1a + p2 * (1 - p2) / n2a)
    return rd, rd - 1.96 * se, rd + 1.96 * se, se


def study_rr(e1, n1, e2, n2, cc=0.5):
    if e1 == 0 or e2 == 0 or (n1 - e1) == 0 or (n2 - e2) == 0:
        e1a, n1a, e2a, n2a = e1 + cc, n1 + 2*cc, e2 + cc, n2 + 2*cc
    else:
        e1a, n1a, e2a, n2a = e1, n1, e2, n2
    rr = (e1a/n1a) / (e2a/n2a)
    log_rr = np.log(rr)
    se = np.sqrt(1/e1a - 1/n1a + 1/e2a - 1/n2a)
    return rr, log_rr, se


# ------------------------------------------------------------------------------
# Random-effects pools (both scales)
# ------------------------------------------------------------------------------
def dl_pool_rd(data):
    effects, se_eff = [], []
    for item in data:
        rd, _, _, se = study_rd(*item[2:6])
        effects.append(rd); se_eff.append(se)
    effects = np.array(effects); se_eff = np.array(se_eff)
    w_fe = 1.0 / se_eff**2
    pooled_fe = (w_fe * effects).sum() / w_fe.sum()
    Q = (w_fe * (effects - pooled_fe) ** 2).sum()
    df = len(effects) - 1
    c = w_fe.sum() - (w_fe**2).sum() / w_fe.sum()
    tau2 = max(0.0, (Q - df) / c) if c > 0 else 0.0
    w_re = 1.0 / (se_eff**2 + tau2)
    pooled_re = (w_re * effects).sum() / w_re.sum()
    se_pool = np.sqrt(1.0 / w_re.sum())
    I2 = max(0.0, (Q - df) / Q) * 100 if Q > 0 else 0.0
    p_Q = float(1 - stats.chi2.cdf(Q, df)) if df > 0 else float("nan")
    return {
        "pooled_rd": float(pooled_re),
        "ci_low":    float(pooled_re - 1.96 * se_pool),
        "ci_high":   float(pooled_re + 1.96 * se_pool),
        "se":        float(se_pool),
        "z":         float(pooled_re / se_pool),
        "p_effect":  float(2 * (1 - stats.norm.cdf(abs(pooled_re / se_pool)))),
        "Q": float(Q), "df": df, "p_Q": p_Q,
        "I2": float(I2), "tau2": float(tau2),
        "pooled_fe_rd": float(pooled_fe),
        "weights_re_pct": (w_re / w_re.sum() * 100).tolist(),
    }


def dl_pool_rr(data):
    """Pool on log(RR) scale -- same engine as Script 01, used here for method (B)."""
    log_eff, se_eff = [], []
    for item in data:
        _, log_rr, se = study_rr(*item[2:6])
        log_eff.append(log_rr); se_eff.append(se)
    log_eff = np.array(log_eff); se_eff = np.array(se_eff)
    w_fe = 1 / se_eff**2
    pooled_fe = (w_fe * log_eff).sum() / w_fe.sum()
    Q = (w_fe * (log_eff - pooled_fe) ** 2).sum()
    df = len(log_eff) - 1
    c = w_fe.sum() - (w_fe**2).sum() / w_fe.sum()
    tau2 = max(0.0, (Q - df) / c) if c > 0 else 0.0
    w_re = 1 / (se_eff**2 + tau2)
    pooled_re = (w_re * log_eff).sum() / w_re.sum()
    se_pool = np.sqrt(1 / w_re.sum())
    return {
        "rr":       float(np.exp(pooled_re)),
        "ci_low":   float(np.exp(pooled_re - 1.96 * se_pool)),
        "ci_high":  float(np.exp(pooled_re + 1.96 * se_pool)),
    }


# ------------------------------------------------------------------------------
# Combined reporting function
# ------------------------------------------------------------------------------
def analyse(data, outcome_name):
    print("\n" + "=" * 90)
    print(f"{outcome_name}  -  Absolute effect analyses")
    print("=" * 90)

    print(f"\n{'Study':<22}{'HMBF n/N':<14}{'BMBF n/N':<14}"
          f"{'RD (%)':>10}{'95% CI (%)':>22}{'Events/1000':>22}")
    print("-" * 104)
    for item in data:
        label, year, e1, n1, e2, n2 = item[:6]
        rd, lo, hi, _ = study_rd(e1, n1, e2, n2)
        print(f"{label} {year:<16} {str(e1)+'/'+str(n1):<14}{str(e2)+'/'+str(n2):<14}"
              f"{rd*100:>+9.2f}  [{lo*100:+6.2f}, {hi*100:+6.2f}]"
              f"  {rd*1000:+6.1f} [{lo*1000:+6.1f}, {hi*1000:+6.1f}]")

    # (A) DIRECTLY POOLED RD
    pooled = dl_pool_rd(data)
    print(f"\n(A) DIRECTLY POOLED RISK DIFFERENCE (random-effects, DL):")
    print(f"    RD = {pooled['pooled_rd']*100:+.2f}%  "
          f"[{pooled['ci_low']*100:+.2f}%, {pooled['ci_high']*100:+.2f}%]")
    print(f"       = {pooled['pooled_rd']*1000:+.1f} per 1,000  "
          f"[{pooled['ci_low']*1000:+.1f} to {pooled['ci_high']*1000:+.1f} per 1,000]")
    print(f"    Z = {pooled['z']:+.2f}, p = {pooled['p_effect']:.3f}")
    print(f"    Heterogeneity: Q = {pooled['Q']:.2f} (df = {pooled['df']}, "
          f"p = {pooled['p_Q']:.3f}), I² = {pooled['I2']:.1f}%, "
          f"tau² = {pooled['tau2']:.6f}")

    # (B) GRADE-STYLE INDIRECT ABSOLUTE EFFECT
    rr_pool = dl_pool_rr(data)
    total_e2 = sum(x[4] for x in data)
    total_n2 = sum(x[5] for x in data)
    baseline = total_e2 / total_n2
    expected = baseline * rr_pool['rr']
    expected_lo = baseline * rr_pool['ci_low']
    expected_hi = baseline * rr_pool['ci_high']
    abs_effect = expected - baseline
    abs_lo = expected_lo - baseline
    abs_hi = expected_hi - baseline

    print(f"\n(B) GRADE-STYLE ABSOLUTE EFFECT (from pooled RR):")
    print(f"    Assumed baseline risk (BMBF arm, pooled): "
          f"{baseline*100:.2f}% ({baseline*1000:.1f} per 1,000)")
    print(f"    Pooled RR = {rr_pool['rr']:.3f}  "
          f"[{rr_pool['ci_low']:.3f}, {rr_pool['ci_high']:.3f}]")
    print(f"    Expected HMBF risk = {expected*100:.2f}% "
          f"({expected*1000:.1f} per 1,000)")
    print(f"    Absolute effect = {abs_effect*1000:+.1f} per 1,000  "
          f"[{abs_lo*1000:+.1f} to {abs_hi*1000:+.1f} per 1,000]")

    return {
        "study_level": [
            {"label": f"{item[0]} {item[1]}", "e1": item[2], "n1": item[3],
             "e2": item[4], "n2": item[5],
             "rd":    study_rd(*item[2:6])[0],
             "rd_lo": study_rd(*item[2:6])[1],
             "rd_hi": study_rd(*item[2:6])[2]}
            for item in data
        ],
        "A_directly_pooled_RD": pooled,
        "B_GRADE_style": {
            "baseline_risk": baseline,
            "pooled_rr": rr_pool,
            "expected_hmbf_risk": expected,
            "expected_hmbf_ci":  [expected_lo, expected_hi],
            "absolute_effect":    abs_effect,
            "absolute_effect_ci": [abs_lo, abs_hi],
        },
    }


# ------------------------------------------------------------------------------
# RD Forest plot
# ------------------------------------------------------------------------------
def rd_forest(data, outcome_name, save_path):
    rows = []
    for item in data:
        label, year, e1, n1, e2, n2 = item[:6]
        rd, lo, hi, se = study_rd(e1, n1, e2, n2)
        rows.append({"label": f"{label} {year}", "e1": e1, "n1": n1,
                     "e2": e2, "n2": n2, "rd": rd, "lo": lo, "hi": hi, "se": se})
    pooled = dl_pool_rd(data)

    n = len(rows)
    row_h = 0.9
    y_header, y_rule, y_start = 0.5, 1.0, 1.8
    y_pool = y_start + n * row_h + 0.5
    y_het = y_pool + 1.1
    y_bot = y_het + 0.8

    fig_h = max(5.5, 0.65 * y_bot + 0.8)
    fig = plt.figure(figsize=(16, fig_h))
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.3, 1.0], wspace=0.02)
    ax_tbl = fig.add_subplot(gs[0, 0])
    ax_plot = fig.add_subplot(gs[0, 1])
    for ax in (ax_tbl, ax_plot):
        ax.set_ylim(0, y_bot); ax.invert_yaxis()

    # Table side
    ax_tbl.set_xlim(0, 1); ax_tbl.axis("off")
    col = {"study": 0.00, "hmbf": 0.44, "bmbf": 0.60, "weight": 0.78}
    ax_tbl.text(col["study"], y_header, "Study", fontsize=11,
                fontweight="bold", va="center")
    ax_tbl.text(col["hmbf"], y_header, "HMBF\nevents/N",
                fontsize=10, fontweight="bold", va="center", ha="center")
    ax_tbl.text(col["bmbf"], y_header, "BMBF\nevents/N",
                fontsize=10, fontweight="bold", va="center", ha="center")
    ax_tbl.text(col["weight"], y_header, "Weight",
                fontsize=11, fontweight="bold", va="center", ha="center")
    ax_tbl.axhline(y=y_rule, color="black", linewidth=0.6)

    for i, (r, w) in enumerate(zip(rows, pooled['weights_re_pct'])):
        y = y_start + i * row_h
        ax_tbl.text(col["study"], y, r['label'], fontsize=10.5, va="center")
        ax_tbl.text(col["hmbf"], y, f"{r['e1']}/{r['n1']}",
                    fontsize=10.5, va="center", ha="center")
        ax_tbl.text(col["bmbf"], y, f"{r['e2']}/{r['n2']}",
                    fontsize=10.5, va="center", ha="center")
        ax_tbl.text(col["weight"], y, f"{w:.1f}%", fontsize=10,
                    va="center", ha="center", color="#555")

    y_sep = y_start + (n - 1) * row_h + row_h * 0.55
    ax_tbl.axhline(y=y_sep, color="gray", linewidth=0.5)

    total_e1 = sum(r['e1'] for r in rows); total_n1 = sum(r['n1'] for r in rows)
    total_e2 = sum(r['e2'] for r in rows); total_n2 = sum(r['n2'] for r in rows)
    ax_tbl.text(col["study"], y_pool, "Pooled (random-effects, DL)",
                fontsize=10.5, fontweight="bold", va="center")
    ax_tbl.text(col["hmbf"], y_pool, f"{total_e1}/{total_n1}",
                fontsize=10.5, fontweight="bold", va="center", ha="center")
    ax_tbl.text(col["bmbf"], y_pool, f"{total_e2}/{total_n2}",
                fontsize=10.5, fontweight="bold", va="center", ha="center")
    ax_tbl.text(col["weight"], y_pool, "100.0%",
                fontsize=10.5, fontweight="bold", va="center", ha="center")

    het = (f"Heterogeneity:  tau^2 = {pooled['tau2']:.5f};   "
           f"Q = {pooled['Q']:.2f} (df = {pooled['df']}, p = {pooled['p_Q']:.3f});   "
           f"I^2 = {pooled['I2']:.1f}%\n"
           f"Test for overall effect: Z = {pooled['z']:.2f},  p = {pooled['p_effect']:.3f}")
    ax_tbl.text(col["study"], y_het, het, fontsize=10,
                family="monospace", color="#222", va="center")

    # Plot side
    all_lows  = [r['lo'] for r in rows] + [pooled['ci_low']]
    all_highs = [r['hi'] for r in rows] + [pooled['ci_high']]
    span = max(abs(min(all_lows)), abs(max(all_highs))) + 0.03
    ax_plot.set_xlim(-span, span)
    ax_plot.axvline(x=0, color="black", linewidth=0.8)
    ax_plot.axhline(y=y_rule, color="black", linewidth=0.6)

    ax_plot.text(span * 1.3, y_header, "RD % [95% CI]   ->   per 1,000",
                 fontsize=11, fontweight="bold", va="center", clip_on=False)

    for i, (r, w) in enumerate(zip(rows, pooled['weights_re_pct'])):
        y = y_start + i * row_h
        ax_plot.plot([r['lo'], r['hi']], [y, y], color="black", linewidth=1.3)
        for xcap in (r['lo'], r['hi']):
            ax_plot.plot([xcap, xcap], [y - 0.14, y + 0.14],
                         color="black", linewidth=1.3)
        size = 80 + 18 * w
        ax_plot.scatter([r['rd']], [y], s=size, marker="s",
                        color="#2b6cb0", edgecolor="black", linewidth=0.8, zorder=5)
        ax_plot.text(span * 1.3, y,
                     f"{r['rd']*100:+6.2f}%  [{r['lo']*100:+6.2f}, "
                     f"{r['hi']*100:+6.2f}]  -> {r['rd']*1000:+6.1f}/1000",
                     fontsize=10, va="center", family="monospace", clip_on=False)

    ax_plot.axhline(y=y_sep, color="gray", linewidth=0.5)
    diamond = Polygon([[pooled['ci_low'], y_pool],
                       [pooled['pooled_rd'], y_pool - 0.38],
                       [pooled['ci_high'], y_pool],
                       [pooled['pooled_rd'], y_pool + 0.38]],
                      closed=True, facecolor="#c53030", edgecolor="black", zorder=6)
    ax_plot.add_patch(diamond)
    ax_plot.text(span * 1.3, y_pool,
                 f"{pooled['pooled_rd']*100:+6.2f}%  "
                 f"[{pooled['ci_low']*100:+6.2f}, {pooled['ci_high']*100:+6.2f}]  "
                 f"-> {pooled['pooled_rd']*1000:+6.1f}/1000",
                 fontsize=10.5, fontweight="bold", va="center",
                 family="monospace", clip_on=False)

    ax_plot.set_yticks([])
    for s in ("top", "right", "left"):
        ax_plot.spines[s].set_visible(False)

    tick_vals = [-0.2, -0.1, 0, 0.1, 0.2]
    tick_vals = [t for t in tick_vals if -span <= t <= span]
    ax_plot.set_xticks(tick_vals)
    ax_plot.set_xticklabels([f"{t*100:+.0f}%" for t in tick_vals], fontsize=10)
    ax_plot.set_xlabel("Risk difference (HMBF - BMBF, absolute)\n"
                       "← Favours HMBF        Favours BMBF →",
                       fontsize=11, labelpad=8)

    fig.suptitle(f"Risk difference forest plot - {outcome_name}",
                 fontsize=14, fontweight="bold", y=0.98)
    plt.subplots_adjust(left=0.02, right=0.84, top=0.91, bottom=0.11)
    plt.savefig(save_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"\nSaved: {save_path}")


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    nec_rd    = analyse(NEC_DATA,    "NEC (any stage)")
    sepsis_rd = analyse(SEPSIS_DATA, "Late-onset sepsis (culture-proven)")

    rd_forest(NEC_DATA,    "NEC (any stage)",
              os.path.join(OUTPUT_DIR, "forest_NEC_RD.png"))
    rd_forest(SEPSIS_DATA, "Late-onset sepsis (culture-proven)",
              os.path.join(OUTPUT_DIR, "forest_sepsis_RD.png"))

    with open(os.path.join(OUTPUT_DIR, "rd_results.json"), "w") as f:
        json.dump({"NEC": nec_rd, "Sepsis": sepsis_rd}, f, indent=2, default=str)
    print(f"\nSaved: {os.path.join(OUTPUT_DIR, 'rd_results.json')}")
