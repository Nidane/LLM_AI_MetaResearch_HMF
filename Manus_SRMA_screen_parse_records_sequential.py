import re
from pathlib import Path
src=Path('/home/ubuntu/upload/130.Meta&SystematicR.abstract.txt')
text=src.read_text(errors='replace')
starts={}
for n in range(1,131):
    m=re.search(rf'(?m)^{n}\.\s+', text)
    if m:
        starts[n]=m.start()
missing=[n for n in range(1,131) if n not in starts]
print('found starts',len(starts),'missing',missing)
records=[]
for n in range(1,131):
    if n not in starts:
        continue
    start=starts[n]
    next_starts=[starts[k] for k in range(n+1,131) if k in starts and starts[k]>start]
    end=min(next_starts) if next_starts else len(text)
    records.append((n,text[start:end].strip()))
print('records',len(records), 'first-last', records[0][0], records[-1][0])
outdir=Path('/home/ubuntu/pubmed_records_seq')
outdir.mkdir(exist_ok=True)
for n,b in records:
    (outdir/f'record_{n:03d}.txt').write_text(b)
# screening
terms={
'human':['human milk-based','human milk based','human milk-derived','human milk derived','human-derived','human derived','donor milk-derived','donor-derived','exclusive human milk','human milk fortifier','human milk fortification','human milk-based fortifier','hm-based','hm-derived','100% human milk','all-human milk'],
'bovine':['bovine','cow','cow\'s','cows','cow’s','preterm formula','bovine milk-based','bovine milk based','bovine-derived','bovine derived','cow milk-based','cow milk based','bovine fortifier','bovine-based','cow-based','cows’ milk','cows milk'],
'outcome':['necrotizing enterocolitis','necrotising enterocolitis','nec','sepsis','late-onset sepsis','bloodstream infection','infection'],
'review':['systematic review','meta-analysis','meta analysis','network meta-analysis','network meta analysis']
}
rows=[]
for n,b in records:
    low=b.lower()
    matches={cat:[] for cat in terms}
    for cat,ts in terms.items():
        for t in ts:
            if t=='nec':
                if re.search(r'\bnec\b', low): matches[cat].append(t)
            elif t in low:
                matches[cat].append(t)
    score=2*bool(matches['human'])+2*bool(matches['bovine'])+2*bool(matches['outcome'])+bool(matches['review'])
    lines=[x.strip() for x in b.splitlines() if x.strip()]
    title_lines=[]
    for ln in lines[1:10]:
        if re.search(r'\([0-9]+\)|Author information:|Rockville \(MD\)|Bethesda \(MD\)|Copyright|BACKGROUND:', ln): break
        title_lines.append(ln)
    pmid=re.search(r'PMID:\s*(\d+)', b)
    doi=re.search(r'DOI:\s*([^\n]+)', b)
    if score>=5 or ('human milk-derived fortifiers compared' in low) or ('human milk-derived fortifier versus bovine' in low) or ('human milk-based fortifier' in low and 'bovine' in low):
        rows.append([n,score,pmid.group(1) if pmid else '',doi.group(1).strip() if doi else '',' '.join(title_lines),'; '.join(matches['human']),'; '.join(matches['bovine']),'; '.join(matches['outcome'])])
Path('/home/ubuntu/seq_flagged_records.tsv').write_text('\n'.join(['num\tscore\tpmid\tdoi\ttitle\thuman_terms\tbovine_terms\toutcome_terms']+['\t'.join(map(str,r)) for r in rows]))
print('flagged',len(rows))
for r in rows:
    print('\t'.join(map(str,r[:5])))
