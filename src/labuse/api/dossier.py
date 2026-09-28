"""« Dossier parcelle » PDF (mandat wave-adresses, Lot 4) — usage interne de l'abonné.

Réutilise le générateur du module Flash (branche feat/module-flash) en DÉPENDANCE
SOUPLE : si le module n'est pas déployé, l'endpoint répond 501 avec un message
honnête — les fondations (quota, gating plan, bouton front) restent en place et
s'activent au merge du générateur. Différences avec Flash : réservé aux abonnés
(auth globale), quota mensuel (config, Essentiel) / illimité (Intégral — gating
stubbé Phase 0), mention « Généré via LABUSE pour [raison sociale] », pas de vente.
Usage cible : comité d'engagement, banque, client final de l'abonné.
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import plans
from ..config import get_settings

log = logging.getLogger("labuse.dossier")
router = APIRouter(prefix="/dossier", tags=["dossier"])


def get_db():
    from .app import get_db as _g
    yield from _g()


def _quota_mois(db: Session, sujet: str) -> int:
    """Dossiers générés par ce sujet depuis le début du mois (usage_compteurs).
    Jour de référence = heure LOCALE python (cohérent avec protection._aujourdhui)."""
    premier = date.today().replace(day=1)
    return int(db.execute(text(
        "SELECT COALESCE(sum(n), 0) FROM usage_compteurs "
        "WHERE kind = 'dossier' AND sujet = :s AND jour >= :p"),
        {"s": sujet, "p": premier}).scalar() or 0)


@router.get("/statut")
def dossier_statut(request: Request, db: Session = Depends(get_db)) -> dict:
    """Disponibilité + quota restant — le front adapte le bouton (grisé/compteur)."""
    from .protection import sujet_quota
    s = get_settings()
    try:
        import labuse.flash  # noqa: F401
        generateur = True
    except ImportError:
        generateur = False
    illimite = plans.acces("dossier_illimite")
    utilises = _quota_mois(db, sujet_quota(request))   # M-K (P2-38) : quota dossiers par compte
    return {"disponible": generateur,
            "raison": None if generateur else
            "générateur de rapports non déployé (mandat module-flash à merger)",
            "plan": plans.plan_courant(), "illimite": illimite,
            "quota_mois": None if illimite else s.dossier_quota_mois,
            "utilises_mois": utilises,
            "restants": None if illimite else max(0, s.dossier_quota_mois - utilises)}


@router.get("/{idu}.pdf")
def dossier_pdf(idu: str, request: Request, carte: bool = True,
                db: Session = Depends(get_db)) -> Response:
    """PDF brandé de LA parcelle (template Flash allégé — pas de page tarifaire).
    `carte=false` : sans fond cartographique (tests, environnements sans réseau)."""
    from .protection import sujet_quota
    s = get_settings()
    sujet = sujet_quota(request)          # M-K (P2-38) : quota mensuel dossiers épinglé au compte

    if not plans.acces("dossier_parcelle"):          # stub : toujours vrai aujourd'hui
        raise HTTPException(403, detail=plans.refus("dossier_parcelle"))
    # M23-E : PORTE DE QUOTA abonné (30/j Intégral · 200/j Illimité usage loyal ;
    # Flash HORS quota) — 429 honnête au dépassement, passant sans session (pilote).
    from ..quota import porte_export
    porte_export(request, db)
    if not plans.acces("dossier_illimite"):
        utilises = _quota_mois(db, sujet)
        if utilises >= max(1, s.dossier_quota_mois):
            raise HTTPException(429, detail={
                "detail": f"Quota mensuel de Dossiers parcelle atteint "
                          f"({s.dossier_quota_mois}/mois, plan Essentiel).",
                **plans.refus("dossier_illimite")})

    # EXPORTS-2 lot 8 — le Dossier est servi par le BUILDER UNIQUE (src/labuse/exports), plus le
    # gabarit Flash. Mention d'attribution du compte imprimée sur chaque page (M73 C6/C7).
    from ..exports import builder
    from ..exports.rendu import render_pdf
    from .app import parcel_fiche
    from .tenant import current_compte
    try:
        fiche = parcel_fiche(idu, db=db, request=request)
    except ValueError as exc:                    # parcelle inconnue
        raise HTTPException(404, str(exc))
    res = builder.construire(db, idu, "dossier", fiche=fiche, compte_id=current_compte(request))
    _pour = "" if (s.raison_sociale or "").strip() in ("", "Pilote LABUSE") else f" pour {s.raison_sociale}"
    # EXPORTS-FIX-1-BIS point 7 — la mention d'attribution vit dans un BLOC DE MARGE @page
    # (@bottom-center, contenu STATIQUE qui SE REND dans ce WeasyPrint, contrairement à
    # string()/element()) : jamais dans le flux → aucun chevauchement possible (badge « sourcé »,
    # titres). Le div `position:fixed` (F1) qui chevauchait encore est retiré.
    _txt = ("Généré via LABUSE" + _pour).replace("\\", "").replace('"', "'")
    style = ('<style>@page { @bottom-center { content: "' + _txt + '"; '
             'font: 7pt "Inter","DejaVu Sans",sans-serif; color: #5F6C65; } }</style>')
    pdf = render_pdf(res.html.replace("</head>", style + "</head>"))

    from .protection import _aujourdhui
    db.execute(text(
        "INSERT INTO usage_compteurs (jour, sujet, kind, n) "
        "VALUES (:j, :s, 'dossier', 1) "
        "ON CONFLICT (jour, sujet, kind) DO UPDATE SET n = usage_compteurs.n + 1"),
        {"j": _aujourdhui(), "s": sujet})
    log.info("dossier parcelle %s généré (%s)", idu, res.numero)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'inline; filename="dossier_labuse_{idu}.pdf"',
                             # RECETTE-8 W19 — URL stable + PDF regénéré à la requête : jamais de
                             # cache navigateur/proxy qui resservirait une version périmée.
                             "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                             "Pragma": "no-cache"})
