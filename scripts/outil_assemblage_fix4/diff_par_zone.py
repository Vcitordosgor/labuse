import csv
from collections import defaultdict

def load(p):
    d={}
    with open(p) as f:
        for r in csv.DictReader(f): d[r['idu']]=r
    return d
cur=load('/tmp/fix4_courant.csv'); base=load('/tmp/fix4_base.csv')
def num(x):
    try: return float(x)
    except: return None

# per-zone montant change (CA central + CF central)
byzone=defaultdict(lambda: {'n':0,'chg':0,'gaps':[],'cf_gaps':[]})
movers=[]
for idu,c in cur.items():
    b=base.get(idu)
    if not b: continue
    z=f"{c['commune']}/{c['zone']}"
    st=byzone[z]; st['n']+=1
    ca_c,ca_b=num(c['ca_central']),num(b['ca_central'])
    cf_c,cf_b=num(c['cf_central']),num(b['cf_central'])
    if cf_c is not None and cf_b is not None:
        g=cf_c-cf_b
        if abs(g)>0.5:
            st['chg']+=1; st['gaps'].append(abs(g)); st['cf_gaps'].append(g)
            movers.append((idu,c['commune'],c['zone'],c['kind'],ca_b,ca_c,cf_b,cf_c,
                           b['declenchee'],c['declenchee'],b['regime'],c['regime']))

def med(xs):
    xs=sorted(xs); return xs[len(xs)//2] if xs else 0.0

print("=== MONTANT (charge foncière centrale) qui change — PAR ZONE ===")
print(f"{'zone':24} {'n':>5} {'change':>7} {'médian €':>12} {'max €':>14} {'total €':>16}")
tot_n=tot_chg=0
for z in sorted(byzone):
    s=byzone[z]
    mx=max(s['gaps']) if s['gaps'] else 0.0
    md=med(s['gaps']); tt=sum(s['cf_gaps'])
    print(f"{z:24} {s['n']:>5} {s['chg']:>7} {md:>12,.0f} {mx:>14,.0f} {tt:>16,.0f}")
    tot_n+=s['n']; tot_chg+=s['chg']
print(f"{'TOTAL':24} {tot_n:>5} {tot_chg:>7}")

print(f"\n=== {len(movers)} parcelles dont le montant change — 8 exemples ===")
print("idu | commune | zone | kind | CF avant→après | regime avant→après")
for m in movers[:8]:
    print(f"  {m[0]} {m[1]}/{m[2]} {m[3]} | {num(m[6]):,.0f}→{num(m[7]):,.0f} € | {m[10] or '—'}→{m[11] or '—'}")

# control : euros doivent être 0
ctrl=[m for m in movers if m[3]=='control']
print(f"\nContrôle (display-only) : {len(ctrl)} parcelle(s) control dont le montant change (attendu 0)")
