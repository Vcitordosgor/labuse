"""Ingestion cadastre — ÉCRITURE en base des parcelles (M-C/F6).

Déplacé de `connectors/cadastre.py` : le package `connectors/` doit rester de la LECTURE
pure (clients d'API externes) ; l'écriture en base (upsert parcels) vit dans `ingestion/`.
Le connecteur (`CadastreConnector`, `parse_parcelles`) reste dans connectors/ ; c'est SON
résultat qu'on ingère ici.
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session


def ingest_parcels(session: Session, parcels: list[dict], commune_name: str | None,
                   run_id: int | None, origine: str | None = None) -> int:
    """Insère des parcelles (géométrie GeoJSON → 4326), surface/centroïde calculés en base.

    Surface mesurée en 2975 (jamais en degrés). Upsert par IDU. Géométrie passée par
    ST_MakeValid : quelques parcelles cadastrales sont topologiquement invalides
    (anneaux auto-sécants) et feraient échouer ST_Intersection côté cascade.

    `origine` (Lot A) : 'audit' pour un ajout à la demande. Posé À L'INSERTION UNIQUEMENT —
    l'upsert NE TOUCHE JAMAIS l'origine d'une parcelle déjà présente (clause SET sans
    `origine`), pour qu'un audit recoupant une parcelle déjà au référentiel (ex. polygone
    qui chevauche des parcelles connues) ne la marque pas 'audit' à tort. NB : NULL = origine
    « référentiel » ; un COALESCE l'écraserait à tort par 'audit' — d'où l'omission.
    """
    n = 0
    for p in parcels:
        gj = json.dumps(p["geometry"])
        session.execute(
            text(
                """
                INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox, ingestion_run_id, origine)
                VALUES (
                    :idu, :commune, :section, :numero,
                    ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)),
                    ST_Area(ST_Transform(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)), 2975)),
                    ST_Centroid(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))),
                    ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))),
                    :run, :origine
                )
                ON CONFLICT (idu) DO UPDATE SET
                    geom = EXCLUDED.geom, surface_m2 = EXCLUDED.surface_m2,
                    centroid = EXCLUDED.centroid, bbox = EXCLUDED.bbox, updated_at = now()
                """
            ),
            {"idu": p["idu"], "commune": commune_name or p.get("commune"),
             "section": p.get("section"), "numero": p.get("numero"), "gj": gj, "run": run_id,
             "origine": origine},
        )
        n += 1
    session.flush()
    return n
