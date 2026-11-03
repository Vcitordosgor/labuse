"""JOHN-TAYLOR-1 — le JOURNAL des actions de John.

Le mandat : « Chaque action est journalisée avec l'heure et le compte. » Une seule table, écrite par
`actions.executer` (et par rien d'autre). Elle trace QUI (compte), QUAND (heure Réunion via `now()`),
QUOI (action + arguments), si l'action demandait une confirmation, et le RÉSULTAT (ok + résumé).

Lecture seule pour le carnet de bord / le dashboard : `dernieres()`.
"""
from __future__ import annotations

import json

from sqlalchemy import text

DDL = """
CREATE TABLE IF NOT EXISTS john_journal (
  id          bigserial PRIMARY KEY,
  ts          timestamptz NOT NULL DEFAULT now(),
  compte_id   integer,                 -- le compte admin à l'origine de l'ordre (None = système/test)
  compte      varchar(120),            -- libellé lisible (email/nom) pour le journal
  action      varchar(48) NOT NULL,    -- la clé d'action (liste fermée)
  args        jsonb NOT NULL DEFAULT '{}'::jsonb,
  confirme    boolean NOT NULL DEFAULT false,  -- vrai si l'action exigeait « tu confirmes ? »
  ok          boolean NOT NULL,
  resume      text                     -- une phrase sur le résultat (pour le journal lisible)
)
"""


def ensure(db) -> None:
    db.execute(text(DDL))


def enregistrer(db, *, action: str, args: dict, ok: bool, resume: str,
                compte_id: int | None = None, compte: str | None = None,
                confirme: bool = False) -> None:
    """Pose UNE ligne de journal. Appelée systématiquement par `actions.executer`, y compris quand
    l'action est refusée (hors liste) ou échoue : le journal dit AUSSI ce qui n'a pas été fait."""
    ensure(db)
    db.execute(text(
        "INSERT INTO john_journal (compte_id, compte, action, args, confirme, ok, resume) "
        "VALUES (:cid, :c, :a, CAST(:ar AS jsonb), :cf, :ok, :r)"),
        {"cid": compte_id, "c": (compte or None) and compte[:120], "a": action[:48],
         "ar": json.dumps(args, ensure_ascii=False, default=str), "cf": confirme,
         "ok": ok, "r": resume})


def dernieres(db, n: int = 30) -> list[dict]:
    """Les N dernières lignes de journal (pour l'onglet / le carnet). Heures en ISO Réunion."""
    ensure(db)
    rows = db.execute(text(
        "SELECT ts, compte, action, args, confirme, ok, resume FROM john_journal "
        "ORDER BY ts DESC LIMIT :n"), {"n": max(1, min(n, 200))}).mappings().all()
    return [{"ts": r["ts"].isoformat(), "compte": r["compte"], "action": r["action"],
             "args": r["args"], "confirme": r["confirme"], "ok": r["ok"], "resume": r["resume"]}
            for r in rows]
