"""CIRCUIT-1 lot 3.6 — LE JOURNAL DES GESTES : Injecter, Calculer, Basculer, Revenir, purge
et agents écrivent une ligne `circuit_journal(ts, geste, cible, par, resultat, details)`.
Le « qui » manquant pour Injecter et Calculer (constat CIRCUIT-0 Q7.4) est comblé ici.
Jamais bloquant : un journal qui refuse d'écrire ne casse pas le geste (log.error, pas raise).
"""
from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import text

log = logging.getLogger("labuse.circuit_journal")

DDL = """
CREATE TABLE IF NOT EXISTS circuit_journal (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  geste varchar(24) NOT NULL,      -- injecter | calculer | basculer | revenir | purger | agent | job | filtre | controle
  cible text NOT NULL,             -- source, run, réservoir…
  par varchar(120),                -- qui (email admin, 'cron', 'cli')
  resultat varchar(24) NOT NULL,   -- lance | ok | echec | refuse
  details jsonb,
  lot varchar(40)                  -- CIRCUIT-P2 (lot 4.1) : identifiant de PASSAGE groupé (un job
                                   -- de filtres sur 39 sources, une volée d'agents) → une ligne
)
"""

GESTES = ("injecter", "calculer", "basculer", "revenir", "purger", "agent", "job", "filtre",
          "controle")

# ── CIRCUIT-P2 (lot 4.3) — les CATÉGORIES de geste, en français, DANS L'ORDRE FIXE de la barre du
#    journal (présentes même vides). Un geste stocké → une catégorie ; « tous » est ajouté au front.
CATEGORIES = [
    ("vanne", "vanne"), ("calcul", "calcul"), ("bascule", "bascule"), ("agent", "agent"),
    ("controle", "contrôle"), ("filtre", "filtre"), ("sonde", "sonde"), ("cron", "cron"),
]
CATEGORIE_LABEL = dict(CATEGORIES)
#: stored geste → catégorie d'affichage (les libellés techniques ne remontent jamais tels quels).
GESTE_CATEGORIE = {
    "injecter": "vanne", "calculer": "calcul", "basculer": "bascule",
    "revenir": "filtre",          # « revenir à la précédente » = retour d'une version filtrée
    "agent": "agent", "controle": "controle", "filtre": "filtre",
    "sonde": "sonde", "job": "cron", "purger": "cron",
}


def categorie_de(geste: str) -> str:
    return GESTE_CATEGORIE.get(geste, geste)


def gestes_de_categorie(categorie: str) -> list[str]:
    """Les gestes stockés qui tombent dans une catégorie (pour filtrer le journal)."""
    return [g for g, c in GESTE_CATEGORIE.items() if c == categorie] or [categorie]


def nouveau_lot() -> str:
    """Un identifiant de passage groupé (un job de filtres, une volée d'agents)."""
    return uuid.uuid4().hex[:32]


#: CIRCUIT-P2 (lot 4.4) — « par » dit un NOM, jamais un rôle technique (« cli », « admin »).
_PAR_NOM = {None: "système", "": "système", "cli": "système", "cron": "système", "admin": "Vic"}


def par_nom(par: str | None) -> str:
    """Le nom lisible d'un acteur : « cli » → système, « admin » → Vic ; un nom déjà propre
    (« système », « ingest-catnat », un e-mail) est gardé tel quel."""
    return _PAR_NOM.get((par or "").strip() or None, (par or "").strip() or "système")


def ensure(db) -> None:
    db.execute(text(DDL))
    # CIRCUIT-P2 (lot 4.1) — la colonne `lot` peut manquer sur une table d'avant : ajout idempotent.
    db.execute(text("ALTER TABLE circuit_journal ADD COLUMN IF NOT EXISTS lot varchar(40)"))


def journaliser(db, geste: str, cible: str, par: str | None, resultat: str,
                details: dict | None = None, *, lot: str | None = None) -> None:
    """Une ligne de journal — le geste continue même si l'écriture échoue (jamais bloquant).
    `lot` (CIRCUIT-P2) : marque un passage groupé (mêmes lot → une seule ligne au journal)."""
    try:
        ensure(db)
        db.execute(text(
            "INSERT INTO circuit_journal (geste, cible, par, resultat, details, lot) "
            "VALUES (:g, :c, :p, :r, :d, :l)"),
            {"g": geste, "c": cible[:500], "p": (par or "")[:120] or None, "r": resultat,
             "d": json.dumps(details or {}, ensure_ascii=False, default=str), "l": lot})
    except Exception:  # noqa: BLE001
        log.error("circuit_journal : écriture impossible (geste=%s cible=%s)", geste, cible)
