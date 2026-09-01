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

from ..ingestion.ortho_tiles import millesime_servi

router = APIRouter(prefix="/ortho", tags=["ortho"])


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.get("/equipements/{idu}")
def equipements(idu: str, db: Session = Depends(get_db)) -> dict:
    """Badges fiche parcelle (Lot 6) : piscine, pente — sourcés ortho IGN.
    SOLAIRE M2 (renoncement) : PV/CES RETIRÉS du payload — la détection PV V0 (colorimétrie) est
    ABANDONNÉE (précision 0 % mesurée, cf. qa/solaire/PV_PHASE1.md). Plus aucun pv_* servi."""
    row = db.execute(text("""
        SELECT pe.piscine, round(pe.piscine_surface_m2) AS piscine_m2,
               pe.piscine_confiance,
               t.pente_moy_deg, t.pente_non_batie_deg, t.flag_terrassement_lourd
        FROM parcels p
        LEFT JOIN parcel_equipements pe ON pe.idu = p.idu
        LEFT JOIN parcel_terrain t ON t.idu = p.idu
        WHERE p.idu = :idu
    """), {"idu": idu}).mappings().first()
    if row is None:
        raise HTTPException(404)
    # CONNEXIONS-2 Lot 6.3 (propagation M2) — si la source ORTHO est DÉSACTIVÉE au dashboard, cet outil
    # sert « source désactivée » plutôt qu'un chiffre périmé (jamais un chiffre muet d'une source coupée).
    from ..sources_catalog import source_active
    if not source_active(db, "%ortho%"):
        return {"desactivee": True, "millesime": None,
                "source": "Source ortho désactivée au dashboard — badges non servis."}
    # CONNEXIONS-2 Lot 6.4 — millésime LU dans data_sources (centralisé), plus en dur.
    mil = millesime_servi(db)
    return {**dict(row), "millesime": mil,
            "source": f"Détection automatique sur orthophotographie IGN {mil} — "
                      "précision 90,7 % mesurée sur échantillon indépendant interne ; "
                      "fiabilité statistique, non contractuelle. © IGN (Licence Ouverte)."}
