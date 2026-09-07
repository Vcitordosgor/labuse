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
    res = builder.construire(db, idu, document, fiche=fiche, compte_id=current_compte(request))
    html = _mention_marque(res.html) if marque else res.html
    pdf = render_pdf(html, forms=forms)
    log.info("document %s %s généré (%s)", document, idu, res.numero)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{res.numero}.pdf"'})


@router.get("/financier/{idu}.pdf")
def financier_pdf(idu: str, request: Request, db: Session = Depends(get_db)) -> Response:
    return rendre_document(db, idu, request, "financier")


@router.get("/apporteur/{idu}.pdf")
def apporteur_pdf(idu: str, request: Request, db: Session = Depends(get_db)) -> Response:
    return rendre_document(db, idu, request, "apporteur", forms=True, marque=False)


@router.get("/resume/{idu}.pdf")
def resume_pdf(idu: str, request: Request, db: Session = Depends(get_db)) -> Response:
    return rendre_document(db, idu, request, "resume")


# ── redirections des routes anciennes → le document équivalent (Banquier + Argumentaire → Financier).
@router.get("/dossier-banquier/{idu}.pdf")
def _redir_banquier(idu: str) -> RedirectResponse:
    return RedirectResponse(f"/financier/{idu}.pdf", status_code=308)


@router.get("/argumentaire/{idu}.pdf")
def _redir_argumentaire(idu: str) -> RedirectResponse:
    return RedirectResponse(f"/financier/{idu}.pdf", status_code=308)
