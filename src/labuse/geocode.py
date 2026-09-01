"""CONNEXIONS-2 Lot 9.2 (KO-13) — géocodage BAN UNIQUE : une fonction, un `BAN_URL`, appelée PARTOUT.

Avant : deux implémentations BAN + `ST_Contains` (`audit.audit_by_address` et `api/scoreur._geocode`),
chacune avec son propre `BAN_URL` et son client httpx — le docstring de scoreur prétendait « réutilise
audit » mais réimplémentait. Ici, LE seul appel HTTP au service /search de la BAN. Le géocodage BAN
n'est pas un portail (aucune doctrine anti-robot) : requête à la demande, 2 tentatives (rate-limit).

Note : `ingestion/ban_adresses.py` (import BULK du CSV BAN) et la table interne `ban_adresses`
(autocomplete Copilote) sont des mécanismes DISTINCTS (pas un appel /search) — hors de ce point.
"""
from __future__ import annotations

import httpx

from .config import get_settings

#: LE seul endpoint /search de la BAN (géocodage à la demande). Un seul, ici.
BAN_URL = "https://api-adresse.data.gouv.fr/search/"


class BanIndisponible(Exception):
    """Le service BAN n'a pas répondu (réseau / rate-limit après 2 tentatives)."""


class BanIntrouvable(Exception):
    """La BAN a répondu mais l'adresse n'a aucun résultat."""


def geocode_ban(q: str, *, limit: int = 1, ua: str = "LA-BUSE/0.1") -> dict:
    """Géocode `q` via la BAN. Renvoie {lon, lat, label, properties} du 1er résultat.
    Lève `ValueError` (adresse trop courte), `BanIndisponible` (service KO) ou `BanIntrouvable`."""
    q = (q or "").strip()
    if len(q) < 3:
        raise ValueError("Adresse trop courte.")
    ban, last = None, None
    for _ in range(2):   # BAN rate-limite parfois : une 2e tentative suffit
        try:
            with httpx.Client(timeout=get_settings().http_timeout_s,
                              headers={"User-Agent": ua}) as c:
                r = c.get(BAN_URL, params={"q": q, "limit": limit})
                r.raise_for_status()
                ban = r.json()
            break
        except Exception as exc:  # noqa: BLE001 — on retente une fois, sinon on remonte proprement
            last = exc
    if ban is None:
        raise BanIndisponible(f"Géocodage (BAN) injoignable : {type(last).__name__}.")
    feats = ban.get("features") or []
    if not feats:
        raise BanIntrouvable(f"Adresse « {q} » non trouvée.")
    f0 = feats[0]
    lon, lat = f0["geometry"]["coordinates"]
    props = f0.get("properties", {})
    return {"lon": lon, "lat": lat, "label": props.get("label", q), "properties": props}
