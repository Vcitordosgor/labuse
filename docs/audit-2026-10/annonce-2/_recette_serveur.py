"""Harnais de RECETTE ANNONCE-2 (hors code servi) — lance l'API sur :8930 avec un fetch Leboncoin
SIMULÉ, pour jouer les trois cas au navigateur SANS appel réseau sortant :

  · bien PRÉSENT au Radar  → aucun fetch (lookup Radar). URL réelle (list_id en base).
  · bien ABSENT + bloqué   → `_fetch_page_oneshot` LÈVE (DataDome simulé) → message d'échec du mandat.
  · bien ABSENT + réussi   → `_fetch_page_oneshot` rend une FIXTURE LOCALE (qa/radar-terrains/…).

Le patch ne vit QUE dans ce lanceur de recette ; le code servi n'est pas touché. Lancer avec
PYTHONPATH=<worktree>/src et LABUSE_ENV=local + LABUSE_DATABASE_URL vers la base Mac.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("LABUSE_ENV", "local")
os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg:///labuse")

import labuse.pige.api as api  # noqa: E402

_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE = (_ROOT / "qa" / "radar-terrains" / "T-possession.html").read_text(encoding="utf-8")

# Sentinelle du cas « fetch réussi » : un list_id ABSENT de la base (→ repli fetch) dont l'URL porte
# ce numéro ; on rend alors la page d'annonce fixture (terrain La Possession).
_SENTINELLE_FETCH_OK = "9000000003"


def _fetch_simule(url: str) -> str:
    if _SENTINELLE_FETCH_OK in url:
        return _FIXTURE
    # tout autre lien absent du Radar = portail qui bloque (DataDome) → RuntimeError, comme en vrai.
    raise RuntimeError("le portail bloque la lecture automatique (HTTP 403)")


api._fetch_page_oneshot = _fetch_simule

if __name__ == "__main__":
    import uvicorn

    from labuse.api.app import app

    uvicorn.run(app, host="127.0.0.1", port=8930, log_level="warning")
