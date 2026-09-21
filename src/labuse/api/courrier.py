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
    # GB-023 — œ/Œ absentes de latin-1 (police fpdf de base) → décomposées AVANT l'encodage
    # (cœur→coeur), jamais un « ? » à l'écran. (æ/Æ sont, elles, DANS latin-1 → on n'y touche pas :
    # « ex æquo » doit rester « ex æquo ».)
    "œ": "oe", "Œ": "OE",
    "’": "'", "‘": "'", "“": '"', "”": '"', "—": "-", "–": "-", "…": "...", " ": " ", " ": " ",
}.items()}


def get_db():
    from .app import get_db as _g
    yield from _g()


def ensure_tables(engine) -> None:
    courrier.ensure_tables(engine)


@router.get("/statut")
def courrier_statut(request: Request, db: Session = Depends(get_db)) -> dict:
    """Disponibilité + tarif — le front n'affiche le bouton QUE si disponible=true.
    OUTILS-FIX-4 D1/D2 — le front interroge ce statut À L'OUVERTURE de l'outil Courrier : l'état du
    service (disponible/indisponible) et le PLAFOND du jour (avec ce qu'il reste) sont désormais connus
    AVANT toute saisie, plus seulement à travers l'erreur 422 au moment d'envoyer. Le plafond quotidien
    (`courrier_max_jour`, celui qui déclenche le 422) et le nombre déjà envoyé aujourd'hui pour ce sujet
    sont le POINT DE VÉRITÉ back — le front n'affiche que ce qu'il reçoit."""
    from .protection import sujet_de
    from ..config import get_settings
    prov = courrier.provider_actif()
    plafond = max(1, int(get_settings().courrier_max_jour))
    try:
        envoyes = courrier.envois_du_jour(db, sujet_de(request))
    except Exception:  # noqa: BLE001 — le plafond est informatif, jamais un 500
        envoyes = 0
    return {"disponible": prov != "stub", "provider": prov, "tarif": courrier.tarif(),
            "raison": None if prov != "stub" else
            "L'envoi postal n'est pas encore disponible — la demande est enregistrée.",
            "plafond_jour": plafond, "envoyes_jour": envoyes, "reste_jour": max(0, plafond - envoyes)}


class EnvoiIn(BaseModel):
    destinataires: list[dict] = Field(min_length=1, max_length=500)  # [{idu, adresse}]
    modele: str | None = None                 # slug du gabarit utilisé (traçabilité)
    assume_contenu: bool = False              # case OBLIGATOIRE (responsabilité émetteur)


@router.post("/envois")
def courrier_envoyer(body: EnvoiIn, request: Request, db: Session = Depends(get_db)) -> dict:
    # OBSOLÈTE (CONNEXIONS-2 Lot 4, KO-6) — chemin d'envoi DIRECT `courrier_envois`, scopé session/IP,
    # DORMANT (provider stub → bouton masqué, aucun front ne l'appelle). Le système Courrier SERVI est
    # `courrier_demandes` (le client prépare, LABUSE dépose). On garde ce chemin (Merci Facteur futur)
    # mais il devra être RE-SCOPÉ au compte et rattaché à la demande avant activation (mandat d'hygiène).
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


def _valider_pipeline_entry(db: Session, cid: int | None, pe_id: int | None) -> int | None:
    """KO-6 — n'accepte un pipeline_entry_id QUE s'il appartient au compte courant (SEC-IDOR). Sinon None."""
    if pe_id is None:
        return None
    from sqlalchemy import text as _t
    ok = db.execute(_t(
        "SELECT 1 FROM pipeline_entries WHERE id = :id AND compte_id IS NOT DISTINCT FROM :c"),
        {"id": pe_id, "c": cid}).scalar()
    return pe_id if ok else None


class DemandeIn(BaseModel):
    parcelles: list[str] = Field(min_length=1, max_length=500)
    modele: str | None = None
    corps: str = Field(min_length=10, max_length=8000)
    communes: str | None = None               # récap lisible « Saint-Denis ×1 · Saint-Paul ×2 »
    # CONNEXIONS-2 Lot 4 (KO-6) — rattachement à la piste/projet d'origine (courrier depuis le CRM).
    pipeline_entry_id: int | None = None
    projet_id: int | None = None


@router.post("/demande")
def courrier_demande(body: DemandeIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Le client DEMANDE l'envoi de N courriers. Enregistre la demande (statut « À déposer »), puis
    notifie Vic sur les canaux EXISTANTS (cloche + Brevo). La notif ne peut jamais faire échouer la
    demande (elle est déjà enregistrée)."""
    from .tenant import current_compte
    cid = current_compte(request)
    parcelles = [p.strip() for p in body.parcelles if p.strip()]
    if not parcelles:
        raise HTTPException(422, "aucune parcelle valide dans la demande.")
    # KO-6 — si la demande vient d'une piste, on ne rattache QU'À une piste DU compte (sinon on ignore
    # le lien, jamais un rattachement croisé). Idem projet.
    pe_id = _valider_pipeline_entry(db, cid, body.pipeline_entry_id)
    d = courrier.creer_demande(db, compte_id=cid, parcelles=parcelles,
                               communes=body.communes, modele=body.modele, corps=body.corps,
                               pipeline_entry_id=pe_id, projet_id=body.projet_id)
    db.commit()
    # FIX-GB-013 — demande identique récente déjà enregistrée (double-submit / retry / 2 onglets) : on
    # renvoie l'existante SANS re-notifier Vic ni renvoyer un 2ᵉ e-mail (la 1ʳᵉ l'a déjà fait).
    if d.get("existing"):
        return {"ok": True, **d}
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
                          f"puis faire avancer le statut (À déposer → Déposé → Envoyé).")
            send_email_async(dest, f"[LABUSE] {titre}", corps_mail, contexte="Courrier")
    except Exception:
        pass
    return {"ok": True, **d}


@router.get("/demandes")
def courrier_demandes(request: Request, db: Session = Depends(get_db)) -> dict:
    """Les demandes DU client courant — timeline de statut (À déposer → Déposé → Envoyé)."""
    from .tenant import current_compte
    return {"demandes": courrier.demandes_de(db, current_compte(request))}


@router.get("/admin/demandes")
def courrier_admin_demandes(request: Request, statut: str | None = None,
                            db: Session = Depends(get_db)) -> dict:
    """Vue admin (Vic) : liste des demandes (client, n, communes, corps, date, statut)."""
    from . import auth
    auth.exiger_admin(request)
    # ADMIN-1 (AD8) — libellés servis des statuts (source unique courrier.STATUT_LIBELLES) pour les chips.
    return {"demandes": courrier.demandes_admin(db, statut), "statuts": list(courrier.STATUTS_DEMANDE),
            "statut_libelles": dict(courrier.STATUT_LIBELLES)}


class StatutIn(BaseModel):
    statut: str


#: libellés client des statuts — SOURCE UNIQUE (CONNEXIONS-2 Lot 4) : courrier.STATUT_LIBELLES.
_STATUT_LIBELLES = courrier.STATUT_LIBELLES


@router.post("/demandes/{demande_id}/statut")
def courrier_client_statut(demande_id: int, body: StatutIn, request: Request,
                           db: Session = Depends(get_db)) -> dict:
    """CONNEXIONS-2 Lot 4 (KO-6) — la CLIENTE saisit le RETOUR de SA demande : « répondu » ou « sans
    réponse » (les seuls statuts qu'elle contrôle ; le reste du cycle est côté LABUSE). Scopé compte
    (elle ne touche que SES demandes). Ferme la boucle : le retour est relu au dashboard et au Kanban."""
    from .tenant import current_compte
    cid = current_compte(request)
    try:
        d = courrier.set_statut_demande(db, demande_id, body.statut, compte_id=cid, reserve_retour=True)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    lib = _STATUT_LIBELLES.get(courrier.normaliser_statut(body.statut), body.statut)
    # trace admin : le retour du client remonte au fil Pilotage (Vic voit que la boucle est bouclée)
    try:
        from .events import creer_notification
        creer_notification(db, kind="systeme", compte_id=None, source="Courrier",
                           titre=f"Retour client sur la demande n°{demande_id} : « {lib} »",
                           detail=f"{d['n']} courrier(s){' · ' + d['communes'] if d.get('communes') else ''}",
                           dedup=f"courrier:retour:{demande_id}:{d['statut']}")
        db.commit()
    except Exception:  # noqa: BLE001 — best-effort
        db.rollback()
    return {"ok": True, **d}


@router.post("/admin/demandes/{demande_id}/statut")
def courrier_admin_statut(demande_id: int, body: StatutIn, request: Request,
                          db: Session = Depends(get_db)) -> dict:
    """Vic fait avancer le statut d'une demande (Tour de contrôle : À déposer → Déposé → Envoyé).
    Le client le voit via /courrier/demandes (sa timeline) ; DASHBOARD-V1 · D8 : chaque
    transition est JOURNALISÉE (event_log admin) + notifiée au client (cloche)."""
    from . import auth
    auth.exiger_admin(request)
    try:
        d = courrier.set_statut_demande(db, demande_id, body.statut)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    lib = _STATUT_LIBELLES.get(d["statut"], d["statut"])   # d['statut'] = canonique (legacy normalisé)
    try:
        from .events import creer_notification
        # trace admin (fil Pilotage) — dédup par (demande, statut) : jamais deux traces d'un même clic
        creer_notification(db, kind="systeme", compte_id=None, source="Courrier",
                           titre=f"Demande n°{demande_id} passée à « {lib} »",
                           detail=f"{d['n']} courrier(s){' · ' + d['communes'] if d.get('communes') else ''}",
                           dedup=f"courrier:statut:{demande_id}:{d['statut']}")
        # notification CLIENT (cloche) — il voit le même statut de son côté
        if d.get("compte_id") is not None:
            creer_notification(db, kind="systeme", compte_id=d["compte_id"], source="Courrier",
                               titre=f"Votre demande de courrier est passée à « {lib} »",
                               detail=f"{d['n']} courrier(s){' · ' + d['communes'] if d.get('communes') else ''}",
                               dedup=f"courrier:statut-client:{demande_id}:{d['statut']}")
        db.commit()
    except Exception:  # noqa: BLE001 — la trace est best-effort, la transition est déjà faite
        db.rollback()
    return {"ok": True, **d}


@router.post("/admin/demandes/deposer-tout")
def courrier_admin_deposer_tout(request: Request, db: Session = Depends(get_db)) -> dict:
    """DASHBOARD-2 (Lot 3) — « Marquer les N déposés » en bloc. Toutes les demandes À DÉPOSER passent
    à « déposé » d'un geste. Chaque transition est JOURNALISÉE (une ligne de synthèse au fil Pilotage)
    et NOTIFIÉE à chaque client concerné (cloche) — même preuve que le geste unitaire, en masse."""
    from . import auth
    auth.exiger_admin(request)
    touchees = courrier.marquer_deposes(db)
    db.commit()
    bloquees = courrier.bloquees_a_deposer(db)   # COURRIER-2 Lot 1 — opposées, laissées en l'état
    if not touchees:
        return {"ok": True, "deposes": 0, "bloquees_opposition": bloquees}
    try:
        from .events import creer_notification
        creer_notification(db, kind="systeme", compte_id=None, source="Courrier",
                           titre=f"{len(touchees)} demande(s) marquée(s) « Déposé » en bloc",
                           detail=", ".join(sorted({t["communes"] for t in touchees if t.get("communes")})) or None,
                           dedup=None)
        # une cloche par client concerné (il voit le même statut de son côté)
        for cid in sorted({t["compte_id"] for t in touchees if t.get("compte_id") is not None}):
            creer_notification(db, kind="systeme", compte_id=cid, source="Courrier",
                               titre="Votre demande de courrier est passée à « Déposé »",
                               detail=None, dedup=f"courrier:depose-bloc:{cid}")
        db.commit()
    except Exception:  # noqa: BLE001 — la trace est best-effort, le dépôt est déjà fait
        db.rollback()
    return {"ok": True, "deposes": len(touchees), "bloquees_opposition": bloquees}


# ─────────────────── COURRIER-2 Lot 1 — REGISTRE D'OPPOSITION (stop@labuse.immo) ───────────────────
class OppositionIn(BaseModel):
    adresse: str | None = None
    idu: str | None = None
    reference: str | None = None
    origine: str = "stop@"
    note: str | None = None


@router.get("/admin/oppositions")
def courrier_admin_oppositions(request: Request, db: Session = Depends(get_db)) -> dict:
    """Liste du registre d'opposition (Vic). GLOBAL, aucun scope compte."""
    from . import auth
    auth.exiger_admin(request)
    return {"oppositions": courrier.lister_oppositions(db)}


@router.post("/admin/oppositions")
def courrier_admin_opposition_ajout(body: OppositionIn, request: Request,
                                    db: Session = Depends(get_db)) -> dict:
    """Vic saisit une opposition reçue sur stop@labuse.immo : adresse et/ou IDU + référence citée."""
    from . import auth
    info = auth.exiger_admin(request)
    par = (info.get("email") or info.get("nom") or info.get("role") or "admin")[:60]
    try:
        opp = courrier.ajouter_opposition(db, adresse=body.adresse, idu=body.idu,
                                          reference=body.reference, origine=body.origine,
                                          note=body.note, par=par)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    try:
        from .events import creer_notification
        cible = opp.get("idu") or opp.get("adresse_norm") or "—"
        creer_notification(db, kind="systeme", compte_id=None, source="Courrier",
                           titre=f"Opposition enregistrée ({opp.get('origine')}) : {cible}",
                           detail=opp.get("reference"), dedup=f"courrier:opposition:{opp['id']}")
        db.commit()
    except Exception:  # noqa: BLE001 — best-effort
        db.rollback()
    return {"ok": True, "opposition": opp}


@router.delete("/admin/oppositions/{opp_id}")
def courrier_admin_opposition_suppr(opp_id: int, request: Request,
                                    db: Session = Depends(get_db)) -> dict:
    """Lève une opposition (erreur de saisie / rétractation écrite)."""
    from . import auth
    auth.exiger_admin(request)
    ok = courrier.supprimer_opposition(db, opp_id)
    db.commit()
    if not ok:
        raise HTTPException(404, "opposition introuvable")
    return {"ok": True}


# ─────────────────── COURRIER-2 Lot 2 — ADRESSAGE (écran avant dépôt) ───────────────────
class AdressageIn(BaseModel):
    idus: list[str] = Field(min_length=1, max_length=500)


@router.post("/adressage")
def courrier_adressage(body: AdressageIn, db: Session = Depends(get_db)) -> dict:
    """Résout, par parcelle, le destinataire + l'adresse d'envoi + le bien concerné, et le MOTIF de
    blocage éventuel (nu/sans adresse/opposition). Sert l'écran avant dépôt : bouton désactivé si
    une parcelle est bloquée. N'expose jamais un particulier (PP = « À l'occupant » ; PM = raison
    sociale, donnée publique)."""
    from .. import courrier_adressage as ca
    return {"resolutions": ca.resoudre_plusieurs(db, body.idus)}


class ComposerIn(BaseModel):
    idu: str


@router.post("/composer")
def courrier_composer(body: ComposerIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """COURRIER-2 Lot 3 — compose le courrier (recto + verso) pour l'aperçu front : MÊME source que le
    PDF, donc aperçu = PDF. Renvoie {recto, verso, ouverture, reference, destinataire, adresse_envoi,
    bloque, motif}."""
    from .. import courrier_adressage as ca, courrier_compose as cc
    res = ca.resoudre_destinataire(db, body.idu)
    comp = cc.composer(db, body.idu, resolution=res, marque=_marque_du_compte(db, request))
    return {"recto": comp["recto"], "verso": comp["verso"], "ouverture": comp["ouverture"],
            "reference": comp["reference"], "destinataire": res.get("destinataire"),
            "adresse_envoi": res.get("adresse_envoi"), "bloque": res["bloque"], "motif": res.get("motif")}


class PdfIn(BaseModel):
    # COURRIER-2 Lot 3 — le PDF est COMPOSÉ serveur (recto A→E + verso) à partir de l'IDU : le front
    # et l'admin appellent le MÊME endpoint → le même PDF. `texte`/`motif` LEGACY : ignorés si `idu`.
    idu: str | None = None
    motif: str = "standard"
    texte: str | None = Field(default=None, max_length=8000)


def _marque_du_compte(db: Session, request: Request) -> dict | None:
    """Marque blanche du compte courant (raison sociale, coordonnées) — pour la signature du courrier."""
    from .tenant import current_compte
    cid = current_compte(request)
    if cid is None:
        return None
    m = db.execute(text("SELECT marque FROM comptes WHERE id = :c"), {"c": cid}).scalar()
    return m if isinstance(m, dict) else None


# RECETTE-1 R41 — palette DA LABUSE portée au PRINT (fonds blancs) : le mint d'écran (#4ADE80) est
# trop clair sur papier → on prend le vert PROFOND `vizGreenDeep` (#2E6B4F) pour le titre et l'accent
# (#2FBE66) pour le filet ; encre presque noire pour le corps, gris pour les mentions.
_DA_VERT = (46, 107, 79)        # #2E6B4F — titre / accents
_DA_VERT_FILET = (47, 190, 102)  # #2FBE66 — filet sous l'en-tête
_DA_ENCRE = (28, 36, 31)        # corps du courrier
_DA_GRIS = (120, 130, 124)      # tagline / pied


def _pdf_safe(s: str) -> str:
    """Ponctuation typographique (’ — … « ») → équivalents latin-1 (polices de base fpdf), jamais un « ? »."""
    return s.translate(_LATIN1_PUNCT).encode("latin-1", "replace").decode("latin-1")


def _pdf_header(pdf) -> None:
    from fpdf.enums import XPos, YPos
    pdf.set_text_color(*_DA_VERT)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 11, "LABUSE", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*_DA_GRIS)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, _pdf_safe("Intelligence foncière — La Réunion"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2.5)
    pdf.set_draw_color(*_DA_VERT_FILET)
    pdf.set_line_width(0.7)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(7)


@router.post("/pdf")
def courrier_pdf(body: PdfIn, request: Request, db: Session = Depends(get_db)) -> Response:
    """COURRIER-2 Lot 3 — PDF COMPOSÉ serveur : RECTO (en-tête destinataire résolu + objet + phrase
    d'entrée « à l'occupant » le cas échéant + corps avec l'ouverture A→E choisie sur les faits +
    signature du compte) et VERSO (synthèse factuelle). Aucune valeur du terrain, aucun placeholder
    {…}, jamais un particulier nommé. Le front et l'admin appellent CE endpoint → le même PDF.

    Repli LEGACY : sans `idu`, on rend `texte` tel quel (ancien flux)."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    from .. import courrier_adressage as ca, courrier_compose as cc

    idu = (body.idu or "").strip() or None
    ref_pied = idu or "—"
    if idu:
        res = ca.resoudre_destinataire(db, idu)
        comp = cc.composer(db, idu, resolution=res, marque=_marque_du_compte(db, request))
        ref_pied = comp["reference"]

    class _Courrier(FPDF):
        def footer(self) -> None:
            self.set_y(-24)
            self.set_draw_color(222, 226, 223)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(1.5)
            self.set_text_color(*_DA_GRIS)
            self.set_font("Helvetica", "", 7)
            if idu:
                self.multi_cell(self.epw, 3.3, _pdf_safe(
                    cc._PIED.format(societe=comp["expediteur"]["societe"])), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
                self.multi_cell(self.epw, 3.3, _pdf_safe(
                    cc._PIED_STOP.format(reference=ref_pied)), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
            else:
                self.multi_cell(self.epw, 3.3, _pdf_safe(
                    "Courrier préparé avec LABUSE — à partir de données publiques (cadastre, PLU, DVF…). "
                    "Ni conseil juridique ni offre d'achat."), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    pdf = _Courrier(format="A4")
    pdf.set_auto_page_break(True, margin=28)
    pdf.set_margins(22, 20, 22)
    pdf.add_page()
    _pdf_header(pdf)

    if not idu:                                   # ── repli LEGACY : texte brut ──
        pdf.set_text_color(*_DA_ENCRE)
        pdf.set_font("Helvetica", "", 11)
        for ligne in (body.texte or "").split("\n"):
            safe = _pdf_safe(ligne)
            if safe.strip() == "":
                pdf.ln(3)
            else:
                pdf.multi_cell(pdf.epw, 6, safe, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        data = bytes(pdf.output())
        return Response(content=data, media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="courrier.pdf"'})

    # ── EN-TÊTE DESTINATAIRE (bloc adresse) ──
    pdf.set_text_color(*_DA_ENCRE)
    pdf.set_font("Helvetica", "", 10)
    if res["bloque"]:
        pdf.set_text_color(*_DA_GRIS)
        pdf.multi_cell(pdf.epw, 5, _pdf_safe(f"[Aperçu — pli non déposable : {res['motif']}]"),
                       new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*_DA_ENCRE)
    dest = res.get("destinataire") or "À l'occupant"
    adr = res.get("adresse_envoi") or (res["bien"].get("adresse") or "")
    for ligne in (dest, *(adr.split(", ") if adr else [])):
        pdf.multi_cell(pdf.epw, 5, _pdf_safe(ligne), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
    pdf.ln(6)

    # ── CORPS (recto composé) ──
    pdf.set_font("Helvetica", "", 11)
    for ligne in comp["recto"].split("\n"):
        safe = _pdf_safe(ligne)
        if safe.strip() == "":
            pdf.ln(3)
        elif safe.startswith("Objet :"):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(pdf.epw, 6, safe, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 11)
        else:
            pdf.multi_cell(pdf.epw, 6, safe, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── VERSO (page 2) : synthèse factuelle ──
    pdf.add_page()
    _pdf_header(pdf)
    verso = comp["verso"]
    pdf.set_text_color(*_DA_VERT)
    pdf.set_font("Helvetica", "B", 13)
    pdf.multi_cell(pdf.epw, 7, _pdf_safe(verso[0] if verso else "Synthèse de la parcelle"),
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_text_color(*_DA_ENCRE)
    pdf.set_font("Helvetica", "", 10.5)
    for ligne in verso[1:]:
        pdf.multi_cell(pdf.epw, 5.6, _pdf_safe(ligne), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(0.8)

    data = bytes(pdf.output())
    nom = idu.replace("/", "-")
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
