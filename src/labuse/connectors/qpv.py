"""Connecteur QPV — Quartiers Prioritaires de la politique de la Ville, génération 2024 (ANCT).

Source : data.gouv.fr / Agence nationale de la cohésion des territoires (ANCT).
Zip GeoJSON national ; on lit le fichier « France Hexagonale + Outre-Mer » (WGS84) et on filtre
`insee_dep=974` → 57 QPV / 13 communes (vérifié live 05/07/2026). Géométrie MultiPolygon propre.
Décret 2023-1314, en vigueur 01/01/2024 (remplace la génération 2015).
"""
from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Iterator

from .base import Connector

ZIP_URL = ("https://static.data.gouv.fr/resources/"
           "quartiers-prioritaires-de-la-politique-de-la-ville-qpv/20260115-204323/qpv-2024-geojson.zip")
# Fichier « toute la France + Outre-Mer » en WGS84 (les autres sont en projections locales/LB93).
MEMBER = "GEOJSON/QP2024_France_Hexagonale_Outre_Mer_WGS84.geojson"
DEP = "974"


class QpvConnector(Connector):
    name = "QPV 2024 (ANCT)"
    test_url = ZIP_URL

    def fetch_dep(self, dep: str = DEP) -> Iterator[dict]:
        """Télécharge le zip national (une fois) et itère les features QPV du département `dep`."""
        with self._client() as c:
            r = c.get(ZIP_URL)
            r.raise_for_status()
            content = r.content
        z = zipfile.ZipFile(io.BytesIO(content))
        data = json.loads(z.read(MEMBER))
        for feat in data.get("features") or []:
            if str((feat.get("properties") or {}).get("insee_dep", "")) == dep:
                yield feat
