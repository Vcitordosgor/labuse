"""M28 Phase A — mesure à blanc q_v12_m28 (filtre bâti ON + départage ON + pondération ON).
Servi intact : prev/étage0 = q_v8_calibre, lignes runs retirées en fin (hygiène hystérésis)."""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope
APRES = "q_v12_m28"
os.environ["LABUSE_ETAGE0_RUN"] = "q_v8_calibre"
for k in ("LABUSE_DISABLE_FILTRE_BATI","LABUSE_DISABLE_DEPARTAGE","LABUSE_DISABLE_AU_POND",
          "LABUSE_DISABLE_BATI_REVELE","LABUSE_DISABLE_BATI_COSIA","LABUSE_DISABLE_AU_STATUT"):
    os.environ.pop(k, None)
from labuse.scoring.p_v2.pipeline import run_score_v2
with session_scope() as s:
    s.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": APRES})
    s.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": APRES})
    s.commit()
t0=time.time()
with session_scope() as s:
    run_score_v2(s, run_id=APRES, rebuild=False, snapshot=False)
with session_scope() as s:
    s.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:r"), {"r": APRES}); s.commit()
print(f"FINI {time.time()-t0:.0f}s — mesure dans {APRES}, servi intact")
