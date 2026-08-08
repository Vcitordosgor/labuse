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
# API dataset data.gouv : résout l'URL RÉELLE du zip (l'URL statique est figée avec un horodatage
# `20260115-204323` qui casse SANS MESSAGE à la prochaine publication) — M-O P2-58.
DATASET_API = ("https://www.data.gouv.fr/api/1/datasets/"
               "quartiers-prioritaires-de-la-politique-de-la-ville-qpv/")
DOWNLOAD_TIMEOUT_S = 120.0   # zip national : timeout EXPLICITE (comme les autres gros téléchargements)
# Fichier « toute la France + Outre-Mer » en WGS84 (les autres sont en projections locales/LB93).
MEMBER = "GEOJSON/QP2024_France_Hexagonale_Outre_Mer_WGS84.geojson"
DEP = "974"


class QpvConnector(Connector):
    name = "QPV 2024 (ANCT)"
    test_url = ZIP_URL

    def _resolve_zip_url(self) -> str:
        """URL du zip QPV 2024 résolue via l'API dataset (l'horodatage de l'URL statique casse à
        chaque publication). Repli SUR l'URL figée si l'API est injoignable/inattendue — jamais un
        échec silencieux : au pire on retombe sur le comportement historique."""
        try:
            with self._client(timeout=30.0) as c:
                r = c.get(DATASET_API)
                r.raise_for_status()
                for res in (r.json().get("resources") or []):
                    url = res.get("url", "")
                    if url.endswith(".zip") and "qpv-2024-geojson" in url:
                        return url
        except Exception:  # noqa: BLE001 — API dataset indisponible → repli sur l'URL figée
            pass
        return ZIP_URL

    def fetch_dep(self, dep: str = DEP) -> Iterator[dict]:
        """Télécharge le zip national (une fois) et itère les features QPV du département `dep`."""
        with self._client(timeout=DOWNLOAD_TIMEOUT_S) as c:
            r = c.get(self._resolve_zip_url())
            r.raise_for_status()
            content = r.content
        z = zipfile.ZipFile(io.BytesIO(content))
        data = json.loads(z.read(MEMBER))
        for feat in data.get("features") or []:
            if str((feat.get("properties") or {}).get("insee_dep", "")) == dep:
                yield feat
