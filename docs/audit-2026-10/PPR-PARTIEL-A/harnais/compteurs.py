#!/usr/bin/env python
"""PPR-PARTIEL-A — compteurs des garde-fous sur un échantillon de parcelles touchant du rouge.

Lecture seule. Pour chaque parcelle de l'échantillon : verdict du garde-fou hors rouge
(_hors_rouge_fragment_servable) ET cause/exigu_raison finale (parcel_faisabilite). Donne, sur
l'échantillon : combien remontent (servies), combien restent à 0 et POURQUOI (garde-fou ou
exclusion FIX-1 §6 : emplacement réservé / portion U/AU minuscule). AUCUNE écriture.

    PYTHONPATH=src LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
        ~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/PPR-PARTIEL-A/harnais/compteurs.py [N]
"""
import os
import sys
from collections import Counter

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.db import _hors_rouge_fragment_servable, parcel_faisabilite

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
eng = create_engine(os.environ.get("LABUSE_DATABASE_URL",
                                   "postgresql+psycopg://openclaw@localhost:5432/labuse"))
gf = Counter(); cause = Counter(); exigu = Counter()
with Session(eng) as s:
    ids = [r[0] for r in s.execute(text(
        "SELECT p.id FROM parcels p WHERE EXISTS (SELECT 1 FROM spatial_layers sl "
        "WHERE sl.kind='ppr' AND sl.subtype='INTERDICTION' "
        "AND ST_Intersects(sl.geom_2975, p.geom_2975)) LIMIT :n"), {"n": N})]
    for pid in ids:
        ok, motif = _hors_rouge_fragment_servable(s, pid); s.rollback()
        gf["servable" if ok else motif] += 1
        res = parcel_faisabilite(s, pid); s.rollback()
        if res is None:
            cause["<none>"] += 1; continue
        _, f = res
        cause[f.cause or "servie"] += 1
        if f.cause == "terrain_exigu":
            exigu[f.exigu_raison or "?"] += 1

print(f"échantillon : {len(ids)} parcelles touchant du rouge\n")
print("garde-fou hors rouge :", dict(gf))
print("cause faisabilité     :", dict(cause))
print("  dont terrain_exigu  :", dict(exigu))
