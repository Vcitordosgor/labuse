"""CONTENANCE-1 (Lot D2) — dry-run faisabilité AVANT/APRÈS sur témoins + CW0658/AS0772/AB0010.

Lancé deux fois sur la base `labuse` (contenance backfillée) :
  - code BASE (PYTHONPATH=…/labuse/src)        → surface = DESSIN  (AVANT)
  - code WORKTREE (PYTHONPATH=…/labuse-contenance/src) → surface = CONTENANCE (APRÈS)
Imprime idu · surface servie · SDP (surface_plancher_m2) · cause. AUCUNE écriture (lecture seule).
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite.db import parcel_faisabilite

IDUS = [
    "97415000CW0658", "97415000AS0772",          # écarts relevés A8
    "97404000AX0047", "97409000AY0786", "97411000CP0427",  # témoins (bonnes/mauvaises)
    "97415000CX0664", "97406000AM0664", "97401000AI0166",  # mauvaise/limite
    "97411000IR0091", "97422000BW2390",          # limite / bonne
]
# AB0010 : commune non précisée au mandat — on résout le premier idu se terminant par AB0010.


def main() -> None:
    with session_scope() as s:
        # résout AB0010 (section AB numéro 0010) sur n'importe quelle commune
        ab = s.execute(text(
            "SELECT idu FROM parcels WHERE idu LIKE '%AB0010' ORDER BY idu LIMIT 1")).scalar()
        idus = IDUS + ([ab] if ab else [])
        print(f"{'idu':16} {'surface servie':>14} {'SDP m²':>9}  cause")
        for idu in idus:
            row = s.execute(text(
                "SELECT id, round(surface_m2) dessin, contenance_m2 FROM parcels WHERE idu=:i"),
                {"i": idu}).mappings().first()
            if not row:
                print(f"{idu:16}  (absente)")
                continue
            res = parcel_faisabilite(s, row["id"])
            if res is None:
                print(f"{idu:16} dessin={row['dessin']} cont={row['contenance_m2']}  (pas de faisabilité)")
                continue
            ctx, fa = res
            sdp = (fa.fourchette or {}).get("surface_plancher_m2")
            print(f"{idu:16} {round(ctx.surface_m2):>14} {round(sdp) if sdp else 0:>9}  "
                  f"dessin={row['dessin']} cont={row['contenance_m2']} cause={fa.cause or '—'} "
                  f"constructible={fa.constructible}")


if __name__ == "__main__":
    main()
