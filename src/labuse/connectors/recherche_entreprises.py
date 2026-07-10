"""Connecteur API Recherche d'entreprises (recherche-entreprises.api.gouv.fr) — Score V.

API publique SANS authentification (DINUM), rate limit documenté ~7 req/s. Deux usages :
  1. `fetch_by_siren`  — enrichissement propriétaire (état administratif, siège, NAF,
     dirigeants avec année de naissance, catégorie juridique) → cache `owner_enrichment`.
  2. `search_by_name`  — fallback matching §4.2 pour les liens DGFiP PM SANS SIREN valide
     (dénomination normalisée → candidats) → cache `owner_denom_lookup`.

Schéma VÉRIFIÉ le 10/07/2026 sur des réponses réelles (SHLMR 310895172, SIDR, SEMADER…),
pas deviné : `results[].{siren, nom_complet, nom_raison_sociale, etat_administratif (A|C),
nature_juridique, activite_principale, date_creation, date_fermeture,
siege.{departement, commune (INSEE), code_postal, libelle_commune, adresse},
dirigeants[].{type_dirigeant, nom, prenoms, annee_de_naissance, date_de_naissance (YYYY-MM),
qualite}}`.

RGPD (règle d'archi #2) : personnes morales, open data DINUM ; signal interne de priorisation,
jamais un export nominatif de masse. Les dirigeants PP ne sont conservés que dans le payload
brut caché (source officielle déjà publique).
"""
from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Iterable, Iterator

from .base import Connector

BASE_URL = "https://recherche-entreprises.api.gouv.fr/search"
SOURCE_NAME = "Recherche d'entreprises (DINUM)"
# Rate limit officiel ~7 req/s ; on vise ~5 req/s pour rester poli.
DEFAULT_THROTTLE_S = 0.2

_FORME_TOKENS = re.compile(
    r"\b(SCI|SARL|SASU|SAS|SA|SNC|EURL|SELARL)\b", re.IGNORECASE)


def normalize_denomination(denom: str | None) -> str:
    """Normalisation §4.2 : uppercase, unaccent, tokens de forme juridique retirés,
    ponctuation → espace, espaces multiples réduits. '' si vide."""
    if not denom:
        return ""
    s = unicodedata.normalize("NFKD", denom)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).upper()
    # Ponctuation AVANT les tokens de forme : « S.C.I. » doit devenir « S C I » → « SCI » ne
    # marcherait pas ; on recolle donc les sigles pointés avant de retirer les tokens.
    s = re.sub(r"\b(S\s*\.?\s*C\s*\.?\s*I|S\s*\.?\s*A\s*\.?\s*R\s*\.?\s*L|S\s*\.?\s*A\s*\.?\s*S)\b\.?",
               lambda m: m.group(1).replace(" ", "").replace(".", ""), s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = _FORME_TOKENS.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_result(rec: dict) -> dict:
    """Un résultat de l'API → dict propriétaire normalisé (payload brut conservé à part)."""
    siege = rec.get("siege") or {}
    dirigeants = []
    for d in rec.get("dirigeants") or []:
        dirigeants.append({
            "type": d.get("type_dirigeant"),
            "qualite": d.get("qualite"),
            "date_de_naissance": d.get("date_de_naissance"),   # 'YYYY-MM' (PP seulement)
            "annee_de_naissance": d.get("annee_de_naissance"),
            "siren": d.get("siren"),                            # si dirigeant personne morale
        })
    return {
        "siren": rec.get("siren"),
        "denomination": rec.get("nom_raison_sociale") or rec.get("nom_complet"),
        "etat_administratif": rec.get("etat_administratif"),    # 'A' actif | 'C' cessée
        "nature_juridique": rec.get("nature_juridique"),        # catégorie juridique INSEE (7xxx = public)
        "categorie_entreprise": rec.get("categorie_entreprise"),  # PME | ETI | GE (INSEE)
        "activite_principale": rec.get("activite_principale"),  # NAF
        "date_creation": rec.get("date_creation"),
        "date_fermeture": rec.get("date_fermeture"),
        "date_mise_a_jour_rne": rec.get("date_mise_a_jour_rne"),
        "siege": {
            "departement": siege.get("departement"),
            "commune_insee": siege.get("commune"),
            "libelle_commune": siege.get("libelle_commune"),
            "code_postal": siege.get("code_postal"),
            "adresse": siege.get("adresse"),
            "code_pays_etranger": siege.get("code_pays_etranger"),
        },
        "dirigeants": dirigeants,
    }


class RechercheEntreprisesConnector(Connector):
    """Client throttlé + retry poli. `name` matche data_sources.name (ajouté au catalogue)."""

    name = SOURCE_NAME
    test_url = BASE_URL
    test_params = {"q": "310895172", "per_page": 1}

    def __init__(self, throttle_s: float = DEFAULT_THROTTLE_S, timeout: float | None = None):
        super().__init__(timeout)
        self.throttle_s = throttle_s

    def _get(self, params: dict, max_retries: int = 5) -> dict:
        last: Exception | None = None
        for attempt in range(max_retries):
            try:
                with self._client() as c:
                    r = c.get(BASE_URL, params=params)
                if r.status_code == 429 or r.status_code >= 500:   # transitoire → backoff
                    last = RuntimeError(f"HTTP {r.status_code}")
                    time.sleep(min(15.0, 1.5 ** attempt))
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as exc:  # réseau / timeout → retry poli
                last = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"recherche-entreprises : échec après {max_retries} essais ({last})")

    def fetch_by_siren(self, siren: str) -> dict | None:
        """La fiche entreprise d'un SIREN. None si inconnue. Ne throttle pas (l'appelant gère)."""
        data = self._get({"q": siren, "per_page": 3})
        for rec in data.get("results") or []:
            if rec.get("siren") == siren:
                return rec
        return None

    def fetch_by_sirens(self, sirens: Iterable[str]) -> Iterator[tuple[str, dict | None]]:
        """Itère (siren, fiche brute|None) pour un ensemble de SIREN, throttlé."""
        for siren in sirens:
            yield siren, self.fetch_by_siren(siren)
            time.sleep(self.throttle_s)

    def search_by_name(self, denomination: str, per_page: int = 5) -> list[dict]:
        """Candidats pour une dénomination (fallback §4.2). Le matching exact (dénomination
        normalisée des deux côtés) est fait par l'appelant — ici on rapporte les candidats."""
        q = denomination.strip()
        if len(q) < 3:      # l'API exige ≥ 3 caractères utiles
            return []
        data = self._get({"q": q, "per_page": per_page})
        return data.get("results") or []
