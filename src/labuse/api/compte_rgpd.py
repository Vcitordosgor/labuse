"""NU5-FIX-1 (C-F5 / C-F6) — libre-service RGPD du compte : EXPORT de mes données (art. 20, promis
en CGV art. 7) et SUPPRESSION de mon compte (art. 17, « à portée de clic » au lieu de « sur demande
par e-mail »). Les deux sont scopés au compte de la SESSION (jamais un autre compte), et la
suppression réutilise la primitive existante `comptes.effacer_compte_rgpd` (hard delete + cascade +
audit anonymisé). Aucune donnée d'un autre tenant n'est jamais lue ni touchée."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

from ..db import session_scope
from .tenant import compte_ou_401

log = logging.getLogger("labuse.compte_rgpd")
router = APIRouter(tags=["compte"])

#: tables portant `compte_id` dont l'export restitue le contenu du compte (portabilité RGPD).
#: Best-effort : une table absente (base partielle) est simplement omise, jamais une 500.
_TABLES_EXPORT = (
    "utilisateurs", "projets", "pipeline_entries", "saved_searches", "saved_filters",
    "watched_parcels", "signalements", "documents_generes", "notif_prefs",
)
#: colonnes jamais exportées (secrets) — on ne restitue pas les empreintes de mot de passe / jetons.
_COLS_SECRETES = {"mot_de_passe_hash", "password_hash", "hash", "token", "jeton", "secret", "totp_secret"}


@router.get("/compte/export")
def exporter_mes_donnees(request: Request) -> dict:
    """RGPD art. 20 — restitue, en JSON, TOUTES les données du compte de la session (une entrée par
    table). Lecture seule, scopée `compte_id`. Les secrets (empreinte de mot de passe, jetons) sont
    exclus."""
    cid = compte_ou_401(request)
    out: dict = {"compte_id": cid, "tables": {}}
    with session_scope() as db:
        for t in _TABLES_EXPORT:
            if not db.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar():
                continue
            if not db.execute(text(
                "SELECT 1 FROM information_schema.columns WHERE table_name = :t "
                "AND column_name = 'compte_id'"), {"t": t}).scalar():
                continue
            try:
                rows = db.execute(text(f"SELECT * FROM {t} WHERE compte_id = :c"), {"c": cid}).mappings().all()
            except Exception:  # noqa: BLE001 — table illisible : on l'omet, jamais une 500
                continue
            out["tables"][t] = [
                {k: (v.isoformat() if hasattr(v, "isoformat") else v)
                 for k, v in dict(r).items() if k not in _COLS_SECRETES}
                for r in rows]
    return out


class SuppressionIn(BaseModel):
    confirmation: str   # doit valoir « SUPPRIMER » (garde-fou anti-clic accidentel)


@router.post("/compte/supprimer")
def supprimer_mon_compte(body: SuppressionIn, request: Request) -> dict:
    """RGPD art. 17 — supprime DÉFINITIVEMENT le compte de la session et toutes ses données
    (cascade). Garde-fou : `confirmation == "SUPPRIMER"`. Réutilise `effacer_compte_rgpd` (audit
    anonymisé conservé). Après ce point, la session n'a plus de compte."""
    cid = compte_ou_401(request)
    if (body.confirmation or "").strip().upper() != "SUPPRIMER":
        raise HTTPException(422, "Confirmation requise : renvoyez confirmation=\"SUPPRIMER\".")
    with session_scope() as db:
        email = db.execute(text(
            "SELECT email FROM utilisateurs WHERE compte_id = :c AND role = 'titulaire' "
            "ORDER BY id LIMIT 1"), {"c": cid}).scalar()
        if not email:
            email = db.execute(text(
                "SELECT email FROM utilisateurs WHERE compte_id = :c ORDER BY id LIMIT 1"),
                {"c": cid}).scalar()
        if not email:
            raise HTTPException(404, "Compte introuvable.")
        from ..comptes import effacer_compte_rgpd
        ok = effacer_compte_rgpd(db, email)
    if not ok:
        raise HTTPException(404, "Compte introuvable.")
    log.info("RGPD libre-service : compte %s supprimé par son titulaire", cid)
    return {"ok": True, "message": "Votre compte et toutes vos données ont été supprimés."}
