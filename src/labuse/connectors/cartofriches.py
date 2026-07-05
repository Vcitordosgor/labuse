"""Connecteur Cartofriches — API Données Foncières du Cerema  [✓ live 05/07/2026].

    Host public : https://apidf-preprod.cerema.fr (⚠ apidf.cerema.fr ne résout pas).
    Sans clé, sans auth, Licence ouverte 2.0. MAJ trimestrielle.
    Endpoints Cartofriches (vérifiés live, INSEE 97415) :
      /cartofriches/geofriches/?code_insee=… → GeoJSON MultiPolygon + propriétés résumé
                                               (dont unite_fonciere_refcad = IDU exacts).
      /cartofriches/friches/{site_id}/        → détail 78 champs (indicateurs).
    Pagination DRF : {count, next, previous, features/results}. Pas de rate-limit exposé →
    throttle prudent (leçon INPI). Couverture 974 : 373 friches (Saint-Paul 9).
"""
from __future__ import annotations

import time
from collections.abc import Iterator

from .base import Connector

BASE = "https://apidf-preprod.cerema.fr"
THROTTLE_S = 0.15

# Champs de détail CLEAN à conserver (on écarte proprio_nom/proprio_type : chaînes JSON cassées
# côté API, sérialisées en tableau de caractères). Vérifié sur 97415_10812.
DETAIL_FIELDS = (
    "site_vocadomi", "site_reconv_type", "site_reconv_annee", "site_occupation",
    "sol_pollution_existe", "sol_pollution_origine", "site_numero_basol", "site_numero_basias",
    "urba_zone_lib", "urba_doc_type", "urba_datappro", "bati_nombre", "bati_etat",
    "taux_artif_ff", "zonage_enviro", "zone_activites", "date_creation", "date_mutation",
    "p_residentiel", "p_industriel", "p_tertiaire", "p_equipement", "p_culturel",
    "p_renaturation", "p_pv", "site_url", "source_url", "source_producteur",
)


class CartofrichesConnector(Connector):
    name = "Cartofriches (Cerema)"
    test_url = f"{BASE}/cartofriches/friches/"
    test_params = {"code_insee": "97415", "page": 1}

    def __init__(self, timeout: float | None = None, throttle_s: float = THROTTLE_S):
        super().__init__(timeout)
        self.throttle_s = throttle_s

    def _get(self, url: str, params: dict | None, max_retries: int = 4) -> dict:
        last: Exception | None = None
        for attempt in range(max_retries):
            try:
                with self._client() as c:
                    r = c.get(url, params=params or {})
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
        raise RuntimeError(f"Cartofriches {url} — échec après {max_retries} essais ({last})")

    def geofriches(self, code_insee: str) -> Iterator[dict]:
        """Itère les friches (GeoJSON Features : géométrie + propriétés résumé) d'une commune,
        en suivant la pagination `next`."""
        url = f"{BASE}/cartofriches/geofriches/"
        params: dict | None = {"code_insee": code_insee}
        while url:
            data = self._get(url, params)
            for feat in data.get("features") or []:
                yield feat
            url = data.get("next")            # URL absolue de la page suivante (ou None)
            params = None
            if url and self.throttle_s:
                time.sleep(self.throttle_s)

    def detail(self, site_id: str) -> dict | None:
        """Détail 78 champs d'une friche. None si absent/inexploitable (on garde alors le résumé)."""
        try:
            return self._get(f"{BASE}/cartofriches/friches/{site_id}/", None)
        except Exception:
            return None
