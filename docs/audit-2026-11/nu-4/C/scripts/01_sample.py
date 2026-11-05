#!/usr/bin/env python3
"""NU4-C — tirage de 500 parcelles sur les 24 communes (≈21/commune), variété forcée.
Déterministe (ordre md5(idu||SEED)). Lecture seule. Réemploi direct de la logique nu-3-J,
mise à l'échelle 120→500. Sortie out/sample500.json."""
import json, hashlib, os, sys
import psycopg
from psycopg.rows import dict_row

PG = "postgresql://openclaw@localhost:5432/labuse"
SEED = "nu4c-v1"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
CIBLE_TOTAL = 500

FLAGS_SQL = """
with ppr_parcels as (
  select distinct p.idu
  from parcels p
  join spatial_layers sl on sl.kind='ppr'
   and sl.geom_2975 is not null
   and p.geom_2975 && sl.geom_2975
   and ST_Intersects(p.geom_2975, sl.geom_2975)
)
select p.idu, p.commune, p.contenance_m2,
  z.zone_fam, z.zone_lib,
  coalesce(r.taux_emprise_pct,0)::float as emprise_pct,
  coalesce(sc.copro,false) as copro,
  d.date_mutation::text as dvf_date, d.nature as dvf_nature,
  (pp.idu is not null) as ppr
from parcels p
left join parcel_zone_plu z on z.idu=p.idu
left join parcel_residuel r on r.parcel_id=p.id
left join parcel_p_score_v2 sc on sc.parcelle_id=p.idu and sc.run_id='q_v20'
left join v_parcel_dvf_last d on d.idu=p.idu
left join ppr_parcels pp on pp.idu=p.idu
where p.cadastre_disparue_le is null
"""

def profiles(r):
    s = set()
    fam = (r["zone_fam"] or "").upper(); lib = (r["zone_lib"] or "").upper()
    if not r["zone_lib"]: s.add("RNU")
    if fam.startswith("A") or lib.startswith("A"): s.add("zoneA")
    if fam.startswith("N") or lib.startswith("N"): s.add("zoneN")
    if "AU" in lib or fam == "AU": s.add("zoneAU")
    if lib.startswith("U") or fam == "U": s.add("zoneU")
    if r["copro"]: s.add("copro")
    if r["emprise_pct"] and r["emprise_pct"] > 2: s.add("bati")
    else: s.add("nu")
    c = r["contenance_m2"] or 0
    if c >= 3000: s.add("grande")
    if 0 < c < 200: s.add("petite")
    if r["dvf_date"] and r["dvf_date"] >= "2024-01-01": s.add("vendue_recente")
    if r["ppr"]: s.add("PPR")
    return s

AXES = ["PPR", "copro", "zoneAU", "RNU", "vendue_recente", "grande", "petite",
        "zoneA", "zoneN", "bati", "nu", "zoneU"]

def h(idu): return hashlib.md5((idu + SEED).encode()).hexdigest()

def main():
    with psycopg.connect(PG, row_factory=dict_row) as cx:
        rows = cx.execute(FLAGS_SQL).fetchall()
    by_comm = {}
    for r in rows:
        r["prof"] = profiles(r)
        by_comm.setdefault(r["commune"], []).append(r)
    n_comm = len(by_comm)
    par_comm = -(-CIBLE_TOTAL // n_comm)  # ceil ≈ 21

    selection = []
    for comm in sorted(by_comm):
        pool = sorted(by_comm[comm], key=lambda r: h(r["idu"]))
        picked = []; covered = set(); remaining = list(pool)
        while len(picked) < par_comm and remaining:
            best = None; best_key = (-1, -1)
            for r in remaining:
                new = r["prof"] & set(AXES) - covered
                wgain = sum((len(AXES) - AXES.index(a)) for a in new)
                key = (wgain, len(new))
                if key > best_key:
                    best = r; best_key = key
            if best is None: break
            picked.append(best); covered |= (best["prof"] & set(AXES)); remaining.remove(best)
        selection.extend(picked)

    # trim déterministe à CIBLE_TOTAL (retirer les md5 les plus hauts)
    selection.sort(key=lambda r: h(r["idu"]))
    selection = selection[:CIBLE_TOTAL]

    allcov = {}
    for r in selection:
        for a in r["prof"] & set(AXES):
            allcov[a] = allcov.get(a, 0) + 1
    out = [{k: r[k] for k in ("idu","commune","contenance_m2","zone_fam","zone_lib",
            "emprise_pct","copro","dvf_date","dvf_nature","ppr")} |
           {"profils": sorted(r["prof"])} for r in selection]
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, "sample500.json"), "w"), ensure_ascii=False, indent=1)
    print(f"sélection : {len(selection)} parcelles / {n_comm} communes (par commune≈{par_comm})")
    from collections import Counter
    print("répartition par commune :", dict(Counter(r["commune"] for r in selection)))
    print("couverture des axes de variété :")
    for a in AXES: print(f"  {a:16} {allcov.get(a,0)}")

if __name__ == "__main__":
    main()
