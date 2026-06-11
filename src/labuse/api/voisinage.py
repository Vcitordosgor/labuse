"""Assemblage foncier — parcelles VOISINES (Phase 5), version simple et prudente.

Un promoteur ne regarde pas une parcelle isolée : il regarde des ENSEMBLES contigus.
On liste les parcelles adjacentes (contact géométrique) avec leur verdict LA BUSE et
leur zone PLU, et on signale un « assemblage à étudier » UNIQUEMENT s'il y a une
cohérence minimale (plusieurs parcelles contiguës classées opportunité / à creuser).

PRUDENCE — on NE prétend JAMAIS : même propriétaire, opération réalisable, accord
possible, constructibilité. Tout est « à vérifier ». Lecture seule ; ne touche ni la
cascade ni le scoring.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# Adjacence = contact à ≤ 0,5 m en 2975 (tolère les micro-jeux du cadastre sans franchir
# une voie). Sous ce seuil de surface, on ignore les slivers cadastraux.
ADJ_BUFFER_M = 0.5
MIN_SURFACE_M2 = 100.0
MAX_VOISINES = 8
_INTERESSANT = ("opportunite", "a_creuser")


def compute_voisinage(session: Session, parcel_id: int,
                      parcel_surface: float | None, parcel_status: str | None) -> dict:
    """Voisines adjacentes (verdict + zone PLU) + drapeau d'assemblage prudent."""
    rows = session.execute(text(
        """
        SELECT n.idu, n.surface_m2, e.status, e.opportunity_score,
               (SELECT string_agg(DISTINCT sl.subtype, ', ')
                  FROM spatial_layers sl
                 WHERE sl.kind = 'plu_gpu_zone' AND ST_Intersects(sl.geom_2975, n.geom_2975)) AS plu_zone
        FROM parcels p
        JOIN parcels n ON n.id <> p.id AND ST_DWithin(p.geom_2975, n.geom_2975, :buf)
        LEFT JOIN LATERAL (
            SELECT status, opportunity_score FROM parcel_evaluations e
            WHERE e.parcel_id = n.id ORDER BY evaluated_at DESC LIMIT 1) e ON true
        WHERE p.id = :pid AND (n.surface_m2 IS NULL OR n.surface_m2 >= :mins)
        ORDER BY (e.status IN ('opportunite', 'a_creuser')) DESC,
                 e.opportunity_score DESC NULLS LAST, n.surface_m2 DESC NULLS LAST
        LIMIT :lim
        """
    ), {"pid": parcel_id, "buf": ADJ_BUFFER_M, "mins": MIN_SURFACE_M2, "lim": MAX_VOISINES}).mappings().all()

    voisines = [{
        "idu": r["idu"],
        "surface_m2": round(r["surface_m2"]) if r["surface_m2"] is not None else None,
        "status": r["status"],
        "opportunity_score": r["opportunity_score"],
        "plu_zone": r["plu_zone"],
    } for r in rows]

    interessantes = [v for v in voisines if v["status"] in _INTERESSANT]
    cur_interessante = parcel_status in _INTERESSANT
    # « Assemblage à étudier » = la parcelle ET au moins une voisine contiguë sont classées
    # opportunité / à creuser → cohérence minimale (jamais une affirmation de faisabilité).
    possible = cur_interessante and len(interessantes) >= 1
    n_total = len(interessantes) + (1 if cur_interessante else 0)
    surface_cumulee = (parcel_surface or 0.0) + sum(v["surface_m2"] or 0 for v in interessantes)
    note = None
    if possible:
        # Formulé comme du CONTEXTE (« continuité foncière »), pas comme un signal rare :
        # mesuré sur Saint-Paul, ~99 % des opportunités ont au moins une voisine contiguë
        # en opportunité/à creuser (tissu urbain) — toute sévérisation du critère serait
        # un choix produit à calibrer avec un promoteur, pas un réglage technique.
        surf_str = f"{surface_cumulee:,.0f}".replace(",", " ")   # espace fine, sans toucher au texte
        note = (f"Continuité foncière : {n_total} parcelles contiguës en opportunité ou à creuser, "
                f"~{surf_str} m² cumulés — un assemblage peut être étudié. "
                "Propriétaires, accords et faisabilité restent à vérifier.")
    return {
        "voisines": voisines,
        "assemblage": {
            "possible": possible,
            "n_interessantes": n_total,
            "surface_cumulee_m2": round(surface_cumulee) if possible else None,
            "note": note,
        },
    }
