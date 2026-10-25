from artifact_tool import Workbook, SpreadsheetFile
from datetime import datetime
import re, textwrap, os, json, math
path = "/mnt/data/130.Meta&SystematicR.abstract.txt"
raw = open(path, encoding="utf-8", errors="replace").read()

# Manually curated extraction based on the uploaded PubMed abstracts.
included = [
    {
        "Record No.": 6,
        "First author / year": "Feng 2025",
        "Citation": "Int Breastfeed J. 2025 Dec 25;21(1):9",
        "Title": "Impact of three mammalian milk-derived fortifiers on morbidity and mortality in preterm infants: a systematic review and network meta-analysis.",
        "Review type": "Systematic review + network meta-analysis",
        "Search date / databases": "Multiple databases including MEDLINE, CINAHL, PubMed, CNKI, Cochrane CENTRAL; date not stated in abstract.",
        "Population": "Preterm infants in NICUs.",
        "Studies / sample": "10 studies / 545 preterm infants for qualitative analysis; 5 studies in network meta-analysis.",
        "Human-based fortifier terms": "Human milk-derived fortifier (HMF).",
        "Bovine/cow-based comparator terms": "Bovine milk-derived fortifier (BMF); also compared donkey milk-derived fortifier (DMF).",
        "Direct comparison?": "Yes, HMF vs BMF included in NMA; NEC estimate directly reported as BMF compared with HMF.",
        "NEC result": "Compared with HMF, BMF was associated with increased NEC risk: RR 2.33, 95% CI 1.22–4.44. HMF ranked most favourable for reducing NEC incidence and mortality.",
        "Sepsis result": "Neonatal sepsis was considered; abstract states DMF might be a potential option for reducing neonatal sepsis. HMF-vs-BMF sepsis estimate not extractable from the abstract.",
        "Other outcomes": "Mortality, IVH, morbidity/mortality; DMF potentially favourable for IVH and neonatal sepsis.",
        "Authors' conclusion": "HMF may reduce NEC; DMF may have potential anti-inflammatory benefits; findings are preliminary due to few/small studies.",
        "Evidence quality / limitations": "Limited number of studies and small sample sizes; further RCTs needed.",
        "Conflict of interest": "No competing interests declared.",
        "DOI": "10.1186/s13006-025-00801-w",
        "PMID": "41449441",
        "PMCID": "PMC12849099",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/41449441/",
        "Source basis": "Uploaded PubMed record/abstract."
    },
    {
        "Record No.": 9,
        "First author / year": "Reyes 2025",
        "Citation": "Nutrients. 2025 Oct 28;17(21):3384",
        "Title": "Human Milk Fortification and Necrotizing Enterocolitis in Very Low Birthweight Infants: State of Evidence and Systematic Review with Meta-Analysis.",
        "Review type": "Systematic state-of-evidence review + meta-analysis",
        "Search date / databases": "PubMed, Web of Science, Scopus through July 2025.",
        "Population": "VLBW infants; most studies enrolled infants ≤1250 g.",
        "Studies / sample": "20 studies: 5 RCTs and 15 observational cohorts; n = 6794 infants.",
        "Human-based fortifier terms": "Exclusive human milk diet (EHMD) including human milk-derived fortifiers; human milk-derived fortifiers.",
        "Bovine/cow-based comparator terms": "Cow milk-derived diets; cow milk-containing diets.",
        "Direct comparison?": "Yes for NEC: includes direct fortifier-type comparisons with a human milk base diet; broader EHMD vs cow milk-containing diets also analysed.",
        "NEC result": "EHMD vs cow milk-containing diets: Bell Stage ≥2 NEC OR 0.59, 95% CI 0.42–0.81; surgical NEC OR 0.43, 95% CI 0.32–0.58. Direct fortifier type with human milk base: Bell Stage ≥2 NEC OR 0.65, 95% CI 0.44–0.97, n = 2102; surgical NEC OR 0.51, 95% CI 0.26–0.98, n = 1659.",
        "Sepsis result": "Not reported in the abstract.",
        "Other outcomes": "Medical NEC, surgical NEC; sensitivity analyses by study design and exclusion of infant formula from controls.",
        "Authors' conclusion": "EHMD with human milk-derived fortifiers was associated with lower odds of medical and surgical NEC in VLBW infants.",
        "Evidence quality / limitations": "RCT numbers and sample sizes remain limited; authors note consistency across RCT and observational studies.",
        "Conflict of interest": "S.M.R. consultant for Prolacta Bioscience and financially supported; T.L.P. consultant for Rev Bioscience and financially supported; J.F. no conflicts disclosed.",
        "DOI": "10.3390/nu17213384",
        "PMID": "41228457",
        "PMCID": "PMC12609769",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/41228457/",
        "Source basis": "Uploaded PubMed record/abstract."
    },
    {
        "Record No.": 10,
        "First author / year": "Huizing 2025",
        "Citation": "Acta Paediatr. 2025 Dec;114(12):3309–3316",
        "Title": "Absence of Evidence of Beneficial Effects of Human Milk-Based Fortifier: A Bayesian Model-Averaged Meta-Analysis.",
        "Review type": "Bayesian model-averaged meta-analysis of RCTs",
        "Search date / databases": "Not stated in abstract.",
        "Population": "Infants with gestational age <32 weeks or birthweight <1500 g.",
        "Studies / sample": "3 RCTs; n = 405 infants.",
        "Human-based fortifier terms": "Human milk-based fortifier (HMBF/HMBFs).",
        "Bovine/cow-based comparator terms": "Bovine milk-based fortifier (BMBF).",
        "Direct comparison?": "Yes, RCTs comparing HMBF versus BMBF.",
        "NEC result": "NEC stage II–III: BF10 = 0.86; no conclusive evidence for either benefit or no effect.",
        "Sepsis result": "Late-onset sepsis: BF10 = 0.69; no conclusive evidence.",
        "Other outcomes": "Mortality BF10 = 1.07; BPD BF10 = 0.92; severe ROP BF10 = 0.75.",
        "Authors' conclusion": "Existing RCTs do not provide sufficient evidence to confirm or exclude an effect of HMBF vs BMBF on NEC, mortality, sepsis, BPD or severe ROP.",
        "Evidence quality / limitations": "Only 3 RCTs/405 infants; Bayesian evidence inconclusive.",
        "Conflict of interest": "Authors declare no conflicts of interest.",
        "DOI": "10.1111/apa.70260",
        "PMID": "40729426",
        "PMCID": "PMC12599611",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/40729426/",
        "Source basis": "Uploaded PubMed record/abstract."
    },
    {
        "Record No.": 23,
        "First author / year": "Galis 2024",
        "Citation": "Nutrients. 2024 Mar 21;16(6):910",
        "Title": "Association of Fortification with Human Milk versus Bovine Milk-Based Fortifiers on Short-Term Outcomes in Preterm Infants-A Meta-Analysis.",
        "Review type": "Meta-analysis",
        "Search date / databases": "PubMed, Embase, Google Scholar, CENTRAL, CINAHL; January 2015–August 2023.",
        "Population": "Preterm infants ≤28 weeks gestation and/or birthweight ≤1500 g on an exclusive human milk diet.",
        "Studies / sample": "4 studies; n = 681 infants.",
        "Human-based fortifier terms": "Human milk-derived fortifiers (HMFs); HM-HMFs diet.",
        "Bovine/cow-based comparator terms": "Bovine milk fortifiers (BMFs); HM-BMFs diet.",
        "Direct comparison?": "Yes, HMFs compared with BMFs.",
        "NEC result": "NEC stage ≥2: RR 0.48, 95% CI 0.20–1.17; p = 0.11; I² = 39%; no statistically significant difference.",
        "Sepsis result": "Sepsis: RR 0.97, 95% CI 0.66–1.42; p = 0.96; I² = 26%; no statistically significant difference.",
        "Other outcomes": "Mortality RR 0.50, 95% CI 0.26–0.94; p = 0.03; BPD and combined ROP also assessed.",
        "Authors' conclusion": "HM-HMFs diet may be associated with decreased mortality, with no association with NEC, BPD, sepsis or ROP.",
        "Evidence quality / limitations": "Small number of studies; authors state findings provide impetus for subsequent clinical trials.",
        "Conflict of interest": "Authors declare no conflict of interest.",
        "DOI": "10.3390/nu16060910",
        "PMID": "38542821",
        "PMCID": "PMC10975992",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/38542821/",
        "Source basis": "Uploaded PubMed record/abstract."
    },
    {
        "Record No.": 52,
        "First author / year": "Grace 2021",
        "Citation": "Arch Dis Child Fetal Neonatal Ed. 2021 Mar;106(2):137–142",
        "Title": "Safety and efficacy of human milk-based fortifier in enterally fed preterm and/or low birthweight infants: a systematic review and meta-analysis.",
        "Review type": "Systematic review + meta-analysis of randomized/quasi-randomized trials",
        "Search date / databases": "Databases, trial registries and references searched until 5 Nov 2019.",
        "Population": "Preterm and/or VLBW infants born <34 weeks gestation and/or birthweight <1500 g.",
        "Studies / sample": "2 trials; 334 infants included; primary outcome data for 332 infants.",
        "Human-based fortifier terms": "Human milk-based fortifier; human milk-based milk fortifier.",
        "Bovine/cow-based comparator terms": "Cow's milk-based fortifier.",
        "Direct comparison?": "Yes, human milk-based vs cow's milk-based fortifier.",
        "NEC result": "Necrotising enterocolitis Bell stage II or higher: RR 0.47, 95% CI 0.22–0.98; reduced risk with human milk-based fortifier.",
        "Sepsis result": "Late-onset sepsis: no clear evidence of an effect; effect estimate not reported in abstract.",
        "Other outcomes": "Other outcomes assessed, but no clear evidence of effect per abstract.",
        "Authors' conclusion": "Human milk-based fortifiers may reduce NEC compared with cow's milk-based fortifiers; overall evidence quality low.",
        "Evidence quality / limitations": "Low to very low evidence due to imprecision and lack of blinding in one study; further powered trials needed.",
        "Conflict of interest": "Competing interests: none declared.",
        "DOI": "10.1136/archdischild-2020-319406",
        "PMID": "32943531",
        "PMCID": "",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/32943531/",
        "Source basis": "Uploaded PubMed record/abstract."
    },
    {
        "Record No.": 66,
        "First author / year": "Ananthan 2020",
        "Citation": "Adv Nutr. 2020 Sep 1;11(5):1325–1333",
        "Title": "Human Milk-Derived Fortifiers Compared with Bovine Milk-Derived Fortifiers in Preterm Infants: A Systematic Review and Meta-Analysis.",
        "Review type": "Systematic review + meta-analysis of RCTs",
        "Search date / databases": "Search details not stated in abstract.",
        "Population": "Preterm infants.",
        "Studies / sample": "6 RCTs included; NEC and sepsis analyses used 4 RCTs with n = 334 infants.",
        "Human-based fortifier terms": "Human milk-derived fortifier (HMF).",
        "Bovine/cow-based comparator terms": "Bovine milk-derived fortifier (BMF).",
        "Direct comparison?": "Yes, HMF compared with BMF.",
        "NEC result": "NEC ≥ stage II: RR 0.38, 95% CI 0.15–0.95; p = 0.04; I² = 9%; n = 334, 4 RCTs. Surgical NEC: RR 0.13, 95% CI 0.02–0.67; p = 0.02; I² = 0%; n = 209, 3 RCTs.",
        "Sepsis result": "Late-onset sepsis: RR 0.96, 95% CI 0.56–1.67; p = 0.90; I² = 63%; n = 334, 4 RCTs; no significant difference.",
        "Other outcomes": "Mortality, weight gain, length, head circumference; HMF associated with lower weight gain.",
        "Authors' conclusion": "HMF compared with BMF decreased NEC risk but lowered weight gain; evidence quality low/very low and NEC benefit was not robust after excluding high-risk-of-bias studies.",
        "Evidence quality / limitations": "GRADE low to very low; sensitivity analyses removed NEC significance; adequately powered non-industry RCTs needed.",
        "Conflict of interest": "No conflict statement included in extracted abstract segment.",
        "DOI": "10.1093/advances/nmaa039",
        "PMID": "32277813",
        "PMCID": "PMC7490161",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/32277813/",
        "Source basis": "Uploaded PubMed record/abstract."
    },
    {
        "Record No.": 69,
        "First author / year": "Premkumar 2019",
        "Citation": "Cochrane Database Syst Rev. 2019 Nov 7;2019(11):CD013145",
        "Title": "Human milk-derived fortifier versus bovine milk-derived fortifier for prevention of mortality and morbidity in preterm neonates.",
        "Review type": "Cochrane systematic review",
        "Search date / databases": "CENTRAL, MEDLINE/PREMEDLINE, Embase, CINAHL, BIOSIS, conference abstracts, trial registries; searched September 2018.",
        "Population": "Preterm infants fed breast milk.",
        "Studies / sample": "1 randomized trial; 127 infants met eligibility criteria; NEC data for 125 infants.",
        "Human-based fortifier terms": "Human milk-derived fortifier; human milk-based fortifier.",
        "Bovine/cow-based comparator terms": "Bovine milk-derived fortifier.",
        "Direct comparison?": "Yes, randomized/quasi-randomized trials of human milk-derived vs bovine milk-derived fortifier.",
        "NEC result": "NEC: RR 0.95, 95% CI 0.20–4.54; 1 study, 125 infants; low-certainty evidence; no decrease in risk.",
        "Sepsis result": "Human milk-derived fortifier did not decrease late-onset sepsis/infection; effect estimate not reported in abstract.",
        "Other outcomes": "Growth, feeding intolerance, mortality.",
        "Authors' conclusion": "Insufficient evidence; low-certainty evidence suggests HMF may not change NEC, mortality, feeding intolerance, infection or growth compared with bovine milk-derived fortifier.",
        "Evidence quality / limitations": "Only one RCT; low-certainty evidence.",
        "Conflict of interest": "Authors report no known conflicts; Cochrane Neonatal support disclosed via Gerber Foundation with editorial independence.",
        "DOI": "10.1002/14651858.CD013145.pub2",
        "PMID": "31697857",
        "PMCID": "PMC6837687",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/31697857/",
        "Source basis": "Uploaded PubMed record/abstract."
    }
]

related = [
    {
        "Record No.": 4,
        "First author / year": "Hamouda 2026",
        "Title": "Effect of different feeding approaches on growth, neonatal morbidities, mortality and neurodevelopmental outcome in preterm infants: a systematic review and network meta-analysis.",
        "Reason not classified as clean direct HMF-vs-BMF review": "Broad NMA of feeding approaches. Abstract reports HM + bovine milk fortifier variants for growth and states no significant neonatal morbidity/mortality differences, but does not provide a direct human-derived vs bovine/cow-derived fortifier comparison for NEC/sepsis.",
        "DOI": "10.1136/archdischild-2024-327677",
        "PMID": "41554628",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/41554628/"
    },
    {
        "Record No.": 13,
        "First author / year": "Campbell-Yeo 2025",
        "Title": "Effect of Multi-Nutrient Milk Fortification on Preterm Neonate Outcomes: A Network Meta-Analysis.",
        "Reason not classified as clean direct HMF-vs-BMF review": "Relevant NMA includes human-milk-based and bovine fortifier treatment classes and NEC/sepsis outcomes, but the abstract only reports rankings, not a direct HMF-vs-BMF effect estimate. Included as related but not direct/extractable from the abstract.",
        "DOI": "10.3390/nu17101651",
        "PMID": "40431391",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/40431391/"
    },
    {
        "Record No.": 15,
        "First author / year": "Contreras Chova 2024",
        "Title": "Strategies for the Fortification of Human Milk in Preterm Infants: A Systematic Review.",
        "Reason not classified as clean direct HMF-vs-BMF review": "General systematic review of fortification strategies; abstract does not report direct HMF-vs-BMF NEC/sepsis estimates.",
        "DOI": "10.7759/cureus.73380",
        "PMID": "39659332",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/39659332/"
    },
    {
        "Record No.": 16,
        "First author / year": "Azhar 2024/2025",
        "Title": "Nutritional Management of Low Birth Weight and Preterm Infants in Low- and Low Middle-Income Countries.",
        "Reason not classified as clean direct HMF-vs-BMF review": "Review/update of broad nutrition evidence in LMIC contexts; discusses breast milk fortification and NEC with formula but not a direct human-based vs bovine/cow-based fortifier comparison.",
        "DOI": "10.1159/000542154",
        "PMID": "39591949",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/39591949/"
    },
    {
        "Record No.": 18,
        "First author / year": "Quigley 2024",
        "Title": "Donor human milk for preventing necrotising enterocolitis in very preterm or very low-birthweight infants.",
        "Reason not classified as clean direct HMF-vs-BMF review": "Cochrane review of donor human milk versus formula for NEC/infection/mortality; not a fortifier-source comparison.",
        "DOI": "10.1002/14651858.CD002971.pub6",
        "PMID": "39240476",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/39240476/"
    },
    {
        "Record No.": 42,
        "First author / year": "Bridges 2021",
        "Title": "Comparative effectiveness of liquid human milk fortifiers: A systematic review and meta-analysis.",
        "Reason not classified as clean direct HMF-vs-BMF review": "Compares liquid HMFs derived from exclusive human milk or hydrolyzed protein versus powder HMFs; NEC/sepsis included, but not specifically human-derived vs bovine/cow-derived fortifier.",
        "DOI": "10.1002/ncp.10663",
        "PMID": "34101248",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/34101248/"
    },
    {
        "Record No.": 48,
        "First author / year": "Kumar 2021",
        "Title": "Fortification of Human Milk With Infant Formula for Very Low Birth Weight Preterm Infants: A Systematic Review.",
        "Reason not classified as clean direct HMF-vs-BMF review": "Compares human milk fortified with infant formula versus HMF; not human milk-derived vs bovine/cow milk-derived fortifier.",
        "DOI": "",
        "PMID": "",
        "PubMed URL": ""
    },
    {
        "Record No.": 55,
        "First author / year": "Thanigainathan 2020",
        "Title": "Early fortification of human milk versus late fortification to promote growth in preterm infants.",
        "Reason not classified as clean direct HMF-vs-BMF review": "Timing of fortification; not fortifier source comparison. Abstract mentions subgroup by type of fortifier, but not direct HMF-vs-BMF outcome estimates.",
        "DOI": "10.1002/14651858.CD013392.pub2",
        "PMID": "",
        "PubMed URL": ""
    },
    {
        "Record No.": 61,
        "First author / year": "Brown 2020",
        "Title": "Multi-nutrient fortification of human milk for preterm infants.",
        "Reason not classified as clean direct HMF-vs-BMF review": "Cochrane review of multi-nutrient fortification versus no fortification; not fortifier-source comparison.",
        "DOI": "10.1002/14651858.CD000343.pub4",
        "PMID": "",
        "PubMed URL": ""
    },
    {
        "Record No.": 65,
        "First author / year": "van Katwyk 2020",
        "Title": "Economic Analysis of Exclusive Human Milk Diets for High-Risk Neonates, a Canadian Hospital Perspective.",
        "Reason not classified as clean direct HMF-vs-BMF review": "Economic/cost analysis using meta-analysis-derived inputs; not primarily a clinical systematic review comparing HMF vs BMF on NEC/sepsis.",
        "DOI": "10.1089/bfm.2019.0273",
        "PMID": "32302511",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/32302511/"
    },
    {
        "Record No.": 70,
        "First author / year": "Bührer 2020",
        "Title": "Nutritional interventions to reduce rates of infection, necrotizing enterocolitis and mortality in very preterm infants.",
        "Reason not classified as clean direct HMF-vs-BMF review": "Systematic review of meta-analyses/RCTs across nutritional interventions. Abstract states no differences emerged between infants receiving human or bovine milk-based fortifiers, but does not provide a dedicated direct comparison or estimate.",
        "DOI": "10.1038/s41390-019-0630-2",
        "PMID": "31645057",
        "PubMed URL": "https://pubmed.ncbi.nlm.nih.gov/31645057/"
    }
]

terms = [
    ["Concept", "Synonyms / search variants to treat as the same concept", "Caution"],
    ["Human-based milk fortifier", "human milk-derived fortifier; human milk-based fortifier; human-derived fortifier; donor human milk-derived fortifier; donor-derived fortifier; human milk-based milk fortifier; exclusive human milk diet (EHMD) including human milk-derived fortifier; HMBF/HMBFs; HMDF/HMDFs; HMF when context clearly means human milk-derived/human milk-based fortifier", "HMF can also mean generic human milk fortifier, not necessarily human-derived; context must be checked."],
    ["Bovine/cow milk-based fortifier", "bovine milk-derived fortifier; bovine milk-based fortifier; cow milk-derived fortifier; cow's milk-based fortifier; cow milk-containing diets; BMF; BMBF; bovine fortifier", "Some reviews compare whole diets that include formula/cow milk exposures; note whether comparison isolates fortifier type."],
    ["NEC", "necrotizing enterocolitis; necrotising enterocolitis; NEC; Bell stage ≥2; Bell's stage II or higher; medical NEC; surgical NEC; NEC stage II–III", "Stage definitions vary; extracted exactly as reported."],
    ["Sepsis", "sepsis; late-onset sepsis; late onset sepsis; neonatal sepsis; infection; late-onset invasive infection", "Not all abstracts report effect estimates; do not infer from broad 'infection' without context."]
]

summary_rows = [
    ["Item", "Value"],
    ["Uploaded PubMed records screened", "130 records in 130.Meta&SystematicR.abstract.txt"],
    ["Primary inclusion criterion", "Systematic review/meta-analysis/network meta-analysis with direct or explicit comparison of human-based/human milk-derived/human milk-based fortifier vs bovine/cow milk-derived/cow milk-based fortifier."],
    ["Target outcomes", "NEC (any reported stage) and sepsis/late-onset sepsis/neonatal sepsis/infection where extractable."],
    ["Included direct/comparative reviews", len(included)],
    ["Close related but not clean direct/extractable", len(related)],
    ["Most relevant direct NEC+sepsis extractable rows", "Galis 2024; Huizing 2025; Ananthan 2020; Grace 2021; Premkumar 2019. Feng 2025 includes NEC direct and sepsis broadly; Reyes 2025 focuses on NEC with no sepsis abstract estimate."],
    ["Date created", datetime.now().strftime("%Y-%m-%d %H:%M")]
]

# Create workbook
wb = Workbook.create()
ws_sum = wb.worksheets.add("Summary")
ws_inc = wb.worksheets.add("Included_Direct_Reviews")
ws_rel = wb.worksheets.add("Related_Not_Direct")
ws_terms = wb.worksheets.add("Screening_Terms")

# Write summary
ws_sum.get_range("A1").values = [["Screening summary: human-based vs bovine/cow milk-based fortifiers on NEC and sepsis"]]
ws_sum.get_range("A3:B10").values = summary_rows
ws_sum.get_range("A12").values = [["Interpretation note"]]
ws_sum.get_range("A13:B16").values = [
    ["Directness", "Reviews were included if the abstract explicitly compared human milk-derived/human milk-based fortifier with bovine/cow milk-derived/cow milk-based fortifier, even if a network meta-analysis included other fortifier types."],
    ["Outcome availability", "Some included reviews directly compare fortifier type but only report NEC in the abstract. Those were retained and flagged as 'sepsis not reported/not extractable'."],
    ["No new full-text review", "This spreadsheet is based on the uploaded PubMed record/abstract text, not full-text supplemental tables."],
    ["Source", "130.Meta&SystematicR.abstract.txt uploaded by user."]
]

# Include table
inc_headers = list(included[0].keys())
inc_matrix = [inc_headers] + [[row.get(h, "") for h in inc_headers] for row in included]
ws_inc.get_range_by_indexes(0,0,len(inc_matrix),len(inc_headers)).values = inc_matrix

rel_headers = list(related[0].keys())
rel_matrix = [rel_headers] + [[row.get(h, "") for h in rel_headers] for row in related]
ws_rel.get_range_by_indexes(0,0,len(rel_matrix),len(rel_headers)).values = rel_matrix

ws_terms.get_range_by_indexes(0,0,len(terms),len(terms[0])).values = terms

# Styling
header_fmt = {
    "fill": "#1F4E78",
    "font": {"bold": True, "color": "#FFFFFF"},
    "horizontal_alignment": "center",
    "vertical_alignment": "center",
}
subheader_fmt = {
    "fill": "#D9EAF7",
    "font": {"bold": True},
}
for ws in [ws_sum, ws_inc, ws_rel, ws_terms]:
    # freeze headers where appropriate
    try:
        ws.freeze_panes.freeze_rows(1)
    except Exception as e:
        pass

ws_sum.get_range("A1:B1").format = {"fill": "#1F4E78", "font": {"bold": True, "color": "#FFFFFF", "size": 14}}
ws_sum.merge_cells("A1:B1")
ws_sum.get_range("A3:B3").format = header_fmt
ws_sum.get_range("A12:B12").format = {"fill": "#1F4E78", "font": {"bold": True, "color": "#FFFFFF"}}
ws_sum.merge_cells("A12:B12")

# Format included headers
ws_inc.get_range_by_indexes(0,0,1,len(inc_headers)).format = header_fmt
ws_rel.get_range_by_indexes(0,0,1,len(rel_headers)).format = header_fmt
ws_terms.get_range_by_indexes(0,0,1,len(terms[0])).format = header_fmt

# Add tables (if supported)
try:
    ws_inc.tables.add(ws_inc.get_range_by_indexes(0,0,len(inc_matrix),len(inc_headers)), True, "IncludedDirectReviews")
except Exception as e:
    print("table inc failed", e)
try:
    ws_rel.tables.add(ws_rel.get_range_by_indexes(0,0,len(rel_matrix),len(rel_headers)), True, "RelatedNotDirect")
except Exception as e:
    print("table rel failed", e)
try:
    ws_terms.tables.add(ws_terms.get_range_by_indexes(0,0,len(terms),len(terms[0])), True, "ScreeningTerms")
except Exception as e:
    print("table terms failed", e)

# Set column widths and wrap
# Summary
ws_sum.get_range("A:A").format.column_width = 28
ws_sum.get_range("B:B").format.column_width = 100
ws_sum.get_range("A1:B16").format.wrap_text = True
ws_sum.get_range("A1:B16").format.vertical_alignment = "top"

# Included widths
widths = {
    "A": 10, "B": 18, "C": 28, "D": 44, "E": 24, "F": 36, "G": 32, "H": 28,
    "I": 34, "J": 34, "K": 30, "L": 54, "M": 54, "N": 44, "O": 54, "P": 42,
    "Q": 42, "R": 24, "S": 16, "T": 18, "U": 34, "V": 28
}
for col, w in widths.items():
    try:
        ws_inc.get_range(f"{col}:{col}").format.column_width = w
    except Exception as e:
        pass
ws_inc.get_range_by_indexes(0,0,len(inc_matrix),len(inc_headers)).format.wrap_text = True
ws_inc.get_range_by_indexes(0,0,len(inc_matrix),len(inc_headers)).format.vertical_alignment = "top"

# Related widths
rel_widths = {"A":10, "B":18, "C":48, "D":80, "E":24, "F":16, "G":34}
for col, w in rel_widths.items():
    ws_rel.get_range(f"{col}:{col}").format.column_width = w
ws_rel.get_range_by_indexes(0,0,len(rel_matrix),len(rel_headers)).format.wrap_text = True
ws_rel.get_range_by_indexes(0,0,len(rel_matrix),len(rel_headers)).format.vertical_alignment = "top"

# Terms widths
for col,w in {"A":28,"B":96,"C":60}.items():
    ws_terms.get_range(f"{col}:{col}").format.column_width = w
ws_terms.get_range_by_indexes(0,0,len(terms),3).format.wrap_text = True
ws_terms.get_range_by_indexes(0,0,len(terms),3).format.vertical_alignment = "top"

# Row heights
for ws, rows in [(ws_sum, 16), (ws_inc, len(inc_matrix)), (ws_rel, len(rel_matrix)), (ws_terms, len(terms))]:
    try:
        ws.get_range_by_indexes(0,0,rows,1).format.row_height = 46
    except Exception:
        pass
try:
    ws_sum.get_range("A1:B1").format.row_height = 30
except Exception:
    pass

# Data validation on Direct comparison column
try:
    col_idx = inc_headers.index("Direct comparison?")
    col_letter = chr(ord('A')+col_idx)
    ws_inc.get_range(f"{col_letter}2:{col_letter}{len(inc_matrix)}").data_validation = {
        "rule": {"type": "list", "values": ["Yes", "Yes for NEC; sepsis not extractable", "Partial/indirect"]}
    }
except Exception as e:
    print("validation failed", e)

# Conditional formatting: highlight sepsis not reported
try:
    sepsis_idx = inc_headers.index("Sepsis result")
    col_letter = chr(ord('A')+sepsis_idx)
    ws_inc.get_range(f"{col_letter}2:{col_letter}{len(inc_matrix)}").conditional_formats.add_custom(
        f'=ISNUMBER(SEARCH("Not reported",{col_letter}2))',
        {"fill": "#FFF2CC"}
    )
    ws_inc.get_range(f"{col_letter}2:{col_letter}{len(inc_matrix)}").conditional_formats.add_custom(
        f'=ISNUMBER(SEARCH("not extractable",{col_letter}2))',
        {"fill": "#FFF2CC"}
    )
except Exception as e:
    print("conditional failed", e)

# Inspect and export
print("Workbook created", len(included), len(related))

# Compact verification
check = wb.inspect({
    "kind": "table",
    "range": "Included_Direct_Reviews!A1:V8",
    "include": "values,formulas",
    "table_max_rows": 10,
    "table_max_cols": 8
})
print(check.ndjson[:2000])
errors = wb.inspect({
    "kind": "match",
    "search_term": "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    "options": {"use_regex": True, "max_results": 300},
    "summary": "final formula error scan"
})
print(errors.ndjson[:1000])
out="/mnt/data/hmf_vs_bovine_fortifier_meta_reviews.xlsx"
SpreadsheetFile.export_xlsx(wb).save(out)
print(out, os.path.getsize(out))
