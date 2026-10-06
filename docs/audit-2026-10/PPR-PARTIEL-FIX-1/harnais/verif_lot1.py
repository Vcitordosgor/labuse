"""PPR-PARTIEL-FIX-1 — vérification du lot 1 (surface_hors_ppr_rouge) sur les témoins.
Lecture seule. Usage :
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/.../harnais/verif_lot1.py
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from labuse.db import session_factory
from labuse.faisabilite.db import parcel_faisabilite, surface_hors_ppr_rouge

TEMOINS = [
    ("97409000AY0786", "Saint-André UC 4877 — rouge 145 m² → BADGE (motif ppr_rouge)"),
    ("97415000HL0001", "Saint-Paul 17k — gros stock ppr_rouge → BADGE (remplace IR0368)"),
    ("97411000IR0368", "Saint-Denis Uma 57554 — servie 0 pour EMPLACEMENT RÉSERVÉ → PAS de badge"),
    ("97409000BM0449", "Saint-André 213 — hors rouge 180 m² (<200) → PAS de badge (exigu correct)"),
    ("97409000AB0010", "Saint-André 22902 — ENTIÈREMENT rouge → PAS de badge (rouge intégral)"),
    ("97411000BZ1065", "contrôle : sans rouge → rien ne change"),
]


def resolve(session, idu: str) -> int | None:
    r = session.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).first()
    return int(r[0]) if r else None


def main() -> None:
    extra = sys.argv[1:]
    session = session_factory()()
    try:
        print(f"{'IDU':16} {'cause':16} {'exigu':10} {'parc m²':>9} {'rouge m²':>9} "
              f"{'hors m²':>9} {'%':>4}  badge")
        print("-" * 90)
        for idu, _note in TEMOINS + [(x, "") for x in extra]:
            pid = resolve(session, idu)
            if pid is None:
                print(f"{idu:16} INTROUVABLE")
                continue
            fa = parcel_faisabilite(session, pid)
            cause = exigu = "—"
            if fa is not None:
                cause = fa[1].cause or "(calculée)"
                exigu = fa[1].exigu_raison or "—"
            # mesure brute du rouge pour le tableau (même SQL que la fonction)
            row = session.execute(text(
                "SELECT ST_Area(p.geom_2975) parc, ST_Area(ST_Intersection("
                " ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975,p.geom_2975))),p.geom_2975)) rouge "
                "FROM spatial_layers sl, parcels p WHERE p.id=:pid AND sl.kind='ppr' "
                "AND sl.subtype='INTERDICTION' AND ST_Intersects(sl.geom_2975,p.geom_2975) "
                "GROUP BY p.geom_2975"), {"pid": pid}).first()
            parc = float(row.parc) if row else 0.0
            rouge = float(row.rouge or 0.0) if row else 0.0
            hors = max(0.0, parc - rouge)
            res = surface_hors_ppr_rouge(session, pid, faisa=fa)
            badge = f"{res['hors_rouge_m2']} m² ({res['pct']} %)" if res else "— (rien)"
            print(f"{idu:16} {cause:16} {exigu:10} {parc:9.0f} {rouge:9.0f} "
                  f"{hors:9.0f} {100*hors/parc if parc else 0:4.0f}  {badge}")
    finally:
        session.rollback()
        session.close()


if __name__ == "__main__":
    main()
