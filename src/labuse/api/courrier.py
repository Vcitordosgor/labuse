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

# Ponctuation typographique → équivalents latin-1 (fidélité du PDF au texte affiché ; « — »/« ’ »
# ne doivent pas devenir « ? »). « « » » gardent leurs guillemets français (déjà latin-1).
_LATIN1_PUNCT = {ord(a): b for a, b in {
    "’": "'", "‘": "'", "“": '"', "”": '"', "—": "-", "–": "-", "…": "...", " ": " ", " ": " ",
}.items()}


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


# COURRIER-SERVICE (refonte 13 outils) — la route « /demande » et la table `courrier_demandes`
# REVIENNENT : le client prépare (destinataires + rédaction), puis DEMANDE l'envoi à LABUSE. À chaque
# demande, Vic est notifié par les CANAUX EXISTANTS (cloche event_log `systeme` + e-mail Brevo) ; il
# rappelle, confirme le tarif au téléphone, et fait avancer le statut depuis la vue admin. Aucun envoi
# automatique, aucun prix affiché côté client (garde-fous du mandat).

def _client_label(db: Session, cid: int | None) -> str:
    if cid is None:
        return "Un client"
    nom = db.execute(text("SELECT nom FROM comptes WHERE id = :c"), {"c": cid}).scalar()
    return nom or f"Compte #{cid}"


class DemandeIn(BaseModel):
    parcelles: list[str] = Field(min_length=1, max_length=500)
    modele: str | None = None
    corps: str = Field(min_length=10, max_length=8000)
    communes: str | None = None               # récap lisible « Saint-Denis ×1 · Saint-Paul ×2 »


@router.post("/demande")
def courrier_demande(body: DemandeIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Le client DEMANDE l'envoi de N courriers. Enregistre la demande (statut « Demandé »), puis
    notifie Vic sur les canaux EXISTANTS (cloche + Brevo). La notif ne peut jamais faire échouer la
    demande (elle est déjà enregistrée)."""
    from .tenant import current_compte
    cid = current_compte(request)
    parcelles = [p.strip() for p in body.parcelles if p.strip()]
    if not parcelles:
        raise HTTPException(422, "aucune parcelle valide dans la demande.")
    d = courrier.creer_demande(db, compte_id=cid, parcelles=parcelles,
                               communes=body.communes, modele=body.modele, corps=body.corps)
    db.commit()
    client = _client_label(db, cid)
    com = f" ({body.communes})" if body.communes else ""
    titre = f"{client} demande l'envoi de {d['n']} courrier{'s' if d['n'] > 1 else ''}{com}"
    # ① CLOCHE — event_log `systeme`, compte NULL = feed pilote/admin (invisible aux clients ; jamais
    #    exclu du filtre cloche). Même patron que notifier_fraicheur.
    try:
        from .events import creer_notification
        creer_notification(db, kind="systeme", compte_id=None, source="Courrier",
                           titre=titre, detail=(body.corps or "")[:280], lien="/courrier/admin",
                           dedup=f"courrier:demande:{d['id']}", permanent=True)
        db.commit()
    except Exception:
        db.rollback()   # la notif est best-effort — la demande reste enregistrée
    # ② E-MAIL BREVO à Vic — async (ne bloque pas la requête). Destinataire = admin_email (repli from).
    try:
        from ..config import get_settings
        from ..mail import send_email_async
        s = get_settings()
        dest = s.admin_email or s.mail_from
        if dest:
            corps_mail = (f"{titre}\n\nParcelles ({d['n']}) : {', '.join(parcelles)}\n\n"
                          f"Corps du courrier :\n{body.corps}\n\n"
                          f"→ Vue admin /courrier/admin : rappeler le client, confirmer le tarif, "
                          f"puis faire avancer le statut (Demandé → Tarif confirmé → Envoyé).")
            send_email_async(dest, f"[LABUSE] {titre}", corps_mail)
    except Exception:
        pass
    return {"ok": True, **d}


@router.get("/demandes")
def courrier_demandes(request: Request, db: Session = Depends(get_db)) -> dict:
    """Les demandes DU client courant — timeline de statut (Demandé → Tarif confirmé → Envoyé)."""
    from .tenant import current_compte
    return {"demandes": courrier.demandes_de(db, current_compte(request))}


@router.get("/admin/demandes")
def courrier_admin_demandes(request: Request, statut: str | None = None,
                            db: Session = Depends(get_db)) -> dict:
    """Vue admin (Vic) : liste des demandes (client, n, communes, corps, date, statut)."""
    from . import auth
    auth.exiger_admin(request)
    return {"demandes": courrier.demandes_admin(db, statut), "statuts": list(courrier.STATUTS_DEMANDE)}


class StatutIn(BaseModel):
    statut: str


@router.post("/admin/demandes/{demande_id}/statut")
def courrier_admin_statut(demande_id: int, body: StatutIn, request: Request,
                          db: Session = Depends(get_db)) -> dict:
    """Vic fait avancer le statut d'une demande (après le rappel tarif). Le client le voit via
    /courrier/demandes (sa timeline)."""
    from . import auth
    auth.exiger_admin(request)
    try:
        d = courrier.set_statut_demande(db, demande_id, body.statut)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    return {"ok": True, **d}


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
        # Les polices de base fpdf sont latin-1 : la ponctuation typographique (’ — … « ») deviendrait
        # « ? ». On la ramène à ses équivalents latin-1 AVANT l'encodage → le PDF reste FIDÈLE au
        # courrier affiché (apostrophes, tirets), jamais un « ? » à la place.
        safe = ligne.translate(_LATIN1_PUNCT).encode("latin-1", "replace").decode("latin-1")
        # LARGEUR EXPLICITE (epw = largeur utile) et JAMAIS w=0 : sous fpdf2 2.8.7, un
        # multi_cell(w=0, "") sur une ligne VIDE (les \n\n entre paragraphes) laisse le curseur
        # à la marge droite → le multi_cell suivant a 0 largeur → FPDFException « Not enough
        # horizontal space ». Avec epw, la ligne vide avance proprement d'une ligne.
        pdf.multi_cell(pdf.epw, 6, safe)
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
