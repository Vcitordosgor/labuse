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
-- M102-B1 : contexte d'interprétation du tour (intent + params du routeur + clarification) — jamais
-- servi au client, relu par fil() pour interpréter le tour SUIVANT dans son contexte.
ALTER TABLE copilote_messages ADD COLUMN IF NOT EXISTS payload jsonb;
-- COPILOTE-2 lot 6 : FERMER LE BUCKET PILOTE NULL. Une conversation sans compte (visiteur anonyme /
-- pilote) portait compte_id NULL — et `IS NOT DISTINCT FROM NULL` faisait de TOUS les anonymes UN
-- SEUL espace partagé (un visiteur lisait la mémoire d'un autre). On grave le `sujet` (jeton de
-- SESSION, `protection.sujet_de` : « s:<hash cookie> » ou « ip:<hash> ») ; la cloison anonyme se fait
-- DÉSORMAIS sur ce sujet, jamais sur NULL nu. Comptes connectés : sujet NULL, cloison par compte_id.
ALTER TABLE copilote_conversations ADD COLUMN IF NOT EXISTS sujet varchar(24);
CREATE INDEX IF NOT EXISTS ix_copilote_conv_sujet ON copilote_conversations (sujet, updated_at DESC);
"""

# COPILOTE-2 lot 6 — LA CLOISON UNIQUE. Compte connecté (`:c` non NULL) → cloison par compte_id, le
# sujet est ignoré. Anonyme (`:c` NULL) → cloison par `sujet` de session (jamais le NULL partagé).
# Le sujet anonyme est TOUJOURS présent (jamais NULL) : deux anonymes de sessions différentes ne se
# lisent plus ; un anonyme retrouve SA conversation. `alias` = table des conversations dans la requête.
def _cloison(alias: str = "c") -> str:
    return (f"({alias}.compte_id IS NOT DISTINCT FROM :c "
            f"AND (:c IS NOT NULL OR {alias}.sujet IS NOT DISTINCT FROM :s))")


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        c.execute(text(DDL))


def _titre(message: str) -> str:
    t = " ".join((message or "").split())
    return (t[:57] + "…") if len(t) > 58 else (t or "Nouvelle conversation")


def enregistrer(db: Session, *, compte_id: int | None, conversation_id: int | None,
                message: str, reponse: dict, payload: dict | None = None,
                sujet: str | None = None) -> int | None:
    """Journalise un tour (message client + réponse Copilote). Crée la conversation au 1er tour
    (titre = 1re demande). `payload` (M102-B1) = contexte d'interprétation du tour (intent +
    params du routeur), relu par fil(). `sujet` (lot 6) = jeton de session anonyme (grave la cloison
    hors compte). Retourne l'id de conversation."""
    import json
    try:
        db.execute(text(DDL))
        cid = conversation_id
        if cid is None:
            cid = db.execute(text(
                "INSERT INTO copilote_conversations (compte_id, sujet, titre, run_id) "
                "VALUES (:c, :s, :t, :r) RETURNING id"),
                {"c": compte_id, "s": (sujet if compte_id is None else None),
                 "t": _titre(message), "r": reponse.get("run_id")}).scalar()
        else:
            db.execute(text("UPDATE copilote_conversations c SET updated_at = now() "
                            "WHERE c.id = :i AND " + _cloison("c")),
                       {"i": cid, "c": compte_id, "s": sujet})
        db.execute(text("INSERT INTO copilote_messages (conversation_id, role, texte, intent) "
                        "VALUES (:i, 'client', :t, NULL)"), {"i": cid, "t": message[:2000]})
        db.execute(text("INSERT INTO copilote_messages (conversation_id, role, texte, intent, payload) "
                        "VALUES (:i, 'copilote', :t, :n, CAST(:p AS jsonb))"),
                   {"i": cid, "t": (reponse.get("text") or "")[:4000], "n": reponse.get("intent"),
                    "p": json.dumps(payload, ensure_ascii=False) if payload else None})
        return cid
    except Exception:
        db.rollback()
        return conversation_id


def fil(db: Session, compte_id: int | None, conversation_id: int,
        ttl_minutes: int, max_tours: int = 6, sujet: str | None = None) -> tuple[list[dict], dict | None]:
    """M102-B1 — le FIL pour l'INTERPRÉTATION : (history [{role: user|assistant, content}],
    prior = payload du dernier tour Copilote). Cloison compte. Le contexte a une DURÉE DE VIE
    bornée (`ttl_minutes` depuis le dernier tour) : au-delà, ([], None) — la conversation reste
    lisible/reprenable à l'écran, seule la mémoire d'interprétation expire (le contexte ne
    traîne pas). Jamais d'exception sortante (un fil illisible = interprétation à froid, dite
    par l'absence de contexte, pas un crash)."""
    try:
        rows = db.execute(text(
            "SELECT m.role, m.texte, m.payload FROM copilote_messages m "
            "JOIN copilote_conversations c ON c.id = m.conversation_id "
            "WHERE m.conversation_id = :i AND " + _cloison("c") + " "
            "  AND c.updated_at >= now() - make_interval(mins => :ttl) "
            "ORDER BY m.ts DESC, m.id DESC LIMIT :n"),
            {"i": conversation_id, "c": compte_id, "s": sujet, "ttl": int(ttl_minutes),
             "n": int(max_tours) * 2}).mappings().all()
    except Exception:
        db.rollback()
        return [], None
    if not rows:
        return [], None
    history = [{"role": "user" if r["role"] == "client" else "assistant",
                "content": (r["texte"] or "")[:600]} for r in reversed(rows)]
    prior = next((dict(r["payload"]) for r in rows
                  if r["role"] == "copilote" and r["payload"]), None)
    return history, prior


def lister(db: Session, compte_id: int | None, limite: int = 40, sujet: str | None = None) -> list[dict]:
    """Les missions passées du compte (titre auto, date, statut) — pour rouvrir. Cloison lot 6 :
    compte connecté par compte_id, visiteur anonyme par sujet de session (jamais le NULL partagé)."""
    rows = db.execute(text(
        "SELECT c.id, c.titre, c.statut, c.run_id, c.updated_at, "
        "  (SELECT count(*) FROM copilote_messages m WHERE m.conversation_id = c.id) AS n_messages "
        "FROM copilote_conversations c WHERE " + _cloison("c") + " "
        "ORDER BY c.updated_at DESC LIMIT :l"), {"c": compte_id, "s": sujet, "l": limite}).mappings().all()
    return [dict(r) for r in rows]


def charger(db: Session, compte_id: int | None, conversation_id: int, sujet: str | None = None) -> dict | None:
    """Restaure une conversation (ses messages, et le run_id si mission RECHERCHE à rejouer).
    Cloison lot 6 : un id étranger (autre compte OU autre session anonyme) → None → 404."""
    conv = db.execute(text(
        "SELECT c.id, c.titre, c.statut, c.run_id, c.created_at FROM copilote_conversations c "
        "WHERE c.id = :i AND " + _cloison("c")),
        {"i": conversation_id, "c": compte_id, "s": sujet}).mappings().first()
    if not conv:
        return None
    msgs = db.execute(text(
        "SELECT role, texte, intent, ts FROM copilote_messages WHERE conversation_id = :i ORDER BY ts"),
        {"i": conversation_id}).mappings().all()
    return {**dict(conv), "messages": [dict(m) for m in msgs]}


def purger(db: Session, jours: int) -> int:
    """Rétention : supprime les conversations plus vieilles que N jours (cron J+1, Train 8).
    RETOURS-8 (R11) — appelée par le job quotidien `copilote-purge`, avec la rétention effective
    (réglage admin, défaut 7 j). Les messages tombent par CASCADE (FK ON DELETE CASCADE)."""
    n = db.execute(text("DELETE FROM copilote_conversations "
                        "WHERE updated_at < now() - make_interval(days => :j)"), {"j": jours}).rowcount
    return n or 0


def mesure(db: Session) -> dict:
    """RETOURS-8 (R11.2) — ce que PÈSENT les conversations stockées : nombre de conversations et de
    messages, taille en base (octets, index compris) et croissance des 7 derniers jours (messages/jour
    moyen). Lecture seule, tolérante à l'absence de table (base neuve) → zéros."""
    try:
        db.execute(text(DDL))
        r = db.execute(text(
            "SELECT (SELECT count(*) FROM copilote_conversations) AS n_conv, "
            "       (SELECT count(*) FROM copilote_messages) AS n_msg, "
            "       pg_total_relation_size('copilote_conversations') AS o_conv, "
            "       pg_total_relation_size('copilote_messages') AS o_msg")).mappings().one()
        croissance = db.execute(text(
            "SELECT count(*) FROM copilote_messages WHERE ts > now() - interval '7 days'")).scalar() or 0
        octets = int(r["o_conv"] or 0) + int(r["o_msg"] or 0)
        return {"conversations": int(r["n_conv"] or 0), "messages": int(r["n_msg"] or 0),
                "octets": octets, "mo": round(octets / 1e6, 2),
                "messages_7j": int(croissance), "croissance_jour": round(int(croissance) / 7.0, 1)}
    except Exception:  # noqa: BLE001 — la mesure ne casse jamais l'appelant
        return {"conversations": 0, "messages": 0, "octets": 0, "mo": 0.0,
                "messages_7j": 0, "croissance_jour": 0.0}
