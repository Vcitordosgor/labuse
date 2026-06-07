"""Connecteur WFS générique (hubs DEAL / PEIGEO / Géoplateforme)  [§6].

Piloté par config/wfs_layers.yaml : chaque couche déclarée mappe un typename
distant vers un `spatial_kind` LA BUSE. `test_connection` interroge GetCapabilities ;
`fetch_layer` demande du GeoJSON (EPSG:4326). Permet de tenir la promesse
« tout relié au même endroit » sans coder un connecteur par hub.
"""
from __future__ import annotations

from typing import Any

from .. import config
from .base import Connector, ConnectionTestResult


class WfsConnector(Connector):
    name = "WFS générique"

    def __init__(self, endpoint_key: str | None = None, timeout: float | None = None):
        super().__init__(timeout)
        self.cfg = config.wfs_layers()
        self.endpoint_key = endpoint_key

    def _endpoint(self, key: str) -> dict:
        ep = self.cfg.get("endpoints", {}).get(key)
        if not ep:
            raise KeyError(f"Endpoint WFS inconnu : {key}")
        return ep

    def get_capabilities_url(self, key: str) -> str:
        base = self._endpoint(key)["base_url"]
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}service=WFS&request=GetCapabilities"

    def fetch_layer(self, endpoint_key: str, typename: str, bbox: tuple | None = None, max_features: int = 1000) -> dict:
        """GetFeature en GeoJSON (srsName EPSG:4326)."""
        base = self._endpoint(endpoint_key)["base_url"]
        params: dict[str, Any] = {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeNames": typename, "outputFormat": "application/json",
            "srsName": "EPSG:4326", "count": max_features,
        }
        if bbox:
            params["bbox"] = ",".join(str(b) for b in bbox) + ",EPSG:4326"
        with self._client() as c:
            r = c.get(base, params=params)
            r.raise_for_status()
            return r.json()

    def test_connection(self) -> ConnectionTestResult:
        key = self.endpoint_key
        if not key:
            return ConnectionTestResult(self.name, False, "Aucun endpoint WFS sélectionné.")
        try:
            with self._client() as c:
                r = c.get(self.get_capabilities_url(key))
            ok = r.status_code == 200 and "WFS_Capabilities" in r.text
            return ConnectionTestResult(
                f"WFS:{key}", ok, "GetCapabilities OK" if ok else f"HTTP {r.status_code}",
                status_code=r.status_code, sample=(r.text[:200] if ok else None),
            )
        except Exception as exc:
            return ConnectionTestResult(f"WFS:{key}", False, f"Inatteignable : {type(exc).__name__}: {exc}")
