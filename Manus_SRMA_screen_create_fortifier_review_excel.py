from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from pathlib import Path

out = Path('/home/ubuntu/human_vs_bovine_fortifier_NEC_sepsis_reviews.xlsx')

included = [
    {
        'Record #': 6,
        'Include category': 'Included: direct network meta-analysis; NEC and sepsis addressed',
        'First author, year': 'Feng 2025',
        'Citation': 'Int Breastfeed J. 2025 Dec 25;21(1):9.',
        'Title': 'Impact of three mammalian milk-derived fortifiers on morbidity and mortality in preterm infants: a systematic review and network meta-analysis.',
        'PMID': '41449441',
        'PMCID': 'PMC12849099',
        'DOI': '10.1186/s13006-025-00801-w',
        'Review type': 'Systematic review and network meta-analysis',
        'Eligible designs': 'Randomized controlled trials were included in the network meta-analysis; 10 studies in qualitative synthesis, 5 in network meta-analysis.',
        'Population': 'Preterm infants in neonatal intensive care units; full text states focus on exclusively breastfed infants receiving maternal or donated breast milk.',
        'Human-based fortifier terms used': 'Human milk-derived fortifier; HMF',
        'Bovine/cow-based fortifier terms used': 'Bovine milk-derived fortifier; BMF',
        'Comparator framework': 'Three-node network: BMF, HMF, and donkey milk-derived fortifier (DMF).',
        'NEC definition/stage': 'Necrotizing enterocolitis incidence; stage not specified in PubMed abstract.',
        'NEC result': 'Reported as BMF versus HMF: RR = 2.33, 95% CI 1.22–4.44, indicating higher NEC risk with BMF and benefit favoring HMF. SUCRA for NEC: HMF 86.4%, DMF 37.7%, BMF 25.9%.',
        'Sepsis definition': 'Neonatal sepsis.',
        'Sepsis result': 'Sepsis was a secondary outcome. The article states confidence intervals for neonatal sepsis crossed 1, so no statistically significant difference was found. SUCRA ranked DMF 74.1%, BMF 43.4%, HMF 32.5%; no exact HMF-vs-BMF sepsis RR was available in the PubMed abstract or extracted full-text markdown.',
        'Authors conclusion relevant to question': 'HMF may be associated with reduced NEC; DMF may be useful for IVH and neonatal sepsis, but evidence is limited and hypothesis-generating.',
        'Quality/limitations noted': 'Limited number of studies and small sample sizes; findings described as preliminary/hypothesis-generating.',
        'Conflict/funding note from PubMed': 'Authors declare no competing interests.',
        'Decision rationale': 'Directly compares HMF with BMF and reports NEC; includes sepsis as a network outcome, although exact HMF-vs-BMF sepsis estimate was not extractable from PubMed abstract.'
    },
    {
        'Record #': 9,
        'Include category': 'Included: direct fortifier-source comparison for NEC only',
        'First author, year': 'Reyes 2025',
        'Citation': 'Nutrients. 2025 Oct 28;17(21):3384.',
        'Title': 'Human Milk Fortification and Necrotizing Enterocolitis in Very Low Birthweight Infants: State of Evidence and Systematic Review with Meta-Analysis.',
        'PMID': '41228457',
        'PMCID': 'PMC12609769',
        'DOI': '10.3390/nu17213384',
        'Review type': 'Systematic state-of-evidence review and meta-analysis',
        'Eligible designs': 'RCTs and observational cohorts; 20 studies total, including 5 RCTs and 15 observational studies, n = 6794.',
        'Population': 'Very low birthweight infants, mostly infants born ≤1250 g.',
        'Human-based fortifier terms used': 'Exclusive human milk diet (EHMD) including human milk-derived fortifiers',
        'Bovine/cow-based fortifier terms used': 'Cow milk-derived fortifiers; cow milk-containing diets',
        'Comparator framework': 'EHMD with human milk-derived fortifiers versus cow milk-derived/cow milk-containing diets; also direct fortifier-type comparisons with human milk as the base diet.',
        'NEC definition/stage': 'Bell Stage ≥2 NEC and surgical NEC.',
        'NEC result': 'Overall EHMD vs cow milk-containing diets: Bell Stage ≥2 NEC OR = 0.59, 95% CI 0.42–0.81; surgical NEC OR = 0.43, 95% CI 0.32–0.58. Direct fortifier-type comparison with human-milk base: Bell Stage ≥2 NEC OR = 0.65, 95% CI 0.44–0.97; surgical NEC OR = 0.51, 95% CI 0.26–0.98.',
        'Sepsis definition': 'Not reported in PubMed abstract.',
        'Sepsis result': 'Not reported/extracted for the target comparison in the PubMed abstract.',
        'Authors conclusion relevant to question': 'EHMD with human milk-derived fortifiers was associated with lower odds of medical and surgical NEC in VLBW infants.',
        'Quality/limitations noted': 'Limited number and sample size of RCTs; includes observational evidence and varying control diets.',
        'Conflict/funding note from PubMed': 'S.M.R. consultant for Prolacta Bioscience and financially supported; T.L.P. consultant for Rev Bioscience and supported; J.F. no conflicts disclosed.',
        'Decision rationale': 'Directly compares human milk-derived fortifier strategies with cow milk-derived/cow milk-containing diets for NEC, but sepsis is not reported in the abstract.'
    },
    {
        'Record #': 10,
        'Include category': 'Included: direct Bayesian meta-analysis; NEC and sepsis addressed',
        'First author, year': 'Huizing 2025',
        'Citation': 'Acta Paediatr. 2025 Dec;114(12):3309-3316.',
        'Title': 'Absence of Evidence of Beneficial Effects of Human Milk-Based Fortifier: A Bayesian Model-Averaged Meta-Analysis.',
        'PMID': '40729426',
        'PMCID': 'PMC12599611',
        'DOI': '10.1111/apa.70260',
        'Review type': 'Bayesian model-averaged meta-analysis of RCTs',
        'Eligible designs': 'Randomized controlled trials; 3 RCTs, n = 405.',
        'Population': 'Infants with gestational age <32 weeks or birthweight <1500 g.',
        'Human-based fortifier terms used': 'Human milk-based fortifier; HMBF',
        'Bovine/cow-based fortifier terms used': 'Bovine milk-based fortifier; BMBF',
        'Comparator framework': 'HMBF versus BMBF.',
        'NEC definition/stage': 'Necrotising enterocolitis stage II–III.',
        'NEC result': 'Bayes factor BF10 = 0.86 for NEC, which did not provide conclusive evidence for either benefit or no effect.',
        'Sepsis definition': 'Late-onset sepsis.',
        'Sepsis result': 'BF10 = 0.69 for late-onset sepsis; no conclusive evidence favoring an effect of HMBF or absence of effect.',
        'Authors conclusion relevant to question': 'Existing RCTs do not provide sufficient evidence to confirm or exclude an effect of HMBF compared with BMBF on NEC, mortality, sepsis, BPD, or severe ROP.',
        'Quality/limitations noted': 'Evidence limited to 3 RCTs and 405 infants; Bayesian evidence inconclusive.',
        'Conflict/funding note from PubMed': 'Authors declare no conflicts of interest.',
        'Decision rationale': 'Direct RCT-based comparison of HMBF versus BMBF with both NEC and late-onset sepsis outcomes.'
    },
    {
        'Record #': 23,
        'Include category': 'Included: direct meta-analysis; NEC and sepsis addressed',
        'First author, year': 'Galis 2024',
        'Citation': 'Nutrients. 2024 Mar 21;16(6):910.',
        'Title': 'Association of Fortification with Human Milk versus Bovine Milk-Based Fortifiers on Short-Term Outcomes in Preterm Infants-A Meta-Analysis.',
        'PMID': '38542821',
        'PMCID': 'PMC10975992',
        'DOI': '10.3390/nu16060910',
        'Review type': 'Meta-analysis',
        'Eligible designs': 'Studies reporting outcomes in target infants; 4 studies, n = 681.',
        'Population': 'Preterm infants with ≤28 weeks gestation and/or birthweight ≤1500 g on an exclusive human milk diet fortified with HMF versus BMF.',
        'Human-based fortifier terms used': 'Human milk-derived fortifiers; HM-HMFs diet',
        'Bovine/cow-based fortifier terms used': 'Bovine milk fortifiers; HM-BMFs group',
        'Comparator framework': 'Exclusive human milk diet, mother’s own milk or donor human milk, fortified with HMF versus BMF.',
        'NEC definition/stage': 'NEC stage ≥2.',
        'NEC result': 'RR = 0.48, 95% CI 0.20–1.17, p = 0.11, I² = 39%; no statistically significant association.',
        'Sepsis definition': 'Sepsis; late-onset timing not specified in abstract.',
        'Sepsis result': 'RR = 0.97, 95% CI 0.66–1.42, p = 0.96, I² = 26%; no difference.',
        'Authors conclusion relevant to question': 'HM-HMFs diet could possibly be associated with decreased mortality with no association with NEC, BPD, sepsis, or ROP.',
        'Quality/limitations noted': 'Limited by the small number of studies included.',
        'Conflict/funding note from PubMed': 'Authors declare no conflict of interest.',
        'Decision rationale': 'Directly compares human milk-derived and bovine milk-based fortifiers and reports both NEC and sepsis estimates.'
    },
    {
        'Record #': 52,
        'Include category': 'Included: direct systematic review/meta-analysis; NEC and sepsis addressed',
        'First author, year': 'Grace 2021',
        'Citation': 'Arch Dis Child Fetal Neonatal Ed. 2021 Mar;106(2):137-142.',
        'Title': 'Safety and efficacy of human milk-based fortifier in enterally fed preterm and/or low birthweight infants: a systematic review and meta-analysis.',
        'PMID': '32943531',
        'PMCID': '',
        'DOI': '10.1136/archdischild-2020-319406',
        'Review type': 'Systematic review and meta-analysis',
        'Eligible designs': 'Randomized or quasi-randomized controlled trials; 2 trials, n = 334.',
        'Population': 'Infants born <34 weeks’ gestation and/or birthweight <1500 g.',
        'Human-based fortifier terms used': 'Human milk-based fortifier',
        'Bovine/cow-based fortifier terms used': 'Cow’s milk-based fortifier',
        'Comparator framework': 'Fortification of human milk with human milk-based fortifier versus cow’s milk-based fortifier.',
        'NEC definition/stage': 'Necrotising enterocolitis, Bell’s stage II or higher.',
        'NEC result': 'RR = 0.47, 95% CI 0.22–0.98; human milk-based fortifier reduced risk of NEC compared with cow’s milk-based fortifier.',
        'Sepsis definition': 'Late-onset sepsis.',
        'Sepsis result': 'No clear evidence of an effect on late-onset sepsis; exact effect estimate not provided in PubMed abstract.',
        'Authors conclusion relevant to question': 'Findings suggest reduced NEC incidence with human milk-based fortifiers versus cow’s milk-based fortifiers; evidence quality is low.',
        'Quality/limitations noted': 'Quality of evidence low to very low due to imprecision and lack of blinding in one study.',
        'Conflict/funding note from PubMed': 'Competing interests: none declared.',
        'Decision rationale': 'Direct RCT/quasi-RCT comparison of human milk-based versus cow’s milk-based fortifier with NEC and late-onset sepsis as main outcomes.'
    },
    {
        'Record #': 66,
        'Include category': 'Included: direct systematic review/meta-analysis; NEC and sepsis addressed',
        'First author, year': 'Ananthan 2020',
        'Citation': 'Adv Nutr. 2020 Sep 1;11(5):1325-1333.',
        'Title': 'Human Milk-Derived Fortifiers Compared with Bovine Milk-Derived Fortifiers in Preterm Infants: A Systematic Review and Meta-Analysis.',
        'PMID': '32277813',
        'PMCID': 'PMC7490161',
        'DOI': '10.1093/advances/nmaa039',
        'Review type': 'Systematic review and meta-analysis',
        'Eligible designs': 'Randomized controlled trials; 6 RCTs included.',
        'Population': 'Preterm infants receiving milk fortification.',
        'Human-based fortifier terms used': 'Human milk-derived fortifier; HMF',
        'Bovine/cow-based fortifier terms used': 'Bovine milk-derived fortifier; BMF',
        'Comparator framework': 'HMF versus BMF in preterm infants.',
        'NEC definition/stage': 'NEC ≥ Stage II and surgical NEC.',
        'NEC result': 'NEC ≥ Stage II: RR = 0.38, 95% CI 0.15–0.95, p = 0.04, I² = 9%, n = 334, 4 RCTs. Surgical NEC: RR = 0.13, 95% CI 0.02–0.67, p = 0.02, I² = 0%, n = 209, 3 RCTs.',
        'Sepsis definition': 'Late-onset sepsis.',
        'Sepsis result': 'RR = 0.96, 95% CI 0.56–1.67, p = 0.90, I² = 63%, n = 334, 4 RCTs; no significant difference.',
        'Authors conclusion relevant to question': 'HMF compared with BMF decreased NEC risk but was associated with lower weight gain; confidence in results is low.',
        'Quality/limitations noted': 'NEC benefit was no longer significant after excluding high-risk-of-bias studies; GRADE evidence low to very low.',
        'Conflict/funding note from PubMed': 'Not specified in PubMed record.',
        'Decision rationale': 'Directly compares HMF with BMF and reports pooled estimates for NEC, surgical NEC, and late-onset sepsis.'
    },
    {
        'Record #': 69,
        'Include category': 'Included: direct Cochrane systematic review; NEC and sepsis/infection addressed',
        'First author, year': 'Premkumar 2019',
        'Citation': 'Cochrane Database Syst Rev. 2019 Nov 7;2019(11):CD013145.',
        'Title': 'Human milk-derived fortifier versus bovine milk-derived fortifier for prevention of mortality and morbidity in preterm neonates.',
        'PMID': '31697857',
        'PMCID': 'PMC6837687',
        'DOI': '10.1002/14651858.CD013145.pub2',
        'Review type': 'Cochrane systematic review',
        'Eligible designs': 'Randomized and quasi-randomized controlled trials; 1 randomized trial met criteria, n = 127.',
        'Population': 'Exclusively breast milk-fed preterm infants.',
        'Human-based fortifier terms used': 'Human milk-derived fortifier; human milk-based fortifier',
        'Bovine/cow-based fortifier terms used': 'Bovine milk-derived fortifier',
        'Comparator framework': 'Breast milk fortified with human milk-derived fortifier versus breast milk fortified with bovine milk-derived fortifier.',
        'NEC definition/stage': 'Necrotizing enterocolitis; stage not specified in abstract.',
        'NEC result': 'RR = 0.95, 95% CI 0.20–4.54; 1 study, 125 infants, low-certainty evidence; no decrease in NEC.',
        'Sepsis definition': 'Late-onset sepsis/infection.',
        'Sepsis result': 'Human milk-derived fortifiers did not decrease late-onset sepsis/infection; exact effect estimate not provided in PubMed abstract.',
        'Authors conclusion relevant to question': 'Insufficient evidence; low-certainty evidence suggests human milk-derived fortifier may not change NEC, mortality, feeding intolerance, infection, or growth compared with bovine milk-derived fortifier.',
        'Quality/limitations noted': 'Only one eligible trial; low-certainty evidence.',
        'Conflict/funding note from PubMed': 'Authors report no known conflicts relevant to the review; Cochrane Neonatal support from The Gerber Foundation with editorial independence safeguards.',
        'Decision rationale': 'Direct Cochrane comparison of human milk-derived versus bovine milk-derived fortifier with NEC and infection/sepsis outcomes.'
    }
]

candidate_log = [
    (6, '41449441', '10.1186/s13006-025-00801-w', 'Included', 'Direct HMF/BMF/DMF network meta-analysis; NEC reported and sepsis assessed.'),
    (9, '41228457', '10.3390/nu17213384', 'Included for NEC; sepsis not reported in abstract', 'Direct human milk-derived fortifier/EHMD versus cow milk-derived/cow-containing comparison for NEC.'),
    (10, '40729426', '10.1111/apa.70260', 'Included', 'Direct HMBF versus BMBF Bayesian meta-analysis; NEC and late-onset sepsis reported.'),
    (11, '40534564', '10.1177/19345798251350987', 'Excluded', 'Comparison is human breast milk fortification with human milk fortifier versus preterm infant formula; not a human-derived versus bovine/cow-derived fortifier source comparison.'),
    (13, '40431391', '10.3390/nu17101651', 'Excluded near-miss', 'Broad feeding-regimen network meta-analysis with treatment-class rankings, not a dedicated direct HMF versus BMF effect extraction for NEC/sepsis.'),
    (17, '39332772', '10.1016/j.tjnut.2024.09.010', 'Excluded', 'Plant-based milk consumption in children/adolescents; wrong population and intervention.'),
    (18, '39239939', '10.1002/14651858.CD002971.pub6', 'Excluded', 'Donor human milk versus formula for preventing NEC; not fortifier source.'),
    (23, '38542821', '10.3390/nu16060910', 'Included', 'Direct HMF versus BMF meta-analysis with NEC and sepsis pooled estimates.'),
    (33, '35280446', '10.3389/fped.2021.793311', 'Excluded', 'Exclusive maternal milk versus formula; not fortifier source.'),
    (37, '34669996', '10.1111/jpc.15810', 'Excluded', 'Early versus delayed human milk fortification; not fortifier source.'),
    (41, '34207261', '10.3390/nu13062089', 'Excluded', 'Human milk feeding/growth comparison, mainly versus formula; not fortifier source.'),
    (42, '34101248', '10.1002/ncp.10663', 'Excluded near-miss', 'Liquid human milk fortifier formulation review comparing exclusive HM-derived or hydrolyzed-protein liquid HMFs versus powder HMF controls; not a clean human-derived versus bovine/cow-derived source comparison.'),
    (45, '33733486', '10.1002/14651858.CD012413.pub3', 'Excluded', 'High versus standard volume enteral feeds; not fortifier source.'),
    (52, '32943531', '10.1136/archdischild-2020-319406', 'Included', 'Direct human milk-based versus cow’s milk-based fortifier systematic review/meta-analysis; NEC and late-onset sepsis assessed.'),
    (55, '32726863', '10.1002/14651858.CD013392.pub2', 'Excluded', 'Early versus late fortification; fortifier type only as a study characteristic.'),
    (66, '32277813', '10.1093/advances/nmaa039', 'Included', 'Direct HMF versus BMF systematic review/meta-analysis with NEC, surgical NEC, and late-onset sepsis estimates.'),
    (69, '31697857', '10.1002/14651858.CD013145.pub2', 'Included', 'Direct Cochrane comparison of human milk-derived versus bovine milk-derived fortifier with NEC and infection/sepsis outcomes.'),
    (70, '31645057', '10.1038/s41390-019-0630-2', 'Excluded near-miss', 'Broad overview of nutritional interventions to reduce infection/NEC/mortality; not a dedicated direct fortifier-source review.'),
    (91, '29461479', '10.3390/nu10020238', 'Excluded', 'Donor human milk/BPD and broader dietary patterns; not direct fortifier source comparison for NEC/sepsis.'),
    (94, '28159204', '10.1016/j.clp.2016.11.011', 'Excluded near-miss', 'Systematic review of unanswered questions; asks about human milk-based versus cow milk-based fortifiers but does not provide pooled NEC/sepsis estimates in PubMed abstract.'),
]

synonyms = [
    ('Human-based fortifier keywords considered', 'human milk fortifier; fortified human milk; human-derived fortifier; human milk-derived fortifier; human milk fortification; human milk-based fortification; human milk-based fortifier; donor milk-derived fortifier; donor-derived fortifier; human’s milk fortifier; human’s milk fortification; human milk-based human milk fortifier; HMF; HMBF; HM-HMF; exclusive human milk diet where fortifier source was human-derived'),
    ('Bovine/cow-based fortifier keywords considered', 'bovine milk-derived fortifier; bovine milk-based fortifier; bovine-derived fortifier; bovine-based fortifier; bovine fortifier; BMF; BMBF; cow milk-derived fortifier; cow milk-based fortifier; cow’s milk-based fortifier; cow-derived; cow-based; cow milk-containing diet where the fortifier/source comparison was explicit'),
    ('Outcome keywords considered', 'necrotizing enterocolitis; necrotising enterocolitis; NEC; Bell Stage ≥2; stage II–III; surgical NEC; sepsis; neonatal sepsis; late-onset sepsis; infection; late-onset infection'),
    ('Main inclusion rule', 'Systematic review, meta-analysis, Bayesian meta-analysis, or network meta-analysis from the supplied 130 PubMed records that directly compared human-based/human-derived/human milk-based fortifier with bovine/cow milk-derived or cow’s milk-based fortifier, and reported NEC and/or sepsis/infection outcomes.'),
    ('Important interpretation note', 'Some reviews reported results as HMF versus BMF whereas Feng 2025 reported the NEC effect as BMF versus HMF. Direction of effect is explicitly stated in the extraction table to avoid inversion errors.')
]

wb = Workbook()
ws = wb.active
ws.title = 'Included direct reviews'
headers = list(included[0].keys())
ws.append(headers)
for row in included:
    ws.append([row[h] for h in headers])

# Create candidate log sheet
ws2 = wb.create_sheet('Candidate screening log')
ws2.append(['Record #','PMID','DOI','Decision','Rationale'])
for r in candidate_log:
    ws2.append(list(r))

# Create methods/synonyms sheet
ws3 = wb.create_sheet('Methods and synonyms')
ws3.append(['Item','Details'])
for r in synonyms:
    ws3.append(list(r))
ws3.append(['Screening summary','All 130 numbered PubMed records in the uploaded file were parsed. Twenty records were keyword-flagged as plausible candidates and were screened more closely. Seven records were included as direct human-based versus bovine/cow-based fortifier comparisons for NEC and/or sepsis outcomes.'])

# Summary sheet
ws4 = wb.create_sheet('Outcome summary')
ws4.append(['Record #','First author, year','NEC finding','Sepsis finding','Overall interpretation'])
for row in included:
    ws4.append([row['Record #'], row['First author, year'], row['NEC result'], row['Sepsis result'], row['Authors conclusion relevant to question']])

# Style all sheets
for wsx in wb.worksheets:
    wsx.freeze_panes = 'A2'
    wsx.auto_filter.ref = wsx.dimensions
    for cell in wsx[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='1F4E78')
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin = Side(style='thin', color='D9E2F3')
    for row in wsx.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical='top', wrap_text=True)
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    # Add table if dimensions valid
    max_row = wsx.max_row
    max_col = wsx.max_column
    ref = f"A1:{get_column_letter(max_col)}{max_row}"
    tab = Table(displayName=(wsx.title.replace(' ','_').replace('-','_')[:25] + '_tbl'), ref=ref)
    style = TableStyleInfo(name='TableStyleMedium2', showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
    tab.tableStyleInfo = style
    wsx.add_table(tab)
    # widths
    for col in range(1, max_col+1):
        letter = get_column_letter(col)
        header = wsx.cell(1,col).value or ''
        if header in ['Title','NEC result','Sepsis result','Authors conclusion relevant to question','Quality/limitations noted','Decision rationale','Rationale','Details','Overall interpretation']:
            wsx.column_dimensions[letter].width = 55
        elif header in ['Citation','Comparator framework','Population','Eligible designs']:
            wsx.column_dimensions[letter].width = 42
        elif header in ['Record #','PMID','PMCID']:
            wsx.column_dimensions[letter].width = 14
        else:
            wsx.column_dimensions[letter].width = 24

# Move summary first? Keep included first.
wb.save(out)
print(out)
