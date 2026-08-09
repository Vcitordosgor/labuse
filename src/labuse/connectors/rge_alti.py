"""Connecteur RGE ALTI (altimétrie IGN) — LECTURE pure (M-C/F6).

Unifie l'appel au service de calcul d'altitude, qui était RECOPIÉ à deux endroits (le throttle
« quota 5 req/s », l'URL, les paramètres `ign_rge_alti_wld`/`zonly`, le lotissement par 100) :
`ingestion.layers_ingest.ingest_pente` (pente sur grille) et `api.enrichment._alti_query` (cote
altimétrique de fiche). Une seule source de vérité pour l'endpoint et le throttle.

Le seuil NODATA (le service renvoie des altitudes sentinelles négatives) est laissé à l'APPELANT :
la pente tolère > -9999, la fiche écarte <= -1000 — conventions différentes, volontairement.
"""
from __future__ import annotations

import time

import httpx

#: Endpoint unique du calcul d'altitude RGE ALTI (IGN / Géoplateforme).
ALTI_URL = "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json"
#: Taille de lot (le service accepte des listes de points).
ALTI_BATCH = 100
#: Throttle entre deux lots — quota 5 req/s côté IGN.
ALTI_THROTTLE_S = 0.21


def fetch_elevations(points: list[tuple[float, float]], *, client: httpx.Client,
                     batch: int = ALTI_BATCH, throttle_s: float = ALTI_THROTTLE_S) -> list:
    """Altitudes RGE ALTI pour une liste de points (lon, lat en 4326), par lots + throttle.

    Retourne les élévations BRUTES du service, alignées sur `points` (None si le service renvoie
    null) — l'appelant applique son propre seuil NODATA. `client` : httpx.Client fourni (réutilise
    la config/User-Agent de l'appelant). `raise_for_status` propagé (l'appelant dégrade)."""
    out: list = []
    for k in range(0, len(points), batch):
        part = points[k:k + batch]
        r = client.get(ALTI_URL, params={
            "lon": "|".join(f"{lon:.6f}" for lon, _ in part),
            "lat": "|".join(f"{lat:.6f}" for _, lat in part),
            "resource": "ign_rge_alti_wld", "zonly": "true"})
        r.raise_for_status()
        out.extend(r.json().get("elevations", []))
        if throttle_s and len(points) > batch:
            time.sleep(throttle_s)
    return out
