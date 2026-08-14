"""API courrier postal (Lot 2B) — voir src/labuse/courrier.py pour la doctrine.

Le front interroge /courrier/statut : provider stub → le bouton « Envoyer un courrier »
N'EST PAS AFFICHÉ (jamais de bouton mort). Aucun envoi sans la case de responsabilité.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import courrier

router = APIRouter(prefix="/courrier", tags=["courrier"])


def get_db():
    from .app import get_db as _g
    yield from _g()


def ensure_tables(engine) -> None:
    courrier.ensure_tables(engine)


@router.get("/statut")
def courrier_statut(db: Session = Depends(get_db)) -> dict:
    """Disponibilité + tarif — le front n'affiche le bouton QUE si disponible=true."""
    prov = courrier.provider_actif()
    return {"disponible": prov != "stub", "provider": prov, "tarif": courrier.tarif(),
            "raison": None if prov != "stub" else
            "L'envoi postal n'est pas encore disponible — la demande est enregistrée."}


class EnvoiIn(BaseModel):
    destinataires: list[dict] = Field(min_length=1, max_length=500)  # [{idu, adresse}]
    modele: str | None = None                 # slug du gabarit utilisé (traçabilité)
    assume_contenu: bool = False              # case OBLIGATOIRE (responsabilité émetteur)


@router.post("/envois")
def courrier_envoyer(body: EnvoiIn, request: Request, db: Session = Depends(get_db)) -> dict:
    from .protection import sujet_de
    mal_formes = [d for d in body.destinataires if not (d.get("adresse") or "").strip()]
    if mal_formes:
        raise HTTPException(422, f"{len(mal_formes)} destinataire(s) sans adresse.")
    try:
        return courrier.envoyer(db, sujet_de(request), body.destinataires,
                                modele=body.modele, assume_contenu=body.assume_contenu)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


# M82 (option B, arbitrage Vic) — la route « /demande » et la table dead-letter `courrier_demandes`
# ont été RETIRÉES : aucune promesse d'envoi ni de traitement (personne ne lisait la file). L'outil
# ne fait plus que GÉNÉRER le courrier, téléchargeable en PDF (voir /pdf) — le client l'envoie lui-même.
# Le canal d'envoi prestataire (/envois, courrier.envoyer) reste en code, DORMANT, pour rouvrir l'option
# A quand un client le demandera. La table physique `courrier_demandes` (~2 lignes) peut être droppée
# en maintenance ; plus aucune écriture ne la vise.


class PdfIn(BaseModel):
    idu: str | None = None
    motif: str = "standard"
    texte: str = Field(min_length=10, max_length=8000)


@router.post("/pdf")
def courrier_pdf(body: PdfIn) -> Response:
    """M82 : rend le courrier généré en PDF TÉLÉCHARGEABLE — le client l'imprime/l'envoie lui-même
    (utile même sans traitement automatique). Adressage générique, aucune identité de propriétaire."""
    from fpdf import FPDF
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, margin=20)
    pdf.set_margins(20, 20, 20)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, "LABUSE", ln=1)
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(4)
    for ligne in body.texte.split("\n"):
        safe = ligne.encode("latin-1", "replace").decode("latin-1")   # polices de base = latin-1
        pdf.multi_cell(0, 6, safe)
    data = bytes(pdf.output())
    nom = (body.idu or "parcelle").replace("/", "-")
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="courrier-{nom}.pdf"'})


@router.get("/envois")
def courrier_suivi(request: Request, db: Session = Depends(get_db)) -> dict:
    """Suivi des envois du sujet courant (statuts prestataire)."""
    from .protection import sujet_de
    rows = [dict(r) for r in db.execute(text(
        "SELECT id, ts, idu, adresse, statut, provider, prix_eur, modele "
        "FROM courrier_envois WHERE sujet = :s ORDER BY ts DESC LIMIT 200"),
        {"s": sujet_de(request)}).mappings()]
    return {"envois": rows, "n": len(rows)}
