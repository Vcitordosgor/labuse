"""COHERENCE-FIX-1 (lot E) — POPULATION LÉGALE INSEE, au millésime le plus récent, avec l'année.

Constat COHERENCE-1 (FAUX-CLIENT n° 6) : la fiche commune lisait les habitants dans Sudocuh
(fichier DGALN arrêté au 31/12/2024, qui reporte un millésime de recensement plus ancien) —
10 communes sur 24 servies 5-8 % SOUS la population légale en vigueur, sans afficher l'année.
Vrai hier, faux aujourd'hui, sans date pour le dire.

Ici : la population municipale LÉGALE en vigueur, lue de geo.api.gouv.fr (qui republie les
populations légales INSEE en vigueur au 1er janvier), stockée dans `population_legale` avec son
MILLÉSIME (l'année de référence du recensement : N−3 pour une entrée en vigueur au 1/1/N —
convention INSEE) et servie partout étiquetée « Population légale <millésime> (INSEE) ».
Sudocuh reste le repli si la table n'est pas peuplée (avec SON millésime affiché).

    labuse population-legale-sync         # 24 communes, ~2 s (geo.api.gouv)
"""
from __future__ import annotations

import datetime as _dt

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE_NAME = "Population légale (INSEE via geo.api.gouv)"
API_URL = "https://geo.api.gouv.fr/departements/974/communes?fields=population,code,nom"
DOC_URL = "https://geo.api.gouv.fr/decoupage-administratif/communes"

_DDL = """
CREATE TABLE IF NOT EXISTS population_legale (
  insee varchar(5) PRIMARY KEY,
  commune text NOT NULL,
  pop_mun integer NOT NULL,
  millesime integer NOT NULL,
  source text NOT NULL DEFAULT 'geo.api.gouv (populations légales INSEE)',
  importe_le timestamptz NOT NULL DEFAULT now()
)
"""


def millesime_en_vigueur(aujourdhui: _dt.date | None = None) -> int:
    """L'année de référence des populations légales EN VIGUEUR : N−3 (convention INSEE — les
    populations légales « millésimées A » entrent en vigueur au 1er janvier A+3)."""
    d = aujourdhui or _dt.date.today()
    return d.year - 3


def _ensure_source(session: Session) -> None:
    """Upsert de la ligne catalogue `data_sources` (idempotent) — le millésime y entre AUSSI
    (c'est lui que la clé de fraîcheur des caches hache, lot A)."""
    from ..sources_catalog import normalize_status
    mil = str(millesime_en_vigueur())
    statut = normalize_status("connecte")
    row = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).first()
    if row is None:
        session.execute(text(
            """INSERT INTO data_sources (name, category, provider, access_type, status,
                   reliability_level, documentation_url, endpoint_url, source_millesime,
                   source_cadence, last_sync_at)
               VALUES (:n, 'demographie', 'INSEE via geo.api.gouv.fr', 'api', :st, 'verifie',
                   :doc, :api, :mil, 'annuelle', now())"""),
            {"n": SOURCE_NAME, "st": statut, "doc": DOC_URL, "api": API_URL, "mil": mil})
    else:
        session.execute(text(
            "UPDATE data_sources SET source_millesime = :mil, last_sync_at = now() WHERE name = :n"),
            {"mil": mil, "n": SOURCE_NAME})


def sync(session: Session, millesime: int | None = None) -> dict:
    """(Re)charge les 24 populations légales. Idempotent (upsert par INSEE). Bruyant sur un
    payload anormal (moins de 20 communes → on n'écrase RIEN)."""
    mil = millesime or millesime_en_vigueur()
    session.execute(text(_DDL))
    r = httpx.get(API_URL, timeout=30)
    r.raise_for_status()
    rows = [c for c in r.json() if c.get("population") is not None]
    if len(rows) < 20:
        raise RuntimeError(f"population-legale-sync : {len(rows)} communes reçues (< 20) — "
                           "payload anormal, rien n'est écrit.")
    for c in rows:
        session.execute(text(
            """INSERT INTO population_legale (insee, commune, pop_mun, millesime)
               VALUES (:i, :c, :p, :m)
               ON CONFLICT (insee) DO UPDATE SET commune = EXCLUDED.commune,
                 pop_mun = EXCLUDED.pop_mun, millesime = EXCLUDED.millesime, importe_le = now()"""),
            {"i": c["code"], "c": c["nom"], "p": int(c["population"]), "m": mil})
    _ensure_source(session)
    return {"communes": len(rows), "millesime": mil}


def lire(session: Session, insee: str) -> dict | None:
    """La population légale servie (fiche commune, Quartier, Étude de zone, Dossier) : pop_mun,
    millésime (année) et l'étiquette prête à afficher. None si la table n'est pas peuplée."""
    try:
        row = session.execute(text(
            "SELECT pop_mun, millesime FROM population_legale WHERE insee = :i"),
            {"i": insee}).mappings().first()
    except Exception:  # noqa: BLE001 — table absente (base de test) : repli Sudocuh à l'appelant
        session.rollback()
        return None
    if not row:
        return None
    return {"pop_mun": int(row["pop_mun"]), "millesime": int(row["millesime"]),
            "etiquette": f"Population légale {row['millesime']} (INSEE)"}
