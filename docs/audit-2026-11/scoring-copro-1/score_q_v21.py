import time
from labuse.db import session_scope
from labuse.scoring.p_v2.pipeline import run_score_v2
t0=time.time()
with session_scope() as s:
    res=run_score_v2(s, run_id="q_v21", rebuild=False, snapshot=True, recette="q_v15")
print("run:",res["run_id"],"n:",res["n"],"duree:",res["duree_s"],"s")
print("tiers:",res["tiers"])
print("taux_base:",res["taux_base"],"snapshot:",res["snapshot"])
print("etage0 utilisé (params):", end=" ")
from sqlalchemy import text
with session_scope() as s:
    print(s.execute(text("SELECT params->>'etage0_run' FROM p_score_v2_runs WHERE run_id='q_v21'")).scalar())
print(f"total {time.time()-t0:.0f}s")
