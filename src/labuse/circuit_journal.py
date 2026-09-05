"""CIRCUIT-1 lot 3.6 — LE JOURNAL DES GESTES : Injecter, Calculer, Basculer, Revenir, purge
et agents écrivent une ligne `circuit_journal(ts, geste, cible, par, resultat, details)`.
Le « qui » manquant pour Injecter et Calculer (constat CIRCUIT-0 Q7.4) est comblé ici.
Jamais bloquant : un journal qui refuse d'écrire ne casse pas le geste (log.error, pas raise).
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import text

log = logging.getLogger("labuse.circuit_journal")

DDL = """
CREATE TABLE IF NOT EXISTS circuit_journal (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  geste varchar(24) NOT NULL,      -- injecter | calculer | basculer | revenir | purger | agent | job | filtre
  cible text NOT NULL,             -- source, run, réservoir…
  par varchar(120),                -- qui (email admin, 'cron', 'cli')
  resultat varchar(24) NOT NULL,   -- lance | ok | echec | refuse
  details jsonb
)
"""

GESTES = ("injecter", "calculer", "basculer", "revenir", "purger", "agent", "job", "filtre")


def ensure(db) -> None:
    db.execute(text(DDL))


def journaliser(db, geste: str, cible: str, par: str | None, resultat: str,
                details: dict | None = None) -> None:
    """Une ligne de journal — le geste continue même si l'écriture échoue (jamais bloquant)."""
    try:
        ensure(db)
        db.execute(text(
            "INSERT INTO circuit_journal (geste, cible, par, resultat, details) "
            "VALUES (:g, :c, :p, :r, :d)"),
            {"g": geste, "c": cible[:500], "p": (par or "")[:120] or None, "r": resultat,
             "d": json.dumps(details or {}, ensure_ascii=False, default=str)})
    except Exception:  # noqa: BLE001
        log.error("circuit_journal : écriture impossible (geste=%s cible=%s)", geste, cible)
