"""Endpoint outil « Gabarit réglementaire » — GET /outils/gabarit/{idu}.

Le front n'affiche que ce que l'API sert (doctrine LABUSE : zéro recalcul au front).
Le calcul est porté par le moteur pur `labuse.gabarit.engine`.

- `/outils/gabarit/demo`  → démonstration sur la parcelle FICTIVE (CDC §9), calcul complet
  (conservée pour les tests ; le bouton de démo est retiré du front en GABARIT-2).
- `/outils/gabarit/{idu}` → raccordement RÉEL (GABARIT-2) : cadastre + PLU + classification
  des limites (BD TOPO) + PPR rouge. Calcul complet si tout est réuni ; sinon « Calcul
  incomplet » + motif métier (parcelle sans façade, limite non qualifiée, PLU non validé…).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..gabarit.builder import build_gabarit_input
from ..gabarit.contract import GabaritResult
from ..gabarit.engine import INCOMPLETE_MESSAGE, compute_gabarit
from ..gabarit.fixtures import demo_gabarit_input

router = APIRouter(prefix="/outils/gabarit", tags=["gabarit"])


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.get("/{idu}", response_model=GabaritResult)
def gabarit_detail(idu: str, db: Session = Depends(get_db)) -> GabaritResult:
    if idu == "demo":
        res = compute_gabarit(demo_gabarit_input())
        res.raccordement = {"mode": "fixtures",
                            "avertissement": "Données FICTIVES de démonstration (CDC §9)"}
        return res

    build = build_gabarit_input(db, idu)
    if build is None:
        raise HTTPException(404, f"Parcelle inconnue : {idu}")

    if build.blocking:
        return GabaritResult(status="incomplete", message=INCOMPLETE_MESSAGE,
                             validationErrors=build.blocking, raccordement=build.raccordement)

    res = compute_gabarit(build.input)
    res.raccordement = build.raccordement
    return res
