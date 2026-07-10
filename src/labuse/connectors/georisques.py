"""Connecteur Géorisques — API REST  [✓ live, SPIKE 2026-06 ; étendu Vague B 2026-07].

    https://www.georisques.gouv.fr/api/v1/...
    Confirmés (HTTP 200) : /gaspar/risques, /gaspar/catnat, /gaspar/azi,
    /zonage_sismique. Vague B (vérifié live 05/07/2026, INSEE 97415) :
      /ssp (sites et sols pollués : casias + instructions), /cavites, /installations_classees.
    ⚠ pas d'endpoint /ppr en v1 (404). ⚠ /rga (argiles) : 500 sur code_insee, vide sur latlon
    même en métropole — écarté (N/A géologique à La Réunion, île volcanique).
    Rate-limit officiel ~1000 req/min/IP → throttle prudent (leçon INPI : on ne se fait pas brider).
    Requête par code_insee, ou par latlon+rayon pour les aléas localisés.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from .base import Connector

BASE = "https://www.georisques.gouv.fr/api/v1"
PAGE_SIZE = 100          # max page raisonnable ; réduit les appels (1000 req/min/IP)
THROTTLE_S = 0.15        # ~6-7 req/s, très en deçà du plafond


class GeorisquesConnector(Connector):
    name = "Géorisques"
    test_url = f"{BASE}/gaspar/catnat"
    test_params = {"code_insee": "97415", "page": 1, "page_size": 1}

    def __init__(self, timeout: float | None = None, throttle_s: float = THROTTLE_S):
        super().__init__(timeout)
        self.throttle_s = throttle_s

    def _get(self, path: str, params: dict, max_retries: int = 4) -> dict:
        last: Exception | None = None
        for attempt in range(max_retries):
            try:
                with self._client() as c:
                    r = c.get(f"{BASE}/{path.lstrip('/')}", params=params)
                if r.status_code == 429 or r.status_code >= 500:  # transitoire → backoff patient
                    ra = r.headers.get("Retry-After")
                    time.sleep(float(ra) if (ra or "").isdigit() else min(20.0, 2 ** attempt))
                    last = RuntimeError(f"HTTP {r.status_code}")
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as exc:  # réseau / timeout → retry poli
                last = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"Géorisques {path} — échec après {max_retries} essais ({last})")

    def _paginate(self, path: str, code_insee: str, subkey: str | None = None,
                  throttle_s: float | None = None) -> Iterator[dict]:
        """Itère les objets d'un endpoint paginé filtré par commune. `subkey` : pour /ssp, la
        sous-collection imbriquée ('casias' | 'instructions'), chacune avec ses propres pages."""
        throttle_s = self.throttle_s if throttle_s is None else throttle_s
        page = 1
        while True:
            data = self._get(path, {"code_insee": code_insee, "page": page, "page_size": PAGE_SIZE})
            block = data.get(subkey) if subkey else data
            if not isinstance(block, dict):
                return
            items = block.get("data") or []
            for it in items:
                yield it
            total_pages = int(block.get("total_pages") or 1)
            if page >= total_pages or not items:
                return
            page += 1
            if throttle_s:
                time.sleep(throttle_s)

    # ── Vague B : couches par commune (paginées) ──

    def sites_pollues(self, code_insee: str) -> Iterator[tuple[str, dict]]:
        """Sites et sols pollués /ssp → (subtype, objet) pour casias (ex-BASIAS), instructions
        (ex-BASOL) et conclusions_sis (SIS — Secteurs d'Information sur les Sols : PÉRIMÈTRES
        MultiPolygon réglementaires, LOT 2 data-gap ; champs propres nom/id_sis/
        statut_classification/superficie, vérifié live 97407). [✓ live 974]."""
        for it in self._paginate("ssp", code_insee, subkey="casias"):
            yield "casias", it
        for it in self._paginate("ssp", code_insee, subkey="instructions"):
            yield "instruction", it
        for it in self._paginate("ssp", code_insee, subkey="conclusions_sis"):
            yield "sis", it

    def cavites(self, code_insee: str) -> Iterator[dict]:
        """Cavités souterraines /cavites (naturelle, carrière, ouvrage civil…). [✓ live 974]."""
        yield from self._paginate("cavites", code_insee)

    def installations_classees(self, code_insee: str) -> Iterator[dict]:
        """ICPE /installations_classees (régime, statut Seveso, code NAF). [✓ live 974]."""
        yield from self._paginate("installations_classees", code_insee)

    def mvt(self, code_insee: str) -> Iterator[dict]:
        """Mouvements de terrain /mvt (coulée, glissement, éboulement…) avec lon/lat + fiabilité.
        [✓ live 974 : 160 objets Saint-Paul, coordonnées réelles]."""
        yield from self._paginate("mvt", code_insee)

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
