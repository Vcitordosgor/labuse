"""ÉTUDE DE ZONE · Z2 — connecteur ISOCHRONE IGN (Géoplateforme, service navigation/isochrone).

LECTURE pure : un point (lon, lat 4326) + un temps (minutes) + un mode (voiture/à pied) → un polygone
GeoJSON de la zone atteignable. `raise_for_status` propagé : l'APPELANT (zone.py) dégrade honnêtement
et NOMME l'échec — jamais un cercle substitué en silence.

Le temps est un temps de trajet « hors trafic » (le service ne modélise pas le trafic) — la mention est
affichée par l'appelant à chaque temps.
"""
from __future__ import annotations

import httpx

#: Service isochrone de la Géoplateforme IGN (moteur Valhalla sur BD TOPO).
ISOCHRONE_URL = "https://data.geopf.fr/navigation/isochrone"
#: profils du service → nos deux modes.
_PROFILE = {"voiture": "car", "pied": "pedestrian"}


def fetch_isochrone(lon: float, lat: float, minutes: int, mode: str, *, client: httpx.Client) -> dict:
    """Polygone GeoJSON (geometry) de la zone atteignable en `minutes` depuis (lon, lat) en `mode`.

    `mode` ∈ {'voiture', 'pied'}. Retourne le dict geometry GeoJSON (type Polygon/MultiPolygon, 4326).
    Lève httpx.HTTPStatusError / ValueError si le service échoue ou renvoie une réponse inexploitable —
    l'appelant décide du dégradé (jamais un cercle en silence)."""
    profile = _PROFILE.get(mode)
    if profile is None:
        raise ValueError(f"mode d'isochrone inconnu : {mode!r} (attendu 'voiture' ou 'pied')")
    r = client.get(ISOCHRONE_URL, params={
        "point": f"{lon:.6f},{lat:.6f}",
        "resource": "bdtopo-valhalla",
        "costType": "time",
        "costValue": int(minutes) * 60,     # secondes
        "profile": profile,
        "direction": "departure",
        "geometryFormat": "geojson",
    }, timeout=30.0)
    r.raise_for_status()
    data = r.json()
    geom = data.get("geometry")
    if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError("réponse isochrone IGN sans géométrie polygonale exploitable")
    return geom
