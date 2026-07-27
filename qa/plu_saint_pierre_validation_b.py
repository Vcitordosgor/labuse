"""Point d'arrêt B — échantillon 10 parcelles avant/après + écart repli vs calibré (échantillon 400).
Lecture seule en base. AUCUN re-run de scoring."""
import os, random, shutil, sys, json

YAML = "config/plu_saint_pierre.yaml"
AWAY = "/tmp/plu_sp/_plu_saint_pierre.yaml.away"

from sqlalchemy import text
from labuse.db import make_engine
from sqlalchemy.orm import Session

eng = make_engine(os.environ["LABUSE_DATABASE_URL"])

SAMPLE_ZONES = [("Ug", 2), ("Uf", 2), ("Ud", 1), ("UdBO", 1), ("Ucv", 1), ("Up", 1), ("Us", 1), ("AU02", 1)]

with Session(eng) as s:
    picked = []
    for lib, n in SAMPLE_ZONES:
        rows = s.execute(text("""
            WITH pool AS (SELECT parcelle_id FROM parcel_p_score_v2
                          WHERE run_id='q_v7_defisc' AND parcelle_id LIKE '97416%' AND tier <> 'ecartee')
            SELECT p.id, p.idu, p.surface_m2 FROM pool JOIN parcels p ON p.idu = pool.parcelle_id
            JOIN spatial_layers z ON z.kind='plu_gpu_zone' AND z.attrs->>'partition'='DU_97416'
              AND z.attrs->>'libelle' = :lib
              AND ST_Intersects(z.geom_2975, ST_PointOnSurface(p.geom_2975))
            ORDER BY p.idu LIMIT :n"""), {"lib": lib, "n": n}).all()
        picked += [(lib, r.id, r.idu, r.surface_m2) for r in rows]

    pool_ids = s.execute(text("""
        WITH pool AS (SELECT parcelle_id FROM parcel_p_score_v2
                      WHERE run_id='q_v7_defisc' AND parcelle_id LIKE '97416%' AND tier <> 'ecartee')
        SELECT p.id FROM pool JOIN parcels p ON p.idu = pool.parcelle_id""")).scalars().all()
random.seed(42)
dist_ids = random.sample(pool_ids, min(400, len(pool_ids)))


def run_pass(ids):
    import importlib
    import labuse.faisabilite.plu_rules as pr
    import labuse.faisabilite.db as fdb
    pr._doc_for.cache_clear()
    out = {}
    with Session(eng) as s:
        for pid in ids:
            try:
                r = fdb.parcel_faisabilite(s, pid)
            except Exception as e:
                out[pid] = {"err": str(e)[:80]}
                continue
            if r is None:
                out[pid] = None
                continue
            ctx, f = r
            out[pid] = {"zone": f.zone, "constructible": f.constructible, "calibree": f.calibree,
                        "verdict": f.verdict[:90], "sdp": f.fourchette.get("surface_plancher_m2"),
                        "niveaux": f.fourchette.get("niveaux"),
                        "emprise": f.fourchette.get("emprise_constructible_m2"),
                        "logts": f.fourchette.get("logements_sous_sol"),
                        "src_hauteur": (f.steps and next((st.source for st in f.steps if "iveaux" in st.label), "")) or ""}
    return out

all_ids = [pid for _, pid, _, _ in picked] + dist_ids

# PASSE AVANT (repli) : YAML déplacé
shutil.move(YAML, AWAY)
try:
    avant = run_pass(all_ids)
finally:
    shutil.move(AWAY, YAML)
# PASSE APRÈS (calibré)
apres = run_pass(all_ids)

print("=== ÉCHANTILLON 10 PARCELLES (avant → après) ===")
for lib, pid, idu, surf in picked:
    a, b = avant.get(pid), apres.get(pid)
    print(f"\n[{lib}] {idu} ({surf:.0f} m²)")
    for tag, d in (("AVANT", a), ("APRES", b)):
        if not d:
            print(f"  {tag}: aucun résultat"); continue
        print(f"  {tag}: calibree={d.get('calibree')} constructible={d.get('constructible')} "
              f"niveaux={d.get('niveaux')} emprise={d.get('emprise')} SDP={d.get('sdp')} "
              f"logts={d.get('logts')} src_hauteur={d.get('src_hauteur')!r}")
        print(f"         verdict: {d.get('verdict')}")

print("\n=== ÉCART REPLI vs CALIBRÉ (échantillon aléatoire, seed 42) ===")
import statistics
pairs = [(avant[p], apres[p]) for p in dist_ids if avant.get(p) and apres.get(p) and "err" not in avant[p] and "err" not in apres[p]]
n = len(pairs)
both_c = [(a, b) for a, b in pairs if a["constructible"] and b["constructible"] and a["sdp"] and b["sdp"]]
lost = sum(1 for a, b in pairs if a["constructible"] and not b["constructible"])
gained = sum(1 for a, b in pairs if not a["constructible"] and b["constructible"])
deltas = [b["sdp"] - a["sdp"] for a, b in both_c]
rel = [(b["sdp"] - a["sdp"]) / a["sdp"] * 100 for a, b in both_c if a["sdp"]]
print(f"n={n} | constructibles avant→après : perdent la constructibilité {lost}, la gagnent {gained}")
if deltas:
    print(f"SDP (parcelles constructibles aux 2 passes, n={len(deltas)}) :")
    print(f"  médiane delta {statistics.median(deltas):+.0f} m² ({statistics.median(rel):+.1f} %)")
    up = sum(1 for d in deltas if d > 0); down = sum(1 for d in deltas if d < 0); eq = sum(1 for d in deltas if d == 0)
    print(f"  hausse {up} / baisse {down} / égal {eq}")
    qs = statistics.quantiles(rel, n=4)
    print(f"  quartiles delta relatif : {qs[0]:+.1f} % / {qs[1]:+.1f} % / {qs[2]:+.1f} %")
json.dump({"picked": [[l, i] for l, _, i, _ in picked]}, open("/tmp/plu_sp/sample.json", "w"))
