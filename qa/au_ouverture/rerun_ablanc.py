"""Re-run À BLANC de l'AU-OUVERTURE (mandat GO RE-RUN, Vic). AUCUNE bascule servie.

Deux scorings JETABLES sur la MÊME cascade étage 0 (q_v8_calibre) et la MÊME hystérésis (prev =
q_v8_calibre, le run calibré latest) :
  * AVANT : LABUSE_DISABLE_AU_STATUT=1 → au_statut neutralisé (base de référence).
  * APRÈS : parcel_au_statut peuplé (4 communes, modèle AFFINÉ).
Le delta entre les deux est PUREMENT l'effet AU-OUVERTURE (+ la recalibration N_e qu'il induit).

Astuce hystérésis : on supprime la LIGNE p_score_v2_runs de AVANT (en gardant ses lignes de tiers)
pour que APRÈS retrouve q_v8_calibre comme prev — exactement le même que AVANT. Runs jetables :
purgés en fin de mesure ? NON ici — on garde q_v8_au_avant/apres pour le rapport ; purge explicite
à la fin du mandat.
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope

AVANT, APRES = "q_v8_au_avant", "q_v8_au_apres"
ETAGE0 = "q_v8_calibre"

def purge(label):
    with session_scope() as s:
        s.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": label})
        s.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": label})

def latest_run():
    with session_scope() as s:
        return s.execute(text("SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()

def score(label, disable_au):
    os.environ["LABUSE_ETAGE0_RUN"] = ETAGE0
    if disable_au:
        os.environ["LABUSE_DISABLE_AU_STATUT"] = "1"
    else:
        os.environ.pop("LABUSE_DISABLE_AU_STATUT", None)
    from labuse.scoring.p_v2.pipeline import run_score_v2
    t0 = time.time()
    with session_scope() as s:
        prev = s.execute(text("SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()
        run_score_v2(s, run_id=label, rebuild=False, snapshot=False)
    print(f"  [{label}] au_disable={disable_au} prev={prev} → {time.time()-t0:.0f}s", flush=True)

# repartir propre si un run précédent traîne
purge(AVANT); purge(APRES)
print("latest avant tout:", latest_run(), flush=True)

print("=== AVANT (au OFF) ===", flush=True)
score(AVANT, disable_au=True)

# retirer la ligne runs de AVANT pour que APRÈS retrouve le MÊME prev (q_v8_calibre)
with session_scope() as s:
    s.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": AVANT})
print("latest après suppression ligne AVANT:", latest_run(), flush=True)

print("=== APRÈS (au ON) ===", flush=True)
score(APRES, disable_au=False)
print("FINI", flush=True)
