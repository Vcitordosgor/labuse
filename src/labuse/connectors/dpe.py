"""Connecteur DPE ADEME — jeu `dpe03existant` (logements existants, 3CL réformée) [✓ live 05/07].

API data-fair : GET https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines
    filtre `qs=` (Lucene), pagination par curseur `after` (URL `next`), `size`, `select`.
Sans clé (quota anonyme réduit ; ~1200 req/min authentifié). Base nationale 15,1 M ; 974 = 910.

⚠ Le champ `_geopoint` de l'ADEME est FAUX au 974 (100 % hors Réunion) → on re-géocode
`adresse_ban` via la BAN (api-adresse, `citycode`) pour obtenir un point réel. Rattachement
approximatif tracé (`rattachement='geocode'`).
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

from .base import Connector

DATASET = "dpe03existant"
LINES = f"https://data.ademe.fr/data-fair/api/v1/datasets/{DATASET}/lines"
BAN = "https://api-adresse.data.gouv.fr/search/"

# Champs récupérés (noms RÉELS du schéma, vérifiés — pas devinés).
SELECT = ",".join([
    "numero_dpe", "etiquette_dpe", "etiquette_ges", "type_batiment",
    "surface_habitable_logement", "annee_construction", "adresse_ban", "adresse_brut",
    "code_insee_ban", "code_postal_ban", "date_etablissement_dpe",
])

# Emprise Réunion (validation d'un géocodage : sinon on n'attache pas).
REUNION_BBOX = (55.2, 55.9, -21.6, -20.8)  # lon_min, lon_max, lat_min, lat_max


def in_reunion(lon: float, lat: float) -> bool:
    lo1, lo2, la1, la2 = REUNION_BBOX
    return lo1 <= lon <= lo2 and la1 <= lat <= la2


class DpeConnector(Connector):
    name = "DPE ADEME (logements existants)"
    test_url = LINES
    test_params = {"qs": "code_insee_ban:97415", "size": 1}

    def __init__(self, timeout: float | None = None, throttle_s: float = 0.1):
        super().__init__(timeout)
        self.throttle_s = throttle_s

    def _get(self, url: str, params: dict | None, max_retries: int = 4) -> dict:
        last: Exception | None = None
        for attempt in range(max_retries):
            try:
                with self._client() as c:
                    r = c.get(url, params=params or {})
                if r.status_code == 429 or r.status_code >= 500:
                    ra = r.headers.get("Retry-After")
                    time.sleep(float(ra) if (ra or "").isdigit() else min(20.0, 2 ** attempt))
                    last = RuntimeError(f"HTTP {r.status_code}")
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as exc:  # réseau / timeout → retry poli
                last = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"DPE {url} — échec après {max_retries} essais ({last})")

    def fetch_commune(self, code_insee: str, size: int = 100) -> Iterator[dict]:
        """Itère TOUS les DPE d'une commune (filtre `code_insee_ban`), pagination par curseur `after`."""
        url: str | None = LINES
        params: dict | None = {"qs": f"code_insee_ban:{code_insee}", "size": size, "select": SELECT}
        while url:
            data = self._get(url, params)
            for rec in data.get("results") or []:
                yield rec
            nxt = data.get("next")
            if not nxt:
                return
            after = parse_qs(urlparse(nxt).query).get("after", [None])[0]
            if not after:
                return
            # on garde nos qs/size/select et on ajoute le curseur (l'URL next les porte déjà, mais
            # on reste explicite pour ne pas dépendre d'un host interne renvoyé dans `next`).
            params = {"qs": f"code_insee_ban:{code_insee}", "size": size, "select": SELECT, "after": after}
            if self.throttle_s:
                time.sleep(self.throttle_s)

    def geocode(self, adresse: str, citycode: str) -> tuple[float, float, float] | None:
        """Re-géocode une adresse via la BAN (restreinte à la commune). Retourne (lon, lat, score)
        SEULEMENT si le point tombe en Réunion — sinon None (on n'invente pas un rattachement)."""
        if not adresse:
            return None
        data = self._get(BAN, {"q": adresse, "citycode": citycode, "limit": 1})
        feats = data.get("features") or []
        if not feats:
            return None
        lon, lat = feats[0]["geometry"]["coordinates"]
        if not in_reunion(lon, lat):
            return None
        return lon, lat, feats[0]["properties"].get("score")
