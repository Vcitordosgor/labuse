#!/usr/bin/env python
"""PPR-PARTIEL-A — chronomètre du run borné aux parcelles touchant du rouge.

Lecture seule : on RECALCULE `parcel_faisabilite` (cœur per-parcelle du résiduel) sur un
échantillon de parcelles touchant du rouge et on mesure le temps par parcelle, pour estimer
la durée du run complet (≈151 545 parcelles). AUCUNE écriture, aucun run servi.

    PYTHONPATH=src LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
        ~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/PPR-PARTIEL-A/harnais/chrono_run.py [N]
"""
import os
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.db import parcel_faisabilite

N = int(sys.argv[1]) if len(sys.argv) > 1 else 500
url = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
eng = create_engine(url)

with Session(eng) as s:
    ids = [r[0] for r in s.execute(text(
        "SELECT p.id FROM parcels p WHERE EXISTS (SELECT 1 FROM spatial_layers sl "
        "WHERE sl.kind='ppr' AND sl.subtype='INTERDICTION' "
        "AND ST_Intersects(sl.geom_2975, p.geom_2975)) LIMIT :n"
    ), {"n": N})]
    print(f"échantillon : {len(ids)} parcelles touchant du rouge")

    ok = err = 0
    t0 = time.perf_counter()
    for pid in ids:
        try:
            parcel_faisabilite(s, pid)
            ok += 1
        except Exception as e:  # noqa: BLE001 — chronomètre : on compte l'échec, on continue
            err += 1
            if err <= 3:
                print(f"  ! {pid}: {type(e).__name__}: {e}")
        s.rollback()  # pas d'état résiduel entre parcelles
    dt = time.perf_counter() - t0

per = dt / max(1, ok)
total = 151_545
print(f"\n{ok} ok / {err} err en {dt:.1f}s → {per*1000:.0f} ms/parcelle (faisabilité seule)")
print(f"extrapolation per-parcelle × {total:,} = {per*total/60:.0f} min ({per*total/3600:.1f} h)")
