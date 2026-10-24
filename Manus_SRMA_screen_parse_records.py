import re
from pathlib import Path
src=Path('/home/ubuntu/upload/130.Meta&SystematicR.abstract.txt')
text=src.read_text(errors='replace')
# Identify record headers: line begins 1-130 period followed by journal citation text.
pattern=re.compile(r'(?m)^([1-9][0-9]?|1[0-2][0-9]|130)\.\s+(?=[A-Z][A-Za-z0-9 &.()/-]+\.)')
matches=list(pattern.finditer(text))
records=[]
for idx,m in enumerate(matches):
    num=int(m.group(1))
    start=m.start()
    end=matches[idx+1].start() if idx+1<len(matches) else len(text)
    records.append((num,text[start:end].strip()))
print('matches',len(matches),'records',len(records),'first-last',records[0][0],records[-1][0])
nums=[n for n,_ in records]
print('missing', [i for i in range(1,131) if i not in nums])
print('dups', sorted({n for n in nums if nums.count(n)>1}))
# save all records to individual files for inspection
outdir=Path('/home/ubuntu/pubmed_records')
outdir.mkdir(exist_ok=True)
for n,b in records:
    (outdir/f'record_{n:03d}.txt').write_text(b)

# screen again
human_terms=[r'human milk-based',r'human milk based',r'human milk-derived',r'human milk derived',r'human-derived',r'human derived',r'donor milk-derived',r'donor-derived',r'exclusive human milk',r'human milk fortifier',r'human milk fortification',r'hm-based',r'hm-derived',r'100% human milk',r'all-human milk']
bovine_terms=[r'bovine',r'cow',r"cow's",r'cows',r'preterm formula',r'bovine milk-based',r'bovine milk based',r'bovine-derived',r'bovine derived',r'cow milk-based',r'cow milk based',r'bovine fortifier',r'bovine-based',r'cow-based',r'cows\’ milk',r'cow’s milk']
outcome_terms=[r'necrotizing enterocolitis',r'necrotising enterocolitis',r'\bnec\b',r'sepsis',r'late-onset sepsis',r'bloodstream infection',r'infection']
review_terms=[r'systematic review',r'meta-analysis',r'meta analysis',r'network meta-analysis',r'network meta analysis']
rows=[]
for n,b in records:
    low=b.lower()
    hm=[t for t in human_terms if re.search(re.escape(t).replace('\\\\b','\\b'), low)]
    bov=[t for t in bovine_terms if t in low]
    out=[t for t in outcome_terms if re.search(re.escape(t).replace('\\\\b','\\b'), low)]
    rev=[t for t in review_terms if t in low]
    score=2*bool(hm)+2*bool(bov)+2*bool(out)+bool(rev)
    title=''
    lines=[x.strip() for x in b.splitlines()]
    nonempty=[x for x in lines if x]
    title_lines=[]
    for ln in nonempty[1:8]:
        if re.search(r'\([0-9]+\)|Author information:', ln): break
        title_lines.append(ln)
    title=' '.join(title_lines)
    pmid=re.search(r'PMID:\s*(\d+)', b)
    doi=re.search(r'DOI:\s*([^\n]+)', b)
    if score>=5 or ('human milk-derived fortifiers compared' in low) or ('human milk-based fortifier' in low and 'bovine' in low):
        rows.append((n,score,pmid.group(1) if pmid else '',doi.group(1).strip() if doi else '',title,'; '.join(hm),'; '.join(bov),'; '.join(out)))
Path('/home/ubuntu/strict_flagged_records.tsv').write_text('\n'.join(['num\tscore\tpmid\tdoi\ttitle\thm_terms\tbovine_terms\toutcome_terms']+[f'{r[0]}\t{r[1]}\t{r[2]}\t{r[3]}\t{r[4]}\t{r[5]}\t{r[6]}\t{r[7]}' for r in rows]))
print('flagged',len(rows))
for r in rows:
    print('\t'.join(map(str,r[:5])))
