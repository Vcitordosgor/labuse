"""GABARIT-3D-1 (pilote, étape 3) — PHOTO AÉRIENNE drapée.

Le SERVEUR tire l'orthophotographie IGN (Géoplateforme WMS) POUR LE CADRE de la scène, puis la met en
cache par identifiant de scène. Le navigateur n'appelle JAMAIS l'IGN directement : il demande cette image
au serveur (proxy). Le millésime (date de prise de vue) vient du graphe de mosaïquage BD ORTHO®.

Référentiel : RGR92 / UTM 40 Sud (EPSG:2975) — le même que le fond LiDAR, donc le drapage est aligné.
La photo n'entre PAS dans le PDF à ce stade.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

WMS_R = "https://data.geopf.fr/wms-r"        # orthophotographie (raster)
WMS_V = "https://data.geopf.fr/wms-v/ows"    # graphe de mosaïquage (millésime, vecteur)
LAYER_ORTHO = "ORTHOIMAGERY.ORTHOPHOTOS"
LAYER_GRAPHE = "ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE"
_UA = {"User-Agent": "labuse-gabarit3d/1.0"}
_MAX_PX = 1400

_CACHE = Path(__file__).resolve().parents[3] / "data" / "ortho_cache"   # data/ est hors-git


def _bbox_absolue(scene) -> Optional[tuple[float, float, float, float]]:
    """Cadre de la scène en EPSG:2975 absolu (cadre local + origine)."""
    t = scene.terrain if isinstance(scene.terrain, dict) else None
    if not t or not t.get("cadre") or not t.get("origin_2975"):
        return None
    c, (ox, oy) = t["cadre"], t["origin_2975"]
    return (c[0] + ox, c[1] + oy, c[2] + ox, c[3] + oy)


def _millesime(client, bbox) -> dict:
    """Millésime (date de prise de vue) au centre du cadre, via le graphe de mosaïquage. Best-effort."""
    # fenêtre SERRÉE (±2 m, 3×3 px) : une requête sur tout le cadre peut tomber sur une jointure de
    # mosaïque et ne rien renvoyer. On essaie le centre puis quelques points (service parfois capricieux).
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    qw, qh = (bbox[2] - bbox[0]) / 4, (bbox[3] - bbox[1]) / 4
    d = 2.0
    for px, py in ((cx, cy), (cx - qw, cy - qh), (cx + qw, cy + qh), (cx - qw, cy + qh)):
        try:
            r = client.get(WMS_V, params={
                "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetFeatureInfo",
                "LAYERS": LAYER_GRAPHE, "QUERY_LAYERS": LAYER_GRAPHE, "STYLES": "", "CRS": "EPSG:2975",
                "BBOX": f"{px - d},{py - d},{px + d},{py + d}", "WIDTH": 3, "HEIGHT": 3,
                "I": 1, "J": 1, "FORMAT": "image/png", "INFO_FORMAT": "application/json"})
            feats = r.json().get("features", [])
            if feats:
                p = feats[0].get("properties", {})
                dv = str(p.get("date_vol") or "").rstrip("Z")
                an = p.get("pva") or (dv[:4] if dv[:4].isdigit() else None)
                if an:
                    return {"millesime": int(an), "date_vol": dv or None}
        except Exception:  # noqa: BLE001 — le millésime ne doit jamais faire échouer la photo
            continue
    return {"millesime": None, "date_vol": None}


def ortho_pour_scene(scene, *, timeout: float = 8.0) -> Optional[dict]:
    """Retourne {png: bytes, millesime, date_vol, source} pour le cadre de la scène, ou None si indisponible.
    Mise en cache par identifiant de scène (png + méta JSON)."""
    bbox = _bbox_absolue(scene)
    if not bbox or not scene.scene_id:
        return None
    _CACHE.mkdir(parents=True, exist_ok=True)
    png_p, meta_p = _CACHE / f"{scene.scene_id}.png", _CACHE / f"{scene.scene_id}.json"
    if png_p.exists() and meta_p.exists():
        meta = json.loads(meta_p.read_text())
        return {"png": png_p.read_bytes(), **meta}

    w_m, h_m = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if w_m <= 0 or h_m <= 0:
        return None
    if w_m >= h_m:
        w = min(_MAX_PX, max(256, int(w_m * 4))); h = max(1, int(w * h_m / w_m))
    else:
        h = min(_MAX_PX, max(256, int(h_m * 4))); w = max(1, int(h * w_m / h_m))

    import httpx
    try:
        with httpx.Client(timeout=timeout, headers=_UA) as client:
            r = client.get(WMS_R, params={
                "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": LAYER_ORTHO,
                "STYLES": "", "CRS": "EPSG:2975", "BBOX": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
                "WIDTH": w, "HEIGHT": h, "FORMAT": "image/png"})
            if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image/"):
                return None
            png = r.content
            meta = {"source": "IGN · BD ORTHO®", "largeur_px": w, "hauteur_px": h, **_millesime(client, bbox)}
    except Exception:  # noqa: BLE001 — réseau IGN indisponible → la vue reste en relief
        return None
    png_p.write_bytes(png)
    meta_p.write_text(json.dumps(meta))
    return {"png": png, **meta}
