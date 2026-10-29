"""EXPORTS-2 lot 8 — LES ROUTES DES 5 DOCUMENTS servis par le BUILDER UNIQUE (src/labuse/exports) :
Dossier · Résumé · Financier · Apporteur (le Pré-dossier PC garde sa route ZIP). Les routes
anciennes (Banquier, Argumentaire, Projet) redirigent vers le document équivalent — le Financier.
La page publique Flash est inchangée côté paiement ; c'est sa LIVRAISON qui bascule sur le Dossier
sans la section 9 (cf. facturation._flash_fulfill)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.documents")
router = APIRouter(tags=["documents"])


def get_db():
    from .app import get_db as _g
    yield from _g()


def _mention_marque(html: str) -> str:
    """Attribution imprimée sur chaque page (position:fixed) — « Généré via LABUSE pour <raison> »,
    sans « pour » quand la marque blanche n'est pas résolue (M73 C6)."""
    from ..config import get_settings
    s = get_settings()
    pour = "" if (s.raison_sociale or "").strip() in ("", "Pilote LABUSE") else f" pour {s.raison_sociale}"
    mention = (f'<div style="position:fixed;bottom:2mm;right:0;font-size:7pt;color:#5F6C65;'
               f'font-family:Inter,sans-serif;">Généré via LABUSE{pour}</div>')
    return html.replace("</body>", mention + "</body>")


def rendre_document(db, idu: str, request: Request, document: str, *,
                    forms: bool = False, marque: bool = True) -> Response:
    """Assemble un document par le builder unique et le rend en PDF. `forms=True` : champs
    remplissables (Apporteur). `marque=True` : mention d'attribution du compte."""
    from ..exports import builder
    from ..exports.rendu import render_pdf
    from ..quota import porte_export
    from .app import parcel_fiche
    from .tenant import current_compte
    porte_export(request, db)
    try:
        fiche = parcel_fiche(idu, db=db, request=request)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    try:
        res = builder.construire(db, idu, document, fiche=fiche, compte_id=current_compte(request))
    except builder.DocumentNonEtablissable as exc:
        # RECETTE-5 (V18b) — le document ne se génère pas ; on rend 422 + la liste des manques,
        # que l'écran affiche (« il manque : … ») au lieu de télécharger des pages vides.
        raise HTTPException(status_code=422, detail={
            "erreur": "document_non_etablissable",
            "message": "Ce document ne peut pas être établi : il manque des éléments indispensables.",
            "manques": exc.manques,
        })
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        # RECETTE-7 (C1) — un ÉCHEC TECHNIQUE n'est PAS une donnée manquante : on LOGUE la trace
        # (pour lire la cause) et on rend une erreur DISTINCTE (500, sans « manques ») — l'écran la
        # dit comme telle, jamais sous le bandeau « il manque : ».
        log.exception("document %s %s : échec technique de génération", document, idu)
        raise HTTPException(status_code=500, detail={
            "erreur": "erreur_technique",
            "message": "Le document n'a pas pu être généré (erreur technique).",
        })
    html = _mention_marque(res.html) if marque else res.html
    try:
        pdf = render_pdf(html, forms=forms)
    except Exception as exc:  # noqa: BLE001 — le rendu PDF (WeasyPrint) peut échouer : dit comme technique.
        log.exception("document %s %s : échec du rendu PDF", document, idu)
        raise HTTPException(status_code=500, detail={
            "erreur": "erreur_technique",
            "message": "Le document n'a pas pu être rendu (erreur technique).",
        })
    log.info("document %s %s généré (%s)", document, idu, res.numero)
    # RECETTE-5 (V17) — nom de fichier HUMAIN (« Dossier financier — FI-….pdf ») : le titre du document
    # (point unique builder.titre_document) + le numéro. Fallback ASCII (`filename=`) sur le numéro seul,
    # nom accentué en `filename*` (RFC 5987) pour les navigateurs.
    from urllib.parse import quote
    nom = f"{builder.titre_document(document)} — {res.numero}.pdf"
    dispo = f'inline; filename="{res.numero}.pdf"; filename*=UTF-8\'\'{quote(nom)}'
    # RECETTE-8 W19 — 🔴 l'URL du document est STABLE (/financier/{idu}.pdf, sans jeton) : le
    # navigateur (et tout proxy) mettait la PREMIÈRE réponse en cache et la resservait telle quelle
    # aux téléchargements suivants → une saisie modifiée ne changeait pas le PDF (le back, lui, relit
    # le questionnaire et régénère à chaque appel — prouvé, deux prix ⇒ deux HTML). `no-store`
    # interdit toute mise en cache : chaque téléchargement reflète la dernière saisie.
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": dispo,
                             "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                             "Pragma": "no-cache"})


@router.get("/financier/{idu}.pdf")
def financier_pdf(idu: str, request: Request, db: Session = Depends(get_db)) -> Response:
    return rendre_document(db, idu, request, "financier")


@router.get("/apporteur/{idu}.pdf")
def apporteur_pdf(idu: str, request: Request, db: Session = Depends(get_db)) -> Response:
    return rendre_document(db, idu, request, "apporteur", forms=True, marque=False)


# ── DOCS-1 (Lot C) — les 3 nouveaux documents : miroirs des outils Gabarit, Comparer, Étude de zone. ──
def _pdf_response(res, document: str, *, marque: bool = True) -> Response:
    """Rend un ResultatDoc en PDF (WeasyPrint) avec la même enveloppe que les 4 documents existants :
    mention d'attribution, nom de fichier humain, no-store."""
    from ..exports import builder
    from ..exports.rendu import render_pdf
    from urllib.parse import quote
    html = _mention_marque(res.html) if marque else res.html
    try:
        pdf = render_pdf(html)
    except Exception:  # noqa: BLE001
        log.exception("document %s : échec du rendu PDF", document)
        raise HTTPException(status_code=500, detail={"erreur": "erreur_technique",
                            "message": "Le document n'a pas pu être rendu (erreur technique)."})
    nom = f"{builder.titre_document(document)} — {res.numero}.pdf"
    dispo = f'inline; filename="{res.numero}.pdf"; filename*=UTF-8\'\'{quote(nom)}'
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": dispo,
                             "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                             "Pragma": "no-cache"})


@router.get("/gabarit/{idu}.pdf")
def gabarit_pdf(idu: str, request: Request, db: Session = Depends(get_db)) -> Response:
    """Le Gabarit, sortie seule de l'enveloppe réglementaire. 422 + message si « Calcul incomplet »."""
    from ..exports import builder
    from ..quota import porte_export
    from .. import cadastre_disparue as _cd
    porte_export(request, db)
    # CHASSE-DONNEES-FIX-1 (Lot 2) — parcelle disparue du cadastre : le Gabarit REFUSE (jamais une
    # enveloppe réglementaire sur une parcelle sortie du cadastre).
    _disp = _cd.info_disparue(db, idu)
    if _disp:
        raise HTTPException(status_code=422, detail={
            "erreur": "parcelle_disparue", "message": _cd.phrase_disparue(_disp)})
    try:
        res = builder.construire_gabarit(db, idu)
    except builder.DocumentNonEtablissable as exc:
        raise HTTPException(status_code=422, detail={
            "erreur": "document_non_etablissable",
            "message": "Ce document ne peut pas être établi : il manque des éléments indispensables.",
            "manques": exc.manques})
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        log.exception("gabarit %s : échec technique", idu)
        raise HTTPException(status_code=500, detail={"erreur": "erreur_technique",
                            "message": "Le document n'a pas pu être généré (erreur technique)."})
    return _pdf_response(res, "gabarit")


@router.get("/comparatif.pdf")
def comparatif_pdf(idus: str, request: Request, db: Session = Depends(get_db)) -> Response:
    """Le Comparatif, miroir de /compare : 2-3 parcelles en colonnes (page paysage). `idus` = IDU
    séparés par des virgules (2 obligatoires)."""
    from ..exports import builder
    from ..quota import porte_export
    from .. import cadastre_disparue as _cd
    ids = [x.strip() for x in (idus or "").split(",") if x.strip()][:3]
    if len(ids) < 2:
        raise HTTPException(422, "au moins deux parcelles sont requises")
    porte_export(request, db)
    # CHASSE-DONNEES-FIX-1 (Lot 2) — le Comparatif REFUSE de composer si l'une des parcelles est
    # disparue du cadastre (il la présentait comme vivante, ou servait sa remplaçante en silence).
    _disparues = [i for i in ids if _cd.info_disparue(db, i)]
    if _disparues:
        raise HTTPException(status_code=422, detail={
            "erreur": "parcelle_disparue",
            "message": "Parcelle(s) disparue(s) du cadastre : " + ", ".join(_disparues)
                       + " — le comparatif ne peut pas être composé."})
    try:
        from .app import compare as _compare_fn
        data = _compare_fn(idus=",".join(ids), db=db)
        res = builder.construire_comparatif(ids, data.get("parcels") or [])
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        log.exception("comparatif %s : échec technique", ids)
        raise HTTPException(status_code=500, detail={"erreur": "erreur_technique",
                            "message": "Le document n'a pas pu être généré (erreur technique)."})
    return _pdf_response(res, "comparatif")


@router.get("/etude-zone.pdf")
def etude_zone_pdf(idu: str, request: Request, rayon_km: float = 2.0,
                   sous_destination: str | None = None,
                   db: Session = Depends(get_db)) -> Response:
    """L'Étude de zone, miroir de /outils/etude-zone en mode rayon : carte du périmètre + 7 sections.
    RECETTE-OUTILS-3 (S3) — `sous_destination` (activité choisie dans la fenêtre Docs) : le PDF affiche
    l'activité et son verdict par zone PLU (autorisé / sous condition / interdit / en calibration),
    exactement comme l'outil — le menu « Activité » MODIFIE la lecture de la zone."""
    from ..exports import builder
    from ..quota import porte_export
    porte_export(request, db)
    try:
        from .app import EtudeZoneIn, etude_zone as _etude_zone_fn
        zone = _etude_zone_fn(EtudeZoneIn(idu=idu, rayon_km=rayon_km,
                                          sous_destination=(sous_destination or None)), db)
        # DOCS-COHERENCE-1 (recette Vic) — le « Prix médian du bâti » de l'Étude de zone décrit la
        # fenêtre RÉELLE du prix lu dans la fiche (prix_ancien : médiane + n + rayon, « 3 602 €/m² —
        # 15 ventes à moins de 1 000 m »), identique au Comparatif ; « Ventes (12 mois) » reste à part.
        try:
            from ..marche_service import DVF_BANQUIER_ADAPTATIF, marche_dvf
            _pa = marche_dvf(db, idu, profil=DVF_BANQUIER_ADAPTATIF)
            if _pa and _pa.get("median"):
                zone.setdefault("marche", {})["prix_ancien"] = _pa
        except Exception:  # noqa: BLE001 — le prix de la fiche est un plus, jamais un bloqueur
            pass
        res = builder.construire_etude_zone(idu, rayon_km, zone, _zone_map_html(db, zone))
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        log.exception("etude-zone %s : échec technique", idu)
        raise HTTPException(status_code=500, detail={"erreur": "erreur_technique",
                            "message": "Le document n'a pas pu être généré (erreur technique)."})
    return _pdf_response(res, "etude-zone")


def _zone_map_html(db, zone: dict) -> str:
    """Carte du périmètre (page 1) : ortho IGN + géométrie de la zone, MÊME composant que l'Apporteur
    (plan_ortho). Best-effort : réseau/géométrie absents → cadre neutre légendé (jamais d'erreur)."""
    import json
    geom = (zone or {}).get("geom")
    if geom:
        try:
            from .plan_situation import plan_ortho
            from ..flash.report import storage_dir
            res = plan_ortho(json.dumps(geom), cache_dir=storage_dir() / "tiles", zoom_delta=0, zoom_max=17)
            if res.get("ok"):
                import base64
                img = "data:image/jpeg;base64," + base64.b64encode(res["jpeg"]).decode()
                cap = res.get("attribution") or ""
                return (f'<img class="zone-map" src="{img}" alt="Carte du périmètre">'
                        + (f'<div class="zone-echelle">{cap}</div>' if cap else ""))
        except Exception:  # noqa: BLE001 — la carte est un plus, jamais un bloqueur du document
            pass
    return '<div class="zone-map-ph">Carte du périmètre (fond cartographique momentanément indisponible)</div>'


# ── ANNONCE-3 — « Analyse d'annonce » : deux entrées (adresse → parcelle, lien → commune), MÊMES
#    chemins que l'outil « Analyser une annonce ». Le PDF sorti de l'outil et celui sorti de Docs sont
#    identiques (mêmes routes, mêmes endpoints, mêmes chiffres que l'écran).
@router.get("/analyse-annonce/{idu}.pdf")
def analyse_annonce_parcelle_pdf(idu: str, request: Request, db: Session = Depends(get_db)) -> Response:
    """Variante PARCELLE (entrée adresse) : rapport parcelle (tuiles + estimation + foncier + plan de
    situation). Lit les MÊMES endpoints que l'écran (fiche, exposition, classement du run servi)."""
    from ..exports import builder
    from ..quota import porte_export
    porte_export(request, db)
    try:
        res = builder.construire_analyse_annonce_parc(db, idu, request=request)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        log.exception("analyse-annonce parcelle %s : échec technique", idu)
        raise HTTPException(status_code=500, detail={"erreur": "erreur_technique",
                            "message": "Le document n'a pas pu être généré (erreur technique)."})
    return _pdf_response(res, "analyse-annonce")


#: ANNONCE-3 — message d'échec IDENTIQUE à l'outil (AnalyserAnnonce.tsx `messageErreur`) : la lecture du
#: lien passe par la MÊME voie (Radar d'abord, sinon fetch) ; en cas d'échec le PDF ne se génère pas et
#: l'écran affiche cette phrase (via le hook useOuvrirDocument → detail.message), jamais un code HTTP.
_ANNONCE_ECHEC = {
    "url_bloquee": "Cette annonce n'a pas encore été relevée par LABUSE et Leboncoin bloque sa lecture "
                   "automatique. Entrez l'adresse du bien pour l'analyser.",
    "url_illisible": "Cette page n'est pas une annonce exploitable. Entrez l'adresse du bien pour l'analyser.",
    "url_invalide": "Collez un lien d'annonce Leboncoin, ou entrez l'adresse du bien pour l'analyser.",
}


@router.get("/analyse-annonce.pdf")
def analyse_annonce_lien_pdf(url: str, request: Request, db: Session = Depends(get_db)) -> Response:
    """Variante COMMUNE (entrée lien) : rapport commune (ce que dit l'annonce + prix face au marché +
    la commune). MÊME chemin que l'outil : Radar D'ABORD, sinon fetch one-shot, sinon le MÊME message
    d'échec (422 + phrase, pas de code HTTP à l'écran)."""
    from ..exports import builder
    from ..quota import porte_export
    from ..pige.api import AnnonceAnalyseIn, radar_annonce_analyser
    porte_export(request, db)
    res_annonce = radar_annonce_analyser(AnnonceAnalyseIn(url=url))
    if not res_annonce.get("ok") or not res_annonce.get("annonce"):
        erreur = res_annonce.get("erreur")
        raise HTTPException(status_code=422, detail={
            "erreur": erreur or "url_illisible",
            "message": _ANNONCE_ECHEC.get(erreur, "La lecture de l'annonce a échoué. "
                       "Entrez l'adresse du bien pour l'analyser.")})
    # ANNONCE-5 — `radar_annonce_analyser` renvoie désormais le RAPPORT ENRICHI (annonce normalisée +
    # lectures bâti/foncière + bloc commune complet, PLU/aléas inclus). Le builder le rend tel quel : le
    # PDF (outil ET Docs) == l'écran, même point de données, plus aucun appel commune_contexte ici.
    try:
        res = builder.construire_analyse_annonce_lien(res_annonce)
    except Exception:  # noqa: BLE001
        log.exception("analyse-annonce lien : échec technique")
        raise HTTPException(status_code=500, detail={"erreur": "erreur_technique",
                            "message": "Le document n'a pas pu être généré (erreur technique)."})
    return _pdf_response(res, "analyse-annonce")


# RECETTE-3 (T2, décision Vic) — le document Résumé est SUPPRIMÉ : sa route /resume/{idu}.pdf
# n'existe plus (aucun autre document ne l'appelait ; l'ex-redirection export.pdf pointe désormais
# vers le Dossier). Reste Dossier · Financier · Apporteur (+ Flash via facturation, Pré-dossier ZIP).


# ── redirections des routes anciennes → le document équivalent (Banquier + Argumentaire → Financier).
@router.get("/dossier-banquier/{idu}.pdf")
def _redir_banquier(idu: str) -> RedirectResponse:
    return RedirectResponse(f"/financier/{idu}.pdf", status_code=308)


@router.get("/argumentaire/{idu}.pdf")
def _redir_argumentaire(idu: str) -> RedirectResponse:
    return RedirectResponse(f"/financier/{idu}.pdf", status_code=308)
