"""GEOPF-3 — INGESTION SCOT (Géoportail de l'Urbanisme via Géoplateforme WFS) →
spatial_layers kind='scot'.

Schéma de Cohérence Territoriale : le document de planification supra-communal (au-dessus du
PLU). Distinct du SAR (kind='sar', échelle régionale) et du PLU (zonage communal). On stocke le
PÉRIMÈTRE (polygone du territoire couvert) + le nom (title GPU) + la date d'approbation (lue dans
l'idurba CNIG `<siren>_SCOT_<AAAAMMJJ>` du périmètre) + le statut approuvé/en projet.

Sert deux usages : la couche carte (famille urbanisme) et la fiche commune (carte Urbanisme :
nom du SCOT + date d'approbation, par intersection commune × périmètre).

100 % LECTURE — Licence Ouverte (GPU). Île entière, commune=NULL (un SCOT couvre plusieurs
communes). Idempotent : purge kind='scot' puis réinsère. Source data_sources = « SCOT (GPU) ».
"""
from __future__ import annotations

import json
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.wfs import WfsConnector

ILE_BBOX = (55.20, -21.42, 55.90, -20.85)
SOURCE_NAME = "SCOT (GPU)"
KIND = "scot"

# idurba CNIG SCOT : "<siren>_SCOT_<AAAAMMJJ>" → date d'approbation du document.
_IDURBA_DATE = re.compile(r"_SCOT_(\d{4})(\d{2})(\d{2})")


def _date_approbation(idurba: str | None) -> str | None:
    if not idurba:
        return None
    m = _IDURBA_DATE.search(idurba)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def build_scot(session: Session, log=lambda *_: None) -> dict:
    """Ingère les périmètres SCOT de La Réunion (GPU). Renvoie {'scot': n}."""
    wfs = WfsConnector("geoplateforme_wfs")
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).scalar()
    # date d'approbation par partition, lue dans les périmètres (idurba).
    per = wfs.fetch_layer("geoplateforme_wfs", "wfs_scot:perimetre_scot", bbox=ILE_BBOX, max_features=200)
    dates: dict[str, str] = {}
    for f in per.get("features", []) or []:
        p = f.get("properties") or {}
        d = _date_approbation(p.get("idurba"))
        if p.get("partition") and d:
            dates[p["partition"]] = d
    session.execute(text("DELETE FROM spatial_layers WHERE kind = :k"), {"k": KIND})
    fc = wfs.fetch_layer("geoplateforme_wfs", "wfs_scot:scot", bbox=ILE_BBOX, max_features=200)
    n = 0
    for f in fc.get("features", []) or []:
        if not f.get("geometry"):
            continue
        p = f.get("properties") or {}
        title = (p.get("title") or "SCOT")[:255]
        partition = p.get("partition")
        approuve = bool(p.get("approved"))
        attrs = {"title": title, "partition": partition, "approuve": approuve,
                 "date_approbation": dates.get(partition),
                 "gpu_timestamp": p.get("gpu_timestamp"),
                 "statut": "approuvé" if approuve else "en projet",
                 "source": "Géoportail de l'urbanisme (GPU) — wfs_scot"}
        session.execute(text(
            """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune)
               VALUES (:k, :s, :nm,
                       ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))),
                       CAST(:a AS jsonb), :sid, NULL)"""),
            {"k": KIND, "s": ("approuve" if approuve else "projet"), "nm": title,
             "g": json.dumps(f["geometry"]), "a": json.dumps(attrs), "sid": sid})
        n += 1
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                    {"n": SOURCE_NAME})
    session.flush()
    log(f"  scot: {n}")
    return {"scot": n}
