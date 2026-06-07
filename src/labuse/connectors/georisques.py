"""Connecteur Géorisques — API REST  [✓ vérifié §6].

    https://www.georisques.gouv.fr/api/v1/...
    /gaspar/catnat, /azi, /ppr, zonage sismique, retrait-gonflement argiles,
    radon, cavités, sites pollués (BASIAS/BASOL). Requête par latlon+rayon ou code_insee.
"""
from __future__ import annotations

from typing import Any

from .base import Connector

BASE = "https://www.georisques.gouv.fr/api/v1"


class GeorisquesConnector(Connector):
    name = "Géorisques"
    test_url = f"{BASE}/gaspar/catnat"
    test_params = {"code_insee": "97411", "page": 1, "page_size": 1}

    def _get(self, path: str, params: dict) -> dict:
        with self._client() as c:
            r = c.get(f"{BASE}/{path.lstrip('/')}", params=params)
            r.raise_for_status()
            return r.json()

    def ppr(self, code_insee: str) -> dict:
        return self._get("ppr", {"code_insee": code_insee})

    def catnat(self, code_insee: str) -> dict:
        return self._get("gaspar/catnat", {"code_insee": code_insee})

    def by_latlon(self, lat: float, lon: float, rayon_m: int = 1000) -> dict[str, Any]:
        """Agrège quelques risques autour d'un point (rayon en m)."""
        common = {"latlon": f"{lon},{lat}", "rayon": rayon_m}
        out: dict[str, Any] = {}
        for key, path in [
            ("zonage_sismique", "zonage_sismique"),
            ("argiles", "rga"),
            ("cavites", "cavites"),
            ("pollution", "ssp"),
        ]:
            try:
                out[key] = self._get(path, common)
            except Exception as exc:  # une source en panne n'empêche pas le reste (§4)
                out[key] = {"error": f"{type(exc).__name__}: {exc}"}
        return out
