"""LOT 6 (data-gap) — Zone des 50 pas géométriques (limite haute, DEAL Réunion).

Source : WFS Lizmap DEAL 974 (QGIS Server), couche `LIMITE_HA` « Limite haute des 50 pas
géométriques » — 163 tronçons MultiLineString (~184 km), VÉRIFIÉ live 10/07/2026.
Généalogie (abstract WMS) : numérisée sur le cadastre de 1877, géoréférencée orthos 2012/1950 ;
attribut `Source` : 'historique' (158) ou 'Étude documentaire Février 2026' (5) — couche vivante.

⚠ La BANDE POLYGONALE des 50 pas n'est diffusée nulle part en open data (vérifié : data.gouv
= Mayotte seulement, PEIGEO en erreur, Géolittoral rien). APPROXIMATION documentée : on
matérialise un CORRIDOR de ±90 m autour de la limite haute (les 50 pas historiques = 81,20 m
depuis le rivage) → flag « parcelle AU CONTACT de la bande des 50 pas — régime foncier
spécifique à vérifier (cession encadrée, agence des 50 pas) ». Sur-inclusif côté terre par
construction : le libellé fiche dit « à vérifier », jamais « dans la bande ».
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

URL = ("https://deal974.lizmap.com/cartes/index.php/lizmap/service"
       "?repository=00cartogenerale&project=deal_reunion&SERVICE=WFS&VERSION=1.0.0"
       "&REQUEST=GetFeature&TYPENAME=LIMITE_HA&OUTPUTFORMAT=GeoJSON")
SOURCE_NAME = "50 pas géométriques — limite haute (DEAL)"
CORRIDOR_M = 90.0   # ~81,20 m historiques + marge de numérisation


def ingest_cinquante_pas(session: Session, run_id: int | None = None, log=print) -> dict:
    """Télécharge la limite haute et matérialise le corridor (idempotent)."""
    with httpx.Client(timeout=max(get_settings().http_timeout_s, 120.0),
                      headers={"User-Agent": constants.USER_AGENT}, follow_redirects=True) as c:
        r = c.get(URL)
        r.raise_for_status()
        feats = r.json().get("features") or []
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'cinquante_pas'"))
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).scalar()
    n = 0
    for f in feats:
        p = f.get("properties") or {}
        if not f.get("geometry"):
            continue
        session.execute(text(
            """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, ingestion_run_id)
               VALUES ('cinquante_pas', 'corridor_limite_haute', :n,
                       ST_Transform(ST_Buffer(ST_Transform(
                           ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326), 2975), :larg), 4326),
                       CAST(:a AS jsonb), :sid, :run)"""),
            {"n": f"Limite haute des 50 pas ({p.get('Source') or 'historique'})",
             "g": json.dumps(f["geometry"]), "larg": CORRIDOR_M,
             "a": json.dumps({"source_ligne": p.get("Source"), "longueur_km": p.get("Longueur"),
                              "corridor_m": CORRIDOR_M,
                              "genealogie": "cadastre 1877, géoréf. orthos 2012/1950"}),
             "sid": sid, "run": run_id})
        n += 1
    session.flush()
    return {"troncons": len(feats), "corridors": n}
