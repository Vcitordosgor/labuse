"""SECTEUR-2b (U1) — le panneau de détail d'une commune de la couche VEFA (clic sur la carte). Tout
depuis les moteurs existants (`ingestion.vefa_neuf.detail_commune`), chaque chiffre avec son n."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/outils/vefa-neuf", tags=["vefa-neuf"])


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.get("/{ref}")
def vefa_detail(ref: str, db: Session = Depends(get_db)) -> dict:
    """Détail VEFA d'une commune : médiane €/m² (36 mois) + n, tendance 12 mois, répartition
    appartements/maisons, offre engagée Sitadel (24 mois), lien fiche commune (côté front). `ref` = code
    INSEE (5 chiffres) OU nom de commune — le clic carte porte le nom, on résout l'INSEE ici."""
    from ..ingestion.vefa_neuf import detail_commune
    insee = ref if re.fullmatch(r"\d{5}", ref) else db.execute(text(
        "SELECT substring(idu,1,5) FROM parcels WHERE commune = :c LIMIT 1"), {"c": ref}).scalar()
    if not insee:
        raise HTTPException(404, f"commune inconnue : {ref}")
    return detail_commune(db, insee)
