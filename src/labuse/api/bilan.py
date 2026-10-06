"""BILAN-1 — routes du bilan promoteur.

Un moteur (``labuse.bilan.moteur``), deux portes (onglet Bilan de la fiche,
bouton « Générer le bilan » de la page Docs). Ici vivent :
  · les RATIOS MAISON du compte (Lot 4) — GET/PUT/DELETE /bilan-ratios[/{poste}] ;
  · (lots suivants) le modèle pré-rempli + le calcul + les sorties PDF/Excel.

Doctrine : le front n'envoie que des saisies et affiche le résultat ; aucun calcul
côté client. La cloison par compte suit api/tenant (bilan_ratios ∈ SCOPED_TABLES).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..bilan.catalogue import charger_catalogue
from .tenant import compte_ou_401, current_compte, scope_clause

router = APIRouter(tags=["bilan"])


def get_db():  # branché sur la session app au moment de l'inclusion (cf. app.py)
    from .app import get_db as _g

    yield from _g()


def _postes_connus() -> set[str]:
    return {p.id for p in charger_catalogue().postes()}


class RatioIn(BaseModel):
    valeur: float
    tva: float | None = None


@router.get("/bilan-ratios")
def lister_ratios(request: Request, db: Session = Depends(get_db)) -> dict[str, dict]:
    """Les ratios mémorisés par le compte courant : {poste_id: {valeur, tva}}."""
    cid = current_compte(request)
    rows = db.execute(
        text(
            "SELECT poste_id, valeur, tva FROM bilan_ratios "
            f"WHERE {scope_clause()} ORDER BY poste_id"
        ),
        {"cid": cid},
    ).all()
    return {r[0]: {"valeur": r[1], "tva": r[2]} for r in rows}


@router.put("/bilan-ratios/{poste_id}")
def enregistrer_ratio(
    poste_id: str, corps: RatioIn, request: Request, db: Session = Depends(get_db)
) -> dict:
    """Mémorise (ou met à jour) un ratio maison. Écriture → compte identifié requis."""
    if poste_id not in _postes_connus():
        raise HTTPException(404, f"Poste inconnu : {poste_id}")
    cid = compte_ou_401(request)
    db.execute(
        text(
            "INSERT INTO bilan_ratios (compte_id, poste_id, valeur, tva, maj_at) "
            "VALUES (:cid, :pid, :val, :tva, now()) "
            "ON CONFLICT (compte_id, poste_id) DO UPDATE "
            "SET valeur = EXCLUDED.valeur, tva = EXCLUDED.tva, maj_at = now()"
        ),
        {"cid": cid, "pid": poste_id, "val": corps.valeur, "tva": corps.tva},
    )
    db.commit()
    return {"poste_id": poste_id, "valeur": corps.valeur, "tva": corps.tva}


@router.delete("/bilan-ratios/{poste_id}")
def oublier_ratio(
    poste_id: str, request: Request, db: Session = Depends(get_db)
) -> dict:
    cid = compte_ou_401(request)
    db.execute(
        text(
            "DELETE FROM bilan_ratios "
            "WHERE compte_id IS NOT DISTINCT FROM :cid AND poste_id = :pid"
        ),
        {"cid": cid, "pid": poste_id},
    )
    db.commit()
    return {"poste_id": poste_id, "supprime": True}
