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
    """Contexte + pré-faisabilité d'une parcelle, EMPRISE SUR GÉOMÉTRIE RÉELLE
    (ST_Buffer du contour cadastral par le recul séparatif, EPSG:2975).
    None si parcelle/zone introuvable."""
    from .engine import Hypotheses

    ctx = parcel_context(session, parcel_id)
    if ctx is None or not ctx.zone:
        return None
    rules = resolve_zone(ctx.zone)
    if rules is None:
        return None

    hyp = Hypotheses.charger()
    recul = (float(rules.recul_limites_sep_m)
             if isinstance(rules.recul_limites_sep_m, (int, float))
             else hyp.recul_limites_defaut_m)
    area = session.execute(
        text("SELECT ST_Area(ST_Buffer(geom_2975, -:d)) FROM parcels WHERE id = :pid"),
        {"d": recul, "pid": parcel_id}).scalar()
    emprise_geo = (float(area or 0.0), recul)
    return ctx, estimate_capacity(rules, ctx.surface_m2, ctx.contraintes, hyp=hyp, emprise_geo=emprise_geo)


def fiche_payload(session: Session, parcel_id: int) -> dict | None:
    """Payload JSON de la carte de faisabilité pour la fiche parcelle.
    None si la parcelle n'est pas couverte (zone hors PLU Saint-Paul outillé)."""
    res = parcel_faisabilite(session, parcel_id)
    if res is None:
        return None
    ctx, f = res
    c = ctx.contraintes

    # Bilan promoteur (PARTIE 1) — uniquement si constructible ; isolé/défensif.
    bilan = None
    try:
        from .bilan import compute_bilan, sector_price
        from .engine import Hypotheses
        if f.constructible:
            hyp = Hypotheses.charger()
            b = compute_bilan(f.fourchette.get("shab_vendable_m2", 0), ctx.surface_m2,
                              sector_price(session, ctx.parcel_id, hyp), hyp)
            bilan = {
                "fiable": b.fiable, "fiabilite": b.fiabilite, "verdict": b.verdict,
                "prix_dvf": b.prix_dvf, "comparables": (b.prix_dvf or {}).get("comparables"),
                "ca": b.ca, "charge_fonciere": b.charge_fonciere,
                "steps": [{"label": s.label, "formule": s.formule, "valeur": s.valeur, "source": s.source}
                          for s in b.steps],
                "hypotheses": b.hypotheses, "avertissements": b.avertissements, "bandeau": b.bandeau,
            }
    except Exception:  # noqa: BLE001 - le bilan ne casse jamais la fiche
        bilan = None

    return {
        "zone": f.zone,
        "zone_resolue": f.zone_resolue,
        "surface_m2": round(ctx.surface_m2),
        "constructible": f.constructible,
        "verdict": f.verdict,
        "fourchette": f.fourchette,
        "contexte": {
            "pente_pct": round(c.pente_pct) if c.pente_pct is not None else None,
            "littoral": c.bande_littorale,
            "safer": c.agricole_sar,
        },
        "steps": [{"label": s.label, "formule": s.formule, "valeur": s.valeur, "source": s.source}
                  for s in f.steps],
        "hypotheses": f.hypotheses,
        "avertissements": f.avertissements,
        "modulation": f.modulation,
        "bandeau": f.bandeau,
        "bilan": bilan,
    }
