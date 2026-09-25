"""GEOPF-3 — INGESTION MESURES COMPENSATOIRES (GéoMCE via Géoplateforme WFS) →
spatial_layers kind='mesures_compensatoires'.

Géoportail des mesures compensatoires (GéoMCE, MTE / OFB / DREAL) : emprises des mesures de
compensation écologique imposées à un maître d'ouvrage au titre de la séquence Éviter-Réduire-
Compenser (ERC). Sur une parcelle, une mesure compensatoire = obligation écologique dormante
(gestion imposée, non-constructibilité de fait) → une CONTRAINTE (point unique
servitudes.contraintes_parcelle → « Pièges et risques » + fiche).

Trois géométries : surfaciques (polygones, couverture mesurable), linéaires, ponctuelles. Toutes
sous le même kind, subtype = 'surface' | 'ligne' | 'point'. Île entière, commune=NULL (une mesure
couvre plusieurs communes). Idempotent : purge kind puis réinsère.

100 % LECTURE — Licence Ouverte 2.0 (Etalab). Le maître d'ouvrage est « non diffusable » à la
source (on ne l'invente pas). Source data_sources = « GéoMCE — mesures compensatoires ».
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.wfs import WfsConnector

ILE_BBOX = (55.20, -21.42, 55.90, -20.85)
# (typename WFS, subtype servi selon la géométrie).
_LAYERS = [("MESURES_COMPENSATOIRES:emprises_polygones", "surface"),
           ("MESURES_COMPENSATOIRES:emprises_lineaires", "ligne"),
           ("MESURES_COMPENSATOIRES:emprises_ponctuelles", "point")]
SOURCE_NAME = "GéoMCE — mesures compensatoires"
KIND = "mesures_compensatoires"


def build_mesures_compensatoires(session: Session, log=lambda *_: None) -> dict:
    """Ingère les mesures compensatoires (GéoMCE) de La Réunion. Renvoie {subtype: n}."""
    wfs = WfsConnector("geoplateforme_wfs")
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).scalar()
    session.execute(text("DELETE FROM spatial_layers WHERE kind = :k"), {"k": KIND})
    counts: dict[str, int] = {}
    for typename, subtype in _LAYERS:
        fc = wfs.fetch_layer("geoplateforme_wfs", typename, bbox=ILE_BBOX, max_features=2000)
        n = 0
        for f in fc.get("features", []) or []:
            if not f.get("geometry"):
                continue
            p = f.get("properties") or {}
            projet = (p.get("projet") or "Mesure compensatoire")[:255]
            attrs = {"identifiant": p.get("identifiant"), "projet": p.get("projet"),
                     "theme": p.get("theme"), "type_procedure": p.get("type_procedure"),
                     "date_decision": p.get("date_decision"), "classe": p.get("classe"),
                     "type_mesure": p.get("type_mesure"), "categorie": p.get("categorie"),
                     "sous_categorie": p.get("sous_categorie"),
                     "liste_communes": p.get("liste_communes"),
                     "source": "GéoMCE (MTE/OFB via Géoplateforme WFS)"}
            session.execute(text(
                """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune)
                   VALUES (:k, :s, :nm,
                           ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))),
                           CAST(:a AS jsonb), :sid, NULL)"""),
                {"k": KIND, "s": subtype, "nm": projet, "g": json.dumps(f["geometry"]),
                 "a": json.dumps(attrs), "sid": sid})
            n += 1
        counts[subtype] = n
        log(f"  mesures_compensatoires {subtype}: {n}")
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                    {"n": SOURCE_NAME})
    session.flush()
    return counts
