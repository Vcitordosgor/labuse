"""Mesure AVANT/APRÈS de l'effet du déclassement AU sur les tiers (point d'arrêt Vic 30/07).

Isole l'effet du SEUL déclassement : deux runs à blanc sur la MÊME cascade (q_v8_calibre) et le
MÊME run précédent (hystérésis identique), différant uniquement par la présence de `parcel_au_statut`.
- baseline `q_v8_au_avant` : LABUSE_DISABLE_AU_STATUT=1 (colonne au_statut None partout).
- après   `q_v8_au_apres` : au_statut lu → génériques déclassées.
Le run baseline est retiré de p_score_v2_runs avant le run après, pour que les DEUX aient
q_v8_calibre comme run précédent (sinon l'après hériterait de la baseline en hystérésis).

RIEN DE SERVI N'EST TOUCHÉ : run servi = q_v7_defisc, intact. Runs jetables, purgés à la fin.
"""
import json
import os

from sqlalchemy import text

from labuse.db import session_scope, engine
from labuse.scoring.p_v2.pipeline import run_score_v2

CASCADE = "q_v8_calibre"
AVANT, APRES = "q_v8_au_avant", "q_v8_au_apres"


def _purge(run_id):
    with engine().begin() as c:
        c.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": run_id})
        c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": run_id})


def _tiers(run_id):
    with session_scope() as s:
        rows = s.execute(text(
            "SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id=:r GROUP BY tier"),
            {"r": run_id}).all()
    return {t: n for t, n in rows}


os.environ["LABUSE_ETAGE0_RUN"] = CASCADE
_purge(AVANT)
_purge(APRES)

# --- baseline (déclassement DÉSACTIVÉ) ---
os.environ["LABUSE_DISABLE_AU_STATUT"] = "1"
with session_scope() as s:
    run_score_v2(s, run_id=AVANT, rebuild=False, snapshot=False)
tiers_avant = _tiers(AVANT)
# retire la baseline de la table des runs → l'après aura q_v8_calibre comme prev (hystérésis identique)
with engine().begin() as c:
    c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": AVANT})

# --- après (déclassement ACTIF) ---
os.environ["LABUSE_DISABLE_AU_STATUT"] = "0"
with session_scope() as s:
    run_score_v2(s, run_id=APRES, rebuild=False, snapshot=False)
tiers_apres = _tiers(APRES)

# --- diff tiers ---
tiers = sorted(set(tiers_avant) | set(tiers_apres))
print("\n=== TIERS AVANT / APRÈS (effet du seul déclassement AU) ===")
for t in tiers:
    a, b = tiers_avant.get(t, 0), tiers_apres.get(t, 0)
    d = b - a
    print(f"  {t:28s} {a:7d} -> {b:7d}  ({d:+d})")

# --- mouvements par parcelle (avant baseline encore en parcel_p_score_v2) ---
with session_scope() as s:
    mv = s.execute(text("""
        SELECT a.tier AS avant, b.tier AS apres, count(*) AS n
        FROM parcel_p_score_v2 a JOIN parcel_p_score_v2 b ON a.parcelle_id=b.parcelle_id
        WHERE a.run_id=:av AND b.run_id=:ap AND a.tier <> b.tier
        GROUP BY a.tier, b.tier ORDER BY n DESC
    """), {"av": AVANT, "ap": APRES}).all()
print("\n=== MOUVEMENTS (tier_avant -> tier_après) ===")
tot = 0
for av, ap, n in mv:
    tot += n
    print(f"  {av:26s} -> {ap:26s} {n}")
print(f"  TOTAL parcelles qui bougent : {tot}")

# combien des mouvements sont des génériques marquées (mouvement ATTENDU)
with session_scope() as s:
    attendu = s.execute(text("""
        SELECT count(*) FROM parcel_p_score_v2 a
        JOIN parcel_p_score_v2 b ON a.parcelle_id=b.parcelle_id
        JOIN parcels p ON p.idu=a.parcelle_id
        JOIN parcel_au_statut au ON au.parcel_id=p.id AND au.classe='générique'
        WHERE a.run_id=:av AND b.run_id=:ap AND a.tier<>b.tier
    """), {"av": AVANT, "ap": APRES}).scalar()
    inattendu = s.execute(text("""
        SELECT a.parcelle_id, a.tier, b.tier FROM parcel_p_score_v2 a
        JOIN parcel_p_score_v2 b ON a.parcelle_id=b.parcelle_id
        WHERE a.run_id=:av AND b.run_id=:ap AND a.tier<>b.tier
          AND a.parcelle_id NOT IN (
            SELECT p.idu FROM parcel_au_statut au JOIN parcels p ON p.id=au.parcel_id
            WHERE au.classe='générique')
        ORDER BY a.parcelle_id
    """), {"av": AVANT, "ap": APRES}).all()
print(f"\n  mouvements ATTENDUS (génériques marquées) : {attendu}")
print(f"  mouvements INATTENDUS (hors génériques)   : {len(inattendu)}")
for idu, av, ap in inattendu[:60]:
    print(f"     {idu}  {av} -> {ap}")

# --- golden : tier avant/après sur les 116 ancres ---
import pathlib
gp = pathlib.Path(__file__).resolve().parents[2] / "reports/m6-audit/golden/golden-parcelles.json"
golden = list(json.load(open(gp))["parcelles"])
with session_scope() as s:
    grows = s.execute(text("""
        SELECT a.parcelle_id, a.tier AS avant, b.tier AS apres,
               (SELECT classe FROM parcel_au_statut au JOIN parcels p ON p.id=au.parcel_id
                WHERE p.idu=a.parcelle_id) AS au_classe
        FROM parcel_p_score_v2 a JOIN parcel_p_score_v2 b ON a.parcelle_id=b.parcelle_id
        WHERE a.run_id=:av AND b.run_id=:ap AND a.parcelle_id = ANY(:g)
        ORDER BY a.parcelle_id
    """), {"av": AVANT, "ap": APRES, "g": golden}).all()
chg = [(i, a, p, c) for i, a, p, c in grows if a != p]
print(f"\n=== GOLDEN (116 ancres) — tiers avant/après ===")
print(f"  golden dont le tier CHANGE : {len(chg)}")
for idu, av, ap, cl in chg:
    print(f"     {idu}  {av} -> {ap}   [{cl}]")

json.dump({"tiers_avant": tiers_avant, "tiers_apres": tiers_apres,
           "mouvements_total": tot, "attendus": attendu, "inattendus": len(inattendu),
           "golden_change": [(i, a, p, c) for i, a, p, c in chg]},
          open(pathlib.Path(__file__).parent / "mesure_tiers_resultat.json", "w"),
          ensure_ascii=False, indent=2)
print("\n✓ résultat écrit dans qa/au_ouverture/mesure_tiers_resultat.json")
