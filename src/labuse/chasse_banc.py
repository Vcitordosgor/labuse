"""SOLIDITE-1 (Lot 2) — joue les 25 gardes CHASSE-DONNÉES EN-PROCESS, contre la prod.

Comme le banc de cohérence nocturne (`scripts.coherence.banc` en mode en-process), on ne tape PAS l'API
publique : un TestClient FastAPI en interne, authentifié par une session pilote mintée (auth active, hôte
réservé exempté du rate-limit). Les gardes de `chasse_donnees` appellent `_api(path)` (qui attend du JSON
OU du texte brut selon la route) et `_db()` (psycopg lecture seule, DSN = LABUSE_DATABASE_URL → la prod) :
on redirige `_api` vers le client en-process, on laisse `_db` lire la prod directement.

Itère `chasse_donnees.GARDES` : toute garde ajoutée là-bas entre ici sans un geste de plus.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger("labuse.chasse.banc")

_RACINE = Path(__file__).resolve().parents[2]


def jouer_gardes_en_process() -> list[tuple[str, str, str]]:
    """Joue toutes les gardes et rend [(nom, verdict, detail)] (verdict ∈ OK/ECART/SKIP). Une garde qui
    lève est capturée en SKIP (jamais une exception qui tue le passage) — exactement comme `main()`."""
    if str(_RACINE) not in sys.path:
        sys.path.insert(0, str(_RACINE))
    from fastapi.testclient import TestClient

    from .api import auth
    from .api.app import app
    from .api.protection import HOTE_INTERNE
    from scripts.coherence import chasse_donnees as cd

    client = TestClient(app, client=(HOTE_INTERNE, 0))
    client.cookies.set(auth.COOKIE, auth.make_token())    # session pilote (auth active hors 'local')

    def _api_ep(path: str):
        """Même contrat que chasse_donnees._api : JSON si parsable, sinon texte ; lève sur statut >= 400
        (une garde le capte en SKIP via son propre try). Aucun réseau, aucun quota (hôte réservé)."""
        import urllib.error
        r = client.get(path)
        if r.status_code >= 400:
            raise urllib.error.HTTPError(path, r.status_code, "en-process", None, None)
        try:
            return json.loads(r.content)
        except ValueError:
            return r.text

    ancien = cd._api
    cd._api = _api_ep           # les gardes résolvent cd._api au moment de l'appel
    resultats: list[tuple[str, str, str]] = []
    try:
        for nom, garde in cd.GARDES:
            try:
                verdict, detail = garde()
            except Exception as exc:  # noqa: BLE001 — une garde qui plante ne tue pas le banc
                verdict, detail = "SKIP", f"erreur {type(exc).__name__}: {exc}"
            resultats.append((nom, verdict, str(detail)))
    finally:
        cd._api = ancien
    return resultats
