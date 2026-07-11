"""Lot 7 Habitat Solaire — capacités d'accueil du réseau (best effort, ZNI = EDF SEI).

Trouvé sur le portail EDF SEI (Data Fair) : « Capacités d'accueil du réseau -
Corse & Outre-Mer », filtré territoire Réunion → 24 postes sources, capacité
restante S3REnR en MW, MAJ trimestrielle.

LIMITE ASSUMÉE : le jeu « Postes sources - La Réunion » est passé isMetaOnly
(« données de cartographie… retirées afin de renforcer la sécurité publique ») —
AUCUNE géométrie publique. grid_capacity porte donc les capacités PAR POSTE avec
geom NULL ; la colonne dist_poste_source_m de la vue tertiaire reste NULL.
"""
from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from .habitat_solaire_schema import ensure_schema

DATASET_URL = ("https://opendata-reunion.edf.fr/data-fair/api/v1/datasets/"
               "b93j4pbyzvjlyd7d85n1cmzp/lines")


def ingest(session: Session) -> dict[str, Any]:
    ensure_schema(session)
    with httpx.Client(timeout=get_settings().http_timeout_s,
                      headers={"User-Agent": "labuse/habitat-solaire"}) as client:
        data = client.get(DATASET_URL, params={
            "qs": 'territoire:("Réunion")', "size": 200}).raise_for_status().json()
    rows = data.get("results", [])
    session.execute(text("DELETE FROM grid_capacity"))
    for r in rows:
        session.execute(text("""
            INSERT INTO grid_capacity (poste_source, capa_dispo_mw, source)
            VALUES (:poste, :capa,
                    'EDF SEI — Capacités d''accueil Corse & Outre-Mer (MAJ ' || :maj || ')')
        """), {"poste": r.get("poste"),
               "capa": r.get("capacite_restante_s2renrs3renr"),
               "maj": str(r.get("date_de_la_mise_a_jour"))})
    dispo = session.execute(text(
        "SELECT count(*) FILTER (WHERE capa_dispo_mw > 0), sum(capa_dispo_mw)"
        " FROM grid_capacity")).one()
    return {"postes": len(rows), "postes_avec_capacite": dispo[0] or 0,
            "capacite_totale_mw": float(dispo[1] or 0)}
