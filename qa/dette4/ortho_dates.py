"""Date de PRISE DE VUE de l'ortho affichée (exigence Vic 04/08 : toute carte porte la date).

Source : graphe de mosaïquage BD ORTHO (WFS Géoplateforme,
`ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE:graphe_bdortho`) — attributs date_vol / pva / res
au droit du centroïde de la parcelle. Cache mémoire par session (1 requête par parcelle).
"""
from __future__ import annotations

import httpx

_CACHE: dict[str, tuple] = {}
_WFS = "https://data.geopf.fr/wfs/ows"


def date_vol(cl: httpx.Client, lon: float, lat: float, key: str | None = None) -> str:
    """« PVA 2025 · vol 2025-07-22 · 20 cm » — ou « millésime inconnu » si le graphe ne répond
    pas (on AFFICHE l'ignorance plutôt que de la masquer)."""
    k = key or f"{lon:.4f},{lat:.4f}"
    if k in _CACHE:
        p = _CACHE[k]
    else:
        d = 1e-4
        try:
            r = cl.get(_WFS, params={
                "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
                "TYPENAMES": "ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE:graphe_bdortho",
                "COUNT": "1", "OUTPUTFORMAT": "application/json",
                "BBOX": f"{lat-d},{lon-d},{lat+d},{lon+d},urn:ogc:def:crs:EPSG::4326"})
            props = r.json()["features"][0]["properties"]
            p = (props.get("pva"), (props.get("date_vol") or "?").rstrip("Z"), props.get("res"))
        except Exception:
            p = (None, None, None)
        _CACHE[k] = p
    pva, dv, res = p
    if not pva:
        return "ortho : millésime inconnu (graphe muet)"
    return f"ortho : PVA {pva} · vol {dv} · {res} cm"
