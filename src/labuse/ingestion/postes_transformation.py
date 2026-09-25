"""GEOPF-3 — INGESTION POSTES DE TRANSFORMATION (IGN BD TOPO via Géoplateforme WFS) →
spatial_layers kind='poste_transformation'.

Postes de transformation électriques (BD TOPO `poste_de_transformation`, emprises surfaciques).
Utile au foncier : la distance au poste le plus proche conditionne le coût de raccordement d'un
projet et signale une infrastructure électrique de proximité. On stocke l'EMPRISE ; la distance
se calcule côté fiche (tiroir Réseaux), jamais figée ici.

Affiché dans le groupe RÉSEAUX, à côté des lignes HT/MT et des pylônes.

100 % LECTURE — WFS ouvert (Licence Ouverte IGN, BD TOPO® V3). Île entière (bbox 974),
commune=NULL. Idempotent : purge kind='poste_transformation' puis réinsère. Source data_sources
= « BD TOPO IGN » (déjà au catalogue, sonde sentinelle bd-topo-r partagée).
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.wfs import WfsConnector

ILE_BBOX = (55.20, -21.42, 55.90, -20.85)
TYPENAME = "BDTOPO_V3:poste_de_transformation"
SOURCE_NAME = "BD TOPO IGN"
KIND = "poste_transformation"


def build_postes_transformation(session: Session, log=lambda *_: None) -> dict:
    """Ingère les postes de transformation BD TOPO de La Réunion. Renvoie {'poste_transformation': n}."""
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
            topo = p.get("toponyme")
            attrs = {"cleabs": p.get("cleabs"), "toponyme": topo,
                     "importance": p.get("importance"), "etat": p.get("etat_de_l_objet"),
                     "sources": p.get("sources"), "date_creation": p.get("date_creation"),
                     "date_modification": p.get("date_modification"),
                     "source": "BD TOPO IGN (Géoplateforme WFS) — poste_de_transformation"}
            session.execute(text(
                """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune)
                   VALUES (:k, NULL, :nm,
                           ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))),
                           CAST(:a AS jsonb), :sid, NULL)"""),
                {"k": KIND, "nm": topo or "Poste de transformation", "g": json.dumps(f["geometry"]),
                 "a": json.dumps(attrs), "sid": sid})
            n += 1
        if len(feats) < page:
            break
        start += page
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                    {"n": SOURCE_NAME})
    session.flush()
    log(f"  poste_transformation: {n}")
    return {"poste_transformation": n}
