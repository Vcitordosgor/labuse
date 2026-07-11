"""Wave Détection Ortho, Lot 1 — pente terrain : le quick win indépendant.

`parcel_terrain` (data-gap) est COMPLET (423 452 parcelles, pente moy/max + flag) et le
raster de pente 5 m a été CONSERVÉ (`rgealti_pente_5m`, PostGIS raster SRID 2975) —
conformément au mandat on RÉUTILISE : la seule chose qui manque est la pente de la
partie NON BÂTIE de la parcelle (parcelle − emprise BD TOPO), plus juste pour placer
une piscine. Ajoutée en colonne `pente_non_batie_deg` de la MÊME table (jamais de
table de pente concurrente).

Méthode : zonal stats PostGIS raster par lots de parcelles bâties (géométrie non bâtie
= ST_Difference avec l'union des bâtiments), checkpoint = la colonne (relançable, ne
recalcule que les NULL). Parcelles non bâties : pente_non_batie_deg = pente_moy_deg.
"""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import load_yaml_config

DDL = """
ALTER TABLE parcel_terrain ADD COLUMN IF NOT EXISTS pente_non_batie_deg real;
"""


def _cfg() -> dict[str, Any]:
    return load_yaml_config("detection_ortho")["pente"]


def compute(session: Session, *, batch: int = 2000, log=print) -> dict[str, Any]:
    session.execute(text(DDL))
    emprise_min = float(_cfg()["emprise_min_m2"])
    # 1. parcelles NON bâties (ou emprise négligeable) : la pente parcelle fait foi
    n_simple = session.execute(text("""
        UPDATE parcel_terrain t SET pente_non_batie_deg = t.pente_moy_deg
        WHERE t.pente_non_batie_deg IS NULL
          AND NOT EXISTS (SELECT 1 FROM parcel_residuel_bati rb
                          WHERE rb.idu = t.idu AND rb.emprise_batie_m2 > :emin)
    """), {"emin": emprise_min}).rowcount
    session.commit()
    log(f"  non bâties : {n_simple} (pente parcelle reprise)")

    # 2. parcelles bâties : stats zonales du raster sur (parcelle − bâtiments), par lots
    total = 0
    t0 = time.monotonic()
    while True:
        n = session.execute(text("""
            WITH lot AS (
              SELECT t.idu FROM parcel_terrain t
              JOIN parcel_residuel_bati rb ON rb.idu = t.idu AND rb.emprise_batie_m2 > :emin
              WHERE t.pente_non_batie_deg IS NULL
              LIMIT :batch
            ),
            nb AS (
              SELECT p.idu,
                     ST_Difference(p.geom_2975, coalesce(b.g, ST_GeomFromText('POLYGON EMPTY', 2975))) AS geom
              FROM parcels p JOIN lot ON lot.idu = p.idu
              LEFT JOIN LATERAL (
                SELECT ST_Union(sl.geom_2975) AS g FROM spatial_layers sl
                WHERE sl.kind = 'batiment' AND ST_Intersects(sl.geom_2975, p.geom_2975)
              ) b ON true
            ),
            stats AS (
              SELECT nb.idu,
                     sum((ss).sum) / NULLIF(sum((ss).count), 0) AS moy
              FROM nb
              JOIN rgealti_pente_5m r ON ST_Intersects(r.rast, nb.geom)
              CROSS JOIN LATERAL (
                SELECT ST_SummaryStats(ST_Clip(r.rast, nb.geom, true)) AS ss
              ) s
              WHERE NOT ST_IsEmpty(nb.geom)
              GROUP BY nb.idu
            )
            UPDATE parcel_terrain t
            SET pente_non_batie_deg = round(coalesce(stats.moy, tt.pente_moy_deg)::numeric, 2)
            FROM lot
            LEFT JOIN stats ON stats.idu = lot.idu
            JOIN parcel_terrain tt ON tt.idu = lot.idu
            WHERE t.idu = lot.idu
        """), {"emin": emprise_min, "batch": batch}).rowcount
        if not n:
            break
        session.commit()  # checkpoint : relançable, seuls les NULL restent
        total += n
        log(f"  bâties : {total} ({total / (time.monotonic() - t0):.0f}/s)")
    return {"non_baties": n_simple, "baties": total}


def sanity_check(session: Session) -> dict[str, Any]:
    """Médiane des parcelles bâties << médiane île (on construit dans le plat)."""
    med_ile, med_bati = session.execute(text("""
        SELECT
          (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY pente_moy_deg) FROM parcel_terrain),
          (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY t.pente_moy_deg)
           FROM parcel_terrain t JOIN parcel_residuel_bati rb
             ON rb.idu = t.idu AND rb.emprise_batie_m2 > 20)
    """)).one()
    return {"mediane_ile_deg": round(med_ile, 1), "mediane_baties_deg": round(med_bati, 1),
            "ok": med_bati < med_ile}


def run(session: Session, log=print) -> dict[str, Any]:
    out = compute(session, log=log)
    out["sanity"] = sanity_check(session)
    log(f"  sanity (bâties << île) : {out['sanity']}")
    return out
