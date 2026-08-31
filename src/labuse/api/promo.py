"""PROMO-1 — endpoints ADMIN de la collecte de programmes + le rattachement.

P2 : `/admin/programmes/collecter` (coller une URL de portfolio → l'IA propose la liste, RIEN n'est
inséré) puis `/admin/programmes/valider` (l'admin a corrigé ligne à ligne → insertion + rapprochement).
P3 : `/admin/programmes/{id}/lier` (rattachement MANUEL). `/admin/programmes` (vue d'ensemble),
`/admin/programmes/{id}` DELETE. Toutes gardées `exiger_admin`. Aucun texte/photo n'est jamais stocké.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/programmes", tags=["promo"])


def get_db():
    from .app import get_db as _g
    yield from _g()


def _admin(request: Request):
    from .auth import exiger_admin
    exiger_admin(request)


def _resoudre_promoteur(db: Session, siren: str | None, nom: str | None) -> tuple[str | None, str]:
    """(siren, nom) du promoteur : si un SIREN est donné, on résout sa dénomination (Scan patrimoine) ;
    sinon on garde le nom saisi. Le nom est TOUJOURS renseigné (jamais un promoteur anonyme)."""
    if siren:
        d = db.execute(text(
            "SELECT denomination FROM parcelle_personne_morale WHERE siren = :s AND denomination IS NOT NULL LIMIT 1"),
            {"s": siren}).scalar()
        if d:
            return siren, d
    return (siren or None), (nom or "(promoteur non nommé)")


class CollecterIn(BaseModel):
    url: str
    promoteur_siren: str | None = None
    promoteur_nom: str | None = None


@router.post("/collecter")
def collecter(body: CollecterIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Coller l'URL d'un portfolio → l'IA propose {nom, commune, url, annee} par programme. RIEN n'est
    inséré : l'admin corrige et valide ensuite. L'appel modèle est journalisé (leçon S6)."""
    _admin(request)
    from ..promo.collecte import fetch_texte, extraire_programmes
    siren, nom = _resoudre_promoteur(db, body.promoteur_siren, body.promoteur_nom)
    texte, liens, motif = fetch_texte(body.url)
    if motif:
        return {"ok": False, "motif": motif, "promoteur_nom": nom, "promoteur_siren": siren}
    res = extraire_programmes(db, texte, liens)
    if not res.get("ok"):
        return {"ok": False, "motif": res.get("motif"), "promoteur_nom": nom, "promoteur_siren": siren}
    return {"ok": True, "promoteur_siren": siren, "promoteur_nom": nom, "url_portfolio": body.url,
            "programmes": res["programmes"], "n": len(res["programmes"]),
            "note": "Propositions du modèle — corrigez ligne à ligne, puis validez. Rien n'est encore "
                    "enregistré. Aucun texte ni visuel du promoteur n'est conservé, seulement les faits + le lien."}


class ProgIn(BaseModel):
    nom: str
    commune: str | None = None
    url: str | None = None
    annee: int | None = None


class ValiderIn(BaseModel):
    promoteur_siren: str | None = None
    promoteur_nom: str | None = None
    url_portfolio: str
    programmes: list[ProgIn]


@router.post("/valider")
def valider(body: ValiderIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Insère les programmes VALIDÉS par l'admin (dédoublonnés) + tente le rapprochement automatique
    (P3). Rien n'entre sans être passé par ici. Renvoie le compte inséré, ignoré (doublon), rattaché."""
    _admin(request)
    from ..promo.rattachement import rapprocher
    siren, nom = _resoudre_promoteur(db, body.promoteur_siren, body.promoteur_nom)
    insere = ignore = rattache = 0
    lignes = []
    for p in body.programmes:
        if not p.nom.strip():
            continue
        # dédoublonnage : par URL si présente, sinon par (promoteur + nom + commune).
        if p.url:
            existe = db.execute(text("SELECT id FROM programmes WHERE url = :u"), {"u": p.url}).scalar()
        else:
            existe = db.execute(text(
                "SELECT id FROM programmes WHERE promoteur_nom = :pn AND nom = :n "
                "AND commune IS NOT DISTINCT FROM :c AND url IS NULL"),
                {"pn": nom, "n": p.nom.strip(), "c": p.commune}).scalar()
        if existe:
            ignore += 1
            continue
        ratt = rapprocher(db, siren=siren, commune=p.commune, annee=p.annee)
        pid = db.execute(text(
            "INSERT INTO programmes (promoteur_siren, promoteur_nom, nom, commune, url, url_portfolio, "
            "  source, annee, op_siren, op_commune, op_annee, rattachement_confiance, rattachement_mode) "
            "VALUES (:ps, :pn, :n, :c, :u, :up, 'collecte_ia', :an, :os, :oc, :oa, :conf, :mode) RETURNING id"),
            {"ps": siren, "pn": nom, "n": p.nom.strip(), "c": p.commune, "u": p.url, "up": body.url_portfolio,
             "an": p.annee, "os": (ratt or {}).get("op_siren"), "oc": (ratt or {}).get("op_commune"),
             "oa": (ratt or {}).get("op_annee"), "conf": (ratt or {}).get("confiance"),
             "mode": (ratt or {}).get("mode")}).scalar()
        insere += 1
        if ratt:
            rattache += 1
        lignes.append({"id": pid, "nom": p.nom.strip(), "commune": p.commune,
                       "rattache": bool(ratt), "confiance": (ratt or {}).get("confiance")})
    db.commit()
    return {"ok": True, "insere": insere, "ignore_doublon": ignore, "rattache_auto": rattache,
            "lignes": lignes,
            "note": f"{insere} programme(s) enregistré(s), {rattache} rattaché(s) automatiquement "
                    f"(SIREN + commune + période ≥ seuil), {ignore} doublon(s) ignoré(s)."}


class LierIn(BaseModel):
    op_siren: str
    op_commune: str
    op_annee: int | None = None


@router.post("/{prog_id}/lier")
def lier(prog_id: int, body: LierIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Rattachement MANUEL d'un programme à une opération (sous le seuil auto, ou correction admin)."""
    _admin(request)
    n = db.execute(text(
        "UPDATE programmes SET op_siren = :os, op_commune = :oc, op_annee = :oa, "
        "  rattachement_confiance = NULL, rattachement_mode = 'manuel' WHERE id = :id"),
        {"os": body.op_siren, "oc": body.op_commune, "oa": body.op_annee, "id": prog_id}).rowcount
    db.commit()
    if not n:
        raise HTTPException(404, f"programme {prog_id} inconnu")
    return {"ok": True, "mode": "manuel"}


@router.post("/{prog_id}/delier")
def delier(prog_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """Retire le rattachement (le programme retourne « publiés sur leur site », non rattaché)."""
    _admin(request)
    db.execute(text(
        "UPDATE programmes SET op_siren = NULL, op_commune = NULL, op_annee = NULL, "
        "  rattachement_confiance = NULL, rattachement_mode = NULL WHERE id = :id"), {"id": prog_id})
    db.commit()
    return {"ok": True}


@router.get("")
def liste(request: Request, promoteur_siren: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Vue d'ensemble admin des programmes (filtrable par promoteur)."""
    _admin(request)
    where = "WHERE promoteur_siren = :s" if promoteur_siren else ""
    rows = db.execute(text(
        f"SELECT id, promoteur_siren, promoteur_nom, nom, commune, url, url_portfolio, source, annee, "
        f"  date_releve, op_siren, op_commune, op_annee, rattachement_mode, rattachement_confiance "
        f"FROM programmes {where} ORDER BY promoteur_nom, commune NULLS LAST, nom"),
        {"s": promoteur_siren} if promoteur_siren else {}).mappings().all()
    return {"n": len(rows), "programmes": [dict(r) | {"date_releve": r["date_releve"].isoformat() if r["date_releve"] else None} for r in rows]}


@router.delete("/{prog_id}")
def supprimer(prog_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    _admin(request)
    db.execute(text("DELETE FROM programmes WHERE id = :id"), {"id": prog_id})
    db.commit()
    return {"ok": True}
