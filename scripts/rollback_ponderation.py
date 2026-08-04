"""ROLLBACK de la bascule pondération — restaure le scoring q_v8_calibre pré-pondération.

Symétrique exact de scripts/bascule_ponderation.py : supprime le scoring pondéré servi
sous q_v8_calibre (celui-là est reproductible : re-scorer suffit), puis renomme l'archive
q_v8_calibre_pre_pond → q_v8_calibre (scores, runs, snapshots, journal d'exceptions).
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import text
from labuse.db import engine

LABEL, ARCHIVE = "q_v8_calibre", "q_v8_calibre_pre_pond"

with engine().begin() as c:
    if not c.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id=:a"), {"a": ARCHIVE}).scalar():
        raise SystemExit(f"{ARCHIVE} absent — rien à restaurer.")
    # le scoring pondéré est REPRODUCTIBLE (mesure + script) : suppression assumée
    c.execute(text("DELETE FROM score_snapshot_parcelles WHERE snapshot_id IN "
                   "(SELECT id FROM score_snapshots WHERE run_label=:l)"), {"l": LABEL})
    c.execute(text("DELETE FROM score_snapshots WHERE run_label=:l"), {"l": LABEL})
    c.execute(text("DELETE FROM served_run_exceptions WHERE run_id=:l"), {"l": LABEL})
    c.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id=:l"), {"l": LABEL})
    c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id=:l"), {"l": LABEL})
    for tbl, col in [("parcel_p_score_v2", "run_id"), ("p_score_v2_runs", "run_id"),
                     ("score_snapshots", "run_label"), ("served_run_exceptions", "run_id")]:
        c.execute(text(f"UPDATE {tbl} SET {col}=:l WHERE {col}=:a"), {"l": LABEL, "a": ARCHIVE})
print("✓ rollback : scoring pré-pondération restauré sous q_v8_calibre "
      "(re-lancer build-mvt --label q_v8_calibre pour les tuiles).")
