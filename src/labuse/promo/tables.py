"""PROMO-1 (P1) — RÉFÉRENTIEL des PROGRAMMES publiés par les promoteurs sur leur propre site.

DOCTRINE CONTENU (mandat) : on ne stocke QUE des FAITS et un LIEN — jamais les photos ni les textes
descriptifs des promoteurs (droit d'auteur), exactement comme le Radar collecté. Les colonnes ci-dessous
ne portent donc AUCUN visuel ni aucun descriptif : promoteur, nom du programme, commune, l'URL de la page,
la provenance et la date de relevé. Le rattachement à une OPÉRATION (P3) est stocké par les COORDONNÉES
STABLES de l'opération (SIREN + commune + année), pas par un id d'opération (les opérations sont
recalculées à la volée par union-find, elles n'ont pas d'id persistant).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

DDL = """
CREATE TABLE IF NOT EXISTS programmes (
  id              serial PRIMARY KEY,
  promoteur_siren text,                       -- SIREN du promoteur si connu (rattachement fiable)
  promoteur_nom   text NOT NULL,              -- nom du promoteur (toujours présent)
  nom             text NOT NULL,              -- nom du programme (un FAIT, pas un texte marketing)
  commune         text,                       -- commune déclarée sur la page
  url             text,                        -- URL de la page du programme (si individuelle) — le LIEN
  url_portfolio   text NOT NULL,              -- URL du portfolio d'où le programme a été relevé (provenance)
  source          text NOT NULL,              -- 'collecte_ia' | 'saisie_admin'
  annee           int,                         -- année (livraison/commercialisation) si relevée — sert P3
  date_releve     date NOT NULL DEFAULT current_date,
  -- rattachement P3 à une OPÉRATION, par ses coordonnées stables (jamais un id volatil) :
  op_siren        text,
  op_commune      text,
  op_annee        int,
  rattachement_confiance real,
  rattachement_mode text,                     -- 'auto' | 'manuel' | NULL (non rattaché)
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_programmes_promoteur ON programmes (promoteur_siren, promoteur_nom);
CREATE INDEX IF NOT EXISTS idx_programmes_rattach   ON programmes (op_siren, op_commune, op_annee);
-- un même programme (par son URL) n'entre qu'une fois ; les programmes sans URL individuelle sont
-- dédoublonnés à la validation (promoteur + nom + commune).
CREATE UNIQUE INDEX IF NOT EXISTS uq_programmes_url ON programmes (url) WHERE url IS NOT NULL;
"""


def ensure_tables(engine: Engine) -> None:
    """Crée la table `programmes` (idempotent). Split FIX-GB-011 (jamais de `split(';')` naïf)."""
    from ..db import sql_statements
    with engine.begin() as c:
        for stmt in sql_statements(DDL):
            if stmt.strip():
                c.execute(text(stmt))
