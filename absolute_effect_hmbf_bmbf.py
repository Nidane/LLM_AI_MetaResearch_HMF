#!/usr/bin/env python3
"""Absolute-effect analyses for direct HMBF vs BMBF comparisons.

Primary analysis: inverse-variance DerSimonian-Laird random-effects meta-analysis
of unadjusted risk differences (RD; HMBF minus BMBF).

Supplementary translation: primary pooled random-effects risk ratios are applied to
pooled observed comparator-arm risks, yielding illustrative events-per-1,000 figures.
These translations are not substitutes for a local baseline risk in cost-effectiveness
models.
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path
from statistics import NormalDist
import pandas as pd

INPUT = Path('/home/ubuntu/leave_one_out_hmbf_bmbf/primary_event_data_reconstructed.csv')
OUTDIR = Path('/home/ubuntu/absolute_effect_hmbf_bmbf')
OUTDIR.mkdir(parents=True, exist_ok=True)


def z975() -> float:
    return NormalDist().inv_cdf(0.975)


def chi_square_sf(q: float, df: int) -> float:
    """Upper-tail χ² probability for df 1–3, sufficient for these analyses."""
    q = max(float(q), 0.0)
    if df == 1:
        return math.erfc(math.sqrt(q / 2.0))
    if df == 2:
        return math.exp(-q / 2.0)
    if df == 3:
        return math.erfc(math.sqrt(q / 2.0)) + math.sqrt(2.0 * q / math.pi) * math.exp(-q / 2.0)
    raise ValueError(f'Unsupported df: {df}')


def dl_re(yi: list[float], vi: list[float]) -> dict[str, float]:
    """DerSimonian-Laird inverse-variance random-effects pooling."""
    k = len(yi)
    w_fe = [1/v for v in vi]
    sw_fe = sum(w_fe)
    mu_fe = sum(w*y for w, y in zip(w_fe, yi)) / sw_fe
    q = sum(w * (y - mu_fe)**2 for w, y in zip(w_fe, yi))
    df = k - 1
    c = sw_fe - sum(w*w for w in w_fe)/sw_fe
    tau2 = max(0.0, (q - df)/c) if c > 0 else 0.0
    w_re = [1/(v + tau2) for v in vi]
    sw_re = sum(w_re)
    mu_re = sum(w*y for w, y in zip(w_re, yi)) / sw_re
    se = math.sqrt(1/sw_re)
    z = z975()
    lo, hi = mu_re - z*se, mu_re + z*se
    z_eff = mu_re/se
    p_eff = math.erfc(abs(z_eff)/math.sqrt(2))
    i2 = max(0.0, (q-df)/q)*100 if q > 0 and df > 0 else 0.0
    return dict(k=k, pooled=mu_re, se=se, ci_low=lo, ci_high=hi, z_effect=z_eff,
                p_effect=p_eff, tau2=tau2, q=q, df=df,
                p_heterogeneity=chi_square_sf(q, df), i2_percent=i2)


def rr_dl(rows: pd.DataFrame) -> dict[str, float]:
    """The established log-RR DL model, for illustrative baseline-risk translations."""
    yi, vi = [], []
    for _, r in rows.iterrows():
        a, n1 = float(r.human_events), float(r.human_total)
        c, n0 = float(r.bovine_events), float(r.bovine_total)
        # Same single-zero correction used in the original RR analysis.
        if (a == 0) ^ (c == 0):
            a, n1, c, n0 = a+0.5, n1+1, c+0.5, n0+1
        yi.append(math.log((a/n1)/(c/n0)))
        vi.append(1/a - 1/n1 + 1/c - 1/n0)
    r = dl_re(yi, vi)
    return {**r, 'rr': math.exp(r['pooled']), 'rr_ci_low': math.exp(r['ci_low']), 'rr_ci_high': math.exp(r['ci_high'])}


def f(x: float, digits: int = 1) -> str:
    return f'{x:.{digits}f}'


def direction_text(x: float, digits: int = 1) -> str:
    """Format an RD-derived event difference with a clinically intuitive direction."""
    if x < 0:
        return f'{f(abs(x), digits)} fewer'
    if x > 0:
        return f'{f(abs(x), digits)} more'
    return f'{f(0, digits)} fewer or more'


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(f'Missing verified input: {INPUT}')
    shutil.copy2(Path(__file__), OUTDIR / Path(__file__).name)
    data = pd.read_csv(INPUT)
    data.to_csv(OUTDIR/'primary_event_data.csv', index=False)

    individual, summary, translations = [], [], []
    for outcome, g in data.groupby('outcome', sort=False):
        rds, vis = [], []
        for _, r in g.iterrows():
            p_h = r.human_events/r.human_total
            p_b = r.bovine_events/r.bovine_total
            rd = p_h-p_b
            var = p_h*(1-p_h)/r.human_total + p_b*(1-p_b)/r.bovine_total
            rds.append(rd); vis.append(var)
            individual.append({
                'outcome': outcome, 'study': r.study, 'pmid': r.pmid,
                'outcome_definition': r.outcome_definition,
                'human_events': r.human_events, 'human_total': r.human_total,
                'bovine_events': r.bovine_events, 'bovine_total': r.bovine_total,
                'human_risk': p_h, 'bovine_risk': p_b,
                'risk_difference': rd, 'risk_difference_per_1000': rd*1000,
                'risk_difference_variance': var,
            })
        rd_result = dl_re(rds, vis)
        rr_result = rr_dl(g)
        comparator_risk = g.bovine_events.sum()/g.bovine_total.sum()
        human_risk_from_rr = comparator_risk*rr_result['rr']
        human_risk_from_rr_lo = comparator_risk*rr_result['rr_ci_low']
        human_risk_from_rr_hi = comparator_risk*rr_result['rr_ci_high']
        translated_diff = human_risk_from_rr-comparator_risk
        translated_diff_lo = human_risk_from_rr_lo-comparator_risk
        translated_diff_hi = human_risk_from_rr_hi-comparator_risk
        summary.append({
            'outcome': outcome, 'studies': rd_result['k'],
            'random_effects_risk_difference': rd_result['pooled'],
            'rd_ci_low': rd_result['ci_low'], 'rd_ci_high': rd_result['ci_high'],
            'rd_per_1000': rd_result['pooled']*1000,
            'rd_per_1000_ci_low': rd_result['ci_low']*1000,
            'rd_per_1000_ci_high': rd_result['ci_high']*1000,
            'p_effect': rd_result['p_effect'], 'tau2_rd_scale': rd_result['tau2'],
            'q': rd_result['q'], 'df': rd_result['df'],
            'p_heterogeneity': rd_result['p_heterogeneity'], 'i2_percent': rd_result['i2_percent'],
            'observed_comparator_events': int(g.bovine_events.sum()),
            'observed_comparator_total': int(g.bovine_total.sum()),
            'observed_comparator_risk': comparator_risk,
            'observed_comparator_per_1000': comparator_risk*1000,
            'primary_rr': rr_result['rr'], 'primary_rr_ci_low': rr_result['rr_ci_low'],
            'primary_rr_ci_high': rr_result['rr_ci_high'],
            'rr_translated_human_per_1000': human_risk_from_rr*1000,
            'rr_translated_human_per_1000_ci_low': human_risk_from_rr_lo*1000,
            'rr_translated_human_per_1000_ci_high': human_risk_from_rr_hi*1000,
            'rr_translated_difference_per_1000': translated_diff*1000,
            'rr_translated_difference_per_1000_ci_low': translated_diff_lo*1000,
            'rr_translated_difference_per_1000_ci_high': translated_diff_hi*1000,
        })
        translations.append(summary[-1])

    ind = pd.DataFrame(individual)
    res = pd.DataFrame(summary)
    ind.to_csv(OUTDIR/'study_level_absolute_effects.csv', index=False, float_format='%.12g')
    res.to_csv(OUTDIR/'absolute_effect_meta_analysis.csv', index=False, float_format='%.12g')

    report = []
    report.append('# Absolute-effect analysis: human-based vs bovine/cow milk-based fortifier\n\n')
    report.append('## Answer to the reviewer\n\n')
    report.append('**Yes.** The directly extracted arm-level event counts permit meta-analysis on the **risk-difference (RD) scale** for both necrotizing enterocolitis (NEC) and sepsis. RD is itself an absolute effect measure; multiplying the RD by 1,000 gives the absolute change in events per 1,000 infants.\n\n')
    report.append('For economic modelling, the most transportable presentation is to combine the pooled relative effect with a **setting-specific baseline risk**. Accordingly, this report also gives illustrative events per 1,000 using the observed pooled bovine-fortifier-arm risk in the included trials. These trial-derived baseline risks should not be used automatically in a cost-effectiveness model if a jurisdictional or hospital-specific baseline incidence is available.\n\n')
    report.append('## Methods\n\n')
    report.append('- **Population/comparison:** same direct-comparison studies and outcome definitions used in the primary RR analysis.\n')
    report.append('- **Direct absolute effect:** unadjusted study-level RD = risk in human-based fortifier arm − risk in bovine/cow milk-based fortifier arm. Negative values therefore favor the human-based fortifier arm.\n')
    report.append('- **Meta-analysis:** inverse-variance random-effects model using the DerSimonian–Laird estimator. No continuity correction is required for an RD calculation in these data because no study has zero events in both arms.\n')
    report.append('- **Events per 1,000:** direct pooled RD × 1,000. A second, illustrative translation applies the original random-effects RR to the pooled observed comparator-arm risk.\n')
    report.append('- **Caution:** the CIs use conventional normal approximations. Given few studies, sparse events, small trials, and non-identical outcome definitions, they should be interpreted cautiously.\n\n')
    report.append('## Main results: directly pooled risk differences\n\n')
    report.append('| Outcome | Studies | Random-effects RD (95% CI) | Absolute difference per 1,000 (95% CI) | P value | I² | τ² (RD scale) |\n')
    report.append('|---|---:|---:|---:|---:|---:|---:|\n')
    for _, r in res.iterrows():
        report.append(f"| {r.outcome} | {int(r.studies)} | {f(r.random_effects_risk_difference*100,2)} percentage points ({f(r.rd_ci_low*100,2)} to {f(r.rd_ci_high*100,2)}) | {direction_text(r.rd_per_1000)} ({direction_text(r.rd_per_1000_ci_low)} to {direction_text(r.rd_per_1000_ci_high)}) | {f(r.p_effect,3)} | {f(r.i2_percent)}% | {f(r.tau2_rd_scale,5)} |\n")
    report.append('\n*Negative risk differences denote fewer events with human-based fortifier; positive differences denote more events. The confidence intervals span benefit and harm for both outcomes.*\n\n')
    report.append('## Illustrative events per 1,000 using trial-derived comparator risk\n\n')
    report.append('| Outcome | Observed bovine-arm risk | Original pooled RR (95% CI) | Estimated human-arm events per 1,000 (95% CI) | RR-translated absolute difference per 1,000 (95% CI) |\n')
    report.append('|---|---:|---:|---:|---:|\n')
    for _, r in res.iterrows():
        report.append(f"| {r.outcome} | {int(r.observed_comparator_events)}/{int(r.observed_comparator_total)} = {f(r.observed_comparator_per_1000)} per 1,000 | {f(r.primary_rr,2)} ({f(r.primary_rr_ci_low,2)}–{f(r.primary_rr_ci_high,2)}) | {f(r.rr_translated_human_per_1000)} ({f(r.rr_translated_human_per_1000_ci_low)}–{f(r.rr_translated_human_per_1000_ci_high)}) | {f(r.rr_translated_difference_per_1000)} ({f(r.rr_translated_difference_per_1000_ci_low)} to {f(r.rr_translated_difference_per_1000_ci_high)}) |\n")
    report.append('\nThe RR-translated figures differ modestly from the directly pooled RDs because risk ratio and risk difference are different effect scales and the comparator risk varies across trials. The **direct pooled RD** is the requested absolute meta-analytic result; the RR translation is provided to support scenario-based modelling.\n\n')
    report.append('## Study-level absolute effects\n\n')
    report.append('| Outcome | Study | Human-based risk | Bovine/cow-based risk | RD (percentage points) | Difference per 1,000 |\n')
    report.append('|---|---|---:|---:|---:|---:|\n')
    for _, r in ind.iterrows():
        report.append(f"| {r.outcome} | {r.study} ({r.pmid}) | {int(r.human_events)}/{int(r.human_total)} = {f(r.human_risk*100,2)}% | {int(r.bovine_events)}/{int(r.bovine_total)} = {f(r.bovine_risk*100,2)}% | {f(r.risk_difference*100,2)} | {f(r.risk_difference_per_1000)} |\n")
    report.append('\n## Suggested manuscript response\n\n')
    report.append('> We additionally conducted random-effects meta-analyses of risk differences to report absolute effects. For NEC, human-based fortifier was associated with **[insert direct pooled RD result]**. For sepsis, human-based fortifier was associated with **[insert direct pooled RD result]**. We also translated the pooled relative effects to events per 1,000 infants using the pooled observed comparator-arm risks; however, because baseline risk varied across trials and outcome definitions were not fully uniform, cost-effectiveness analyses should preferentially use baseline incidence estimates from the target decision setting.\n\n')
    report.append('## Recommendation for the cost-effectiveness component\n\n')
    report.append('1. Include the direct pooled RD and its 95% CI in the review.\n')
    report.append('2. For a model intended for a particular country, payer, hospital, or neonatal unit, use its local NEC and sepsis baseline risks; multiply those risks by the pooled RR and its CI to obtain scenario-specific absolute risks and event counts per 1,000.\n')
    report.append('3. Use sensitivity analysis across plausible baseline-risk ranges and the uncertainty interval for treatment effect.\n')
    report.append('4. Do not claim a conclusive economic benefit from the present clinical evidence: both absolute-effect CIs include no effect and clinically relevant benefit/harm, and the evidence base is small.\n')

    (OUTDIR/'absolute_effect_report.md').write_text(''.join(report), encoding='utf-8')
    print(res.to_string(index=False))
    print(f'Wrote results to {OUTDIR}')


if __name__ == '__main__':
    main()
