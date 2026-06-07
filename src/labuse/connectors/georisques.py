"""Connecteur Géorisques — API REST  [✓ live, SPIKE 2026-06].

    https://www.georisques.gouv.fr/api/v1/...
    Confirmés (HTTP 200) : /gaspar/risques, /gaspar/catnat, /gaspar/azi,
    /rga (argiles), /zonage_sismique. ⚠ pas d'endpoint /ppr en v1 (404).
    Requête par code_insee, ou par latlon+rayon pour les aléas localisés.
"""
from __future__ import annotations

from typing import Any

from .base import Connector

BASE = "https://www.georisques.gouv.fr/api/v1"


class GeorisquesConnector(Connector):
    name = "Géorisques"
    test_url = f"{BASE}/gaspar/catnat"
    test_params = {"code_insee": "97415", "page": 1, "page_size": 1}

    def _get(self, path: str, params: dict) -> dict:
        with self._client() as c:
            r = c.get(f"{BASE}/{path.lstrip('/')}", params=params)
            r.raise_for_status()
            return r.json()

    def risques(self, code_insee: str, page_size: int = 50) -> dict:
        """Synthèse des risques de la commune (inondation, mvt de terrain, PPR…). [✓ live]"""
        return self._get("gaspar/risques", {"code_insee": code_insee, "page": 1, "page_size": page_size})

    def catnat(self, code_insee: str) -> dict:
        """Arrêtés de catastrophe naturelle. [✓ live]"""
        return self._get("gaspar/catnat", {"code_insee": code_insee})

    def azi(self, code_insee: str) -> dict:
        """Atlas des Zones Inondables (proxy aléa inondation/littoral). [✓ live]"""
        return self._get("gaspar/azi", {"code_insee": code_insee})

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
