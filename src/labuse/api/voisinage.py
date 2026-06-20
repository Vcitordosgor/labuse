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
# J3 — un assemblage n'est signalé qu'à partir de DEUX voisines contiguës intéressantes (et de
# même zone PLU quand la zone est résolue) : avec « ≥ 1 voisine » le bandeau sortait sur ~99 %
# des opportunités du tissu urbain → il ne discriminait rien. On exige une vraie cohérence.
ASSEMBLAGE_MIN_VOISINES = 2


def _zone_tokens(z: str | None) -> set[str]:
    return {t.strip().lower() for t in (z or "").split(",") if t.strip()}


def compute_voisinage(session: Session, parcel_id: int,
                      parcel_surface: float | None, parcel_status: str | None) -> dict:
    """Voisines adjacentes (verdict + zone PLU) + drapeau d'assemblage prudent."""
    rows = session.execute(text(
        """
        SELECT n.idu, n.surface_m2, e.status, e.opportunity_score,
               (SELECT string_agg(DISTINCT sl.subtype, ', ')
                  FROM spatial_layers sl
                 WHERE sl.kind = 'plu_gpu_zone' AND ST_Intersects(sl.geom_2975, n.geom_2975)) AS plu_zone,
               (SELECT string_agg(DISTINCT sl.subtype, ', ')
                  FROM spatial_layers sl
                 WHERE sl.kind = 'plu_gpu_zone' AND ST_Intersects(sl.geom_2975, p.geom_2975)) AS parcel_zone
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

    parcel_zone = rows[0]["parcel_zone"] if rows else None
    ptoks = _zone_tokens(parcel_zone)
    interessantes = [v for v in voisines if v["status"] in _INTERESSANT]
    cur_interessante = parcel_status in _INTERESSANT
    # Cohérence réglementaire : on retient les voisines intéressantes de MÊME zone PLU que la
    # parcelle (un assemblage se monte dans un même régime de zonage). Si la zone n'est pas
    # résolue (donnée PLU absente), on retombe sur la simple contiguïté — mais toujours ≥ 2.
    meme_zone = [v for v in interessantes if ptoks and (ptoks & _zone_tokens(v["plu_zone"]))]
    retenues = meme_zone if ptoks else interessantes
    # « Assemblage à étudier » = la parcelle ET ≥ 2 voisines contiguës cohérentes → vrai bloc
    # mobilisable (jamais une affirmation de faisabilité).
    possible = cur_interessante and len(retenues) >= ASSEMBLAGE_MIN_VOISINES
    n_total = len(retenues) + (1 if cur_interessante else 0)
    surface_cumulee = (parcel_surface or 0.0) + sum(v["surface_m2"] or 0 for v in retenues)
    note = None
    if possible:
        surf_str = f"{surface_cumulee:,.0f}".replace(",", " ")   # espace fine, sans toucher au texte
        zlabel = " de même zone PLU" if ptoks else ""
        note = (f"Continuité foncière : {n_total} parcelles contiguës{zlabel} en opportunité ou "
                f"à creuser, ~{surf_str} m² cumulés — un assemblage peut être étudié. "
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
