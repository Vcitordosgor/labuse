"""SUITE-1 · S3 — le RUN SERVI, relu À LA REQUÊTE (bascule à chaud, sans redémarrage).

Avant : `Q_A_RUN_LABEL` (scoring/score_v_constants.py) était une CONSTANTE lue à l'import → une
bascule (réécriture de `config/served_run.txt` par `golden_ops.promote`) ne prenait effet qu'au
REDÉMARRAGE du serveur. C'est l'inverse de ce que promet le bouton « Basculer ».

Ici, `current()` relit le pointeur versionné à CHAQUE requête, avec un cache TRÈS COURT (quelques
secondes) pour ne pas relire le fichier à chaque ligne SQL d'une même requête. La bascule appelle
`invalidate()` juste après avoir réécrit le fichier → la requête suivante lit le nouveau run.

Point de vérité unique INCHANGÉ : `config/served_run.txt` (backend + bundle front). L'override de
DÉVELOPPEMENT `LABUSE_SERVED_RUN` reste honoré (et prioritaire), comme avant. Lecture seule côté
disque ; ce module n'écrit jamais le pointeur (c'est le rôle de `golden_ops.promote`).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

_SERVED_FILE = Path(__file__).resolve().parents[2] / "config" / "served_run.txt"

#: cache court : un même handler de requête lit le run des dizaines de fois (une par étape SQL). On
#: relit le fichier au plus une fois toutes les quelques secondes — assez pour qu'une bascule prenne
#: effet « immédiatement » du point de vue humain, sans marteler le disque.
_CACHE_TTL_S = 3.0
_cache: dict = {"val": None, "at": 0.0}


def _lire_fichier() -> str:
    """1ʳᵉ ligne non commentée de config/served_run.txt (le pointeur du run servi)."""
    for line in _SERVED_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            return s
    raise RuntimeError(
        f"config/served_run.txt ne contient aucune valeur (uniquement des commentaires) : {_SERVED_FILE}")


def current() -> str:
    """Le run servi COURANT, relu à la requête (cache {_CACHE_TTL_S} s). L'override de DEV
    `LABUSE_SERVED_RUN` est prioritaire et non caché (aucune surprise en test/dev)."""
    override = os.environ.get("LABUSE_SERVED_RUN")
    if override:
        return override
    now = time.monotonic()
    if _cache["val"] is not None and (now - _cache["at"]) < _CACHE_TTL_S:
        return _cache["val"]
    val = _lire_fichier()
    _cache["val"] = val
    _cache["at"] = now
    return val


def invalidate() -> None:
    """À appeler juste après une bascule (réécriture de served_run.txt) : la prochaine lecture relit
    le fichier. Rend la bascule effective SANS redémarrage."""
    _cache["val"] = None
    _cache["at"] = 0.0
