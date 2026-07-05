"""Connecteur base Mérimée — Monuments Historiques (data.culture.gouv.fr) [✓ live 05/07/2026].

Opendatasoft : liste-des-immeubles-proteges-au-titre-des-monuments-historiques.
Filtre `region="La Réunion"` → 204 MH pour le 974. Géométrie `coordonnees_au_format_wgs84`
(dict {lat, lon}) — vérifié PROPRE (50/50 en Réunion, pas le piège du _geopoint DPE).

Usage : générer les abords ABF (tampon ~500 m autour de chaque MH). ⚠ le tampon SUR-COUVRE vs le
régime réel (périmètre délimité PDA, ou 500 m AVEC covisibilité) → flag qualité « à instruire ».
"""
from __future__ import annotations

from collections.abc import Iterator

from .base import Connector

BASE = ("https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets/"
        "liste-des-immeubles-proteges-au-titre-des-monuments-historiques/records")
REGION = "La Réunion"
PAGE = 100  # max ODS v2.1


class MerimeeConnector(Connector):
    name = "ABF / Monuments historiques"
    test_url = BASE
    test_params = {"where": f'region="{REGION}"', "limit": 1}

    def fetch_reunion(self) -> Iterator[dict]:
        """Itère les MH du 974 (pagination ODS offset/limit ≤ 10000)."""
        offset = 0
        while offset < 10000:
            with self._client() as c:
                r = c.get(BASE, params={"where": f'region="{REGION}"', "limit": PAGE, "offset": offset})
                r.raise_for_status()
                res = r.json().get("results") or []
            for rec in res:
                yield rec
            if len(res) < PAGE:
                return
            offset += PAGE

    @staticmethod
    def coords(rec: dict) -> tuple[float, float] | None:
        """(lon, lat) depuis `coordonnees_au_format_wgs84`. None si absent/hors Réunion (on n'attache
        que par la géométrie, cf. amendement Vic : pas de clé cog_insee d'époque)."""
        gp = rec.get("coordonnees_au_format_wgs84")
        lat = lon = None
        if isinstance(gp, dict):
            lat, lon = gp.get("lat"), gp.get("lon")
        elif isinstance(gp, (list, tuple)) and len(gp) == 2:
            lat, lon = gp
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            return None
        if not (-21.6 <= lat <= -20.8 and 55.2 <= lon <= 55.9):
            return None
        return lon, lat
