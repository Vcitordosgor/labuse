"""Badges ortho de la fiche parcelle (mandat wave-ortho, Lot 6).

`/ortho/equipements/{idu}` sert les badges de la fiche (piscine, PV, CES, pente),
sourcés sur détection automatique orthophoto IGN. Lu par Fiche.tsx.

L'outil de validation des détections (`/ortho/validation`, Lot 3) est parti avec le
spin-off « Vues » (M12 Lot C-bis) : c'était l'atelier de qualification commerciale des
segments, futur « Plein Sud ». La TABLE `ortho_detections` reste intacte en base — elle
alimente aussi le scoring expérimental p_model (SQL direct, indépendant de ce routeur).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingestion.ortho_tiles import MILLESIME

router = APIRouter(prefix="/ortho", tags=["ortho"])


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.get("/equipements/{idu}")
def equipements(idu: str, db: Session = Depends(get_db)) -> dict:
    """Badges fiche parcelle (Lot 6) : piscine, PV, CES, pente — sourcés ortho IGN."""
    row = db.execute(text("""
        SELECT pe.piscine, round(pe.piscine_surface_m2) AS piscine_m2,
               pe.piscine_confiance, pe.pv_detecte, round(pe.pv_surface_m2) AS pv_m2,
               pe.pv_probable_ces,
               t.pente_moy_deg, t.pente_non_batie_deg, t.flag_terrassement_lourd
        FROM parcels p
        LEFT JOIN parcel_equipements pe ON pe.idu = p.idu
        LEFT JOIN parcel_terrain t ON t.idu = p.idu
        WHERE p.idu = :idu
    """), {"idu": idu}).mappings().first()
    if row is None:
        raise HTTPException(404)
    return {**dict(row), "millesime": MILLESIME,
            "source": f"Détection automatique sur orthophotographie IGN {MILLESIME} — "
                      "précision 90,7 % mesurée sur échantillon indépendant interne ; "
                      "fiabilité statistique, non contractuelle. © IGN (Licence Ouverte)."}
