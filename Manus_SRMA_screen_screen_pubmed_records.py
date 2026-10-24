import re
from pathlib import Path

src = Path('/home/ubuntu/upload/130.Meta&SystematicR.abstract.txt')
text = src.read_text(errors='replace')
# Split records on lines beginning with record number followed by period and journal citation.
parts = re.split(r'(?m)^\s*(\d+)\.\s+', text)
records = []
for i in range(1, len(parts), 2):
    num = int(parts[i])
    body = parts[i+1].strip()
    records.append((num, body))

human_terms = [
    'human milk-based', 'human milk based', 'human milk-derived', 'human milk derived',
    'human-derived', 'human derived', 'donor milk-derived', 'donor-derived',
    'exclusive human milk', 'human milk fortifier', 'human milk fortification',
    'human milk-based fortifier', 'hm-based', 'hm-derived', 'human milk-based human milk fortifier'
]
bovine_terms = [
    'bovine', 'cow', "cow's", 'cows', 'preterm formula', 'bovine milk-based', 'bovine milk based',
    'bovine-derived', 'bovine derived', 'cow milk-based', 'cow milk based', 'bovine fortifier',
    'bovine-based', 'cow-based', 'milk-derived fortifier'
]
outcome_terms = ['necrotizing enterocolitis', 'necrotising enterocolitis', 'nec ', 'nec,', 'nec.', 'sepsis', 'late-onset sepsis', 'infection']
review_terms = ['systematic review', 'meta-analysis', 'meta analysis', 'network meta-analysis', 'network meta analysis']
compare_terms = ['versus', 'vs', 'compared', 'comparison', 'compare', 'effect of different', 'exclusive human milk diet']

hits = []
for num, body in records:
    low = body.lower()
    score = 0
    hm = [t for t in human_terms if t in low]
    bov = [t for t in bovine_terms if t in low]
    out = [t for t in outcome_terms if t in low]
    rev = [t for t in review_terms if t in low]
    comp = [t for t in compare_terms if t in low]
    if hm: score += 2
    if bov: score += 2
    if out: score += 2
    if rev: score += 1
    if comp: score += 1
    title = ''
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    # Capture title as non-author lines after citation, before blank/authors. Simpler: first few lines until author line contains (1)
    if lines:
        title_lines = []
        for ln in lines[1:8]:
            if re.search(r'\(1\)|Author information|BACKGROUND:', ln):
                break
            title_lines.append(ln)
        title = ' '.join(title_lines)
    if score >= 3 or any(x in low for x in ['human milk-based fortifier', 'human milk derived fortifier', 'exclusive human milk diet', 'bovine milk-based fortifier']):
        pmid = re.search(r'PMID:\s*(\d+)', body)
        doi = re.search(r'DOI:\s*([^\n]+)', body)
        hits.append({
            'num': num,
            'score': score,
            'title': title,
            'pmid': pmid.group(1) if pmid else '',
            'doi': doi.group(1).strip() if doi else '',
            'hm_terms': '; '.join(hm),
            'bovine_terms': '; '.join(bov),
            'outcome_terms': '; '.join(out),
            'snippet': body[:1000].replace('\n',' ')
        })

print(f'Total records parsed: {len(records)}')
print(f'Flagged records: {len(hits)}')
for h in hits:
    print('\n---')
    print(f"#{h['num']} score={h['score']} PMID={h['pmid']} DOI={h['doi']}")
    print(h['title'])
    print('HM:', h['hm_terms'])
    print('Bovine:', h['bovine_terms'])
    print('Outcome:', h['outcome_terms'])
    print(h['snippet'][:700])

# Write simple TSV for inspection
out = Path('/home/ubuntu/flagged_records.tsv')
out.write_text('\n'.join(['num\tscore\tpmid\tdoi\ttitle\thm_terms\tbovine_terms\toutcome_terms'] + [
    f"{h['num']}\t{h['score']}\t{h['pmid']}\t{h['doi']}\t{h['title']}\t{h['hm_terms']}\t{h['bovine_terms']}\t{h['outcome_terms']}" for h in hits
]))
print(f'Wrote {out}')
