"""M42 P1 — index de PERF pour les blocs voisinage & historique servis en fiche (dette perf).

Écriture DB HORS SCORING (index + colonne géométrique dérivée) : ne touche NI tier, NI run, NI
cascade. Idempotent. Objectif : historique `idu_codes` < 1 ms (GIN) et voisinage permis rapide
(geom_2975 indexée, plus de ST_Transform par requête).

Usage : PYTHONPATH=src python scripts/m42_indexes.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import engine  # noqa: E402

STMTS = [
    # GIN sur idu_codes (jsonb) → `idu_codes ? :idu` indexé (historique du site).
    "CREATE INDEX IF NOT EXISTS ix_sitadel_idu_codes_gin ON sitadel_permits USING gin (idu_codes)",
    # colonne géométrique 2975 dérivée (générée) + gist → voisinage permis sans ST_Transform live.
    "ALTER TABLE sitadel_permits ADD COLUMN IF NOT EXISTS geom_2975 geometry(Geometry,2975) "
    "GENERATED ALWAYS AS (ST_Transform(geom, 2975)) STORED",
    "CREATE INDEX IF NOT EXISTS ix_sitadel_geom_2975 ON sitadel_permits USING gist (geom_2975)",
    "ANALYZE sitadel_permits",
]


def main() -> None:
    with engine().begin() as c:
        for s in STMTS:
            t0 = time.time()
            c.execute(text(s))
            print(f"  ✓ ({time.time()-t0:.1f}s) {s.split(chr(40))[0][:70]}")
    print("✓ M42 P1 — index perf posés (GIN idu_codes + geom_2975 permis), 0 écriture scoring.")


if __name__ == "__main__":
    main()
