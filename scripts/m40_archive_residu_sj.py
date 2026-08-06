"""M40 P1.2 — ARCHIVE (réversible) du résidu Saint-Joseph : 3 zones stale 97412_PLU_20240320.

Doctrine M32/M37 : on ARCHIVE, on ne SUPPRIME pas. Renommage de `kind` (réversible), pas un DELETE.
Les 3 zones (subtypes A/N) d'un document superseded (2024-03-20) subsistaient à côté du courant
(97412_PLU_20251210) ; elles touchent 1 671 parcelles TOUTES aussi couvertes par le courant, dont
le subtype A/N est déjà présent → retrait tier-neutre (run gelé de toute façon). Vérifié P0.

Effet : `kind='plu_gpu_zone'` → `kind='plu_gpu_zone__archive_m40'` : les zones sortent du zonage
servi (la cascade et la garde filtrent `kind='plu_gpu_zone'`) mais restent en base, réversibles.
Écriture spatial_layers HORS SCORING (run gelé — 0 tier). Idempotent.

Rollback : UPDATE spatial_layers SET kind='plu_gpu_zone'
             WHERE kind='plu_gpu_zone__archive_m40' AND attrs->>'idurba'='97412_PLU_20240320';

Usage : PYTHONPATH=src python scripts/m40_archive_residu_sj.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import engine  # noqa: E402

IDURBA = "97412_PLU_20240320"
KIND_SERVI = "plu_gpu_zone"
KIND_ARCHIVE = "plu_gpu_zone__archive_m40"


def main() -> None:
    with engine().begin() as c:
        avant = c.execute(text(
            "SELECT id, subtype FROM spatial_layers WHERE kind=:k AND attrs->>'idurba'=:i ORDER BY id"),
            {"k": KIND_SERVI, "i": IDURBA}).all()
        deja = c.execute(text(
            "SELECT count(*) FROM spatial_layers WHERE kind=:k AND attrs->>'idurba'=:i"),
            {"k": KIND_ARCHIVE, "i": IDURBA}).scalar()
        if not avant and deja:
            print(f"  = déjà archivé ({deja} zones en {KIND_ARCHIVE}) — idempotent, rien à faire.")
            return
        n = c.execute(text(
            "UPDATE spatial_layers SET kind=:a WHERE kind=:s AND attrs->>'idurba'=:i"),
            {"a": KIND_ARCHIVE, "s": KIND_SERVI, "i": IDURBA}).rowcount
        print(f"  ✓ {n} zones résidu {IDURBA} archivées : {KIND_SERVI} → {KIND_ARCHIVE} "
              f"(subtypes {[r[1] for r in avant]}). Réversible.")


if __name__ == "__main__":
    main()
