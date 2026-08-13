"""M78 · 1e — TÉLÉMÉTRIE : la feuille de route auto-alimentée.

Journalise ce que le produit ne sait pas encore faire : chaque refus « pas d'outil » (question
ANONYMISÉE, intention, date), chaque critère de recherche non traduisible, chaque 👍/👎. Trié par
fréquence, c'est la liste MESURÉE des prochains outils à construire — pas devinée.

Table dédiée (DDL inline, motif du projet — pas d'Alembic). Anonymisation : on garde le texte de la
demande (utile pour lire le besoin) mais AUCUN identifiant client n'est stocké ici.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

DDL = """
CREATE TABLE IF NOT EXISTS copilote_telemetrie (
  id serial PRIMARY KEY, ts timestamptz DEFAULT now(),
  genre varchar(24),          -- 'refus' | 'critere_non_traduisible' | 'feedback'
  sous_type varchar(32),      -- refus: proprietaire_pp|projection|aucun_outil ; feedback: pouce_haut|pouce_bas
  intention varchar(16),      -- l'intention routée (QUESTION, OUTIL, …)
  demande text,               -- la demande anonymisée (aucun identifiant client)
  mission_id varchar(64),     -- feedback : identifiant de mission (§2f)
  detail text
);
CREATE INDEX IF NOT EXISTS ix_copilote_telem_genre ON copilote_telemetrie (genre, sous_type);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        c.execute(text(DDL))


def _insert(db: Session, **kw) -> None:
    try:
        db.execute(text(DDL))   # idempotent (le harnais tourne hors lifespan)
        db.execute(text(
            "INSERT INTO copilote_telemetrie (genre, sous_type, intention, demande, mission_id, detail) "
            "VALUES (:g, :s, :i, :d, :m, :det)"),
            {"g": kw.get("genre"), "s": kw.get("sous_type"), "i": kw.get("intention"),
             "d": (kw.get("demande") or "")[:500], "m": kw.get("mission_id"),
             "det": kw.get("detail")})
    except Exception:   # la télémétrie ne doit JAMAIS casser une réponse au client
        db.rollback()


def refus(db: Session, sous_type: str, demande: str, intention: str | None = None) -> None:
    """Un refus « pas d'outil » / structurellement inexistant → mesure de ce qui manque au produit."""
    _insert(db, genre="refus", sous_type=sous_type, intention=intention, demande=demande)


def critere_non_traduisible(db: Session, critere: str, demande: str = "") -> None:
    _insert(db, genre="critere_non_traduisible", sous_type=None, demande=demande, detail=critere)


def feedback(db: Session, mission_id: str, pouce: str, commentaire: str = "") -> None:
    """👍/👎 (§2f) — rejoint la télémétrie : ce qu'on obtient sans en être satisfait."""
    _insert(db, genre="feedback", sous_type=f"pouce_{pouce}", mission_id=mission_id, detail=commentaire)


def resume(db: Session) -> list[dict]:
    """Vue triée par fréquence — la feuille de route (§1e)."""
    rows = db.execute(text(
        "SELECT genre, sous_type, count(*) n, max(ts) dernier FROM copilote_telemetrie "
        "GROUP BY genre, sous_type ORDER BY n DESC")).mappings().all()
    return [dict(r) for r in rows]
