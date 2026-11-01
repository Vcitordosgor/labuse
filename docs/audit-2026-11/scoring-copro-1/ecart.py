"""Écart q_v20 → q_v21 : changements de palier, sens, cause (copro / PPR / étage 0)."""
import json
from sqlalchemy import text
from labuse.db import session_scope
from labuse.scoring.tiers_client import code_palier

A, B = "q_v20", "q_v21"
with session_scope() as s:
    # i-affected parcels (PPR cause) + newly-excluded set
    i_aff = {r[0] for r in s.execute(text(
        "SELECT DISTINCT p.idu FROM parcels p JOIN spatial_layers sl "
        "ON sl.kind='ppr' AND sl.subtype='i' AND ST_Intersects(p.geom_2975, sl.geom_2975)")).all()}
    rows = s.execute(text("""
        SELECT a.parcelle_id, a.tier AS ta, b.tier AS tb, a.copro
        FROM parcel_p_score_v2 a JOIN parcel_p_score_v2 b USING (parcelle_id)
        WHERE a.run_id=:a AND b.run_id=:b""" ), {"a":A,"b":B}).all()
    print(f"parcelles communes {A}∩{B}: {len(rows)}")
    # raw tier crosstab (changed only)
    from collections import Counter
    changed = [(idu,ta,tb,copro) for idu,ta,tb,copro in rows if ta!=tb]
    print(f"changements de TIER stocké: {len(changed)}")
    ct = Counter((ta,tb) for _,ta,tb,_ in changed)
    for (ta,tb),n in sorted(ct.items(), key=lambda x:-x[1]):
        print(f"  {ta:12s} -> {tb:12s} : {n}")
    # client palier crosstab
    pc = Counter((code_palier(ta),code_palier(tb)) for _,ta,tb,_ in rows)
    print("\nPALIER CLIENT (code_palier) — crosstab complet:")
    for (pa,pb),n in sorted(pc.items(), key=lambda x:-x[1]):
        flag = "" if pa==pb else "  <-- CHANGE"
        print(f"  {str(pa):12s} -> {str(pb):12s} : {n}{flag}")
    # cause attribution for changed
    def actionable(code): return code in ("priorite","a_suivre")
    cause = Counter()
    examples = {}
    for idu,ta,tb,copro in changed:
        pa,pb = code_palier(ta), code_palier(tb)
        if pa==pb:
            c="(tier change sans change de palier client)"
        elif copro and actionable(pa) and not actionable(pb):
            c="COPRO: actionnable -> sans_signal (E-010)"
        elif tb=="ecartee" and ta!="ecartee":
            c=("PPR: nouvellement écartée (i-zone)" if idu in i_aff else "ÉTAGE0: nouvellement écartée (autre)")
        elif copro:
            c="COPRO: autre"
        else:
            c="AUTRE (à investiguer)"
        cause[c]+=1
        examples.setdefault(c,[]).append((idu,ta,tb))
    print("\nCAUSES des changements de palier:")
    for c,n in cause.most_common():
        ex=", ".join(f"{i}({a}->{b})" for i,a,b in examples[c][:4])
        print(f"  {n:6d}  {c}\n          ex: {ex}")
    # totals per palier each run
    print("\nTOTAUX palier client:")
    for run in (A,B):
        cc=Counter(code_palier(t) for (t,) in s.execute(text(
            "SELECT tier FROM parcel_p_score_v2 WHERE run_id=:r"),{"r":run}).all())
        print(f"  {run}: {dict(cc)}")
    json.dump({"causes":dict(cause),"n_changed":len(changed)}, open("/tmp/ecart.json","w"))
