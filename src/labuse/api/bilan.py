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
import math
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session


# CHIRURGICAL-FIX-1 (E103) — la TVA est une FRACTION (0.021 social, 0.055 interm., 0.20 plein), comme
# le front l'envoie TOUJOURS (champ saisi en % puis divisé par 100 : BilanEcran.tsx). Un appel direct
# qui passerait un POURCENTAGE brut (« 20 ») faisait `ca_ht = ttc / 21` → CA HT faux ×~17, en 200.
# On BORNE et VALIDE donc le taux à l'entrée : hors [0, 1] → 422 explicite, jamais un bilan absurde.
def _valider_tva(v: float | None) -> float | None:
    if v is None:
        return None
    if not (0.0 <= v <= 1.0):
        raise ValueError(
            "La TVA doit être une fraction entre 0 et 1 (ex. 0.20 pour 20 %), pas un pourcentage"
        )
    return v


def _valider_non_negatif(v: float | None) -> float | None:
    """CHIRURGICAL-FIX-1 (LOT I 1b) — un COÛT (taux ou montant d'un poste) ne peut pas être négatif :
    il est refusé à la saisie (une dépense négative = une recette déguisée, qui gonflerait la marge)."""
    if v is not None and v < 0:
        raise ValueError("Un coût ne peut pas être négatif.")
    return v

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

    _tva_fraction = field_validator("tva")(_valider_tva)
    # LOT J 1c — un ratio maison (coût) ne peut pas être négatif, comme toute cellule de saisie du Bilan.
    _ratio_non_negatif = field_validator("valeur")(_valider_non_negatif)


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

    _tva_fraction = field_validator("tva")(_valider_tva)


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

    _tva_fraction = field_validator("tva")(_valider_tva)
    # LOT I 1b — un coût négatif est refusé à la saisie (taux/montant ET assiette).
    _cout_non_negatif = field_validator("valeur", "assiette_valeur")(_valider_non_negatif)


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


def _entrees_servies(db: Session, idu: str, corps: "CalculIn") -> tuple[EntreesBilan, dict]:
    """CHIRURGICAL-FIX-1 (LOT L 1) — L'OBJET CALCULÉ UNIQUE du Bilan : mêmes saisies + MÊME
    préremplissage pour le PDF ET l'Excel, pour qu'un seul calcul donne deux rendus identiques.
      · la surface de terrain (cadastre) entre DANS le calcul (la ligne d'achat = terrain × €/m²,
        au lieu d'être injectée APRÈS le calcul côté PDF → ligne d'achat vide) ;
      · les postes SOURCÉS que le client n'a pas saisis (taxe d'aménagement, redevance d'archéologie)
        sont préremplis des DEUX côtés (l'Excel les laissait à zéro).
    Renvoie `(entrees, prefill)` ; le prefill porte adresse / commune / date du run servi pour l'en-tête."""
    from ..bilan import reperes as _rep
    pf = _rep.bilan_prefill(db, idu)
    e = _entrees(corps)
    if e.programme.terrain is None:
        e.programme.terrain = _terrain_sourcee(db, idu)
    for pid, sp in (pf.get("postes") or {}).items():
        e.postes.setdefault(pid, sp)
    return e, pf


def _hypotheses_bilan(db: Session, idu: str, corps: "CalculIn") -> tuple[str | None, float | None]:
    """CHIRURGICAL-FIX-1 (LOT L 4) — NOMME les hypothèses dans l'en-tête du PDF (« Chaque hypothèse
    est nommée dans le document ») : le prix de vente (= le prix demandé des produits) et, quand la
    surface saisie EST celle du scénario de l'Étude, « scénario de l'Étude (N lots, S m²) · prix de
    vente = neuf VEFA <niveau> ». Rien n'est inventé : si la saisie ne correspond à aucun scénario,
    on renvoie None et l'en-tête reste honnête (« aucune Étude reliée »)."""
    prix = max((p.prix_ttc_m2_suv for p in corps.produits if p.prix_ttc_m2_suv), default=None)
    sdp = corps.programme.sdp
    if not sdp:
        return None, prix
    try:
        from ..exports.etude_faisabilite import scenario_retenu
        from ..implantation import revisions as _rev
        from ..implantation.service import _study_id
        cfg = {"idus": [idu], "type_projet": "collectif", "objectif": "equilibre",
               "stationnement": "aerien", "terrain": "libere", "niveaux_sous_sol": None,
               "programme": None, "hypotheses": None}
        payload = _rev.charger(db, _study_id(cfg))
        resume = (scenario_retenu(payload) or {}).get("resume") if payload else None
    except Exception:  # noqa: BLE001 — en-tête best-effort, jamais bloquante
        resume = None
    if not resume or not resume.get("sdp_m2") or abs(float(resume["sdp_m2"]) - float(sdp)) > 1.0:
        return None, prix     # la saisie n'est pas le scénario de l'Étude → en-tête honnête
    lots = int(resume["logements"]) if resume.get("logements") else None
    niveau = None
    if prix:
        try:
            from ..ingestion.dvf_prix_neuf import resolve_prix_neuf_marche
            pid = db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            _, niveau, _, _ = resolve_prix_neuf_marche(db, pid) if pid else (None, None, None, None)
        except Exception:  # noqa: BLE001
            niveau = None
    bout = (f"scénario de l'Étude ({lots} lots, {round(float(sdp))} m²)" if lots
            else f"scénario de l'Étude ({round(float(sdp))} m²)")
    if prix:
        bout += f" · prix de vente = neuf VEFA{(' ' + niveau) if niveau else ''}"
    return bout, prix


def _terrain_sourcee(db: Session, idu: str) -> float | None:
    """CHIRURGICAL-FIX-1 (LOT K 2) — la surface de terrain pré-remplie = la CONTENANCE CADASTRALE de la
    parcelle (Sourcé), MÊME source pour le PDF et l'Excel. L'import de `reperes` est fait ici (il manquait
    dans la route Excel, où un `NameError` était avalé en silence → terrain vide). L'erreur n'est PLUS
    avalée : si la contenance ne se résout pas, ça remonte au lieu de servir discrètement un blanc."""
    from ..bilan import reperes as _rep
    return _rep.sources_parcelle(db, idu).get("terrain")


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
def calculer_bilan(idu: str, corps: CalculIn, db: Session = Depends(get_db)) -> dict:
    """Calcule le bilan à partir des seules saisies du client. BILAN-2 : calcul EN
    CONTINU (comme l'Excel) — une case vide vaut 0, la marge et les totaux
    s'affichent dès la première saisie. Les lignes vides sont seulement comptées
    (``lignes_vides``). Aucune donnée n'est inventée.

    OUTIL-ASSEMBLAGE-FIX-8 (LOT 1) — l'écran de saisie porte la MÊME mention de mixité que le PDF/Excel
    (source unique `_mixite_structuree`) : obligation, dénominateur, et réserve rattachée à la charge
    foncière. Audit bloquant 1 : à 35 logements, l'écran n'affichait aucune mixité ni borne haute."""
    r = Moteur().calculer(_entrees(corps))
    out = _resultat_dict(r)
    try:
        out["mixite"] = _mixite_structuree(db, idu, corps)
    except Exception:  # noqa: BLE001 — jamais un bloqueur de calcul écran
        out["mixite"] = None
    return out


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
    garde = _rep.garde_fou_bilan(db, idu, sourcee=sourcee)
    sourcee.update({k: garde[k] for k in ("lecture_capacite", "capacite_a_verifier", "export_constat")})
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


def _programme_saisi(corps: CalculIn) -> bool:
    """Les lignes de produit vides de l'éditeur ne constituent pas un programme."""
    return bool(corps.programme.sdp or any(p.lots or p.suv or p.prix_ttc_m2_suv for p in corps.produits))


def _refuser_si_ca_nul(r, autorise_sans_ca: bool = False) -> None:
    """DOCS-COHERENCE-1 (recette Vic, G3) — export REFUSÉ côté SERVEUR si le CA est nul : un Bilan sans
    programme ni prix de vente n'a rien à exporter.
    CHIRURGICAL-FIX-1 (LOT L 4) — SAUF quand la fiche a un GARDE-FOU à porter (parcelle non constructible
    / sans capacité) : le Bilan que l'outil produit DE LUI-MÊME existe pour MONTRER cet avertissement
    (résultat « non calculable »), il n'est pas refusé."""
    if not getattr(r, "ca_ttc", None) and not autorise_sans_ca:
        raise HTTPException(
            422, "Export indisponible : aucun chiffre d'affaires. Saisissez le programme et un prix de vente.")


# OUTIL-ASSEMBLAGE-FIX-8 (LOT 1) — la clause de mixité (Art. 2 des règlements) porte sur les LOGEMENTS
# (seuil 20/30 logements, quota au nombre de logements ou à la SDP affectée aux logements). Un lot
# NON-logement (commerce, bureau, activité, local, stationnement…) ne compte NI pour le seuil NI pour la
# SDP de mixité. On exclut par le libellé du produit : tout produit est un logement SAUF si son libellé
# nomme une autre nature. Audit bloquant 1 : « 24 logements + 8 commerces » déclenchait les 15 % à 32
# lots au lieu de rester sous le seuil de 30 logements.
_RE_NON_LOGEMENT = re.compile(
    r"commerc|bureau|tertiaire|activit|atelier|entrep[oô]t|\blocal\b|\blocaux\b|boutique|"
    r"restaur|h[oô]tel|h[eé]bergement|parking|stationnement|\bbox\b|\bcave\b", re.I)
# Produits AIDÉS (part sociale/accession) — pour dire si le PRIX de cette part est réellement saisi.
_RE_PRODUIT_AIDE = re.compile(
    r"\bpls\b|\blls\b|\bllts\b|\blli\b|\bpsla\b|\bptz\b|social|sociaux|aid[eé]|accession\s+social|"
    r"interm[eé]diaire", re.I)


def _est_logement(libelle: str | None) -> bool:
    """Un produit compte comme logement pour la mixité SAUF si son libellé nomme une autre nature."""
    return not _RE_NON_LOGEMENT.search(libelle or "")


def _logements_sdp_saisis(corps: "CalculIn") -> tuple[float, float]:
    """OUTIL-ASSEMBLAGE-FIX-6/8 (LOT 1) — le PROGRAMME SAISI vu par la mixité : nombre de LOGEMENTS
    (somme des lots des seuls produits logement, commerces exclus) et SDP des LOGEMENTS (surface
    vendable des produits logement ÷ rendement de la commune ; sinon `programme.sdp` saisie)."""
    logs = [p for p in corps.produits if _est_logement(p.libelle)]
    logements = sum(float(p.lots or 0.0) for p in logs)
    suv_log = sum(float(p.suv or 0.0) for p in logs)
    if suv_log > 0:
        from ..faisabilite.engine import Hypotheses
        coef = float(getattr(Hypotheses.charger(), "coef_rendement", 0.0) or 0.0)
        sdp = suv_log / coef if coef else suv_log
    else:
        sdp = float(corps.programme.sdp or 0.0)
    return logements, sdp


def _part_aidee_chiffree(corps: "CalculIn | None", quota_pct: float | None,
                         logements: float) -> tuple[bool, str]:
    """OUTIL-ASSEMBLAGE-FIX-8 (LOT 1) — la part aidée imposée est-elle RÉELLEMENT chiffrée dans la
    saisie ? Renvoie (prix_aidé_saisi, libellé de la part : « ≈ N logements, Q % du programme »).
    Un produit aidé (PLS/LLS/LLTS/PSLA/PTZ/accession sociale/intermédiaire) avec un prix > 0 chiffre la
    part aidée. Audit bloquant 1 (2ᵉ contre-exemple) : 6 PLS à 2 200 €/m² saisis → la note ne doit plus
    dire « part aidée non chiffrée »."""
    q = float(quota_pct or 0.0)
    requis = math.ceil(q / 100.0 * float(logements or 0.0)) if q and logements else 0
    part_txt = (f"≈ {requis} logement{'s' if requis > 1 else ''}, {q:.0f} % du programme"
                if requis else (f"{q:.0f} % du programme" if q else "la part aidée imposée"))
    if corps is None:
        return False, part_txt
    chiffree = any(
        _est_logement(p.libelle) and _RE_PRODUIT_AIDE.search(p.libelle or "")
        and float(p.prix_ttc_m2_suv or 0.0) > 0
        for p in corps.produits)
    return chiffree, part_txt


def _denominateur_saint_paul(m: dict, logements: float) -> str | None:
    """OUTIL-ASSEMBLAGE-FIX-8 (LOT 2 / « mieux » 1) — à Saint-Paul (secteur SMS, Art. 2 p. 106), le
    règlement fixe le dénominateur : 30 % de la SDP affectée aux logements, arrondi SUPÉRIEUR en nombre
    de logements. On le DIT pour que le promoteur contrôle son programme. None hors secteur SMS."""
    if m.get("origine") != "secteur_sms":
        return None
    q = float(m.get("quota_pct") or 0.0)
    if not q:
        return None
    base = (f"Dénominateur : {q:.0f} % de la SDP affectée aux logements, arrondi supérieur en nombre de "
            "logements (Art. 2 p. 106)")
    if logements:
        base += f" — soit ≈ {math.ceil(q / 100.0 * float(logements))} logements sur {int(round(logements))}"
    return base + "."


def _mixite_structuree(db: Session, idu: str, corps: "CalculIn | None" = None) -> dict | None:
    """OUTIL-ASSEMBLAGE-FIX-8 (LOT 1/2) — SOURCE UNIQUE de la mention de mixité du Bilan, structurée pour
    que l'ÉCRAN et les EXPORTS portent la même chose : `note` (obligation + dénominateur Saint-Paul),
    `charge_reserve` (réserve rattachée au MONTANT de charge foncière : borne haute si la part aidée n'est
    pas chiffrée, ou mention que la part aidée EST chiffrée au prix saisi) et `borne_haute` (bool corrigé
    par la saisie). Calculée sur le PROGRAMME RÉELLEMENT SAISI (`corps`) ; sans saisie → scénario servi."""
    from ..faisabilite.bilan import compute_bilan_servi, mixite_pour_programme
    row = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        return None
    m = None
    logements = 0.0
    try:
        if corps is not None and (corps.produits or corps.programme.sdp):
            logements, sdp = _logements_sdp_saisis(corps)
            m = mixite_pour_programme(db, row["id"], logements, sdp)
        else:
            b, _ = compute_bilan_servi(db, row["id"])
            m = b.mixite if (b and getattr(b, "mixite", None)) else None
            logements = float((m or {}).get("logements") or 0.0)
    except Exception:  # noqa: BLE001 — jamais un bloqueur d'export
        return None
    if not isinstance(m, dict) or not m.get("servitude"):
        return None
    cite = " · ".join(x for x in (m.get("article"), m.get("page")) if x)
    # OUTIL-ASSEMBLAGE-FIX-3 (relecture-2) — libellé exact selon l'origine : règle de ZONE (Saint-Denis)
    # vs secteur SMS (Saint-Paul). On ne dit « servitude/secteur » que pour un vrai secteur SMS.
    _amont = "Obligation de mixité du règlement de zone" if m.get("origine") == "zone_reglement" \
        else "Secteur de mixité sociale"
    if not m.get("declenchee"):
        # OUTIL-ASSEMBLAGE-FIX-6 (LOT 2) — exemption ZAC (Savane des Tamarins) : on porte la précision du
        # moteur (programme aidé à l'échelle de la ZAC, non chiffré ici), pas un « non déclenchée » muet.
        _detail = m.get("detail") or ""
        note = _detail if "ZAC" in _detail else f"{_amont} — clause non déclenchée sur ce programme ({cite})."
        return {"note": note, "charge_reserve": None, "borne_haute": False, "declenchee": False,
                "avertissements": list(m.get("avertissements") or []), "mixite": m}
    q = m.get("quota_pct")
    note = (f"Obligation de mixité : {int(q)} % " if q else "Obligation de mixité : ") \
        + (m.get("produits") or "logements aidés") + (f" ({cite})" if cite else "")
    denom = _denominateur_saint_paul(m, logements)   # LOT 2 / « mieux » 1 — dénominateur Saint-Paul
    if denom:
        note += " " + denom
    # OUTIL-ASSEMBLAGE-FIX-8 (LOT 1 / « mieux » 3) — la réserve est RATTACHÉE au montant de charge foncière
    # et dit CE QUI EST VRAIMENT CHIFFRÉ : si la part aidée a un prix saisi, ce n'est plus une borne haute.
    charge_reserve, bh = None, bool(m.get("borne_haute"))
    if bh:
        aide_chiffree, part_txt = _part_aidee_chiffree(corps, q, logements)
        if aide_chiffree:
            charge_reserve = (f"La part aidée ({part_txt}) est chiffrée au prix saisi : la charge foncière "
                              "en tient compte (ce n'est plus une borne haute).")
            bh = False
        else:
            charge_reserve = (f"Charge foncière = BORNE HAUTE : la part aidée ({part_txt}) n'est pas chiffrée "
                              "(aucun prix social/accession saisi). Le montant est un PLAFOND, pas le chiffre "
                              "réglementaire de l'opération.")
    return {"note": note, "charge_reserve": charge_reserve, "borne_haute": bh, "declenchee": True,
            "avertissements": list(m.get("avertissements") or []), "mixite": m}


def _mixite_note(db: Session, idu: str, corps: "CalculIn | None" = None) -> str | None:
    """Note PLATE (obligation + réserve de charge foncière + avertissements) pour le Bilan PDF/Excel —
    bâtie sur la source unique `_mixite_structuree`, pour que l'écran et les documents ne divergent jamais.
    OUTIL-ASSEMBLAGE-FIX-8 (LOT 2) — l'avertissement d'exclusion ZAC (Marie Caze / Sans Souci) voyage
    jusqu'au PDF/Excel (audit bloquant 2 : il était omis des documents individuels d'AH0022)."""
    s = _mixite_structuree(db, idu, corps)
    if not s:
        return None
    txt = s["note"] + (" " + s["charge_reserve"] if s.get("charge_reserve") else "")
    for a in s.get("avertissements") or []:
        txt += " " + a
    return txt


@router.get("/bilan/{idu}.pdf")
def bilan_pdf(
    idu: str, request: Request, doc_id: int = Query(...), db: Session = Depends(get_db)
) -> Response:
    from ..bilan import pdf as _pdf

    corps = _saisies_du_document(db, idu, doc_id, request)
    # DOCS-COHERENCE-1 (recette Vic) — pré-remplissages SOURCÉS (taxe d'aménagement, archéologie) pour
    # les postes que le client n'a PAS saisis : le PDF montre le même Sourcé que l'écran. En-tête
    # complet (adresse BAN) + pied daté du run servi.
    from ..bilan import reperes as _rep
    # CHIRURGICAL-FIX-1 (LOT L 1) — objet calculé UNIQUE (terrain dans le calcul + postes sourcés),
    # le MÊME que la route Excel : un seul calcul, deux rendus identiques.
    e, _pf = _entrees_servies(db, idu, corps)
    r = Moteur().calculer(e)
    _gf = _rep.garde_fou_bilan(db, idu, sdp_saisie=corps.programme.sdp, postes_saisis=set(corps.postes),
                               programme_saisi=_programme_saisi(corps),
                               suv_saisie=sum(p.suv or 0.0 for p in corps.produits))
    _gf["mixite_note"] = _mixite_note(db, idu, corps)   # OUTIL-ASSEMBLAGE-FIX-6 (LOT 1) — programme SAISI
    _refuser_si_ca_nul(r, autorise_sans_ca=bool(_gf.get("alertes") or _gf.get("export_constat")))
    # DOCS-1 — carte de situation sur la couverture du Bilan (best-effort : jamais un bloqueur).
    try:
        from ..exports.builder import _plan_situation_html
        _map = _plan_situation_html(db, idu)
    except Exception:  # noqa: BLE001
        _map = ""
    _prog = corps.programme.model_dump()
    _prog["terrain"] = e.programme.terrain      # la MÊME contenance que celle entrée dans le calcul
    # CHIRURGICAL-FIX-1 (LOT L 4) — en-tête qui NOMME les hypothèses (Étude reliée + prix de vente),
    # au lieu du « aucune Étude reliée · Prix demandé : non renseigné » figé qui contredisait le contenu.
    _etude_reliee, _prix_demande = _hypotheses_bilan(db, idu, corps)
    octets = _pdf.construire_pdf(
        r,
        idu=idu,
        commune=_commune(db, idu),
        adresse=_pf.get("adresse") or "",
        donnees_au=_pf.get("donnees_au"),
        programme=_prog,
        calendrier=dict(corps.calendrier),
        map_html=_map,
        etude_reliee=_etude_reliee,
        prix_demande=_prix_demande,
        garde_fou=_gf,   # LOT K 2b / LOT L — la fiche écarte-t-elle ce programme ?
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
    # CHIRURGICAL-FIX-1 (LOT L 1) — MÊME objet calculé que le PDF (terrain dans le calcul + postes
    # sourcés taxe/archéologie) : le classeur recalcule les MÊMES dépenses / CA / résultat à l'euro.
    e, _ = _entrees_servies(db, idu, corps)
    # CHIRURGICAL-FIX-1 (LOT K 2b / LOT L 4) — même garde-fou que le PDF ; il autorise l'export sans CA
    # quand la parcelle est écartée (le classeur porte alors « non calculable » + l'avertissement).
    from ..bilan import reperes as _rep
    _gf = _rep.garde_fou_bilan(db, idu, sdp_saisie=corps.programme.sdp, postes_saisis=set(corps.postes),
                               programme_saisi=_programme_saisi(corps),
                               suv_saisie=sum(p.suv or 0.0 for p in corps.produits))
    _gf["mixite_note"] = _mixite_note(db, idu, corps)   # OUTIL-ASSEMBLAGE-FIX-6 (LOT 1) — programme SAISI
    _refuser_si_ca_nul(Moteur().calculer(e), autorise_sans_ca=bool(_gf.get("alertes") or _gf.get("export_constat")))
    octets = classeur_bilan_bytes(e, titre=f"Bilan — {idu}", garde_fou=_gf)
    return Response(
        content=octets,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="bilan-{idu}.xlsx"'},
    )
