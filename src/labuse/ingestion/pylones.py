"""GEOPF-3 — INGESTION PYLÔNES (IGN BD TOPO via Géoplateforme WFS) → spatial_layers kind='pylone'.

Supports du réseau électrique de transport (BD TOPO `pylone`, points). Utile au foncier : un
pylône sur ou au ras d'une parcelle = servitude de voisinage, gêne à l'implantation, champ
électromagnétique. On stocke le POINT ; la distance se calcule côté fiche (jamais figée ici).

Affiché dans le groupe RÉSEAUX, à côté des lignes HT/MT (le pylône porte la ligne HTB).

100 % LECTURE — WFS ouvert (Licence Ouverte IGN, BD TOPO® V3). Île entière (bbox 974),
commune=NULL (un pylône n'est pas rattaché à une commune à l'ingestion). Idempotent : purge
kind='pylone' puis réinsère. Source data_sources = « BD TOPO IGN » (déjà au catalogue, sonde
sentinelle bd-topo-r partagée).
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.wfs import WfsConnector

# bbox île (lon, lat, lon, lat) — Géoplateforme EPSG:4326 forme courte (cf. znieff).
ILE_BBOX = (55.20, -21.42, 55.90, -20.85)
TYPENAME = "BDTOPO_V3:pylone"
SOURCE_NAME = "BD TOPO IGN"
KIND = "pylone"


def build_pylones(session: Session, log=lambda *_: None) -> dict:
    """Ingère les pylônes électriques BD TOPO de La Réunion. Renvoie {'pylone': n}."""
    wfs = WfsConnector("geoplateforme_wfs")
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).scalar()
    session.execute(text("DELETE FROM spatial_layers WHERE kind = :k"), {"k": KIND})
    n, start, page = 0, 0, 2000
    while True:
        fc = wfs.fetch_layer("geoplateforme_wfs", TYPENAME, bbox=ILE_BBOX,
                             max_features=page, start_index=start, sort_by="cleabs")
        feats = fc.get("features", []) or []
        for f in feats:
            if not f.get("geometry"):
                continue
            p = f.get("properties") or {}
            attrs = {"cleabs": p.get("cleabs"), "etat": p.get("etat_de_l_objet"),
                     "hauteur": p.get("hauteur"), "date_creation": p.get("date_creation"),
                     "date_modification": p.get("date_modification"),
                     "source": "BD TOPO IGN (Géoplateforme WFS) — pylone"}
            session.execute(text(
                """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune)
                   VALUES (:k, NULL, :nm,
                           ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))),
                           CAST(:a AS jsonb), :sid, NULL)"""),
                {"k": KIND, "nm": "Pylône électrique", "g": json.dumps(f["geometry"]),
                 "a": json.dumps(attrs), "sid": sid})
            n += 1
        if len(feats) < page:
            break
        start += page
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                    {"n": SOURCE_NAME})
    session.flush()
    log(f"  pylone: {n}")
    return {"pylone": n}
