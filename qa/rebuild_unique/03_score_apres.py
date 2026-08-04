"""REBUILD UNIQUE — Étape C : score APRÈS (tables rebâties, correctifs appliqués).

Même étage0 (q_v8_calibre) et même prev (q_v8_calibre, via hystérésis étape A) que l'AVANT.
Le delta AVANT→APRÈS = effet pur des 4 correctifs.
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope

APRES = "q_v9_apres"
ETAGE0 = "q_v8_calibre"

os.environ["LABUSE_ETAGE0_RUN"] = ETAGE0
os.environ.pop("LABUSE_DISABLE_AU_STATUT", None)
from labuse.scoring.p_v2.pipeline import run_score_v2

with session_scope() as s:
    s.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": APRES})
    s.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": APRES})
    s.commit()
    prev = s.execute(text("SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()
    assert prev == ETAGE0, f"prev attendu {ETAGE0}, obtenu {prev}"
    t0 = time.time()
    run_score_v2(s, run_id=APRES, rebuild=False, snapshot=False)
    print(f"  [{APRES}] prev={prev} → {time.time()-t0:.0f}s", flush=True)
    print("  tiers APRÈS :", flush=True)
    for r in s.execute(text("SELECT tier, count(*) n FROM parcel_p_score_v2 WHERE run_id=:r GROUP BY 1 ORDER BY 2 DESC"), {"r": APRES}).all():
        print(f"    {r.tier:28s} {r.n}", flush=True)
print("ÉTAPE C FINIE", flush=True)
