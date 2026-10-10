"""SOURCES-MAJ-1 — purge IDEMPOTENTE du run candidat `q_v18` (Signal p_v2 + Score LABUSE), AVANT
re-calcul. Copie paramétrée de purge_qv16.py (RUN par défaut = q_v18). `run_score_v2` et le run
Score refusent un run_id/run_label déjà présent ; ce script retire q_v18 des 4 tables candidates.
Ne touche RIEN de servi ni la vue parcel_residuel. Rejouable.

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<repo>/src \
        python scripts/audit/scoring/purge_qv18.py [run_id]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

RUN = sys.argv[1] if len(sys.argv) > 1 else "q_v18"

_CIBLES = [
    ("parcel_p_score_v2", "run_id"),
    ("p_score_v2_runs", "run_id"),
    ("score_labuse", "run_label"),
    ("score_labuse_runs", "run_label"),
]


def main() -> None:
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    from sqlalchemy import text

    from labuse.db import session_scope
    if RUN in ("q_v11_m137", "q_v15", "q_v16"):
        raise SystemExit(f"REFUS : {RUN} est un run servi/baseline — purge interdite.")
    with session_scope() as s:
        for tbl, col in _CIBLES:
            exists = s.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": tbl}).scalar()
            if not exists:
                print(f"  {tbl}: absent (ignoré)")
                continue
            n = s.execute(text(f"DELETE FROM {tbl} WHERE {col} = :r"), {"r": RUN}).rowcount
            print(f"  {tbl}: {n} ligne(s) supprimée(s)")
    print(f"✓ purge {RUN} terminée.")


if __name__ == "__main__":
    main()
