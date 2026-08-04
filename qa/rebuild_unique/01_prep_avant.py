"""REBUILD UNIQUE (mandat Vic 04/08) — Étape A : backup + hystérésis + score AVANT.

À BLANC, réversible, AUCUNE bascule. Le run servi (q_v7_defisc) et les tuiles (mvt) ne sont JAMAIS
touchés. On mesure le delta des 4 correctifs (ingestion zone_lib, 2.2 normalize, 2.3 KW, Saint-Benoît)
par la différence AVANT (tables actuelles, pré-correction) vs APRÈS (tables rebâties).

Étape A :
  1. Backup parcel_zone_plu → *_prebascule, parcel_au_statut → *_prebascule (réversibilité totale).
  2. Neutraliser l'hystérésis : supprimer la LIGNE runs des jetables q_v8_au_* (on garde leurs lignes
     de tiers) → previous_run() retombe sur q_v8_calibre (07-30), prev commun avant/après.
  3. Score AVANT (q_v9_avant) : au ON, étage0=q_v8_calibre, contre les tables ACTUELLES.
  4. Supprimer la ligne runs de q_v9_avant → APRÈS retrouvera le MÊME prev (q_v8_calibre).
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope

AVANT = "q_v9_avant"
ETAGE0 = "q_v8_calibre"

def q(s, sql, **p): return s.execute(text(sql), p)

with session_scope() as s:
    # 1. BACKUP (idempotent : drop puis recrée)
    for src in ("parcel_zone_plu", "parcel_au_statut"):
        bak = f"{src}_prebascule"
        q(s, f"DROP TABLE IF EXISTS {bak}")
        q(s, f"CREATE TABLE {bak} AS TABLE {src}")
        n = q(s, f"SELECT count(*) FROM {bak}").scalar()
        print(f"  backup {bak}: {n} lignes", flush=True)
    s.commit()

    # 2. hystérésis : retirer les lignes runs des jetables q_v8_au_* (garder les tiers)
    jet = [r[0] for r in q(s, "SELECT run_id FROM p_score_v2_runs WHERE run_id LIKE 'q_v8_au_%'").all()]
    for j in jet:
        q(s, "DELETE FROM p_score_v2_runs WHERE run_id=:r", r=j)
    # purge d'un éventuel q_v9_avant/apres résiduel
    for j in ("q_v9_avant", "q_v9_apres"):
        q(s, "DELETE FROM parcel_p_score_v2 WHERE run_id=:r", r=j)
        q(s, "DELETE FROM p_score_v2_runs WHERE run_id=:r", r=j)
    s.commit()
    latest = q(s, "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1").scalar()
    print(f"  jetables q_v8_au_* neutralisés ({len(jet)}) ; latest run = {latest}", flush=True)
    assert latest == ETAGE0, f"prev attendu {ETAGE0}, obtenu {latest}"

# 3. SCORE AVANT (au ON, contre tables actuelles)
os.environ["LABUSE_ETAGE0_RUN"] = ETAGE0
os.environ.pop("LABUSE_DISABLE_AU_STATUT", None)
from labuse.scoring.p_v2.pipeline import run_score_v2
t0 = time.time()
with session_scope() as s:
    prev = q(s, "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1").scalar()
    run_score_v2(s, run_id=AVANT, rebuild=False, snapshot=False)
    print(f"  [{AVANT}] prev={prev} → {time.time()-t0:.0f}s", flush=True)

# 4. retirer la ligne runs de AVANT pour que APRÈS retrouve le même prev
with session_scope() as s:
    q(s, "DELETE FROM p_score_v2_runs WHERE run_id=:r", r=AVANT)
    s.commit()
    print("  ligne runs AVANT supprimée (hystérésis) ; latest =",
          q(s, "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1").scalar(), flush=True)
    # tiers AVANT
    print("  tiers AVANT :", flush=True)
    for r in q(s, "SELECT tier, count(*) n FROM parcel_p_score_v2 WHERE run_id=:r GROUP BY 1 ORDER BY 2 DESC", r=AVANT).all():
        print(f"    {r.tier:28s} {r.n}", flush=True)
print("ÉTAPE A FINIE", flush=True)
