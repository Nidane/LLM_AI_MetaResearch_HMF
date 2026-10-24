#!/usr/bin/env python3
"""
================================================================================
Script 01 — MAIN META-ANALYSIS (Risk Ratio)
================================================================================
Human milk-based fortifier (HMBF) vs bovine milk-based fortifier (BMBF)
on necrotising enterocolitis (NEC) and culture-proven late-onset sepsis
in preterm / VLBW infants.

Studies included (user-specified):
  1. O'Connor 2018     (PMID 29878061)   - BMBF arm = HMBF + Similac HMF + modular + formula
  2. Kumbhare 2022     (PMID 36029771)   - H2MF vs BHMF ; NEC was exclusion criterion
  3. Embleton 2023     (PMID 36857051)   - EHM strategy vs bovine-fortifier strategy
  4. Bach Jensen 2024  (PMID 38545091)   - N-Forte trial
  5. Berrington 2025   (PMID 39660504)   - PHMF vs PBMF ; stopped early
                                           SEPSIS = 4/14 vs 1/14 (full study, Day 1-21
                                           + Day 22 to discharge/transfer summed)

Synonym harmonisation applied:
    HMBF arm = HMBF = H2MF = PHMF = human milk-derived fortifier
    BMBF arm = BMBF = BHMF = PBMF = bovine milk-derived fortifier = CMBF

Methods:
  - Per-study effect: Risk ratio (RR), with 0.5 continuity correction applied
    to all four cells of any study with a zero cell (standard Cochrane approach).
  - Pooled effect: Random-effects on log(RR) scale via DerSimonian-Laird (DL).
  - Also reported: Mantel-Haenszel fixed-effect pool for comparison.
  - Heterogeneity: Cochran's Q, I², tau^2.

Outputs:
  - Console summary of all per-study and pooled statistics.
  - forest_NEC.png / forest_sepsis.png (publication-ready forest plots).
  - meta_analysis_results.json (machine-readable results).

Dependencies: numpy, scipy, matplotlib
================================================================================
"""

import os
import json
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

# ------------------------------------------------------------------------------
# DATA
# ------------------------------------------------------------------------------
# Tuple layout: (first_author, year, HMBF_events, HMBF_n, BMBF_events, BMBF_n,
#                outcome_definition_as_reported)

NEC_DATA = [
    ("O'Connor",    2018,  3,  64,  6,  61, "NEC any stage"),
    ("Embleton",    2023,  1,  63,  2,  63, "Surgical NEC"),
    ("Bach Jensen", 2024,  8, 115,  9, 113, "NEC Bell II-III"),
    ("Berrington",  2025,  1,  14,  0,  14, "Medical or surgical NEC"),
]
# Kumbhare 2022 excluded from NEC pool: NEC was an exclusion criterion
# (stage-2 NEC pre-study) and not reported as an outcome.

SEPSIS_DATA = [
    ("O'Connor",    2018,  8,  64, 14,  61, "Culture-proven LOS"),
    ("Kumbhare",    2022,  6,  16,  2,  14, "Culture-proven LOS"),
    ("Embleton",    2023,  6,  63,  8,  63, "Culture-proven LOS"),
    ("Bach Jensen", 2024, 33, 115, 28, 113, "Culture-proven LOS"),
    ("Berrington",  2025,  4,  14,  1,  14, "Culture-proven LOS (full study)"),
    # Berrington: 4 HMBF events = 2 in first 21 d + 2 in Day 22-discharge
    #             1 BMBF events = 0 in first 21 d + 1 in Day 22-discharge
]

OUTPUT_DIR = "/mnt/user-data/outputs"


# ------------------------------------------------------------------------------
# STATISTICS
# ------------------------------------------------------------------------------
def study_rr(e1, n1, e2, n2, cc=0.5):
    """Risk ratio (HMBF vs BMBF) with 95% CI and log-scale SE.

    If any cell is zero, adds 0.5 to all four cells (standard Cochrane
    continuity correction).

    Returns: (rr, ci_lower, ci_upper, log_rr, se_log_rr)
    """
    if e1 == 0 or e2 == 0 or (n1 - e1) == 0 or (n2 - e2) == 0:
        e1a, n1a = e1 + cc, n1 + 2 * cc
        e2a, n2a = e2 + cc, n2 + 2 * cc
    else:
        e1a, n1a, e2a, n2a = e1, n1, e2, n2
    rr = (e1a / n1a) / (e2a / n2a)
    log_rr = np.log(rr)
    se = np.sqrt(1/e1a - 1/n1a + 1/e2a - 1/n2a)
    return rr, float(np.exp(log_rr - 1.96 * se)), float(np.exp(log_rr + 1.96 * se)), log_rr, se


def dl_random_effects(data):
    """DerSimonian-Laird random-effects pool on log(RR) scale.

    Returns dict with pooled RR, 95% CI, Z, p, Q, I², tau², and per-study weights.
    """
    log_effects, se_effects = [], []
    for item in data:
        _, _, _, log_rr, se = study_rr(item[2], item[3], item[4], item[5])
        log_effects.append(log_rr)
        se_effects.append(se)
    log_effects = np.array(log_effects)
    se_effects = np.array(se_effects)

    w_fe = 1.0 / se_effects ** 2
    pooled_fe_log = (w_fe * log_effects).sum() / w_fe.sum()

    # Heterogeneity
    Q = (w_fe * (log_effects - pooled_fe_log) ** 2).sum()
    df = len(log_effects) - 1
    c = w_fe.sum() - (w_fe ** 2).sum() / w_fe.sum()
    tau2 = max(0.0, (Q - df) / c) if c > 0 else 0.0

    # Random-effects
    w_re = 1.0 / (se_effects ** 2 + tau2)
    pooled_re_log = (w_re * log_effects).sum() / w_re.sum()
    se_pooled = np.sqrt(1.0 / w_re.sum())

    I2 = max(0.0, (Q - df) / Q) * 100 if Q > 0 else 0.0
    p_Q = float(1 - stats.chi2.cdf(Q, df)) if df > 0 else float("nan")
    z = pooled_re_log / se_pooled
    p_effect = float(2 * (1 - stats.norm.cdf(abs(z))))

    return {
        "k": len(data),
        "pooled_rr": float(np.exp(pooled_re_log)),
        "ci_low":    float(np.exp(pooled_re_log - 1.96 * se_pooled)),
        "ci_high":   float(np.exp(pooled_re_log + 1.96 * se_pooled)),
        "z": float(z),
        "p_effect": p_effect,
        "Q": float(Q), "df": df, "p_Q": p_Q,
        "I2": float(I2), "tau2": float(tau2),
        "weights_re_pct": (w_re / w_re.sum() * 100).tolist(),
        "pooled_fe_rr": float(np.exp(pooled_fe_log)),
    }


def mantel_haenszel_rr(data):
    """Fixed-effect Mantel-Haenszel pooled RR. Robust to sparse data without
    continuity correction."""
    R = 0.0
    S = 0.0
    num_var = 0.0
    for item in data:
        a, n1, c, n2 = item[2], item[3], item[4], item[5]
        N = n1 + n2
        if N == 0:
            continue
        R += a * n2 / N
        S += c * n1 / N
        num_var += (n1 * n2 * (a + c) - a * c * N) / N ** 2
    if S == 0:
        return None
    rr_mh = R / S
    se = np.sqrt(num_var / (R * S))
    log_rr = np.log(rr_mh)
    return {
        "rr": float(rr_mh),
        "ci_low": float(np.exp(log_rr - 1.96 * se)),
        "ci_high": float(np.exp(log_rr + 1.96 * se)),
    }


# ------------------------------------------------------------------------------
# REPORTING
# ------------------------------------------------------------------------------
def summarise(name, data):
    """Print per-study and pooled statistics for one outcome."""
    print("\n" + "=" * 90)
    print(name)
    print("=" * 90)
    print(f"\n{'Study':<22}{'HMBF n/N':<12}{'BMBF n/N':<12}"
          f"{'RR':>7}  {'[95% CI]':<22}{'Definition':<30}")
    print("-" * 110)
    rows = []
    for item in data:
        label, year, e1, n1, e2, n2 = item[:6]
        defn = item[6] if len(item) > 6 else ""
        rr, lo, hi, log_rr, se = study_rr(e1, n1, e2, n2)
        print(f"{label} {year:<16} {str(e1)+'/'+str(n1):<12}{str(e2)+'/'+str(n2):<12}"
              f"{rr:>7.3f}  [{lo:>5.3f}, {hi:>5.3f}]  {defn}")
        rows.append({"label": f"{label} {year}", "e1": e1, "n1": n1, "e2": e2, "n2": n2,
                     "rr": rr, "lo": lo, "hi": hi, "log_rr": log_rr, "se": se,
                     "definition": defn})

    pooled = dl_random_effects(data)
    mh = mantel_haenszel_rr(data)

    print(f"\nRandom-effects pooled RR (DerSimonian-Laird):")
    print(f"  RR = {pooled['pooled_rr']:.3f}  "
          f"[{pooled['ci_low']:.3f}, {pooled['ci_high']:.3f}]")
    print(f"  Z = {pooled['z']:+.2f},  p = {pooled['p_effect']:.3f}")
    print(f"\nHeterogeneity:")
    print(f"  Q = {pooled['Q']:.2f}  (df = {pooled['df']}, p = {pooled['p_Q']:.3f})")
    print(f"  I² = {pooled['I2']:.1f}%")
    print(f"  tau² = {pooled['tau2']:.4f}")
    print(f"\nFixed-effect pooled RR:")
    print(f"  Inverse-variance (fixed-effect version of DL):  "
          f"{pooled['pooled_fe_rr']:.3f}")
    print(f"  Mantel-Haenszel:  {mh['rr']:.3f}  "
          f"[{mh['ci_low']:.3f}, {mh['ci_high']:.3f}]")
    print(f"\nPer-study weights (random-effects, %):")
    for r, w in zip(rows, pooled['weights_re_pct']):
        print(f"  {r['label']:<22} {w:>5.1f}%")

    return rows, pooled, mh


# ------------------------------------------------------------------------------
# FOREST PLOT
# ------------------------------------------------------------------------------
def forest_plot(rows, pooled, title, save_path, show_definition=True):
    """Produce a two-panel forest plot (table + plot)."""
    n = len(rows)
    row_h = 0.9
    y_header, y_rule, y_start = 0.5, 1.0, 1.8
    y_pool = y_start + n * row_h + 0.5
    y_het = y_pool + 1.1
    y_bot = y_het + 0.8

    fig_h = max(5.5, 0.6 * y_bot + 1.0)
    fig = plt.figure(figsize=(16, fig_h))
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0], wspace=0.02)
    ax_tbl = fig.add_subplot(gs[0, 0])
    ax_plot = fig.add_subplot(gs[0, 1])
    for ax in (ax_tbl, ax_plot):
        ax.set_ylim(0, y_bot)
        ax.invert_yaxis()

    # ----- Table side -----
    ax_tbl.set_xlim(0, 1)
    ax_tbl.axis("off")
    col = {"study": 0.00, "defn": 0.26, "hmbf": 0.60, "bmbf": 0.76, "weight": 0.92}

    ax_tbl.text(col["study"], y_header, "Study", fontsize=11, fontweight="bold", va="center")
    if show_definition:
        ax_tbl.text(col["defn"], y_header, "Outcome definition",
                    fontsize=11, fontweight="bold", va="center")
    ax_tbl.text(col["hmbf"], y_header, "HMBF\nevents/N", fontsize=10,
                fontweight="bold", va="center", ha="center")
    ax_tbl.text(col["bmbf"], y_header, "BMBF\nevents/N", fontsize=10,
                fontweight="bold", va="center", ha="center")
    ax_tbl.text(col["weight"], y_header, "Weight", fontsize=11,
                fontweight="bold", va="center", ha="center")
    ax_tbl.axhline(y=y_rule, color="black", linewidth=0.6)

    short_defn = {
        "NEC any stage": "NEC, any stage",
        "Surgical NEC": "Surgical NEC",
        "NEC Bell II-III": "NEC Bell II-III",
        "Medical or surgical NEC": "NEC (med./surg.)",
        "Culture-proven late-onset sepsis": "Culture-proven LOS",
        "Culture-proven LOS": "Culture-proven LOS",
        "Culture-proven LOS (full study)": "Culture-proven LOS",
    }

    for i, (r, w) in enumerate(zip(rows, pooled['weights_re_pct'])):
        y = y_start + i * row_h
        ax_tbl.text(col["study"], y, r['label'], fontsize=10.5, va="center")
        if show_definition and r.get('definition'):
            d = short_defn.get(r['definition'], r['definition'])
            ax_tbl.text(col["defn"], y, d, fontsize=10, va="center",
                        style="italic", color="#444")
        ax_tbl.text(col["hmbf"], y, f"{int(r['e1'])}/{int(r['n1'])}",
                    fontsize=10.5, va="center", ha="center")
        ax_tbl.text(col["bmbf"], y, f"{int(r['e2'])}/{int(r['n2'])}",
                    fontsize=10.5, va="center", ha="center")
        ax_tbl.text(col["weight"], y, f"{w:.1f}%", fontsize=10,
                    va="center", ha="center", color="#555")

    y_sep = y_start + (n - 1) * row_h + row_h * 0.55
    ax_tbl.axhline(y=y_sep, color="gray", linewidth=0.5)

    total_e1 = sum(int(r['e1']) for r in rows)
    total_n1 = sum(int(r['n1']) for r in rows)
    total_e2 = sum(int(r['e2']) for r in rows)
    total_n2 = sum(int(r['n2']) for r in rows)
    ax_tbl.text(col["study"], y_pool, "Pooled (random-effects, DL)",
                fontsize=10.5, fontweight="bold", va="center")
    ax_tbl.text(col["hmbf"], y_pool, f"{total_e1}/{total_n1}",
                fontsize=10.5, fontweight="bold", va="center", ha="center")
    ax_tbl.text(col["bmbf"], y_pool, f"{total_e2}/{total_n2}",
                fontsize=10.5, fontweight="bold", va="center", ha="center")
    ax_tbl.text(col["weight"], y_pool, "100.0%", fontsize=10.5,
                fontweight="bold", va="center", ha="center")

    het = (f"Heterogeneity:  tau^2 = {pooled['tau2']:.3f};   "
           f"Q = {pooled['Q']:.2f} (df = {pooled['df']}, p = {pooled['p_Q']:.3f});   "
           f"I^2 = {pooled['I2']:.1f}%\n"
           f"Test for overall effect: Z = {pooled['z']:.2f},  "
           f"p = {pooled['p_effect']:.3f}")
    ax_tbl.text(col["study"], y_het, het, fontsize=10, family="monospace",
                color="#222", va="center")

    # ----- Plot side -----
    ax_plot.set_xscale("log")
    all_lows = [r['lo'] for r in rows] + [pooled['ci_low']]
    all_highs = [r['hi'] for r in rows] + [pooled['ci_high']]
    xmin = min(0.05, min(all_lows) * 0.6)
    xmax = max(10, max(all_highs) * 1.4)
    ax_plot.set_xlim(xmin, xmax)
    ax_plot.axvline(x=1, color="black", linewidth=0.8)
    ax_plot.axhline(y=y_rule, color="black", linewidth=0.6)

    ax_plot.text(xmax * 1.5, y_header, "RR [95% CI]",
                 fontsize=11, fontweight="bold", va="center", clip_on=False)

    for i, (r, w) in enumerate(zip(rows, pooled['weights_re_pct'])):
        y = y_start + i * row_h
        ax_plot.plot([r['lo'], r['hi']], [y, y], color="black", linewidth=1.3)
        for xcap in (r['lo'], r['hi']):
            ax_plot.plot([xcap, xcap], [y - 0.14, y + 0.14],
                         color="black", linewidth=1.3)
        size = 80 + 18 * w
        ax_plot.scatter([r['rr']], [y], s=size, marker="s",
                        color="#2b6cb0", edgecolor="black", linewidth=0.8, zorder=5)
        ax_plot.text(xmax * 1.5, y,
                     f"{r['rr']:>5.2f}  [{r['lo']:>5.2f}, {r['hi']:>6.2f}]",
                     fontsize=10.5, va="center", family="monospace", clip_on=False)

    ax_plot.axhline(y=y_sep, color="gray", linewidth=0.5)
    diamond = Polygon([[pooled['ci_low'], y_pool],
                       [pooled['pooled_rr'], y_pool - 0.38],
                       [pooled['ci_high'], y_pool],
                       [pooled['pooled_rr'], y_pool + 0.38]],
                      closed=True, facecolor="#c53030", edgecolor="black", zorder=6)
    ax_plot.add_patch(diamond)
    ax_plot.text(xmax * 1.5, y_pool,
                 f"{pooled['pooled_rr']:>5.2f}  "
                 f"[{pooled['ci_low']:>5.2f}, {pooled['ci_high']:>6.2f}]",
                 fontsize=11, fontweight="bold", va="center",
                 family="monospace", clip_on=False)

    ax_plot.set_yticks([])
    for s in ("top", "right", "left"):
        ax_plot.spines[s].set_visible(False)
    ax_plot.set_xticks([0.1, 0.5, 1, 2, 5, 10])
    ax_plot.set_xticklabels(["0.1", "0.5", "1", "2", "5", "10"], fontsize=10)
    ax_plot.set_xlabel("Risk ratio (HMBF vs BMBF, log scale)\n"
                       "← Favours HMBF        Favours BMBF →",
                       fontsize=11, labelpad=8)

    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98)
    plt.subplots_adjust(left=0.02, right=0.88, top=0.91, bottom=0.11)
    plt.savefig(save_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"\nSaved: {save_path}")


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    nec_rows, nec_pool, nec_mh = summarise(
        "NEC (any stage, as reported in each trial)", NEC_DATA)
    sepsis_rows, sepsis_pool, sepsis_mh = summarise(
        "Late-onset sepsis (culture-proven)", SEPSIS_DATA)

    forest_plot(nec_rows, nec_pool,
                "Figure 1. Necrotising enterocolitis — HMBF vs BMBF",
                os.path.join(OUTPUT_DIR, "forest_NEC.png"))
    forest_plot(sepsis_rows, sepsis_pool,
                "Figure 2. Late-onset sepsis (culture-proven) — HMBF vs BMBF",
                os.path.join(OUTPUT_DIR, "forest_sepsis.png"),
                show_definition=False)

    with open(os.path.join(OUTPUT_DIR, "meta_analysis_results.json"), "w") as f:
        json.dump({
            "NEC": {"studies": nec_rows, "pooled": nec_pool, "mh": nec_mh},
            "Sepsis": {"studies": sepsis_rows, "pooled": sepsis_pool, "mh": sepsis_mh},
        }, f, indent=2, default=str)
    print(f"\nSaved: {os.path.join(OUTPUT_DIR, 'meta_analysis_results.json')}")
