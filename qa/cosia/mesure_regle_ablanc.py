"""Mesure À BLANC du re-score avec emprise = MAX(BD TOPO, CoSIA) — étape 2 du GO Vic 04/08.
AUCUNE bascule : le run servi q_v8_calibre n'est pas touché ; les features partagées sont
RESTAURÉES à l'identique en fin de mesure (kill-switch), avec vérification.

Séquence :
  0. backup p_model_bati (contrôle de restauration).
  1. build_bati (CoSIA ON) → build_static → run_score_v2 q_v11_regle_apres
     (rebuild=True : la chaîne ext est re-matérialisée sur les nouvelles features ;
     etage0 = q_v8_calibre ; prev hystérésis = q_v8_calibre ; snapshot=False).
  2. retrait de la ligne p_score_v2_runs (hygiène hystérésis, lignes de tiers conservées).
  3. RESTAURATION : build_bati (CoSIA OFF) → build_static → rebuild_features(ext) ;
     vérification p_model_bati ≡ backup (count + somme des emprises) — échec BRUYANT sinon.
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope

APRES = "q_v11_regle_apres"
ETAGE0 = "q_v8_calibre"

def _sig(s):
    return s.execute(text("SELECT count(*), round(sum(emprise_bati_m2)::numeric) FROM p_model_bati")).one()

with session_scope() as s:
    s.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": APRES})
    s.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": APRES})
    s.execute(text("DROP TABLE IF EXISTS p_model_bati_backup_mesure"))
    s.execute(text("CREATE TABLE p_model_bati_backup_mesure AS SELECT * FROM p_model_bati"))
    sig0 = _sig(s)
    s.commit()
print(f"[0] backup p_model_bati : {sig0}", flush=True)

t0 = time.time()
os.environ["LABUSE_ETAGE0_RUN"] = ETAGE0
os.environ.pop("LABUSE_DISABLE_BATI_COSIA", None)      # CoSIA ON
os.environ.pop("LABUSE_DISABLE_BATI_REVELE", None)     # règle bâtie révélée ON
os.environ.pop("LABUSE_DISABLE_AU_POND", None)         # pondération servie reste ON
from labuse.scoring.p_model import sql as p_sql
from labuse.scoring.p_v2.pipeline import run_score_v2, rebuild_features
with session_scope() as s:
    p_sql.build_bati(s)
    sig_on = _sig(s)
    p_sql.build_static(s)
    s.commit()
print(f"[1a] features CoSIA ON : p_model_bati {sig_on} ({time.time()-t0:.0f}s)", flush=True)
with session_scope() as s:
    run_score_v2(s, run_id=APRES, rebuild=True, snapshot=False)
print(f"[1b] score {APRES} fait ({time.time()-t0:.0f}s)", flush=True)

with session_scope() as s:                              # hygiène hystérésis
    s.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": APRES})
    s.commit()

t1 = time.time()
os.environ["LABUSE_DISABLE_BATI_COSIA"] = "1"           # CoSIA OFF → état d'avant
with session_scope() as s:
    p_sql.build_bati(s)
    p_sql.build_static(s)
    s.commit()
with session_scope() as s:
    rebuild_features(s)
with session_scope() as s:
    sig1 = _sig(s)
    if tuple(sig1) != tuple(sig0):
        raise SystemExit(f"RESTAURATION NON CONFORME : {sig1} ≠ {sig0} — NE PAS SERVIR, corriger avant tout.")
    s.execute(text("DROP TABLE p_model_bati_backup_mesure"))
    s.commit()
print(f"[3] features RESTAURÉES et vérifiées ≡ backup {sig1} ({time.time()-t1:.0f}s)", flush=True)
print(f"FINI en {time.time()-t0:.0f}s — servi intact, mesure dans {APRES} (lignes conservées).", flush=True)
