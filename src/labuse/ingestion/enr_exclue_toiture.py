"""GEOPF-3 — INGESTION ZONES INTERDITES AUX EnR HORS TOITURE (loi APER, OFB via Géoplateforme WFS)
→ spatial_layers kind='enr_exclue_hors_toiture'.

Loi APER (relative à l'accélération des énergies renouvelables) : certaines zones protégées sont
EXCLUES des aires d'accélération pour toutes les EnR TERRESTRES (au sol) — sauf les toitures, qui
restent possibles. Pour un projet solaire AU SOL, ces zones sont un filtre d'EXCLUSION. Le solaire
en toiture, lui, reste autorisé (on le dit — jamais une interdiction absolue).

Source OFB (INPN) : Parc national (cœur + aire d'adhésion), réserves naturelles. Île entière,
commune=NULL. Idempotent : purge kind puis réinsère.

100 % LECTURE — Licence Ouverte (OFB/INPN). Source data_sources = « Zones exclues EnR sauf toiture (OFB/APER) ».
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.wfs import WfsConnector

ILE_BBOX = (55.20, -21.42, 55.90, -20.85)
TYPENAME = "OFB_ZONES.EXCLUES.SAUF.TOITURE:zones_exclues_aires_acceleration_sauf_toiture"
SOURCE_NAME = "Zones exclues EnR sauf toiture (OFB/APER)"
KIND = "enr_exclue_hors_toiture"


def build_enr_exclue_toiture(session: Session, log=lambda *_: None) -> dict:
    """Ingère les zones d'exclusion EnR hors toiture (loi APER) de La Réunion. Renvoie {kind: n}."""
    wfs = WfsConnector("geoplateforme_wfs")
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).scalar()
    session.execute(text("DELETE FROM spatial_layers WHERE kind = :k"), {"k": KIND})
    fc = wfs.fetch_layer("geoplateforme_wfs", TYPENAME, bbox=ILE_BBOX, max_features=2000)
    n = 0
    for f in fc.get("features", []) or []:
        if not f.get("geometry"):
            continue
        p = f.get("properties") or {}
        nom = (p.get("nom_zone") or "Zone exclue EnR (hors toiture)")[:255]
        attrs = {"nom_zone": p.get("nom_zone"), "type_zone": p.get("type_zone"),
                 "code": p.get("code"), "gestionnaire": p.get("gest_site"),
                 "url_fiche": p.get("url_fiche"), "zonage": p.get("zonage"),
                 "source": "OFB/INPN (Géoplateforme WFS) — zones exclues aires d'accélération sauf toiture"}
        session.execute(text(
            """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune)
               VALUES (:k, :s, :nm,
                       ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))),
                       CAST(:a AS jsonb), :sid, NULL)"""),
            {"k": KIND, "s": (p.get("type_zone") or None), "nm": nom,
             "g": json.dumps(f["geometry"]), "a": json.dumps(attrs), "sid": sid})
        n += 1
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                    {"n": SOURCE_NAME})
    session.flush()
    log(f"  enr_exclue_hors_toiture: {n}")
    return {"enr_exclue_hors_toiture": n}
