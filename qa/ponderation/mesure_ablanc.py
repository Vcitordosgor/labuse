"""Mesure À BLANC de la PONDÉRATION au_sous_plancher (option B, TRAIN 1). AUCUNE bascule.

Deux scorings JETABLES sur la MÊME cascade étage 0 (q_v8_calibre) et la MÊME hystérésis
(prev = q_v8_calibre) :
  * AVANT : LABUSE_DISABLE_AU_POND=1 → pondération OFF (contrôle ; doit reproduire q_v8_calibre).
  * APRÈS : pondération ON (le code option B committé).
Le delta AVANT→APRÈS est PUREMENT l'effet de la pondération (+ recalibration N_e induite).
Le contrôle AVANT vs q_v8_calibre mesure la dérive éventuelle de l'environnement (attendu ≈ 0).

Hygiène [S] : en FIN de mesure, les lignes p_score_v2_runs des DEUX jetables sont retirées
(les lignes parcel_p_score_v2 restent pour l'analyse) — le « latest » de l'hystérésis reste
q_v8_calibre, rien en aval n'est perturbé. Purge complète des lignes en fin de train.
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope

AVANT, APRES = "q_v9_pond_avant", "q_v9_pond_apres"
ETAGE0 = "q_v8_calibre"

def purge(label):
    with session_scope() as s:
        s.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": label})
        s.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": label})

def latest_run():
    with session_scope() as s:
        return s.execute(text("SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()

def score(label, pond_off):
    os.environ["LABUSE_ETAGE0_RUN"] = ETAGE0
    if pond_off:
        os.environ["LABUSE_DISABLE_AU_POND"] = "1"
    else:
        os.environ.pop("LABUSE_DISABLE_AU_POND", None)
    from labuse.scoring.p_v2.pipeline import run_score_v2
    t0 = time.time()
    with session_scope() as s:
        prev = s.execute(text("SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()
        run_score_v2(s, run_id=label, rebuild=False, snapshot=False)
    print(f"  [{label}] pond_off={pond_off} prev={prev} → {time.time()-t0:.0f}s", flush=True)

purge(AVANT); purge(APRES)                      # repartir propre
print("latest avant tout:", latest_run(), flush=True)

print("=== AVANT (pondération OFF — contrôle) ===", flush=True)
score(AVANT, pond_off=True)
with session_scope() as s:                      # même prev pour APRÈS
    s.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": AVANT})
print("latest après retrait ligne AVANT:", latest_run(), flush=True)

print("=== APRÈS (pondération ON) ===", flush=True)
score(APRES, pond_off=False)
with session_scope() as s:                      # hygiène : latest hystérésis = q_v8_calibre
    s.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": APRES})
print("latest final (doit être q_v8_calibre):", latest_run(), flush=True)
print("FINI", flush=True)
