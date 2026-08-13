"""M78 · 2b — HISTORIQUE : reprendre là où on s'est arrêté.

Conversations et missions persistées PAR COMPTE (cloison `compte_id`, motif du projet). Rouvrir le
Copilote montre les missions passées (titre auto, date, statut) ; en rouvrir une restaure la
conversation. Sans historique, chaque visite repart de zéro — c'est ce qui tue l'adoption.

Deux tables (DDL inline, pas d'Alembic). Rétention en config (`copilote_v2_retention_jours`, 90j).
La persistance ne doit JAMAIS casser une réponse au client (try/except + rollback).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

DDL = """
CREATE TABLE IF NOT EXISTS copilote_conversations (
  id serial PRIMARY KEY, compte_id int,
  titre text, statut varchar(16) DEFAULT 'active',   -- active | archivee
  run_id varchar(64),                                -- mission RECHERCHE liée (agent_runs), si tour lourd
  created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS copilote_messages (
  id serial PRIMARY KEY,
  conversation_id int REFERENCES copilote_conversations(id) ON DELETE CASCADE,
  role varchar(10),                                  -- client | copilote
  texte text, intent varchar(16), ts timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_copilote_conv_compte ON copilote_conversations (compte_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_copilote_msg_conv ON copilote_messages (conversation_id, ts);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        c.execute(text(DDL))


def _titre(message: str) -> str:
    t = " ".join((message or "").split())
    return (t[:57] + "…") if len(t) > 58 else (t or "Nouvelle conversation")


def enregistrer(db: Session, *, compte_id: int | None, conversation_id: int | None,
                message: str, reponse: dict) -> int | None:
    """Journalise un tour (message client + réponse Copilote). Crée la conversation au 1er tour
    (titre = 1re demande). Retourne l'id de conversation (à renvoyer au client pour la suite)."""
    try:
        db.execute(text(DDL))
        cid = conversation_id
        if cid is None:
            cid = db.execute(text(
                "INSERT INTO copilote_conversations (compte_id, titre, run_id) "
                "VALUES (:c, :t, :r) RETURNING id"),
                {"c": compte_id, "t": _titre(message), "r": reponse.get("run_id")}).scalar()
        else:
            db.execute(text("UPDATE copilote_conversations SET updated_at = now() WHERE id = :i "
                            "AND compte_id IS NOT DISTINCT FROM :c"), {"i": cid, "c": compte_id})
        db.execute(text("INSERT INTO copilote_messages (conversation_id, role, texte, intent) "
                        "VALUES (:i, 'client', :t, NULL)"), {"i": cid, "t": message[:2000]})
        db.execute(text("INSERT INTO copilote_messages (conversation_id, role, texte, intent) "
                        "VALUES (:i, 'copilote', :t, :n)"),
                   {"i": cid, "t": (reponse.get("text") or "")[:4000], "n": reponse.get("intent")})
        return cid
    except Exception:
        db.rollback()
        return conversation_id


def lister(db: Session, compte_id: int | None, limite: int = 40) -> list[dict]:
    """Les missions passées du compte (titre auto, date, statut) — pour rouvrir."""
    rows = db.execute(text(
        "SELECT c.id, c.titre, c.statut, c.run_id, c.updated_at, "
        "  (SELECT count(*) FROM copilote_messages m WHERE m.conversation_id = c.id) AS n_messages "
        "FROM copilote_conversations c WHERE c.compte_id IS NOT DISTINCT FROM :c "
        "ORDER BY c.updated_at DESC LIMIT :l"), {"c": compte_id, "l": limite}).mappings().all()
    return [dict(r) for r in rows]


def charger(db: Session, compte_id: int | None, conversation_id: int) -> dict | None:
    """Restaure une conversation (ses messages, et le run_id si mission RECHERCHE à rejouer)."""
    conv = db.execute(text(
        "SELECT id, titre, statut, run_id, created_at FROM copilote_conversations "
        "WHERE id = :i AND compte_id IS NOT DISTINCT FROM :c"),
        {"i": conversation_id, "c": compte_id}).mappings().first()
    if not conv:
        return None
    msgs = db.execute(text(
        "SELECT role, texte, intent, ts FROM copilote_messages WHERE conversation_id = :i ORDER BY ts"),
        {"i": conversation_id}).mappings().all()
    return {**dict(conv), "messages": [dict(m) for m in msgs]}


def purger(db: Session, jours: int) -> int:
    """Rétention : supprime les conversations plus vieilles que N jours (cron J+1, Train 8)."""
    n = db.execute(text("DELETE FROM copilote_conversations "
                        "WHERE updated_at < now() - make_interval(days => :j)"), {"j": jours}).rowcount
    return n or 0
