"""REVUE · R3 — moteur unique rejoué sur q_v11_m137 (protocole LOT AP).
La même parcelle par tous les chemins servis (SQL couche servie · fiche · v2/score) doit donner
LES MÊMES chiffres (tier, mult_base, rang, surface). Toute divergence = 🔴.
120 parcelles tirées au sort (tous tiers) + cas canari (score élevé → a_creuser : ICPE/PPR).
"""
import os, sys
os.environ["LABUSE_DATABASE_URL"] = "postgresql+psycopg://openclaw@localhost:5432/labuse"
from fastapi.testclient import TestClient
from sqlalchemy import text
from labuse.api.app import app
from labuse.db import engine
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL as RUN

c = TestClient(app, base_url="http://testserver")
print(f"run servi backend = {RUN}", flush=True)
assert RUN == "q_v11_m137", f"run servi inattendu: {RUN}"

with engine().begin() as e:
    ids = [r[0] for r in e.execute(text(
        "SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id=:r "
        "AND tier IN ('brulante','chaude','reserve_fonciere','a_creuser','ecartee') "
        "ORDER BY random() LIMIT 120"), {"r": RUN}).all()]
    canari = [dict(r._mapping) for r in e.execute(text(
        "SELECT parcelle_id, tier, mult_base FROM parcel_p_score_v2 WHERE run_id=:r "
        "AND tier='a_creuser' AND mult_base > 4 ORDER BY mult_base DESC LIMIT 10"), {"r": RUN}).all()]

echantillon = list(dict.fromkeys(ids + [x["parcelle_id"] for x in canari]))
divergences = []


def approx(a, b, tol=0.01):
    if a is None or b is None:
        return a == b
    return abs(float(a) - float(b)) <= tol


for i, idu in enumerate(echantillon):
    with engine().begin() as e:
        sql = e.execute(text(
            "SELECT s.tier, s.mult_base, s.rang, p.surface_m2 "
            "FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id "
            "WHERE s.parcelle_id=:i AND s.run_id=:r"), {"i": idu, "r": RUN}).mappings().first()
    if not sql:
        continue
    fsv = (c.get(f"/parcels/{idu}").json().get("score_v2") or {})
    fiche = c.get(f"/parcels/{idu}").json()
    v2 = c.get(f"/v2/score/{idu}").json()
    problems = []
    if not (sql["tier"] == fsv.get("tier") == v2.get("tier")):
        problems.append(f"tier SQL={sql['tier']} fiche={fsv.get('tier')} v2={v2.get('tier')}")
    if not (approx(sql["mult_base"], fsv.get("mult_base")) and approx(sql["mult_base"], v2.get("mult_base"))):
        problems.append(f"mult SQL={sql['mult_base']} fiche={fsv.get('mult_base')} v2={v2.get('mult_base')}")
    if not (sql["rang"] == fsv.get("rang") == v2.get("rang")):
        problems.append(f"rang SQL={sql['rang']} fiche={fsv.get('rang')} v2={v2.get('rang')}")
    if not approx(sql["surface_m2"], fiche.get("surface_m2"), tol=1.0):
        problems.append(f"surface SQL={sql['surface_m2']} fiche={fiche.get('surface_m2')}")
    if problems:
        divergences.append({"idu": idu, "problems": problems})
    if (i + 1) % 30 == 0:
        print(f"  … {i+1}/{len(echantillon)} rejouées, {len(divergences)} divergence(s)", flush=True)

print(f"\n=== {len(echantillon)} parcelles rejouées · {len(divergences)} DIVERGENCE(S) ===", flush=True)
for d in divergences[:15]:
    print("  DIVERGENCE", d["idu"], " · ".join(d["problems"]), flush=True)

print(f"\n=== CANARI : {len(canari)} parcelles score élevé classées a_creuser ===", flush=True)
canari_sans_motif = []
for x in canari:
    idu = x["parcelle_id"]
    fiche = c.get(f"/parcels/{idu}").json()
    fsv = fiche.get("score_v2") or {}
    v2 = c.get(f"/v2/score/{idu}").json()
    motif = fsv.get("motif")
    pourquoi = v2.get("pourquoi") or v2.get("raison")
    lignes_contrainte = [l for l in (fiche.get("lines") or []) if (l.get("weight") or 0) < 0]
    a_le_pourquoi = bool(motif) or bool(pourquoi) or len(lignes_contrainte) > 0
    print(f"  {idu} mult={x['mult_base']} motif={motif!r} pourquoi_v2={str(pourquoi)[:50]!r} "
          f"lignes_neg={len(lignes_contrainte)} POURQUOI_LISIBLE={a_le_pourquoi}", flush=True)
    if not a_le_pourquoi:
        canari_sans_motif.append(idu)

print(f"\ncanari SANS pourquoi lisible : {len(canari_sans_motif)}", flush=True)
sys.exit(0 if not divergences and not canari_sans_motif else 2)
