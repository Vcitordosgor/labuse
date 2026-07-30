"""Enquête AR1423 (backfill chaude→brûlante) — arbitrage Vic 30/07. LECTURE / mesure à blanc.

Re-scorage à blanc AVANT/APRÈS déclassement (même protocole que mesure_tiers) pour capturer, sur
`97403000AR1423` : contrib_d, rang, event_date, tier — dans les deux états — ET les seuils brûlante
calibrés du run (brulante_seuil_d, brulante_top_decile_d, n_entree). But : prouver POURQUOI elle
monte (son propre contrib_d, ~constant, ne change pas ; c'est le seuil top-décile qui bouge quand les
génériques quittent le pool chaude). Runs jetables purgés en fin. Rien de servi n'est touché.
"""
import json
import os

from sqlalchemy import text

from labuse.db import session_scope, engine
from labuse.scoring.p_v2.pipeline import run_score_v2

CASCADE = "q_v8_calibre"
AVANT, APRES = "q_v8_ar_avant", "q_v8_ar_apres"
CIBLE = "97403000AR1423"


def _purge(run_id):
    with engine().begin() as c:
        c.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": run_id})
        c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": run_id})


def _row(run_id):
    with session_scope() as s:
        r = s.execute(text(
            "SELECT tier, rang, contrib_d, event_date, mult_base FROM parcel_p_score_v2 "
            "WHERE run_id=:r AND parcelle_id=:i"), {"r": run_id, "i": CIBLE}).mappings().first()
    return dict(r) if r else None


os.environ["LABUSE_ETAGE0_RUN"] = CASCADE
_purge(AVANT); _purge(APRES)

os.environ["LABUSE_DISABLE_AU_STATUT"] = "1"
with session_scope() as s:
    res_av = run_score_v2(s, run_id=AVANT, rebuild=False, snapshot=False)
row_av = _row(AVANT)
with engine().begin() as c:
    c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": AVANT})

os.environ["LABUSE_DISABLE_AU_STATUT"] = "0"
with session_scope() as s:
    res_ap = run_score_v2(s, run_id=APRES, rebuild=False, snapshot=False)
row_ap = _row(APRES)


def _p(res):
    p = res["params"]
    return {"n_entree": p.n_entree, "n_sortie": p.n_sortie,
            "brulante_seuil_d": round(p.brulante_seuil_d, 4),
            "brulante_top_decile_d": round(p.brulante_top_decile_d, 4)}


# contexte statique de la parcelle
with session_scope() as s:
    ctx = s.execute(text("""
        SELECT p.idu, p.commune, z.zone_lib, z.zone_fam,
               ST_Area(p.geom_2975) AS surface_m2
        FROM parcels p LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
        WHERE p.idu=:i"""), {"i": CIBLE}).mappings().first()
    ctx = dict(ctx) if ctx else {}
    ctx["surface_m2"] = round(float(ctx.get("surface_m2") or 0), 1)
    # est-elle marquée AU ? (ne devrait pas : c'est une backfill non-marquée)
    marque = s.execute(text(
        "SELECT classe FROM parcel_au_statut a JOIN parcels p ON p.id=a.parcel_id "
        "WHERE p.idu=:i"), {"i": CIBLE}).scalar()

print("=== CONTEXTE 97403000AR1423 ===")
print(json.dumps(ctx, ensure_ascii=False))
print("marquée parcel_au_statut :", marque or "NON")
print("\n=== AVANT (déclassement OFF) ===")
print(" row   :", row_av)
print(" params:", _p(res_av))
print("\n=== APRÈS (déclassement ON) ===")
print(" row   :", row_ap)
print(" params:", _p(res_ap))

cd_av = float(row_av["contrib_d"]) if row_av and row_av["contrib_d"] is not None else None
cd_ap = float(row_ap["contrib_d"]) if row_ap and row_ap["contrib_d"] is not None else None
print("\n=== DIAGNOSTIC ===")
print(f" contrib_d avant={cd_av} après={cd_ap} (constant ? {cd_av==cd_ap})")
print(f" top_decile_d avant={_p(res_av)['brulante_top_decile_d']} "
      f"après={_p(res_ap)['brulante_top_decile_d']}")
print(f" event_date : {row_av['event_date'] if row_av else None}")

json.dump({"contexte": ctx, "marque": marque,
           "avant": {"row": {k: str(v) for k, v in (row_av or {}).items()}, "params": _p(res_av)},
           "apres": {"row": {k: str(v) for k, v in (row_ap or {}).items()}, "params": _p(res_ap)}},
          open(os.path.join(os.path.dirname(__file__), "enquete_ar1423_resultat.json"), "w"),
          ensure_ascii=False, indent=2)

_purge(AVANT); _purge(APRES)
print("\n✓ jetables purgés, résultat écrit.")
