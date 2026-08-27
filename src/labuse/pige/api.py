"""RADAR P1 · V3 — endpoints ADMIN de la page Radar (réservés au compte pilote, comme le reste).

Câble les fonctions V2 (extraction/intake) : dépôt d'une capture, file d'extraction (brouillons),
validation, file de re-vérification priorisée à deux niveaux, arbre de check quotidien. Aucune
donnée d'annonce republiée : on sert des FAITS + le lien sortant, jamais photo/titre/texte.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from ..db import engine, session_scope
from . import intake
from .tables import EV_BAISSE_PRIX, EV_STATUT_CHANGE, journaliser

router = APIRouter(tags=["radar"])

# seuils de cycle (mandat V0 §4) — repris ici pour la priorisation de la file.
SEUIL_VENTE_LONGUE_J = 90


class DeposerIn(BaseModel):
    lien: str
    image_b64: str
    media_type: str = "image/jpeg"


class ValiderIn(BaseModel):
    bien_id: int
    faits: dict = {}


class BienIn(BaseModel):
    bien_id: int


class PrixIn(BaseModel):
    bien_id: int
    prix: int


@router.post("/admin/radar/deposer")
def radar_deposer(body: DeposerIn, request: Request) -> dict:
    """Saisie du jour : une capture (base64) + son lien → extraction, contrôle commune, dédoublonnage,
    brouillon. Retour immédiat sur doublon d'URL / commune hors périmètre (rien de validé)."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    try:
        image = base64.b64decode(body.image_b64, validate=True)
    except Exception:  # noqa: BLE001
        return {"statut": "echec_extraction", "motif": "image base64 illisible"}
    with session_scope() as db:
        return intake.deposer(db, image, body.media_type, body.lien.strip())


@router.post("/admin/radar/valider")
def radar_valider(body: ValiderIn, request: Request) -> dict:
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        return intake.valider(db, body.bien_id, body.faits, valide_par=None)


@router.get("/admin/radar/extraction")
def radar_extraction(request: Request) -> dict:
    """File d'extraction : les brouillons (valide_at NULL), du plus récent au plus ancien."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with engine().begin() as c:
        rows = [dict(r) for r in c.execute(text(
            """SELECT b.bien_id, b.commune, b.type_bien, b.rattachement_niveau, f.prix,
                      f.surface_hab, f.surface_terrain, f.dpe_classe, f.pieces, f.particulier_pro,
                      f.etiquettes, f.a_verifier, a.portail, a.url_sortante,
                      b.created_at
               FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
               LEFT JOIN pige_annonces a ON a.bien_id = b.bien_id
               WHERE f.valide_at IS NULL
               ORDER BY b.created_at DESC LIMIT 100""")).mappings()]
    for r in rows:
        r["created_at"] = r["created_at"].isoformat() if r["created_at"] else None
    return {"file": rows, "n": len(rows)}


@router.get("/admin/radar/reverif")
def radar_reverif(request: Request) -> dict:
    """File de re-vérification PRIORISÉE : plus anciennes non confirmées d'abord, puis proches du
    seuil de vente longue (90 j), puis suivies par un client (watched_parcels sur l'idu rattaché)."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with engine().begin() as c:
        rows = [dict(r) for r in c.execute(text(
            f"""SELECT b.bien_id, b.commune, b.type_bien, b.statut, f.prix, a.portail, a.url_sortante,
                      b.date_derniere_confirmation, b.date_publication,
                      EXISTS (SELECT 1 FROM watched_parcels w WHERE w.idu = b.idu) AS suivi_client,
                      (b.date_publication IS NOT NULL
                       AND b.date_publication <= current_date - {SEUIL_VENTE_LONGUE_J}) AS proche_longue
               FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
               LEFT JOIN pige_annonces a ON a.bien_id = b.bien_id
               WHERE f.valide_at IS NOT NULL AND b.statut IN ('active','en_vente_longue','a_reverifier')
               ORDER BY suivi_client DESC, proche_longue DESC, b.date_derniere_confirmation ASC
               LIMIT 200""")).mappings()]
    for r in rows:
        for k in ("date_derniere_confirmation", "date_publication"):
            r[k] = r[k].isoformat() if r[k] else None
    return {"file": rows, "n": len(rows)}


@router.post("/admin/radar/toujours-en-ligne")
def radar_toujours(body: BienIn, request: Request) -> dict:
    """Passage LÉGER : confirme qu'une annonce est toujours en ligne (bump date de confirmation)."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        db.execute(text("UPDATE pige_biens SET date_derniere_confirmation = now(), statut = 'active' "
                        "WHERE bien_id = :b"), {"b": body.bien_id})
        db.commit()
    return {"ok": True, "bien_id": body.bien_id}


@router.post("/admin/radar/prix")
def radar_prix(body: PrixIn, request: Request) -> dict:
    """Passage ATTENTIF : prix modifié → historique + drapeau baisse."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        ancien = db.execute(text("SELECT prix FROM pige_faits WHERE bien_id = :b"),
                            {"b": body.bien_id}).scalar()
        db.execute(text("UPDATE pige_faits SET prix = :p, updated_at = now() WHERE bien_id = :b"),
                   {"p": body.prix, "b": body.bien_id})
        db.execute(text("UPDATE pige_biens SET date_derniere_confirmation = now() WHERE bien_id = :b"),
                   {"b": body.bien_id})
        if ancien is not None and body.prix != ancien:
            db.execute(text("INSERT INTO pige_prix_historique (bien_id, ancien_prix, nouveau_prix) "
                            "VALUES (:b, :a, :n)"), {"b": body.bien_id, "a": ancien, "n": body.prix})
            if body.prix < ancien:
                journaliser(db, EV_BAISSE_PRIX, f"Baisse de prix — bien #{body.bien_id}",
                            detail=f"{ancien} € → {body.prix} €",
                            dedup=f"pige:baisse:{body.bien_id}:{body.prix}")
        db.commit()
    return {"ok": True, "bien_id": body.bien_id, "prix": body.prix}


@router.post("/admin/radar/retiree")
def radar_retiree(body: BienIn, request: Request) -> dict:
    """Vic marque une annonce retirée (clic humain). Un lien mort = `retiree`, jamais `retiree_sans_vente`."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with session_scope() as db:
        db.execute(text("UPDATE pige_biens SET statut = 'retiree' WHERE bien_id = :b"), {"b": body.bien_id})
        journaliser(db, EV_STATUT_CHANGE, f"Bien retiré — #{body.bien_id}",
                    detail="marqué retiré (file de re-vérif)", dedup=f"pige:retiree:{body.bien_id}")
        db.commit()
    return {"ok": True, "bien_id": body.bien_id, "statut": "retiree"}


@router.get("/admin/radar/check")
def radar_check(request: Request) -> dict:
    """Arbre de check quotidien : compteurs du rituel + drapeau intake vide depuis 48 h."""
    from ..api.auth import exiger_admin
    exiger_admin(request)
    with engine().begin() as c:
        q = lambda s: c.execute(text(s)).scalar() or 0
        file_extraction = q("SELECT count(*) FROM pige_faits WHERE valide_at IS NULL")
        nouveautes = q("SELECT count(*) FROM pige_biens WHERE date_premiere_saisie::date = current_date")
        en_vente_longue = q("SELECT count(*) FROM pige_biens WHERE statut = 'en_vente_longue'")
        baisses = q("SELECT count(*) FROM event_log WHERE kind = 'pige.baisse_prix' "
                    "AND ts::date = current_date")
        signalements = q("SELECT count(*) FROM event_log WHERE kind = 'pige.signalement_client' "
                         "AND ts::date = current_date")
        derniere = c.execute(text("SELECT max(date_saisie) FROM pige_annonces")).scalar()
    from datetime import datetime, timedelta, timezone
    vide_48h = derniere is None or derniere < datetime.now(tz=timezone.utc) - timedelta(hours=48)
    return {
        "cible_minutes": 15,
        "file_extraction": file_extraction,
        "reverif_du_jour": nouveautes,            # cadence quotidienne du rituel
        "signalements_en_attente": signalements,
        "compteurs": {"nouveautes": nouveautes, "en_vente_longue": en_vente_longue, "baisses": baisses},
        "intake_vide_48h": bool(vide_48h),
        "derniere_saisie": derniere.isoformat() if derniere else None,
    }
