"""Connecteur DPE ADEME — jeu `dpe03existant` (logements existants, 3CL réformée) [✓ live 11/07].

API data-fair : GET https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines
    filtre `qs=` (Lucene), pagination par curseur `after` (URL `next`), `size`, `select`.
Sans clé (quota anonyme réduit ; ~1200 req/min authentifié). Base nationale 15,2 M ;
974 = ~912 (vérifié 11/07/2026 par `code_insee_ban:974*` ET `code_region_ban:04` — le DPE
réglementaire reste marginal à La Réunion, ~10/mois depuis 07/2021). +2 enregistrements 974
hors filtre BAN (CP brut 974xx sans `code_insee_ban`) → `fetch_orphelins_974()`.

⚠ Le champ `_geopoint` de l'ADEME est FAUX au 974 (100 % hors Réunion). En revanche
`coordonnee_cartographique_x/y_ban` sont les coordonnées BAN natives en EPSG:2975 (RGR92 /
UTM 40S) et `identifiant_ban` est la clé BAN → géocodage 100 % LOCAL contre la table
`adresses` (cf. ingestion/dpe.py), plus aucun appel api-adresse.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

from .base import Connector

DATASET = "dpe03existant"
LINES = f"https://data.ademe.fr/data-fair/api/v1/datasets/{DATASET}/lines"

# Champs récupérés (noms RÉELS du schéma, vérifiés — pas devinés).
SELECT = ",".join([
    "numero_dpe", "etiquette_dpe", "etiquette_ges", "type_batiment",
    "surface_habitable_logement", "annee_construction", "adresse_ban", "adresse_brut",
    "code_insee_ban", "code_postal_ban", "code_postal_brut", "date_etablissement_dpe",
    "identifiant_ban", "statut_geocodage", "score_ban",
    "coordonnee_cartographique_x_ban", "coordonnee_cartographique_y_ban",
])

# DPE 974 invisibles du filtre commune : CP brut réunionnais mais géocodage BAN absent.
QS_ORPHELINS_974 = "code_postal_brut:[97400 TO 97490] AND NOT code_insee_ban:974*"

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

    def _fetch_qs(self, qs: str, size: int = 100) -> Iterator[dict]:
        """Itère toutes les lignes d'un filtre Lucene, pagination par curseur `after`."""
        url: str | None = LINES
        params: dict | None = {"qs": qs, "size": size, "select": SELECT}
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
            params = {"qs": qs, "size": size, "select": SELECT, "after": after}
            if self.throttle_s:
                time.sleep(self.throttle_s)

    def fetch_commune(self, code_insee: str, size: int = 100) -> Iterator[dict]:
        """Itère TOUS les DPE d'une commune (filtre `code_insee_ban`)."""
        yield from self._fetch_qs(f"code_insee_ban:{code_insee}", size=size)

    def fetch_orphelins_974(self, size: int = 100) -> Iterator[dict]:
        """DPE réunionnais (CP brut 974xx) SANS géocodage BAN — invisibles du filtre commune."""
        yield from self._fetch_qs(QS_ORPHELINS_974, size=size)
