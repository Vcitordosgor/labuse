import csv
from collections import defaultdict
def load(p):
    d={}
    with open(p) as f:
        for r in csv.DictReader(f): d[r['idu']]=r
    return d
cur=load('/tmp/fix5_courant.csv'); base=load('/tmp/fix5_base.csv')
def num(x):
    try: return float(x)
    except: return None
byzone=defaultdict(lambda:{'n':0,'chg':0,'gaps':[],'u4_new':0,'page_new':0,'decl':0})
for idu,c in cur.items():
    b=base.get(idu)
    if not b: continue
    z=f"{c['commune']}/{c['zone']}"; s=byzone[z]; s['n']+=1
    if c['declenchee']=='1': s['decl']+=1
    cf_c,cf_b=num(c['cf_central']),num(b['cf_central'])
    if cf_c is not None and cf_b is not None and abs(cf_c-cf_b)>0.5:
        s['chg']+=1; s['gaps'].append(abs(cf_c-cf_b))
    if c.get('u4_avert')=='1' and b.get('u4_avert')!='1': s['u4_new']+=1
    if (c['page'] or '')!=(b['page'] or ''): s['page_new']+=1
print("=== MONTANT (charge foncière) qui change — PAR ZONE ===")
print(f"{'zone':18} {'n':>5} {'déclch':>6} {'€ chg':>6} {'médian€':>9} {'max€':>9} {'avert U4 nouv':>13} {'page chg':>9}")
for z in sorted(byzone):
    s=byzone[z]; md=sorted(s['gaps'])[len(s['gaps'])//2] if s['gaps'] else 0; mx=max(s['gaps']) if s['gaps'] else 0
    print(f"{z:18} {s['n']:>5} {s['decl']:>6} {s['chg']:>6} {md:>9.0f} {mx:>9.0f} {s['u4_new']:>13} {s['page_new']:>9}")
