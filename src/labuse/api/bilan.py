"""BILAN-1 — routes du bilan promoteur.

Un moteur (``labuse.bilan.moteur``), deux portes (onglet Bilan de la fiche,
bouton « Générer le bilan » de la page Docs). Ici vivent :
  · les RATIOS MAISON du compte (Lot 4) — GET/PUT/DELETE /bilan-ratios[/{poste}] ;
  · (lots suivants) le modèle pré-rempli + le calcul + les sorties PDF/Excel.

Doctrine : le front n'envoie que des saisies et affiche le résultat ; aucun calcul
côté client. La cloison par compte suit api/tenant (bilan_ratios ∈ SCOPED_TABLES).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..bilan.catalogue import Poste, charger_catalogue
from ..bilan.moteur import (
    EntreesBilan,
    Moteur,
    Produit,
    Programme,
    ResultatBilan,
    SaisiePoste,
)
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


# ===========================================================================
# Calcul — le front envoie les saisies, le moteur rend le bilan (doctrine 5)
# ===========================================================================
class ProduitIn(BaseModel):
    libelle: str = "Produit"
    lots: float | None = None
    suv: float | None = None
    prix_ttc_m2_suv: float | None = None
    tva: float | None = None


class ProgrammeIn(BaseModel):
    terrain: float | None = None
    surface_taxable: float | None = None
    loyer: float | None = None
    sdp: float | None = None  # surface de plancher (m²) — info / repère faisabilité


class SaisieIn(BaseModel):
    valeur: float | None = None
    etat: str = "a_renseigner"
    tva: float | None = None
    assiette_valeur: float | None = None


class CalculIn(BaseModel):
    programme: ProgrammeIn = ProgrammeIn()
    produits: list[ProduitIn] = []
    postes: dict[str, SaisieIn] = {}
    mode: str = "marge"
    marge_cible: float | None = None
    calendrier: dict[str, int | None] = {}  # étape → J+n (mois), info seulement
    # CHASSE-DOCS-FIX-1 (Lot 5.1) — empreinte des hypothèses calculée par le front, STOCKÉE avec le
    # document (serveur), pour que « Sources modifiées depuis » marche d'un autre poste. Ignorée au calcul.
    empreinte: str | None = None


def _entrees(corps: CalculIn) -> EntreesBilan:
    return EntreesBilan(
        programme=Programme(
            terrain=corps.programme.terrain,
            surface_taxable=corps.programme.surface_taxable,
            loyer=corps.programme.loyer,
            sdp=corps.programme.sdp,
        ),
        produits=[
            Produit(
                libelle=p.libelle,
                lots=p.lots,
                suv=p.suv,
                prix_ttc_m2_suv=p.prix_ttc_m2_suv,
                tva=p.tva,
            )
            for p in corps.produits
        ],
        postes={
            pid: SaisiePoste(
                valeur=s.valeur, etat=s.etat, tva=s.tva, assiette_valeur=s.assiette_valeur
            )
            for pid, s in corps.postes.items()
        },
        mode=corps.mode,
        marge_cible=corps.marge_cible,
        calendrier=dict(corps.calendrier),
    )


def _resultat_dict(r: ResultatBilan) -> dict:
    return {
        "complet": r.complet,
        "manquants": r.manquants,
        "lignes_vides": r.lignes_vides,
        "vraisemblance": r.vraisemblance,
        "total_postes": r.total_postes,
        "postes_renseignes": r.postes_renseignes,
        "lignes": [
            {
                "id": ln.id,
                "bloc": ln.bloc,
                "assiette_valeur": ln.assiette_valeur,
                "taux_ou_montant": ln.taux_ou_montant,
                "etat": ln.etat,
                "ht": ln.ht,
                "tva": ln.tva,
                "ttc": ln.ttc,
                "manquant": ln.manquant,
            }
            for ln in r.lignes
        ],
        "blocs": [
            {
                "id": b.id,
                "titre": b.titre,
                "ht": b.ht,
                "tva": b.tva,
                "ttc": b.ttc,
                "complet": b.complet,
                "manquants": b.manquants,
            }
            for b in r.blocs
        ],
        "produits": r.produits,
        "produits_totaux": r.produits_totaux,
        "depenses_ht": r.depenses_ht,
        "depenses_tva": r.depenses_tva,
        "depenses_ttc": r.depenses_ttc,
        "ca_ht": r.ca_ht,
        "ca_tva": r.ca_tva,
        "ca_ttc": r.ca_ttc,
        "tva_residuelle": r.tva_residuelle,
        "resultat_net": r.resultat_net,
        "marge_pct": r.marge_pct,
        "cash_flow": r.cash_flow,
        "aleas": r.aleas,
        "resultat_sans_aleas": r.resultat_sans_aleas,
        "marge_sans_aleas_pct": r.marge_sans_aleas_pct,
        "ratios": r.ratios,
        "prix_max_terrain": r.prix_max_terrain,
        "prix_max_terrain_m2": r.prix_max_terrain_m2,
    }


@router.post("/bilan/{idu}/calcul")
def calculer_bilan(idu: str, corps: CalculIn) -> dict:
    """Calcule le bilan à partir des seules saisies du client. BILAN-2 : calcul EN
    CONTINU (comme l'Excel) — une case vide vaut 0, la marge et les totaux
    s'affichent dès la première saisie. Les lignes vides sont seulement comptées
    (``lignes_vides``). Aucune donnée n'est inventée."""
    r = Moteur().calculer(_entrees(corps))
    return _resultat_dict(r)


# ===========================================================================
# Modèle — la structure + le Sourcé pré-rempli + les repères (jamais appliqués)
# ===========================================================================
def _repere_poste(p: Poste) -> dict | None:
    """Sérialise le repère d'un poste. Doctrine (décision Vic) : **pas de source
    publique, pas de repère** — seuls les repères « registre » (source publique :
    DVF, outil Taxe, archéo, coût de référence, Faisabilité) sont servis, et encore
    uniquement s'ils se résolvent à l'exécution (cf. reperes_publics). Les ratios de
    place (commission, notaire, honoraires…) NE sont PAS des repères : le client les
    saisit, et peut mémoriser les siens (état « Mes ratios »)."""
    r = p.repere
    if r is None or r.kind != "registre":
        return None
    return {"kind": "registre", "registre_id": r.registre_id}


def _serialiser_catalogue() -> dict:
    cat = charger_catalogue()
    return {
        "version": cat.version,
        "tva_legales": cat.tva_legales,
        "assiettes": cat.assiettes,
        "produit_modele": cat.produit_modele,
        "programme": list(cat.programme),
        "calendrier": [dict(c) for c in cat.calendrier],
        "blocs": [
            {
                "id": b.id,
                "titre": b.titre,
                "postes": [
                    {
                        "id": p.id,
                        "libelle": p.libelle,
                        "sub": p.sub,
                        "note": p.note,
                        "mode": p.mode,
                        "base": p.base,
                        "assiette": p.assiette,
                        "unite": p.unite,
                        "tva": p.tva,
                        "tva_sourcee": p.tva_sourcee,
                        "besoin_assiette": p.besoin_assiette,
                        "alea": p.alea,
                        "repere": _repere_poste(p),
                    }
                    for p in b.postes
                ],
            }
            for b in cat.blocs
        ],
    }


@router.get("/bilan/{idu}/modele")
def modele_bilan(idu: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """La structure du bilan + le Sourcé pré-rempli (terrain, zonage, TVA légales)
    + les repères publics résolus (DVF neuf, coût de référence…) + les ratios maison
    du compte. Tout reste modifiable ; rien n'entre dans le calcul sans geste client."""
    from ..bilan import reperes as _rep

    cat = _serialiser_catalogue()
    sourcee = _rep.sources_parcelle(db, idu)
    # DOCS-COHERENCE-1 (G7/A10) — date de la DONNÉE servie (run servi), pour le pied « Données LABUSE
    # au JJ/MM/AAAA » de l'écran Bilan, identique aux 8 documents.
    from ..exports.builder import _donnees_labuse_au
    sourcee["donnees_au"] = _donnees_labuse_au()
    cat["sourcee"] = sourcee  # {terrain, zonage, commune, parcel_id, prix_achat_dvf, donnees_au}
    cat["reperes_publics"] = _rep.reperes_publics(db, idu, sourcee)

    # ratios maison du compte (état « Mes ratios »)
    cid = current_compte(request)
    rows = db.execute(
        text(f"SELECT poste_id, valeur, tva FROM bilan_ratios WHERE {scope_clause()}"),
        {"cid": cid},
    ).all()
    cat["ratios_compte"] = {r[0]: {"valeur": r[1], "tva": r[2]} for r in rows}
    return cat


# ===========================================================================
# Sorties — PDF + Excel vivant, enregistrés dans « Mes documents » (Lot 5)
# ===========================================================================
def _commune(db: Session, idu: str) -> str:
    try:
        v = db.execute(
            text("SELECT commune FROM parcels WHERE idu = :i"), {"i": idu}
        ).scalar()
        return str(v or "")
    except Exception:  # noqa: BLE001
        return ""


@router.post("/bilan/{idu}/generer")
def generer_bilan(
    idu: str, corps: CalculIn, request: Request, db: Session = Depends(get_db)
) -> dict:
    """Génère (enregistre la recette d') un bilan : BILAN-2 — se génère À TOUT
    MOMENT (plus de porte « bilan complet »). Stocke ses saisies en JSON dans
    « Mes documents » (hypotheses). « Ouvrir » régénère PDF/Excel à partir de ces
    mêmes saisies. ``lignes_vides`` est remonté pour information."""
    r = Moteur().calculer(_entrees(corps))
    from .documents_bibliotheque import millesimes_servis

    cid = compte_ou_401(request)
    row = db.execute(
        text(
            "INSERT INTO documents_generes (compte_id, doc_type, cible_idus, hypotheses, millesimes) "
            "VALUES (:cid, 'bilan', :idus, :hyp, :mil) RETURNING id"
        ),
        {
            "cid": cid,
            "idus": [idu],
            # Lot 5.1 — l'empreinte est rangée sous `_empreinte` (clé uniforme lue par la bibliothèque) ;
            # le reste des saisies sert à régénérer le PDF à l'identique (CalculIn ignore `_empreinte`).
            "hyp": json.dumps({**{k: v for k, v in corps.model_dump().items() if k != "empreinte"},
                               "_empreinte": corps.empreinte}),
            "mil": json.dumps(millesimes_servis(db)),
        },
    ).scalar()
    db.commit()
    return {"doc_id": int(row), "complet": r.complet, "lignes_vides": r.lignes_vides}


def _saisies_du_document(db: Session, idu: str, doc_id: int, request: Request) -> CalculIn:
    """Relit les saisies d'un bilan enregistré (cloison par compte). 404 sinon."""
    cid = current_compte(request)
    row = db.execute(
        text(
            "SELECT hypotheses FROM documents_generes "
            f"WHERE id = :id AND doc_type = 'bilan' AND {scope_clause()}"
        ),
        {"id": doc_id, "cid": cid},
    ).scalar()
    if row is None:
        raise HTTPException(404, "Bilan introuvable pour ce compte.")
    data = row if isinstance(row, dict) else json.loads(row)
    return CalculIn.model_validate(data)


@router.get("/bilan/{idu}.pdf")
def bilan_pdf(
    idu: str, request: Request, doc_id: int = Query(...), db: Session = Depends(get_db)
) -> Response:
    from ..bilan import pdf as _pdf

    corps = _saisies_du_document(db, idu, doc_id, request)
    r = Moteur().calculer(_entrees(corps))
    octets = _pdf.construire_pdf(
        r,
        idu=idu,
        commune=_commune(db, idu),
        programme=corps.programme.model_dump(),
        calendrier=dict(corps.calendrier),
    )
    return Response(
        content=octets,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="bilan-{idu}.pdf"'},
    )


@router.get("/bilan/{idu}.xlsx")
def bilan_xlsx(
    idu: str, request: Request, doc_id: int = Query(...), db: Session = Depends(get_db)
) -> Response:
    from ..bilan.excel import classeur_bilan_bytes

    corps = _saisies_du_document(db, idu, doc_id, request)
    e = _entrees(corps)
    octets = classeur_bilan_bytes(e, titre=f"Bilan — {idu}")
    return Response(
        content=octets,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="bilan-{idu}.xlsx"'},
    )
