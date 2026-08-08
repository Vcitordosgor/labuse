"""Connecteur Cadastre — API Carto IGN (PCI / Parcellaire Express)  [✓ vérifié §6].

    GET https://apicarto.ign.fr/api/cadastre/parcelle?code_insee=..&section=..&numero=..
    (ou `geom` = GeoJSON ; source_ign=PCI)

On utilise PCI partout pour la cohérence des IDU (la BD Parcellaire est gelée
depuis 2019, §7bis). Le parsing est testé contre une fixture (réseau bloqué ici).
"""
from __future__ import annotations

import json
from typing import Any

from .base import Connector

BASE = "https://apicarto.ign.fr/api/cadastre"


def _build_idu(props: dict) -> str | None:
    """IDU 14 car. : privilégie le champ `idu` ; sinon reconstruit best-effort."""
    if props.get("idu"):
        return str(props["idu"])
    insee = props.get("code_insee") or ((props.get("code_dep", "") + props.get("code_com", "")) or None)
    com_abs = props.get("com_abs", "000")
    section = props.get("section")
    numero = props.get("numero")
    if not (insee and section and numero):
        return None
    return f"{insee}{com_abs}{section.zfill(2)}{str(numero).zfill(4)}"


def parse_parcelles(feature_collection: dict) -> list[dict[str, Any]]:
    """FeatureCollection API Carto → liste de parcelles normalisées."""
    out: list[dict[str, Any]] = []
    for feat in feature_collection.get("features", []):
        props = feat.get("properties", {}) or {}
        idu = _build_idu(props)
        if not idu or not feat.get("geometry"):
            continue
        out.append({
            "idu": idu,
            "commune": props.get("nom_com") or props.get("code_insee"),
            "code_insee": props.get("code_insee"),
            "section": props.get("section"),
            "numero": str(props.get("numero")) if props.get("numero") is not None else None,
            "contenance": props.get("contenance"),
            "geometry": feat["geometry"],
        })
    return out


# M-C (F6) : `ingest_parcels` (ÉCRITURE en base) a été DÉPLACÉE dans ingestion/cadastre_ingest.py —
# connectors/ reste de la lecture pure. Importer désormais :
#     from ..ingestion.cadastre_ingest import ingest_parcels


class CadastreConnector(Connector):
    name = "Cadastre (API Carto PCI)"
    test_url = f"{BASE}/parcelle"
    test_params = {"code_insee": "97415", "section": "AB", "numero": "0001", "source_ign": "PCI"}

    def fetch_by_section(self, code_insee: str, section: str, numero: str | None = None) -> dict:
        params = {"code_insee": code_insee, "section": section, "source_ign": "PCI"}
        if numero:
            params["numero"] = numero
        with self._client() as c:
            r = c.get(f"{BASE}/parcelle", params=params)
            r.raise_for_status()
            return r.json()

    def fetch_by_geom(self, geojson_geometry: dict) -> dict:
        with self._client() as c:
            r = c.get(f"{BASE}/parcelle", params={"geom": json.dumps(geojson_geometry), "source_ign": "PCI"})
            r.raise_for_status()
            return r.json()
