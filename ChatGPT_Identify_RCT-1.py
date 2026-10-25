from artifact_tool import Workbook, SpreadsheetFile
print("ok")

from artifact_tool import Workbook, SpreadsheetFile
from datetime import datetime

# Define data
today = datetime(2026,5,7)

summary_rows = [
    ["Item", "Value / note"],
    ["Uploaded PubMed export", "HMF.3371.txt (3371 PubMed-style records)"],
    ["User question", "RCTs directly comparing human milk-based / human-derived fortifier vs bovine/cow milk-based fortifier for NEC (any stage) and sepsis"],
    ["Screening approach", "Title/abstract/DOI/PMID text search plus manual screening for synonyms of human-based and bovine-based fortification, randomisation, NEC, and sepsis"],
    ["Important distinction", "Some RCTs compare fortifier source while keeping the base diet human milk in both arms; others compare an exclusive human milk diet bundle that also changes donor milk/formula exposure."],
    ["Primary direct fortifier RCTs found", 4],
    ["Broader EHMD/diet-bundle RCTs found", 4],
    ["Special-population RCT found", 1],
    ["Key caution", "Several abstracts do not report extractable NEC/sepsis event counts; full-text extraction is required before final meta-analysis pooling."],
]

synonym_rows = [
    ["Concept", "Synonyms / screening terms used"],
    ["Human-based fortifier", "human milk-based fortifier; human milk based fortifier; human milk-derived fortifier; human-derived fortifier; donor milk-derived fortifier; donor-derived fortifier; human breast milk-based fortifier; human milk-based human milk fortifier; HMBF; HMF-HM; HM-HMF; PHMF; Prolacta; Prolacta Humavant; HUM"],
    ["Bovine/cow-based fortifier", "bovine milk-based fortifier; bovine-based fortifier; bovine milk-derived fortifier; cow milk-based fortifier; cow's milk-based fortifier; cow milk protein; bovine protein; BMBF; BMF; PBMF; CMBF; CMDF; BOV"],
    ["Diet-bundle comparators", "exclusive human milk diet; EHMD; human milk diet; donor human milk + human milk-derived fortifier; preterm formula; bovine formula; standard diet with cow milk-based fortifier/formula"],
    ["RCT terms", "randomized; randomised; randomly assigned; randomised controlled trial; randomized controlled trial; randomized clinical trial; controlled trial; phase III trial"],
    ["NEC terms", "necrotizing enterocolitis; necrotising enterocolitis; NEC; Bell stage; surgical NEC; medical NEC"],
    ["Sepsis terms", "sepsis; late-onset sepsis; culture-proven sepsis; proven infection; infection; mortality/morbidity composite"],
]

included_headers = [
    "Role for review", "Entry #", "PMID", "Year", "First author", "Title", "Journal",
    "Study design", "Population", "Human-based intervention", "Bovine/control comparator",
    "Comparison directness", "Sample size from abstract", "NEC outcome text in abstract",
    "Sepsis outcome text in abstract", "Trial registration", "Primary meta-analysis eligibility",
    "Notes / extraction caveats", "DOI", "PubMed URL", "Uploaded source"
]

included_rows = [
    [
        "Primary direct fortifier RCT",
        238, "39660504", 2025, "Berrington",
        "Powdered human milk-derived versus bovine milk-derived breastmilk fortification: A multi-centre preterm randomised controlled trial",
        "J Pediatr Gastroenterol Nutr",
        "Multicentre preterm randomised controlled trial",
        "Infants <32 weeks gestation or <1500 g, only received human milk and reached full enteral feeds; no pre-existing GI morbidity",
        "Powdered human milk-based fortifier (PHMF) on otherwise exclusive human milk diet",
        "Powdered bovine milk-based fortifier (PBMF) on otherwise exclusive human milk diet",
        "Clean fortifier-source comparison; base diet otherwise human milk in both arms",
        "31 enrolled; 28 informative (14 PHMF, 14 PBMF)",
        "Rates of key neonatal morbidities did not differ; abstract does not provide NEC counts",
        "Rates of key neonatal morbidities did not differ; abstract does not provide sepsis counts",
        "",
        "Yes, but full text needed for NEC/sepsis event counts",
        "Trial stopped early after manufacturer withdrawal of PHMF; small sample and low event power.",
        "10.1002/jpn3.12431",
        "https://pubmed.ncbi.nlm.nih.gov/39660504/",
        "HMF.3371.txt"
    ],
    [
        "Primary direct fortifier RCT",
        340, "38545091", 2024, "Jensen",
        "Effect of human milk-based fortification in extremely preterm infants fed exclusively with breast milk: a randomised controlled trial",
        "EClinicalMedicine",
        "Multicentre randomised controlled trial at 24 neonatal units in Sweden",
        "Extremely preterm infants born 22+0 to 27+6 weeks, exclusively fed human breast milk (mother's own and/or donor milk)",
        "Targeted fortification with human milk-based fortifier (HMBF)",
        "Targeted fortification with bovine milk-based fortifier (BMBF)",
        "Clean fortifier-source comparison; base diet human milk in both arms",
        "229 randomized; ITT 228 (115 HMBF, 113 BMBF after withdrawal)",
        "Primary composite included NEC stage II-III; 41/115 HMBF vs 39/113 BMBF for NEC/sepsis/death composite; individual NEC count not in PubMed abstract",
        "Primary composite included culture-proven sepsis; individual sepsis count not in PubMed abstract",
        "NCT03797157",
        "Yes",
        "Best direct match for the requested comparison and outcomes, but abstract reports composite, not separate NEC/sepsis counts.",
        "10.1016/j.eclinm.2023.102375",
        "https://pubmed.ncbi.nlm.nih.gov/38545091/",
        "HMF.3371.txt"
    ],
    [
        "Primary direct fortifier RCT",
        1159, "29878061", 2018, "O'Connor",
        "Nutrient enrichment of human milk with human and bovine milk-based fortifiers for infants born weighing <1250 g: a randomized clinical trial",
        "Am J Clin Nutr",
        "Blinded randomized clinical trial",
        "Infants born weighing <1250 g in Ontario neonatal units; fed mother's milk and donor milk as required",
        "Human milk-based fortifier (HMBF), fortification from 100 mL/kg/day and advanced at 140 mL/kg/day",
        "Bovine milk-based fortifier (BMBF), same fortification timing framework",
        "Clean fortifier-source comparison; no formula feeding in the comparison framework",
        "127 randomized (64 HMBF, 63 BMBF)",
        "Composite mortality/morbidity index included NEC; no separate NEC count in PubMed abstract",
        "Composite mortality/morbidity index included late-onset sepsis; no separate sepsis count in PubMed abstract",
        "NCT02137473",
        "Yes",
        "Primary outcome was feeding interruption; NEC/sepsis are embedded in a composite morbidity/mortality index.",
        "10.1093/ajcn/nqy067",
        "https://pubmed.ncbi.nlm.nih.gov/29878061/",
        "HMF.3371.txt"
    ],
    [
        "Primary/sensitivity RCT; direct comparison embedded in EHMD bundle",
        2082, "20036378", 2010, "Sullivan",
        "An exclusively human milk-based diet is associated with a lower rate of necrotizing enterocolitis than a diet of human milk and bovine milk-based products",
        "J Pediatr",
        "Randomized trial with three feeding groups",
        "Extremely premature infants fed their own mother's milk",
        "HM100 and HM40: pasteurized donor human milk-based human milk fortifier, plus pasteurized donor human milk if no mother's milk was available",
        "BOV: bovine milk-based human milk fortifier, plus preterm formula if no mother's milk was available",
        "Fortifier comparison is present, but rescue diet differs (donor human milk vs preterm formula), so treat as EHMD-bundle/confounded",
        "Total n=207 across 3 groups",
        "NEC and surgical NEC significantly lower in exclusive human milk diet groups (P=.02 and P=.007); no event counts in PubMed abstract",
        "Late-onset sepsis rates were similar; no counts in PubMed abstract",
        "NCT00506584",
        "Yes for many HMBF-vs-BMBF reviews; recommend sensitivity analysis",
        "Because non-mother's milk supplementation differed by arm, this is not a pure fortifier-only comparison.",
        "10.1016/j.jpeds.2009.10.040",
        "https://pubmed.ncbi.nlm.nih.gov/20036378/",
        "HMF.3371.txt"
    ],
    [
        "Sensitivity / EHMD bundle RCT",
        1722, "23968744", 2013, "Cristofalo",
        "Randomized trial of exclusive human milk versus preterm formula diets in extremely premature infants",
        "J Pediatr",
        "Multicenter randomized controlled trial",
        "Extremely preterm infants whose mothers did not provide their milk",
        "Pasteurized donor human milk plus human milk-based human milk fortifier (HUM)",
        "Bovine milk-based preterm formula (BOV)",
        "Not a fortifier-only comparison; direct diet-source comparison with HMBF only in human milk arm",
        "Denominators not stated in PubMed abstract; NEC percentages imply about 29 HUM and 24 BOV",
        "NEC 3% (1 case) in HUM vs 21% (5 cases) in BOV, P=.08; surgical NEC 0 HUM vs 4 BOV, P=.04",
        "Sepsis not stated in PubMed abstract",
        "",
        "No for strict HMBF-vs-BMBF; consider EHMD sensitivity/narrative",
        "Comparator is preterm formula rather than bovine milk-based fortifier.",
        "10.1016/j.jpeds.2013.07.011",
        "https://pubmed.ncbi.nlm.nih.gov/23968744/",
        "HMF.3371.txt"
    ],
    [
        "Sensitivity / EHMD bundle RCT",
        454, "36857051", 2023, "Embleton",
        "Effect of an Exclusive Human Milk Diet on the Gut Microbiome in Preterm Infants: A Randomized Clinical Trial",
        "JAMA Netw Open",
        "Randomized clinical trial",
        "Preterm infants <30 weeks gestation at 4 UK NICUs; had only received own mother's milk before 72 h of age",
        "Exclusive human milk diet using pasteurized human milk for shortfall and human milk-derived fortifiers",
        "Bovine formula and bovine-derived fortifier",
        "EHMD bundle; fortifier and formula/donor milk exposure both differ",
        "126 randomized (63 intervention, 63 control)",
        "No differences in time to full feeds, NEC, or other key neonatal morbidities; abstract does not provide NEC counts",
        "Sepsis not separately stated in PubMed abstract",
        "ISRCTN16799022",
        "No for strict fortifier-only; consider EHMD sensitivity/narrative",
        "Primary outcome was microbiome, not clinical NEC/sepsis.",
        "10.1001/jamanetworkopen.2023.1165",
        "https://pubmed.ncbi.nlm.nih.gov/36857051/",
        "HMF.3371.txt"
    ],
    [
        "Sensitivity / EHMD bundle RCT",
        530, "35809401", 2022, "Uthaya",
        "Randomised controlled trial of human derived breast milk fortifier versus bovine milk fortifier on body composition in very preterm babies",
        "Early Hum Dev",
        "Randomised multicentre open-label controlled trial",
        "Infants born below 30 weeks gestation, preferentially receiving own mother's milk",
        "Exclusive human milk diet: human milk formula for shortfall plus human milk-derived fortifier",
        "Cow milk-based supplementation: preterm formula for shortfall plus cow milk-based fortifier",
        "EHMD bundle; fortifier and shortfall feeding source both differ",
        "38 randomized (19 intervention, 19 control); primary outcome analysed in 27",
        "NEC not reported in PubMed abstract",
        "Sepsis not reported in PubMed abstract",
        "",
        "No for strict fortifier-only; consider EHMD sensitivity/narrative if full text reports events",
        "Primary outcome was body composition; clinical event extraction requires full text.",
        "10.1016/j.earlhumdev.2022.105619",
        "https://pubmed.ncbi.nlm.nih.gov/35809401/",
        "HMF.3371.txt"
    ],
    [
        "Sensitivity / EHMD bundle RCT",
        6, "42045666", 2026, "Mizuno",
        "Growth and safety evaluation in very low birth weight infants receiving an exclusive human milk diet: a phase III randomized control trial in Japan",
        "J Perinatol",
        "Prospective controlled open phase III randomized trial",
        "Very low birth weight infants (<1500 g)",
        "EHMD: mother's own milk/donor milk with human milk-based fortifiers",
        "Standard diet: mother's own milk/donor milk with cow milk-based fortifier/formula",
        "EHMD bundle; fortifier/source differences and formula exposure may differ",
        "147 received intervention or control (77 EHMD, 70 Standard Diet)",
        "NEC not separately reported in PubMed abstract; adverse events 32.5% vs 21.4%, P=.13",
        "Sepsis not separately reported in PubMed abstract",
        "jRCT2031210384",
        "No for strict fortifier-only; consider EHMD sensitivity/narrative if full text reports NEC/sepsis",
        "Newest RCT in export; abstract focuses on growth/time to full feeds/safety rather than specific NEC or sepsis counts.",
        "10.1038/s41372-026-02695-w",
        "https://pubmed.ncbi.nlm.nih.gov/42045666/",
        "HMF.3371.txt"
    ],
    [
        "Special population RCT; likely outside preterm HMF meta-analysis",
        480, "36528055", 2023, "Blanco",
        "A Randomized Trial of an Exclusive Human Milk Diet in Neonates with Single Ventricle Physiology",
        "J Pediatr",
        "Multicenter randomized single-blinded controlled trial",
        "Term neonates ≤7 days old with single ventricle physiology and anticipated cardiac surgical palliation",
        "Post-operative exclusive human milk diet; human milk fortified with human milk-based fortifier designed for term neonates once intake reached 60 mL/kg/day",
        "Mixed human/bovine diet; standard fortification with formula once intake reached 100 mL/kg/day",
        "Special population; EHMD vs mixed diet, not preterm VLBW fortifier-only comparison",
        "107 enrolled (55 exclusive human milk, 52 control)",
        "NEC all Bell stages lower in exclusive human milk group: 3.6% vs 15.4%, P=.04",
        "Sepsis not reported in PubMed abstract",
        "NCT02860702",
        "Usually no for the stated preterm HMF question; can discuss separately",
        "Different population and fortifier designed for term neonates; include only if review scope includes cardiac neonates.",
        "10.1016/j.jpeds.2022.11.043",
        "https://pubmed.ncbi.nlm.nih.gov/36528055/",
        "HMF.3371.txt"
    ],
]

outcome_headers = [
    "Study", "Entry #", "Outcome", "Human/HMBF events", "Human/HMBF total",
    "Bovine/control events", "Bovine/control total", "Effect / P value",
    "Outcome extractable from PubMed abstract?", "Directness for target meta-analysis", "Notes"
]
outcome_rows = [
    ["Jensen 2024", 340, "Composite: NEC stage II-III OR culture-proven sepsis OR death", 41, 115, 39, 113, "OR 1.05, 95% CI 0.61-1.81, P=0.86", "Yes", "Primary direct", "Individual NEC and individual sepsis event counts not in PubMed abstract."],
    ["O'Connor 2018", 1159, "Mortality/morbidity composite including death, late-onset sepsis, NEC, chronic lung disease, or severe ROP", "", 64, "", 63, "48.4% HMBF vs 49.2% BMBF; adjusted P=0.76", "Partly (percent only)", "Primary direct", "Full text needed for individual NEC/sepsis counts and event counts."],
    ["Berrington 2025", 238, "Key neonatal morbidities including NEC/sepsis", "", 14, "", 14, "No statistical difference reported", "No counts", "Primary direct", "Trial stopped early; full text needed for individual event counts."],
    ["Sullivan 2010", 2082, "NEC and surgical NEC", "", "", "", "", "NEC P=.02; surgical NEC P=.007 lower with EHMD", "P values only", "Primary/sensitivity", "Total n=207; abstract lacks group-level event counts."],
    ["Sullivan 2010", 2082, "Late-onset sepsis", "", "", "", "", "Rates similar", "No counts", "Primary/sensitivity", "Full text needed for sepsis event counts."],
    ["Cristofalo 2013", 1722, "NEC", 1, 29, 5, 24, "3% HUM vs 21% BOV; P=.08", "Yes (denominators inferred from percentages)", "Sensitivity/EHMD", "Comparator is preterm formula, not BMBF. Denominators inferred from case counts + percentages in abstract."],
    ["Cristofalo 2013", 1722, "Surgical NEC", 0, 29, 4, 24, "P=.04", "Yes (denominators inferred)", "Sensitivity/EHMD", "Comparator is preterm formula, not BMBF."],
    ["Embleton 2023", 454, "NEC and key neonatal morbidities", "", 63, "", 63, "No differences reported", "No counts", "Sensitivity/EHMD", "Primary outcome microbiome; abstract lacks event counts."],
    ["Uthaya 2022", 530, "NEC/sepsis", "", 19, "", 19, "Not reported in abstract", "No", "Sensitivity/EHMD", "Primary outcome body composition; clinical events require full text."],
    ["Mizuno 2026", 6, "Adverse events overall", "", 77, "", 70, "32.5% EHMD vs 21.4% Standard Diet; P=.13", "Percent only", "Sensitivity/EHMD", "NEC/sepsis not separately reported in abstract."],
    ["Blanco 2023", 480, "NEC any Bell stage", 2, 55, 8, 52, "3.6% vs 15.4%; P=.04", "Yes (events inferred from percentages)", "Special population", "Term single-ventricle cardiac neonates; not conventional preterm HMF review population."],
]

excluded_headers = ["Entry #", "PMID", "Year", "First author / article", "Reason excluded from target RCT meta-analysis", "Relevant note", "DOI / PMID URL"]
excluded_rows = [
    [603, "34815288", 2021, "Jensen protocol (N-forte)", "Protocol only; results superseded by Jensen 2024", "Direct HMBF vs BMBF protocol; do not double count.", "https://pubmed.ncbi.nlm.nih.gov/34815288/"],
    [880, "32154499", 2019, "Hopperton/O'Connor follow-up", "Follow-up of OptiMoM RCT; not a separate randomized comparison", "Neurodevelopment follow-up of O'Connor 2018.", "https://pubmed.ncbi.nlm.nih.gov/32154499/"],
    [438, "37085523", 2023, "Yeung cost analysis", "Economic analysis of OptiMoM participants; not a separate RCT", "Useful for cost review, not NEC/sepsis meta-analysis.", "https://pubmed.ncbi.nlm.nih.gov/37085523/"],
    [788, "32943531", 2021, "Grace systematic review/meta-analysis", "Review, not an original RCT", "Useful citation-mining source.", "https://pubmed.ncbi.nlm.nih.gov/32943531/"],
    [870, "32277813", 2020, "Ananthan systematic review/meta-analysis", "Review, not an original RCT", "Useful citation-mining source.", "https://pubmed.ncbi.nlm.nih.gov/32277813/"],
    [927, "31697857", 2019, "Premkumar Cochrane review", "Review, not an original RCT", "Useful methods/eligibility reference.", "https://pubmed.ncbi.nlm.nih.gov/31697857/"],
    [56, "41554861", 2026, "Jiang FortiColos CN", "Comparator is bovine colostrum vs conventional bovine fortifier, not human-based vs bovine-based", "RCT but not the requested human-derived comparator.", "https://pubmed.ncbi.nlm.nih.gov/41554861/"],
    [443, "37004355", 2023, "FortiColos trial", "Bovine colostrum vs conventional bovine milk-derived fortifier", "Not HMBF vs BMBF.", "https://pubmed.ncbi.nlm.nih.gov/37004355/"],
    [819, "32708446", 2020, "Donkey milk-derived HMF vs standard fortifier", "Donkey-derived fortifier, not human-derived fortifier", "Interesting mammalian fortifier comparison but outside human-vs-bovine scope.", "https://pubmed.ncbi.nlm.nih.gov/32708446/"],
    [208, "40037774", 2025, "Picaud novel HMF", "Novel cow milk-based HMF vs control cow milk-based HMF", "Reports NEC percentages but not human-vs-bovine.", "https://pubmed.ncbi.nlm.nih.gov/40037774/"],
    [323, "38724605", 2024, "Wynter immediate bovine HMF", "Timing of bovine fortifier, not source comparison", "NEC/sepsis assessed but not HMBF vs BMBF.", "https://pubmed.ncbi.nlm.nih.gov/38724605/"],
    [406, "37551512", 2023, "Salas early human milk fortification", "Early human-based product vs standard unfortified diet until bovine fortifier ordered; not direct full-period HMBF vs BMBF", "Potential narrative background only.", "https://pubmed.ncbi.nlm.nih.gov/37551512/"],
    [477, "36579930", 2022, "Senthilkumaran cohort", "Retrospective cohort, not RCT", "Direct HMBF vs BMBF but nonrandomized.", "https://pubmed.ncbi.nlm.nih.gov/36579930/"],
    [2992, "1941407", 1991, "Moro human milk protein vs bovine milk protein", "Older protein-source fortification RCT; not multinutrient HMBF/BMBF and no NEC/sepsis in abstract", "May be relevant only for protein-source/growth review.", "https://pubmed.ncbi.nlm.nih.gov/1941407/"],
    [3013, "2085103", 1990, "Hagelberg human vs cow milk protein", "Older protein-source RCT; outcomes amino acids, not NEC/sepsis", "Not suitable for NEC/sepsis meta-analysis from abstract.", "https://pubmed.ncbi.nlm.nih.gov/2085103/"],
    [129, "40901284", 2025, "Ong enhanced vs standard donor human milk fortification", "Dose/strategy comparison, not human-vs-bovine fortifier source", "RCT but wrong comparator.", "https://pubmed.ncbi.nlm.nih.gov/40901284/"],
    [212, "39986385", 2025, "Salas early full enteral nutrition", "Feeding strategy, not fortifier-source comparison", "RCT but wrong intervention.", "https://pubmed.ncbi.nlm.nih.gov/39986385/"],
    [679, "33970187", 2021, "Formula powder vs HMF", "Preterm formula powder vs human milk fortifier strategy, not HMBF vs BMBF", "RCT but wrong comparator.", "https://pubmed.ncbi.nlm.nih.gov/33970187/"],
]

# Helper for column letters
def col_letter(n):
    # 1-indexed
    s = ""
    while n:
        n, r = divmod(n-1, 26)
        s = chr(65+r) + s
    return s

# Build workbook
wb = Workbook.create()

# Remove/ignore default? create sheets
summary = wb.worksheets.add("Summary")
inc = wb.worksheets.add("Included_RCTs")
out = wb.worksheets.add("Outcomes_Abstract")
exc = wb.worksheets.add("Excluded_NearMisses")
syn = wb.worksheets.add("Synonym_Map")

# write data
summary.get_range_by_indexes(0,0,len(summary_rows),len(summary_rows[0])).values = summary_rows
syn.get_range_by_indexes(0,0,len(synonym_rows),len(synonym_rows[0])).values = synonym_rows
inc.get_range_by_indexes(0,0,1,len(included_headers)).values = [included_headers]
inc.get_range_by_indexes(1,0,len(included_rows),len(included_headers)).values = included_rows
out.get_range_by_indexes(0,0,1,len(outcome_headers)).values = [outcome_headers]
out.get_range_by_indexes(1,0,len(outcome_rows),len(outcome_headers)).values = outcome_rows
exc.get_range_by_indexes(0,0,1,len(excluded_headers)).values = [excluded_headers]
exc.get_range_by_indexes(1,0,len(excluded_rows),len(excluded_headers)).values = excluded_rows

# Add tables
try:
    inc.tables.add(inc.get_range_by_indexes(0,0,len(included_rows)+1,len(included_headers)), True, "IncludedRCTs")
    out.tables.add(out.get_range_by_indexes(0,0,len(outcome_rows)+1,len(outcome_headers)), True, "OutcomeAbstracts")
    exc.tables.add(exc.get_range_by_indexes(0,0,len(excluded_rows)+1,len(excluded_headers)), True, "ExcludedNearMisses")
    syn.tables.add(syn.get_range_by_indexes(0,0,len(synonym_rows),len(synonym_rows[0])), True, "SynonymMap")
except Exception as e:
    print("table err", e)

# Formatting
header_fmt = {
    "fill": "#0F766E",
    "font": {"bold": True, "color": "#FFFFFF"},
    "horizontal_alignment": "center",
    "vertical_alignment": "center",
    "wrap_text": True
}
subtle_header_fmt = {
    "fill": "#D1FAE5",
    "font": {"bold": True, "color": "#064E3B"},
    "horizontal_alignment": "left",
    "vertical_alignment": "center",
    "wrap_text": True
}
for sh, rows, cols in [(summary, len(summary_rows), 2), (syn, len(synonym_rows), 2), (inc, len(included_rows)+1, len(included_headers)), (out, len(outcome_rows)+1, len(outcome_headers)), (exc, len(excluded_rows)+1, len(excluded_headers))]:
    sh.get_range_by_indexes(0,0,1,cols).format = header_fmt
    sh.get_range_by_indexes(0,0,rows,cols).format.wrap_text = True
    sh.get_range_by_indexes(0,0,rows,cols).format.vertical_alignment = "top"
    sh.freeze_panes.freeze_rows(1)

# Summary special
summary.get_range("A1:B1").format = header_fmt
summary.get_range("A1:A9").format = subtle_header_fmt
summary.get_range("A1:A9").format.column_width = 34
summary.get_range("B1:B9").format.column_width = 90

# Set column widths
def set_widths(sheet, widths):
    for i,w in enumerate(widths, start=1):
        sheet.get_range(f"{col_letter(i)}:{col_letter(i)}").format.column_width = w

set_widths(syn, [28, 120])
set_widths(inc, [28, 10, 13, 9, 16, 60, 24, 34, 46, 48, 48, 44, 22, 44, 40, 20, 34, 50, 24, 36, 22])
set_widths(out, [20, 10, 42, 15, 15, 16, 16, 28, 24, 28, 48])
set_widths(exc, [10, 13, 9, 34, 50, 46, 42])

# Number formats and highlights
inc.get_range("B:B").format.number_format = "0"
inc.get_range("D:D").format.number_format = "0"
out.get_range("B:B").format.number_format = "0"
exc.get_range("A:A").format.number_format = "0"
exc.get_range("C:C").format.number_format = "0"

# Conditional formatting for eligibility
try:
    inc.get_range(f"Q2:Q{len(included_rows)+1}").conditional_formats.add_custom('=ISNUMBER(SEARCH("Yes",Q2))', {"fill": "#DCFCE7"})
    inc.get_range(f"Q2:Q{len(included_rows)+1}").conditional_formats.add_custom('=ISNUMBER(SEARCH("No",Q2))', {"fill": "#FEE2E2"})
    inc.get_range(f"A2:A{len(included_rows)+1}").conditional_formats.add_custom('=ISNUMBER(SEARCH("Primary direct",A2))', {"fill": "#ECFDF5"})
    inc.get_range(f"A2:A{len(included_rows)+1}").conditional_formats.add_custom('=ISNUMBER(SEARCH("Sensitivity",A2))', {"fill": "#FEF9C3"})
    inc.get_range(f"A2:A{len(included_rows)+1}").conditional_formats.add_custom('=ISNUMBER(SEARCH("Special",A2))', {"fill": "#F3E8FF"})
except Exception as e:
    print("cf err", e)

# Add notes at top of outcome sheet? maybe not.

# Autofit rows maybe can be slow but small
for sh in [summary, syn, inc, out, exc]:
    try:
        sh.get_range_by_indexes(0,0,1,2).format.autofit_rows()
    except Exception as e:
        pass

# Verify key ranges
print("Sheets created")
print(wb.inspect({"kind":"sheet","include":"id,name"}).ndjson[:1000])
print(wb.inspect({"kind":"table","range":"Included_RCTs!A1:E5","include":"values","table_max_rows":5,"table_max_cols":5}).ndjson)

try:
    wb
    print("wb exists", wb)
except NameError as e:
    print("wb missing", e)

# Compact verification and export for the spreadsheet artifact
from artifact_tool import SpreadsheetFile

print("Sheets:")
print(wb.inspect({"kind": "sheet", "include": "id,name"}).ndjson)

print("\nIncluded_RCTs preview:")
print(wb.inspect({
    "kind": "table",
    "range": "Included_RCTs!A1:H10",
    "include": "values,formulas",
    "table_max_rows": 10,
    "table_max_cols": 8
}).ndjson)

print("\nFormula/error scan:")
print(wb.inspect({
    "kind": "match",
    "search_term": "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    "options": {"use_regex": True, "max_results": 300},
    "summary": "final formula error scan"
}).ndjson)

out_path = "/mnt/data/HMF_RCT_fortifier_screening.xlsx"
SpreadsheetFile.export_xlsx(wb).save(out_path)
print(f"\nSaved: {out_path}")

