"""Carte de situation du rapport Flash — tuiles raster LIBRES + contour de la parcelle.

Fond OpenStreetMap (ODbL, attribution obligatoire — imprimée sous la carte), tuiles
téléchargées avec un User-Agent identifié et mises en cache disque (politesse OSM),
embarquées en data-URI dans le HTML (WeasyPrint ne sort JAMAIS sur le réseau au rendu).
Réseau indisponible → retourne None : la page de garde s'affiche sans carte (section
conditionnelle, comme le reste du rapport).
"""
from __future__ import annotations

import base64
import json
import logging
import math
from pathlib import Path

import httpx

log = logging.getLogger("labuse.flash")

TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TILE_PX = 256
USER_AGENT = "LABUSE-Flash/1.0 (rapport parcelle; contact@labuse.immo)"
ATTRIBUTION = "© OpenStreetMap contributors (ODbL)"
# Vue cible en pixels CSS (ratio ~8/5, pleine largeur A4 utile).
VIEW_W, VIEW_H = 720, 450
ZOOM_MAX, ZOOM_MIN = 18, 12


def _lonlat_to_px(lon: float, lat: float, z: int) -> tuple[float, float]:
    """Web Mercator → pixels monde au zoom z (convention tuiles OSM)."""
    n = TILE_PX * (2 ** z)
    x = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n
    return x, y


def _rings(geojson: dict) -> list[list[tuple[float, float]]]:
    """Anneaux extérieurs (lon, lat) d'un Polygon/MultiPolygon/GeometryCollection."""
    t = geojson.get("type")
    if t == "Polygon":
        return [geojson["coordinates"][0]]
    if t == "MultiPolygon":
        return [poly[0] for poly in geojson["coordinates"]]
    if t == "GeometryCollection":
        out: list = []
        for g in geojson.get("geometries", []):
            out.extend(_rings(g))
        return out
    return []


def _fetch_tile(z: int, x: int, y: int, cache_dir: Path, client: httpx.Client) -> bytes | None:
    cached = cache_dir / f"{z}_{x}_{y}.png"
    if cached.exists():
        return cached.read_bytes()
    resp = client.get(TILE_URL.format(z=z, x=x, y=y))
    resp.raise_for_status()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(resp.content)
    return resp.content


def build_situation_map(parcel_geojson: str, cache_dir: Path,
                        timeout_s: float = 10.0) -> dict | None:
    """Prépare la carte de situation : tuiles positionnées + tracé SVG de la parcelle.

    Retourne un dict prêt pour le template (tiles, polygones en px, dimensions,
    attribution), ou None si le fond de carte est indisponible (réseau) — le rapport
    se génère alors sans carte, jamais en erreur.
    """
    try:
        gj = json.loads(parcel_geojson)
        rings = _rings(gj)
        if not rings:
            return None
        lons = [c[0] for ring in rings for c in ring]
        lats = [c[1] for ring in rings for c in ring]
        bbox = (min(lons), min(lats), max(lons), max(lats))

        # Zoom le plus serré où la parcelle tient dans ~55 % de la vue (contexte autour).
        zoom = ZOOM_MIN
        for z in range(ZOOM_MAX, ZOOM_MIN - 1, -1):
            x0, y1 = _lonlat_to_px(bbox[0], bbox[1], z)
            x1, y0 = _lonlat_to_px(bbox[2], bbox[3], z)
            if (x1 - x0) <= VIEW_W * 0.55 and (y1 - y0) <= VIEW_H * 0.55:
                zoom = z
                break

        cx, cy = _lonlat_to_px((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2, zoom)
        left, top = cx - VIEW_W / 2, cy - VIEW_H / 2

        tx0, ty0 = int(left // TILE_PX), int(top // TILE_PX)
        tx1, ty1 = int((left + VIEW_W) // TILE_PX), int((top + VIEW_H) // TILE_PX)
        n_max = 2 ** zoom - 1
        tiles = []
        with httpx.Client(timeout=timeout_s, headers={"User-Agent": USER_AGENT}) as client:
            for tx in range(tx0, tx1 + 1):
                for ty in range(ty0, ty1 + 1):
                    if not (0 <= tx <= n_max and 0 <= ty <= n_max):
                        continue
                    png = _fetch_tile(zoom, tx, ty, cache_dir, client)
                    tiles.append({
                        "left": round(tx * TILE_PX - left),
                        "top": round(ty * TILE_PX - top),
                        "data_uri": "data:image/png;base64," + base64.b64encode(png).decode(),
                    })
        polygons = []
        for ring in rings:
            pts = []
            for lon, lat in ring:
                px, py = _lonlat_to_px(lon, lat, zoom)
                pts.append(f"{px - left:.1f},{py - top:.1f}")
            polygons.append(" ".join(pts))
        return {"width": VIEW_W, "height": VIEW_H, "tiles": tiles,
                "polygons": polygons, "attribution": ATTRIBUTION, "zoom": zoom}
    except Exception as exc:  # noqa: BLE001 — la carte est un plus, jamais un bloqueur
        log.warning("carte de situation indisponible (%s: %s) — rapport sans carte",
                    type(exc).__name__, exc)
        return None
