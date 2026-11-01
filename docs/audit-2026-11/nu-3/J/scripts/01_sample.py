#!/usr/bin/env python3
"""AUDIT-NU-3-J — tirage de 120 parcelles (5/commune) avec variété forcée.
Exclut les témoins nu-1/nu-2. Déterministe (ordre md5(idu||sel)). Lecture seule."""
import json, hashlib, os, sys
import psycopg

PG = "postgresql://openclaw@localhost:5432/labuse"
EXCL = set(l.strip() for l in open("/tmp/nu3j_temoins.txt") if l.strip())
SEED = "nu3j-v1"

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
  sl2.bande as palier,
  d.date_mutation::text as dvf_date, d.nature as dvf_nature,
  (pp.idu is not null) as ppr
from parcels p
left join parcel_zone_plu z on z.idu=p.idu
left join parcel_residuel r on r.parcel_id=p.id
left join parcel_p_score_v2 sc on sc.parcelle_id=p.idu and sc.run_id='q_v20'
left join score_labuse sl2 on sl2.parcel_id=p.id and sl2.run_label='q_v20'
left join v_parcel_dvf_last d on d.idu=p.idu
left join ppr_parcels pp on pp.idu=p.idu
where p.cadastre_disparue_le is null
"""

def profiles(r):
    """Set d'étiquettes de variété portées par la parcelle."""
    s = set()
    fam = (r["zone_fam"] or "").upper()
    lib = (r["zone_lib"] or "").upper()
    if not r["zone_lib"]:
        s.add("RNU")  # pas de zonage opposable
    if fam.startswith("A") or lib.startswith("A"):
        s.add("zoneA")
    if fam.startswith("N") or lib.startswith("N"):
        s.add("zoneN")
    if "AU" in lib or fam == "AU":
        s.add("zoneAU")
    if lib.startswith("U") or fam == "U":
        s.add("zoneU")
    if r["copro"]:
        s.add("copro")
    if r["emprise_pct"] and r["emprise_pct"] > 2:
        s.add("bati")
    else:
        s.add("nu")
    c = r["contenance_m2"] or 0
    if c >= 3000:
        s.add("grande")
    if 0 < c < 200:
        s.add("petite")
    if r["dvf_date"] and r["dvf_date"] >= "2024-01-01":
        s.add("vendue_recente")
    if r["ppr"]:
        s.add("PPR")
    return s

# axes de variété qu'on cherche à couvrir globalement, par priorité de rareté
AXES = ["PPR", "copro", "zoneAU", "RNU", "vendue_recente", "grande", "petite",
        "zoneA", "zoneN", "bati", "nu", "zoneU"]

def h(idu):
    return hashlib.md5((idu + SEED).encode()).hexdigest()

def main():
    with psycopg.connect(PG, row_factory=psycopg.rows.dict_row) as cx:
        rows = cx.execute(FLAGS_SQL).fetchall()
    by_comm = {}
    for r in rows:
        if r["idu"] in EXCL:
            continue
        r["prof"] = profiles(r)
        by_comm.setdefault(r["commune"], []).append(r)

    selection = []
    for comm in sorted(by_comm):
        pool = sorted(by_comm[comm], key=lambda r: h(r["idu"]))
        picked = []
        covered = set()
        # Greedy : à chaque tour, prendre la parcelle (ordre md5) qui apporte
        # le plus d'axes non encore couverts dans cette commune ; égalité -> md5.
        remaining = list(pool)
        while len(picked) < 5 and remaining:
            best = None; best_gain = -1
            for r in remaining:
                gain = len(r["prof"] & set(AXES) - covered)
                # bonus rareté : axes rares pèsent plus
                wgain = sum((len(AXES) - AXES.index(a)) for a in (r["prof"] & set(AXES) - covered))
                key = (wgain, gain)
                if key > (best_gain if isinstance(best_gain, tuple) else (-1,-1)):
                    best = r; best_gain = key
            if best is None:
                break
            picked.append(best); covered |= (best["prof"] & set(AXES))
            remaining.remove(best)
        selection.extend(picked)

    # rapport de couverture
    allcov = {}
    for r in selection:
        for a in r["prof"] & set(AXES):
            allcov[a] = allcov.get(a, 0) + 1
    out = [{k: r[k] for k in ("idu","commune","contenance_m2","zone_fam","zone_lib",
            "emprise_pct","copro","palier","dvf_date","dvf_nature","ppr")} |
           {"profils": sorted(r["prof"])} for r in selection]
    os.makedirs(os.path.dirname(sys.argv[0]) + "/../out", exist_ok=True)
    outp = os.path.join(os.path.dirname(sys.argv[0]), "..", "out", "sample120.json")
    json.dump(out, open(outp, "w"), ensure_ascii=False, indent=1)
    print(f"sélection : {len(selection)} parcelles, {len(by_comm)} communes")
    print("couverture des axes de variété (sur 120) :")
    for a in AXES:
        print(f"  {a:16} {allcov.get(a,0)}")
    print("exclus (témoins nu-1/nu-2) :", len(EXCL))
    print("écrit:", outp)

if __name__ == "__main__":
    main()
