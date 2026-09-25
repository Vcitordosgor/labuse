"""GEOPF-3 — INGESTION LIEUX-DITS (BD NYME / BD TOPO toponymes IGN via Géoplateforme WFS) → table
`lieux_dits`.

Deux couches BD TOPO : `zone_d_habitation` (lieux-dits HABITÉS + quartiers, polygones — ex. Le
Guillaume, Bois de Nèfles) et `lieu_dit_non_habite` (points — ex. Grand Fond). On stocke un POINT
représentatif (centroïde des polygones), le toponyme, la nature et la commune (parcelle la plus
proche). Sert : (a) une 5ᵉ grammaire de recherche « Lieu-dit · … » (zoom au secteur) ; (b) la ligne
« Secteur » de la fiche parcelle (lieu-dit le plus proche, rayon borné).

100 % LECTURE — Licence Ouverte (IGN BD TOPO). Île entière. Idempotent : purge + réinsère.
Source data_sources = « BD NYME — lieux-dits (IGN) ».
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.wfs import WfsConnector

ILE_BBOX = (55.20, -21.42, 55.90, -20.85)
SOURCE_NAME = "BD NYME — lieux-dits (IGN)"

DDL = """
CREATE TABLE IF NOT EXISTS lieux_dits (
  id          serial PRIMARY KEY,
  cleabs      varchar(48),
  toponyme    varchar(255) NOT NULL,
  nature      varchar(64),
  habite      boolean NOT NULL DEFAULT false,
  commune     varchar(64),
  geom        geometry(Point, 4326) NOT NULL,
  geom_2975   geometry(Point, 2975)
);
CREATE INDEX IF NOT EXISTS lieux_dits_geom_gix ON lieux_dits USING gist (geom);
CREATE INDEX IF NOT EXISTS lieux_dits_geom2975_gix ON lieux_dits USING gist (geom_2975);
CREATE INDEX IF NOT EXISTS lieux_dits_topo_idx ON lieux_dits (lower(toponyme));
"""

# (typename, habité ?) — le point représentatif : centroïde pour les polygones, le point tel quel sinon.
_LAYERS = [("BDTOPO_V3:zone_d_habitation", True), ("BDTOPO_V3:lieu_dit_non_habite", False)]


def build_bd_nyme(session: Session, log=lambda *_: None) -> dict:
    """Ingère les lieux-dits BD NYME de La Réunion. Renvoie {'habite': n, 'non_habite': n}."""
    for stmt in DDL.strip().split(";\n"):
        if stmt.strip():
            session.execute(text(stmt))
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).scalar()
    session.execute(text("DELETE FROM lieux_dits"))
    wfs = WfsConnector("geoplateforme_wfs")
    counts = {"habite": 0, "non_habite": 0}
    for typename, habite in _LAYERS:
        start, page = 0, 2000
        while True:
            fc = wfs.fetch_layer("geoplateforme_wfs", typename, bbox=ILE_BBOX,
                                 max_features=page, start_index=start, sort_by="cleabs")
            feats = fc.get("features", []) or []
            for f in feats:
                g = f.get("geometry")
                p = f.get("properties") or {}
                topo = (p.get("toponyme") or "").strip()
                if not g or not topo:
                    continue
                # point représentatif (centroïde 4326) + commune = parcelle la plus proche.
                session.execute(text(
                    """INSERT INTO lieux_dits (cleabs, toponyme, nature, habite, commune, geom, geom_2975)
                       SELECT :cl, :topo, :nat, :hab,
                              (SELECT commune FROM parcels
                               ORDER BY geom_2975 <-> ST_Transform(pt.g, 2975) LIMIT 1),
                              pt.g, ST_Transform(pt.g, 2975)
                       FROM (SELECT ST_PointOnSurface(
                                 ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geo), 4326))) AS g) pt"""),
                    {"cl": p.get("cleabs"), "topo": topo[:255], "nat": p.get("nature"),
                     "hab": habite, "geo": json.dumps(g)})
                counts["habite" if habite else "non_habite"] += 1
            if len(feats) < page:
                break
            start += page
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                    {"n": SOURCE_NAME})
    session.flush()
    log(f"  lieux_dits habité: {counts['habite']}, non habité: {counts['non_habite']}")
    return counts
