"""TOUR DE CONTRÔLE (dashboard admin) — capteurs + endpoints /admin/* (mandat DASHBOARD-V1).

D1 — CAPTEURS. L'app s'instrumente, léger et RGPD-sobre : des COMPTEURS, jamais du contenu.
  · usage_events : ouverture d'outil + heartbeat de session (temps d'usage estimé par pas de
    5 min côté client). Fire-and-forget : l'endpoint ne lève JAMAIS (un capteur qui casse une
    requête client serait pire que pas de capteur).
  · retours : bouton « Signaler » de l'app cliente (bug/idée/question + message) → table
    `retours`, statut nouveau/traité/répondu. Notif cloche admin best-effort.
  · ia_budget : la conso IA est attribuée PAR COMPTE dans ia_log (colonne compte_id, posée par
    la garde d'auth via ai.core.poser_compte — réimplémentation propre du WIP fix/ia-modele-budget,
    branche NON mergée : divergée des fichiers remaniés).
  · quota Copilote PAR LICENCE : comptes.copilote_quota_jour (NULL = défaut config 80/jour) —
    lu par la porte NL de /ia (cf. ia.quota_nl_du_compte).
  · actifs/jour : rien à écrire ici — utilisateurs.dernier_login_at (existant) + usage_events.

Tout endpoint /admin/* passe par auth.exiger_admin (403 client, 401 sans session) — le
cloisonnement EXISTANT, réutilisé, jamais un nouveau mécanisme.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.dashboard")

router = APIRouter(tags=["dashboard"])

#: types de retours clients (bouton « Signaler ») — libellés courts, jamais de texte libre ici.
RETOUR_TYPES = ("bug", "idee", "question")
RETOUR_STATUTS = ("nouveau", "traite", "repondu")
#: outils/vues comptés — borne de longueur, pas de liste fermée (le front envoie sa clé d'outil ;
#: une clé inconnue reste un compteur honnête, jamais une erreur).
USAGE_KINDS = ("outil", "heartbeat")


def ensure_tables(engine) -> None:
    """Idempotent, appelé au boot (heal résilient FIX-GB-011)."""
    with engine.begin() as c:
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS usage_events ("
            " id bigserial PRIMARY KEY, ts timestamptz DEFAULT now(),"
            " compte_id integer, kind varchar(16) NOT NULL, outil varchar(48))"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_usage_events_ts ON usage_events(ts)"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_usage_events_compte_ts ON usage_events(compte_id, ts)"))
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS retours ("
            " id serial PRIMARY KEY, ts timestamptz DEFAULT now(), compte_id integer,"
            " type varchar(12) NOT NULL, message text NOT NULL,"
            " statut varchar(12) NOT NULL DEFAULT 'nouveau', updated_at timestamptz DEFAULT now())"))
        # ia_budget (D1) — attribution du coût IA au compte : colonne sur le ledger EXISTANT ia_log
        # (créé par ai.core._log_cost) ; ALTER d'abord au cas où la table précède cette colonne.
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS ia_log ("
            " id serial PRIMARY KEY, ts timestamptz DEFAULT now(), kind varchar(24), model varchar(64),"
            " stub boolean, tokens_in integer, tokens_out integer, cout_eur numeric(8,5))"))
        c.execute(text("ALTER TABLE ia_log ADD COLUMN IF NOT EXISTS compte_id integer"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_ia_log_compte_ts ON ia_log(compte_id, ts)"))
        # quota Copilote PAR LICENCE (NULL = défaut config copilote_questions_jour_defaut)
        c.execute(text("ALTER TABLE comptes ADD COLUMN IF NOT EXISTS copilote_quota_jour integer"))


# ───────────────────────── capteurs côté CLIENT ─────────────────────────
class UsageIn(BaseModel):
    kind: str = Field(pattern="^(outil|heartbeat)$")
    outil: str | None = Field(default=None, max_length=48)


@router.post("/usage/event")
def usage_event(body: UsageIn, request: Request) -> dict:
    """Capteur d'usage — fire-and-forget : TOUJOURS {ok}, une panne de capteur ne casse jamais
    l'app cliente. RGPD-sobre : (compte, outil, ts), aucun contenu."""
    try:
        from ..db import engine
        cid = getattr(request.state, "compte_id", None)
        with engine().begin() as c:
            c.execute(text("INSERT INTO usage_events (compte_id, kind, outil) VALUES (:c, :k, :o)"),
                      {"c": cid, "k": body.kind, "o": (body.outil or None)})
    except Exception as exc:  # noqa: BLE001 — capteur best-effort, jamais bloquant
        log.debug("usage_event avalé : %s", exc)
    return {"ok": True}


class RetourIn(BaseModel):
    type: str = Field(pattern="^(bug|idee|question)$")
    message: str = Field(min_length=3, max_length=2000)


@router.post("/retours")
def creer_retour(body: RetourIn, request: Request) -> dict:
    """Bouton « Signaler » (app cliente, en haut à droite) : bug/idée/question + message."""
    from ..db import engine
    cid = getattr(request.state, "compte_id", None)
    with engine().begin() as c:
        rid = c.execute(text(
            "INSERT INTO retours (compte_id, type, message) VALUES (:c, :t, :m) RETURNING id"),
            {"c": cid, "t": body.type, "m": body.message.strip()}).scalar_one()
    # cloche admin best-effort (patron courrier_demande) — l'échec de la notif ne perd jamais le retour
    try:
        from ..db import session_scope
        from .events import creer_notification
        with session_scope() as s:
            creer_notification(s, kind="systeme", compte_id=None, source="Retour",
                               titre=f"Nouveau retour client ({body.type})",
                               detail=body.message[:280], lien="/admin",
                               dedup=f"retour:{rid}", permanent=True)
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "id": rid}


# ───────────────────────── quota Copilote PAR LICENCE ─────────────────────────
def quota_nl_du_compte(compte_id: int | None) -> int | None:
    """Quota de questions Copilote/jour pour CE compte : l'override de la licence
    (comptes.copilote_quota_jour), sinon le défaut config (80/jour). None si pas de compte
    (pilote/anonyme → l'appelant garde son quota historique nl_quota_jour)."""
    if compte_id is None:
        return None
    from .. import config
    defaut = int(config.get_settings().copilote_questions_jour_defaut)
    try:
        from ..db import engine
        with engine().begin() as c:
            v = c.execute(text("SELECT copilote_quota_jour FROM comptes WHERE id = :c"),
                          {"c": compte_id}).scalar()
        return int(v) if v is not None else defaut
    except Exception:  # noqa: BLE001 — lecture best-effort : jamais bloquer une question sur une panne
        return defaut
