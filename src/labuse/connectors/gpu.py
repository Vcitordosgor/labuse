"""Connecteur Urbanisme PLU/GPU — API Carto GPU  [✓ vérifié §6].

    GET https://apicarto.ign.fr/api/gpu/zone-urba?geom=<GeoJSON de la parcelle>
    (+ /document, /prescription-surf|lin|pct, /secteur-cc, /acte-sup)

Couverture dépendante de la dématérialisation locale du document d'urbanisme :
si la commune pilote n'y est pas → fallback import du PLU.
"""
from __future__ import annotations

import json
from typing import Any

from .base import Connector

BASE = "https://apicarto.ign.fr/api/gpu"


def parse_zones(feature_collection: dict) -> list[dict[str, Any]]:
    """FeatureCollection zone-urba → liste de zones {libelle, typezone, libelong}."""
    out: list[dict[str, Any]] = []
    for feat in feature_collection.get("features", []):
        p = feat.get("properties", {}) or {}
        out.append({
            "libelle": p.get("libelle"),
            "typezone": p.get("typezone"),        # U / AUc / A / N …
            "libelong": p.get("libelong"),
            "partition": p.get("partition"),
            "geometry": feat.get("geometry"),
        })
    return out


class GpuConnector(Connector):
    name = "Urbanisme PLU/GPU (API Carto)"
    test_url = f"{BASE}/municipality"
    test_params = {"insee": "97411"}

    def zone_urba(self, geojson_geometry: dict) -> list[dict]:
        with self._client() as c:
            r = c.get(f"{BASE}/zone-urba", params={"geom": json.dumps(geojson_geometry)})
            r.raise_for_status()
            return parse_zones(r.json())

    def prescriptions(self, geojson_geometry: dict, kind: str = "surf") -> dict:
        assert kind in {"surf", "lin", "pct"}
        with self._client() as c:
            r = c.get(f"{BASE}/prescription-{kind}", params={"geom": json.dumps(geojson_geometry)})
            r.raise_for_status()
            return r.json()
