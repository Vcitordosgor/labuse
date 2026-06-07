"""Ingestion EN MASSE du cadastre depuis cadastre.data.gouv.fr (Etalab)  [✓ live].

Brief §4 : on ne boucle PAS l'API Carto sur 40 000 parcelles. On télécharge le
GeoJSON bulk de la commune (PCI/DGFiP, millésimé par Etalab) et on ingère en base.

Format Etalab (≠ API Carto) : properties = {id, commune, prefixe, section, numero,
contenance, ...} où `id` EST l'IDU 14 caractères. Géométries en 4326 ; surface
recalculée en 2975 à l'insertion (cf. connectors/cadastre.ingest_parcels).
"""
from __future__ import annotations

import gzip
import json

import httpx

from .. import constants
from ..config import get_settings

BULK_URL = (
    "https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/"
    "communes/{dep}/{insee}/cadastre-{insee}-parcelles.json.gz"
)


def _dep(insee: str) -> str:
    """Préfixe département : 3 car. en outre-mer (974…), 2 en métropole."""
    return insee[:3] if insee.startswith("97") else insee[:2]


def download_parcelles(insee: str, timeout: float | None = None) -> dict:
    """Télécharge + décompresse le GeoJSON bulk des parcelles de la commune."""
    url = BULK_URL.format(dep=_dep(insee), insee=insee)
    to = max(timeout or get_settings().http_timeout_s, 90.0)
    with httpx.Client(timeout=to, headers={"User-Agent": constants.USER_AGENT}, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        return json.loads(gzip.decompress(r.content))


def parse_etalab(fc: dict) -> list[dict]:
    """FeatureCollection Etalab → parcelles normalisées (idu = `id`)."""
    out: list[dict] = []
    for f in fc.get("features", []):
        p = f.get("properties") or {}
        idu = p.get("id")
        if not idu or not f.get("geometry"):
            continue
        out.append({
            "idu": str(idu),
            "commune": p.get("commune"),
            "section": p.get("section"),
            "numero": str(p["numero"]) if p.get("numero") is not None else None,
            "contenance": p.get("contenance"),
            "geometry": f["geometry"],
        })
    return out


def filter_bbox(parcels: list[dict], bbox: tuple[float, float, float, float] | None) -> list[dict]:
    """Restreint à un sous-ensemble borné (minlon, minlat, maxlon, maxlat) — brief : borné d'abord."""
    if not bbox:
        return parcels
    from shapely.geometry import box, shape

    b = box(*bbox)
    return [p for p in parcels if shape(p["geometry"]).intersects(b)]
