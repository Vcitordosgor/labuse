"""Connecteur BODACC — annonces de PROCÉDURES COLLECTIVES (Vague A1, signal accessibilité).

API ouverte Opendatasoft de la DILA, gratuite et SANS clé :
    https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records

On interroge par SIREN (champ `registre`, tableau [formaté, non-formaté]) et on filtre
`familleavis="collective"` (BODACC A = procédures collectives : redressement, liquidation,
sauvegarde, plan…). Interrogation BATCHÉE (`registre IN (...)`) + paginée + throttlée.

Schéma VÉRIFIÉ le 05/07/2026 sur un enregistrement réel (id A200902491993), pas deviné :
  id, publicationavis="A", dateparution (ISO), numeroannonce, familleavis="collective",
  tribunal, registre=["482 309 382","482309382"], jugement{famille, nature, date, ...}.

Licence Ouverte v2.0 — paternité DILA. RGPD : signal interne de priorisation (personnes
morales, open data), jamais un export nominatif de masse (règle d'archi #2).
"""
from __future__ import annotations

import json
import re
import time
from collections.abc import Iterable, Iterator
from datetime import date

from .base import Connector

DATASET = "annonces-commerciales"
BASE = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets"
RECORDS_URL = f"{BASE}/{DATASET}/records"
# Permalien explore ODS d'une annonce : verifiable par un humain (source citee), toujours resolvable.
EXPLORE_URL = "https://bodacc-datadila.opendatasoft.com/explore/dataset/annonces-commerciales/table/?q=id:{id}"
LICENCE = "Licence Ouverte v2.0 — paternité DILA (BODACC)"

PAGE_LIMIT = 100         # max page ODS v2.1
OFFSET_CAP = 10000       # ODS v2.1 : offset + limit <= 10000 (garde-fou pagination)
FAMILLE_COLLECTIVE = "collective"


def _digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def extract_siren(registre) -> str | None:
    """SIREN (9 chiffres) depuis le champ `registre` (str ou liste [formaté, non-formaté])."""
    if isinstance(registre, str):
        registre = [registre]
    for el in registre or []:
        d = _digits(el)
        if len(d) == 9:
            return d
    return None


def _parse_date_iso(s: str | None) -> date | None:
    try:
        return date.fromisoformat(s)  # dateparution ISO « 2009-12-27 »
    except (TypeError, ValueError):
        return None


def parse_record(rec: dict) -> dict | None:
    """Annonce ODS → dict procédure normalisé. None si inexploitable (pas de SIREN valide).

    `date_jugement_txt` reste le texte FRANÇAIS brut de la source (« 10 décembre 2009 ») :
    on ne fabrique pas une date précise à partir d'un libellé libre. La récence fiable pour
    l'étage 2 viendra de `date_annonce` (dateparution ISO).
    """
    siren = extract_siren(rec.get("registre"))
    if not siren:
        return None
    # L'API ODS renvoie l'objet imbriqué `jugement` comme une CHAÎNE JSON (vérifié live), pas un
    # dict — sans ce décodage, type_procedure/date seraient toujours perdus.
    jug = rec.get("jugement")
    if isinstance(jug, str):
        try:
            jug = json.loads(jug)
        except (ValueError, TypeError):
            jug = {}
    if not isinstance(jug, dict):
        jug = {}
    aid = rec.get("id")
    return {
        "annonce_id": aid,
        "siren": siren,
        "type_procedure": jug.get("nature"),          # ex. « Jugement de conversion en liquidation judiciaire »
        "famille_jugement": jug.get("famille"),        # ex. « Jugement prononçant »
        "date_annonce": _parse_date_iso(rec.get("dateparution")),
        "date_jugement_txt": jug.get("date"),          # texte FR brut, non parsé
        "tribunal": rec.get("tribunal"),
        "numero_annonce": rec.get("numeroannonce"),
        "publication": rec.get("publicationavis"),
        "url_source": EXPLORE_URL.format(id=aid) if aid else None,
        "raw": rec,
    }


def _chunks(seq: Iterable[str], n: int) -> Iterator[list[str]]:
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


class BodaccConnector(Connector):
    """Procédures collectives BODACC par SIREN. `name` matche data_sources.name."""

    name = "BODACC (procédures collectives)"
    test_url = RECORDS_URL
    test_params = {"where": f'familleavis="{FAMILLE_COLLECTIVE}"', "limit": 1, "select": "id"}

    @staticmethod
    def _where(sirens: list[str]) -> str:
        vals = ",".join(f'"{s}"' for s in sirens)
        return f'familleavis="{FAMILLE_COLLECTIVE}" AND registre IN ({vals})'

    def _get_page(self, where: str, offset: int, max_retries: int = 4) -> dict:
        params = {"where": where, "limit": PAGE_LIMIT, "offset": offset, "order_by": "dateparution"}
        last: Exception | None = None
        for attempt in range(max_retries):
            try:
                with self._client() as c:
                    r = c.get(RECORDS_URL, params=params)
                if r.status_code == 429 or r.status_code >= 500:  # transitoire → retry
                    last = RuntimeError(f"HTTP {r.status_code}")
                    time.sleep(0.5 * (attempt + 1))
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as exc:  # réseau / timeout → retry poli
                last = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"BODACC : page échouée (offset {offset}) — {last}")

    def fetch_collective_by_sirens(
        self, sirens: Iterable[str], batch_size: int = 40, throttle_s: float = 0.25,
    ) -> Iterator[dict]:
        """Itère les procédures collectives d'un ensemble de SIREN (batché + paginé + throttlé).

        Un batch de `batch_size` SIREN → une requête `registre IN (...)`, paginée par 100.
        L'API est ouverte mais pas illimitée : throttle poli entre pages et batches.
        """
        for batch in _chunks(sorted(set(sirens)), batch_size):
            where = self._where(batch)
            offset = 0
            while True:
                data = self._get_page(where, offset)
                for rec in data.get("results") or []:
                    parsed = parse_record(rec)
                    if parsed:
                        yield parsed
                offset += PAGE_LIMIT
                total = int(data.get("total_count") or 0)
                if offset >= total or offset >= OFFSET_CAP:
                    break
                time.sleep(throttle_s)
            time.sleep(throttle_s)
