"""DOCS-1 (Lot B) — LA BIBLIOTHÈQUE « Mes documents ».

Une table `documents_generes` (la RECETTE d'un document, jamais le PDF) + deux routes :
  · POST /documents           — enregistre une génération (type, parcelle(s), rayon, hypothèses) et
                                prend l'INSTANTANÉ des millésimes de sources servis au moment présent ;
  · GET  /documents           — la liste du compte (Généré le · Document · Sur · Projet · État · actions) ;
  · POST /documents/{id}/rafraichir — remet l'instantané des millésimes à aujourd'hui (après « Régénérer »).

Aucune donnée propre : l'état « À jour / Sources modifiées depuis » compare l'instantané pris à la
génération aux millésimes servis AUJOURD'HUI (data_sources.source_millesime). La régénération d'un PDF
elle-même repasse par le générateur existant (le front rouvre l'URL du document) — ici on ne stocke
que la recette et on la cloisonne par compte (api/tenant — documents_generes ∈ SCOPED_TABLES).
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .tenant import compte_ou_401, current_compte, scope_clause

router = APIRouter(prefix="/documents", tags=["documents"])


def get_db():  # branché sur la session app au moment de l'inclusion (cf. app.py)
    from .app import get_db as _g
    yield from _g()


# Les types de documents que la bibliothèque enregistre (clé interne stable, jamais affichée brute).
# « bilan » = le document « financier » (le mot « Financier » disparaît côté client, DOCS-1 §4).
DOC_TYPES = {"dossier", "bilan", "apporteur", "pre-dossier", "gabarit", "comparatif", "etude-zone"}
#: libellé humain par type (ce que la colonne « Document » affiche).
DOC_LABEL = {
    "dossier": "Dossier", "bilan": "Bilan", "apporteur": "Apporteur",
    "pre-dossier": "Pré-dossier PC", "gabarit": "Gabarit",
    "comparatif": "Comparatif", "etude-zone": "Étude de zone",
}
#: l'Excel n'existe pour aucun document aujourd'hui (il arrive avec le moteur Bilan — BILAN-1). La
#: colonne « Excel » n'est servie que sur les lignes Bilan ET seulement si l'export existe : ici jamais.
_EXCEL_DISPONIBLE: set[str] = set()


def millesimes_servis(db: Session) -> dict[str, str]:
    """{source → millésime} de TOUTES les sources servies aujourd'hui (data_sources.source_millesime).
    C'est l'instantané pris à la génération ET la référence du jour pour l'état « À jour »."""
    try:
        rows = db.execute(text(
            "SELECT name, coalesce(source_millesime, '') FROM data_sources ORDER BY name")).all()
    except Exception:  # noqa: BLE001 — table absente (base nue) : instantané vide, jamais un 500
        return {}
    return {str(n): str(m) for n, m in rows}


class EnregistrerDoc(BaseModel):
    doc_type: str
    idus: list[str]
    rayon_km: float | None = None
    hypotheses: dict | None = None


@router.post("")
def enregistrer(body: EnregistrerDoc, request: Request, db: Session = Depends(get_db)) -> dict:
    """Enregistre une génération dans la bibliothèque du compte + fige l'instantané des millésimes.
    Appelé par la porte juste après « Générer » (le PDF, lui, est ouvert directement par le front)."""
    cid = compte_ou_401(request)
    if body.doc_type not in DOC_TYPES:
        raise HTTPException(422, f"type de document inconnu : {body.doc_type!r}")
    idus = [i.strip() for i in (body.idus or []) if i and i.strip()]
    if not idus:
        raise HTTPException(422, "au moins une parcelle est requise")
    import json
    row = db.execute(text(
        "INSERT INTO documents_generes (compte_id, doc_type, cible_idus, rayon_km, hypotheses, millesimes)"
        " VALUES (:cid, :t, :idus, :r, CAST(:hyp AS jsonb), CAST(:mil AS jsonb)) RETURNING id, created_at"),
        {"cid": cid, "t": body.doc_type, "idus": idus, "r": body.rayon_km,
         "hyp": json.dumps(body.hypotheses) if body.hypotheses is not None else None,
         "mil": json.dumps(millesimes_servis(db))}).mappings().first()
    db.commit()
    return {"id": row["id"], "created_at": row["created_at"].isoformat()}


def _projet_de(db: Session, cid: int | None, idu: str) -> str | None:
    """Le projet du COMPTE qui contient cette parcelle (sinon None → « — »). Scopé par compte."""
    try:
        return db.execute(text(
            "SELECT p.nom FROM projet_parcelles pp"
            " JOIN projets p ON p.id = pp.projet_id"
            " JOIN parcels pa ON pa.id = pp.parcel_id"
            f" WHERE pa.idu = :idu AND {scope_clause('p.')}"
            " ORDER BY pp.proposee_at DESC NULLS LAST LIMIT 1"),
            {"idu": idu, "cid": cid}).scalar()
    except Exception:  # noqa: BLE001 — table absente / base nue : pas de projet, jamais un 500
        return None


def _commune_de(db: Session, idu: str) -> str | None:
    try:
        return db.execute(text("SELECT commune FROM parcels WHERE idu = :idu"), {"idu": idu}).scalar()
    except Exception:  # noqa: BLE001
        return None


# Au-delà de ce seuil, la liste ne rend que les N plus récents + « voir N de plus » (B2).
_PAGE = 200


@router.get("")
def lister(request: Request, db: Session = Depends(get_db), limite: int = _PAGE) -> dict:
    # « Sous 200 lignes tout s'affiche, au-delà voir 200 de plus » (B2) : le front demande 200, puis
    # 400, 600… ; on borne à 2000 (au-delà, c'est une recherche, pas une liste à dérouler).
    """La liste des documents du compte (du plus récent au plus ancien). Chaque ligne porte son état
    (« À jour » / « Sources modifiées depuis ») calculé en comparant son instantané aux millésimes du
    jour, le projet (si la parcelle est dans un projet du compte), et la disponibilité de l'Excel."""
    cid = current_compte(request)
    aujourdhui = millesimes_servis(db)
    total = db.execute(text(
        f"SELECT count(*) FROM documents_generes WHERE {scope_clause()}"), {"cid": cid}).scalar() or 0
    rows = db.execute(text(
        "SELECT id, doc_type, cible_idus, rayon_km, hypotheses, millesimes, created_at"
        f" FROM documents_generes WHERE {scope_clause()}"
        " ORDER BY created_at DESC, id DESC LIMIT :lim"),
        {"cid": cid, "lim": max(1, min(int(limite), 2000))}).mappings().all()
    out = []
    for r in rows:
        idus = list(r["cible_idus"] or [])
        premier = idus[0] if idus else None
        # « À jour » ssi tous les millésimes de l'instantané valent encore ceux servis aujourd'hui.
        instantane = r["millesimes"] or {}
        a_jour = bool(instantane) and all(aujourdhui.get(k) == v for k, v in instantane.items())
        out.append({
            "id": r["id"],
            "doc_type": r["doc_type"],
            "document": DOC_LABEL.get(r["doc_type"], r["doc_type"]),
            "created_at": r["created_at"].isoformat(),
            "idus": idus,
            "rayon_km": float(r["rayon_km"]) if r["rayon_km"] is not None else None,
            "commune": _commune_de(db, premier) if premier else None,
            "projet": _projet_de(db, cid, premier) if premier else None,
            "etat": "a_jour" if a_jour else "modifie",
            "excel": r["doc_type"] == "bilan" and r["doc_type"] in _EXCEL_DISPONIBLE,
            "hypotheses": r["hypotheses"] or None,
        })
    return {"total": total, "documents": out, "reste": max(0, total - len(out))}


@router.post("/{doc_id}/rafraichir")
def rafraichir(doc_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """« Régénérer » : la recette est inchangée, mais l'instantané des millésimes repasse à aujourd'hui
    (le document vient d'être régénéré sur les données du jour). Scopé compte — 404 si pas la sienne."""
    cid = compte_ou_401(request)
    import json
    n = db.execute(text(
        "UPDATE documents_generes SET millesimes = CAST(:mil AS jsonb), created_at = now()"
        f" WHERE id = :id AND {scope_clause()}"),
        {"id": doc_id, "cid": cid, "mil": json.dumps(millesimes_servis(db))}).rowcount
    db.commit()
    if not n:
        raise HTTPException(404, "document introuvable")
    return {"ok": True}


@router.delete("/{doc_id}")
def supprimer(doc_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """Retire une ligne de la bibliothèque du compte (le PDF n'est pas stocké). Scopé — 404 sinon."""
    cid = compte_ou_401(request)
    n = db.execute(text(
        f"DELETE FROM documents_generes WHERE id = :id AND {scope_clause()}"),
        {"id": doc_id, "cid": cid}).rowcount
    db.commit()
    if not n:
        raise HTTPException(404, "document introuvable")
    return {"ok": True}
