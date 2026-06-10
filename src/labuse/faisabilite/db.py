"""Intégration base : résout le contexte d'une parcelle (surface, zone PLU,
contraintes réunionnaises) et lance le moteur. Lecture seule ; aucune écriture,
aucune dépendance à la cascade/scoring.

Le code de sous-zone vient de spatial_layers.name (ex. 'U1c', 'Usdu') pour les
couches PLU ; la surface de ST_Area(geom_2975) (métrique) ; les contraintes des
couches pente / trait_de_cote / safer déjà ingérées.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from .engine import Contraintes, Faisabilite, estimate_capacity
from .plu_rules import resolve_zone

_CTX = text("""
SELECT p.idu, p.commune,
       ST_Area(p.geom_2975)                               AS surface_m2,
       (SELECT z.name FROM spatial_layers z
          WHERE z.commune = p.commune AND z.kind ILIKE '%plu%'
            AND ST_Contains(z.geom, p.centroid)
          ORDER BY ST_Area(z.geom) ASC LIMIT 1)           AS zone,
       (SELECT max((pl.attrs->>'slope_pct')::float) FROM spatial_layers pl
          WHERE pl.commune = p.commune AND pl.kind = 'pente'
            AND ST_Intersects(pl.geom_2975, p.geom_2975))  AS pente_pct,
       EXISTS(SELECT 1 FROM spatial_layers t
          WHERE t.commune = p.commune AND t.kind = 'trait_de_cote'
            AND t.subtype IN ('bande_courte','bande_longue')
            AND ST_Intersects(t.geom_2975, p.geom_2975))    AS littoral,
       EXISTS(SELECT 1 FROM spatial_layers a
          WHERE a.commune = p.commune AND a.kind = 'safer'
            AND ST_Intersects(a.geom_2975, p.geom_2975))     AS safer
FROM parcels p
WHERE p.id = :pid
""")


@dataclass
class ParcelContext:
    parcel_id: int
    idu: str
    commune: str
    surface_m2: float
    zone: str | None
    contraintes: Contraintes


def parcel_context(session: Session, parcel_id: int) -> ParcelContext | None:
    r = session.execute(_CTX, {"pid": parcel_id}).one_or_none()
    if r is None:
        return None
    libelles = []
    c = Contraintes(
        pente_pct=float(r.pente_pct) if r.pente_pct is not None else None,
        bande_littorale=bool(r.littoral),
        agricole_sar=bool(r.safer),
        libelles=libelles,
    )
    if r.safer:
        libelles.append("Parcelle en périmètre SAFER (préemption agricole possible).")
    return ParcelContext(parcel_id, r.idu, r.commune, float(r.surface_m2), r.zone, c)


def parcel_faisabilite(session: Session, parcel_id: int) -> tuple[ParcelContext, Faisabilite] | None:
    """Contexte + pré-faisabilité d'une parcelle. None si parcelle/zone introuvable."""
    ctx = parcel_context(session, parcel_id)
    if ctx is None or not ctx.zone:
        return None
    rules = resolve_zone(ctx.zone)
    if rules is None:
        return None
    return ctx, estimate_capacity(rules, ctx.surface_m2, ctx.contraintes)
