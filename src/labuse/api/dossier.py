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
    """Dossiers générés par ce sujet depuis le début du mois (usage_compteurs)."""
    return int(db.execute(text(
        "SELECT COALESCE(sum(n), 0) FROM usage_compteurs "
        "WHERE kind = 'dossier' AND sujet = :s AND jour >= date_trunc('month', CURRENT_DATE)"),
        {"s": sujet}).scalar() or 0)


@router.get("/statut")
def dossier_statut(request: Request, db: Session = Depends(get_db)) -> dict:
    """Disponibilité + quota restant — le front adapte le bouton (grisé/compteur)."""
    from .protection import sujet_de
    s = get_settings()
    try:
        import labuse.flash  # noqa: F401
        generateur = True
    except ImportError:
        generateur = False
    illimite = plans.acces("dossier_illimite")
    utilises = _quota_mois(db, sujet_de(request))
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
    from .protection import sujet_de
    s = get_settings()
    sujet = sujet_de(request)

    if not plans.acces("dossier_parcelle"):          # stub : toujours vrai aujourd'hui
        raise HTTPException(403, detail=plans.refus("dossier_parcelle"))
    if not plans.acces("dossier_illimite"):
        utilises = _quota_mois(db, sujet)
        if utilises >= max(1, s.dossier_quota_mois):
            raise HTTPException(429, detail={
                "detail": f"Quota mensuel de Dossiers parcelle atteint "
                          f"({s.dossier_quota_mois}/mois, plan Essentiel).",
                **plans.refus("dossier_illimite")})

    try:
        from labuse.flash.report import render_report_html
    except ImportError:
        raise HTTPException(501, detail=(
            "Le générateur de rapports (module Flash) n'est pas déployé sur cette "
            "instance — fonctionnalité active au merge de feat/module-flash."))

    ref = f"DP-{date.today():%Y%m%d}-{idu[-4:]}"
    try:
        html = render_report_html(db, idu, order_ref=ref, with_map=carte,
                                  produit="Dossier parcelle",
                                  produit_sous_titre="DOSSIER PARCELLE · usage interne")
    except ValueError as exc:                    # parcelle inconnue
        raise HTTPException(404, str(exc))
    # Mention d'attribution imprimée sur CHAQUE page (position:fixed en WeasyPrint).
    mention = (f'<div style="position:fixed; bottom:2mm; right:0; font-size:7pt;'
               f' color:#5F6C65; font-family: Inter, sans-serif;">'
               f'Généré via LABUSE pour {s.raison_sociale}</div>')
    html = html.replace("</body>", mention + "</body>")

    from weasyprint import HTML
    pdf = HTML(string=html).write_pdf()

    db.execute(text(
        "INSERT INTO usage_compteurs (jour, sujet, kind, n) "
        "VALUES (CURRENT_DATE, :s, 'dossier', 1) "
        "ON CONFLICT (jour, sujet, kind) DO UPDATE SET n = usage_compteurs.n + 1"),
        {"s": sujet})
    log.info("dossier parcelle %s généré (%s)", idu, ref)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'inline; filename="dossier_labuse_{idu}.pdf"'})
