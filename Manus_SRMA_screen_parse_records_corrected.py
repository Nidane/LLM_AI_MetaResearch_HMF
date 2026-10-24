import re
from pathlib import Path
src=Path('/home/ubuntu/upload/130.Meta&SystematicR.abstract.txt')
text=src.read_text(errors='replace')
starts={}
for n in range(1,131):
    matches=list(re.finditer(rf'(?m)^{n}\.\s+\S', text))
    if matches:
        # choose first plausible occurrence after previous start; if multiple, prefer line that is near chronological numbering
        starts[n]=matches[0].start()
missing=[n for n in range(1,131) if n not in starts]
# Detect non-monotonic starts and try alternatives for affected numbers.
for n in range(2,131):
    if n in starts and n-1 in starts and starts[n] < starts[n-1]:
        alts=list(re.finditer(rf'(?m)^{n}\.\s+\S', text))
        for m in alts:
            if m.start() > starts[n-1]:
                starts[n]=m.start(); break
# Also ensure monotonic by selecting first occurrence after previous finalized start.
prev=-1
for n in range(1,131):
    alts=list(re.finditer(rf'(?m)^{n}\.\s+\S', text))
    chosen=None
    for m in alts:
        if m.start()>prev:
            chosen=m.start(); break
    if chosen is not None:
        starts[n]=chosen; prev=chosen
    else:
        starts.pop(n,None)
missing=[n for n in range(1,131) if n not in starts]
print('found starts',len(starts),'missing',missing)
print('monotonic', all(starts[i] < starts[i+1] for i in range(1,130) if i in starts and i+1 in starts))
records=[]
for n in range(1,131):
    if n not in starts: continue
    start=starts[n]
    end=starts[n+1] if n<130 and n+1 in starts else len(text)
    records.append((n,text[start:end].strip()))
print('records',len(records),'first-last',records[0][0],records[-1][0])
outdir=Path('/home/ubuntu/pubmed_records_clean')
outdir.mkdir(exist_ok=True)
for n,b in records:
    (outdir/f'record_{n:03d}.txt').write_text(b)
# Flag candidates
human_terms=['human milk-based','human milk based','human milk-derived','human milk derived','human-derived','human derived','donor milk-derived','donor-derived','exclusive human milk','human milk fortifier','human milk fortification','human milk-based fortifier','hm-based','hm-derived','100% human milk','all-human milk']
bovine_terms=['bovine','cow',"cow's",'cows','cow’s','preterm formula','bovine milk-based','bovine milk based','bovine-derived','bovine derived','cow milk-based','cow milk based','bovine fortifier','bovine-based','cow-based','cows’ milk','cows milk']
outcome_terms=['necrotizing enterocolitis','necrotising enterocolitis','nec','sepsis','late-onset sepsis','bloodstream infection','infection']
review_terms=['systematic review','meta-analysis','meta analysis','network meta-analysis','network meta analysis']
rows=[]
for n,b in records:
    low=b.lower()
    def has(t):
        return bool(re.search(r'\bnec\b', low)) if t=='nec' else t in low
    hm=[t for t in human_terms if has(t)]
    bov=[t for t in bovine_terms if has(t)]
    out=[t for t in outcome_terms if has(t)]
    rev=[t for t in review_terms if has(t)]
    score=2*bool(hm)+2*bool(bov)+2*bool(out)+bool(rev)
    lines=[x.strip() for x in b.splitlines() if x.strip()]
    title_lines=[]
    for ln in lines[1:10]:
        if re.search(r'\([0-9]+\)|Author information:|Rockville \(MD\)|Bethesda \(MD\)|Copyright|BACKGROUND:', ln): break
        title_lines.append(ln)
    pmid=re.search(r'PMID:\s*(\d+)', b)
    doi=re.search(r'DOI:\s*([^\n]+)', b)
    if score>=5 or ('human milk-derived fortifiers compared' in low) or ('human milk-derived fortifier versus bovine' in low) or ('human milk-based fortifier' in low and 'bovine' in low):
        rows.append([n,score,pmid.group(1) if pmid else '',doi.group(1).strip() if doi else '',' '.join(title_lines),'; '.join(hm),'; '.join(bov),'; '.join(out)])
Path('/home/ubuntu/clean_flagged_records.tsv').write_text('\n'.join(['num\tscore\tpmid\tdoi\ttitle\thuman_terms\tbovine_terms\toutcome_terms']+['\t'.join(map(str,r)) for r in rows]))
print('flagged',len(rows))
for r in rows:
    print('\t'.join(map(str,r[:5])))
