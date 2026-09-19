"""Connecteur DPE ADEME — les TROIS jeux post-2021 : existants, neufs, tertiaire [✓ live 13/09/2026].

API data-fair : GET https://data.ademe.fr/data-fair/api/v1/datasets/{jeu}/lines
    filtre `qs=` (Lucene), pagination par curseur `after` (URL `next`), `size`, `select`.
Sans clé (quota anonyme réduit ; ~1200 req/min authentifié). Base nationale 15,5 M (existants).

⚠ SOURCES-CORRECTION-1, mesuré live 19/09/2026 — le FILTRE FIABLE est le géocodage BAN 974.
`code_insee_ban:974*` = 914 existants (+179 neufs +30 tertiaires) : DPE réunionnais AUTHENTIQUES.
SOURCES-2 les croyait « rabattus de métropole » (à cause d'un CP BRUT métropolitain sur ~900) et
tranchait sur le CP brut → base bloquée à 16. C'était l'inverse : l'`identifiant_ban` est en 974xx
(300/300), il matche EXACTEMENT `adresses` locale (150/300), l'`adresse_ban` est réunionnaise réelle
(« RN 5 Petit Serre, Saint-Louis », score 0,88). Le CP brut est le champ BRUYANT (saisi), pas la
vérité. On moissonne donc l'UNION `code_insee_ban:974*` ∪ CP brut 974 (`fetch_reunion_authentiques`),
la corroboration locale (`ingestion.dpe.ingest_jeu`) restant seul juge de l'homonymie — les vrais
homonymes (75 « neufs ST LEU 97436 » = Saint-Leu-la-Forêt Val-d'Oise, BAN 95563, donc HORS 974* ;
2 existants 97490/97434 = Montpellier/Lille) sont bien rejetés. Il existe aussi 2 orphelins existants
CP brut 974 dont le BAN est non-974 (gardés via `adresse_brut` si corroborés, cf. `parse_record`).

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

# Les trois jeux post-juillet-2021 (slugs data-fair vérifiés live 13/09/2026).
DATASETS = {"existant": "dpe03existant", "neuf": "dpe02neuf", "tertiaire": "dpe01tertiaire"}
DATASET = DATASETS["existant"]  # compat : jeu historique
LINES = f"https://data.ademe.fr/data-fair/api/v1/datasets/{DATASET}/lines"

# Champs récupérés (noms RÉELS du schéma, vérifiés — pas devinés).
_SELECT_COMMUN = [
    "numero_dpe", "etiquette_dpe", "etiquette_ges", "adresse_ban", "adresse_brut",
    "code_insee_ban", "code_postal_ban", "code_postal_brut", "date_etablissement_dpe",
    "identifiant_ban", "statut_geocodage", "score_ban",
    "coordonnee_cartographique_x_ban", "coordonnee_cartographique_y_ban",
]
# `dpe01tertiaire` n'a NI type_batiment NI surface_habitable_logement (vérifié au schéma) :
# sa surface est `surface_utile`, gardée dans raw — jamais maquillée en surface habitable.
_SELECT_PAR_JEU = {
    "existant": _SELECT_COMMUN + ["type_batiment", "surface_habitable_logement", "annee_construction"],
    "neuf": _SELECT_COMMUN + ["type_batiment", "surface_habitable_logement", "annee_construction"],
    "tertiaire": _SELECT_COMMUN + ["surface_utile"],
}
SELECT = ",".join(_SELECT_PAR_JEU["existant"])

# SOURCES-CORRECTION-1 — le signal FIABLE est le géocodage BAN vers un INSEE 974* (l'adresse a été
# résolue en Réunion) : ~914 existants, corroborés à 50 % par correspondance EXACTE d'`identifiant_ban`
# dans la table `adresses` locale (BAN Réunion), adresses réunionnaises réelles (« RN 5 Petit Serre,
# Saint-Louis », « Chemin de la Plaine, Saint-Louis »). Le CP BRUT (saisi par le diagnostiqueur) est du
# BRUIT : il rate ~900 DPE réunionnais authentiques au CP métropolitain (62200/66000…), et laisse passer
# des homonymes (Saint-Leu-la-Forêt, CP 97436 mais BAN 95). La corroboration locale (ingest_jeu) tranche.
QS_BAN_974 = "code_insee_ban:974*"                       # BAN a géocodé l'adresse en Réunion
QS_CP_BRUT_974 = "code_postal_brut:[97400 TO 97490]"     # rattrape les orphelins BAN≠974 (CP brut 974)
QS_REUNION_AUTHENTIQUES = QS_BAN_974                      # compat : la vérité = géocodage BAN 974

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

    def __init__(self, timeout: float | None = None, throttle_s: float = 0.1,
                 jeu: str = "existant"):
        super().__init__(timeout)
        self.throttle_s = throttle_s
        if jeu not in DATASETS:
            raise ValueError(f"jeu DPE inconnu : {jeu!r} (attendu : {sorted(DATASETS)})")
        self.jeu = jeu
        self.lines_url = f"https://data.ademe.fr/data-fair/api/v1/datasets/{DATASETS[jeu]}/lines"
        # SOURCES-5 #18 : plus de `select` restreint (18 champs curés) → l'API renvoie TOUT le schéma
        # ADEME (~230 champs : conso 5 usages, déperditions Ubât, système chauffage/ECS, isolation…)
        # que `raw` conserve intégralement. Le 974 est quasi vide (16 authentiques) → payload dérisoire,
        # mais le schéma est PRÊT pour le jour où l'ADEME réparera son flux DROM. select curé conservé
        # en documentation (_SELECT_PAR_JEU) ; parse_record lit les mêmes champs dans le sur-ensemble.
        self.select = None

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
        url: str | None = self.lines_url
        params: dict | None = {"qs": qs, "size": size}
        if self.select:
            params["select"] = self.select
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
            params = {"qs": qs, "size": size, "after": after}
            if self.select:
                params["select"] = self.select
            if self.throttle_s:
                time.sleep(self.throttle_s)

    def fetch_reunion_authentiques(self, size: int = 100) -> Iterator[dict]:
        """SOURCES-CORRECTION-1 — TOUS les DPE réunionnais du jeu : l'UNION du géocodage BAN 974
        (`code_insee_ban:974*`, le signal fiable) ET du CP brut 974 (rattrape les orphelins dont le
        BAN contredit ou manque), dédupliquée par `numero_dpe`. La corroboration locale (`ingest_jeu`)
        reste seul juge de l'homonymie. Le filtre CP-brut SEUL (moisson SOURCES-2) ratait ~900 DPE
        974 authentiques dont le CP brut est métropolitain (bruit de saisie du diagnostiqueur)."""
        vus: set[str] = set()
        for qs in (QS_BAN_974, QS_CP_BRUT_974):
            for rec in self._fetch_qs(qs, size=size):
                num = str(rec.get("numero_dpe") or "")
                if not num or num in vus:
                    continue
                vus.add(num)
                yield rec

    def fetch_commune(self, code_insee: str, size: int = 100) -> Iterator[dict]:
        """Itère TOUS les DPE d'une commune (filtre `code_insee_ban`)."""
        yield from self._fetch_qs(f"code_insee_ban:{code_insee}", size=size)

    def fetch_orphelins_974(self, size: int = 100) -> Iterator[dict]:
        """DPE réunionnais (CP brut 974xx) SANS géocodage BAN — invisibles du filtre commune."""
        yield from self._fetch_qs(QS_ORPHELINS_974, size=size)
