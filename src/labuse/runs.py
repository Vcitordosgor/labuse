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
#: DONNEES-2 (B4) — le run servi PRÉCÉDENT (retour arrière), point de vérité versionné M80. Lu VIVANT
#: ici (comme le servi), plus jamais figé dans une constante de module (`RUN_PRECEDENT` l'était et
#: mentait après une bascule — la page Flux étiquetait le mauvais « ancien run servi »).
_PRECEDENT_FILE = Path(__file__).resolve().parents[2] / "config" / "run_precedent.txt"

#: cache court : un même handler de requête lit le run des dizaines de fois (une par étape SQL). On
#: relit le fichier au plus une fois toutes les quelques secondes — assez pour qu'une bascule prenne
#: effet « immédiatement » du point de vue humain, sans marteler le disque.
_CACHE_TTL_S = 3.0
_cache: dict = {"val": None, "at": 0.0}
_cache_prec: dict = {"val": None, "at": 0.0}


def _lire(fichier: Path, quoi: str) -> str:
    """1ʳᵉ ligne non commentée d'un pointeur versionné (served_run.txt / run_precedent.txt)."""
    for line in fichier.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            return s
    raise RuntimeError(f"{quoi} ne contient aucune valeur (uniquement des commentaires) : {fichier}")


def _lire_fichier() -> str:
    """1ʳᵉ ligne non commentée de config/served_run.txt (le pointeur du run servi)."""
    return _lire(_SERVED_FILE, "config/served_run.txt")


def current() -> str:
    """Le run servi COURANT, relu à la requête (cache {_CACHE_TTL_S} s). L'override de DEV
    `LABUSE_SERVED_RUN` est prioritaire et non caché (aucune surprise en test/dev)."""
    override = os.environ.get("LABUSE_SERVED_RUN")
    if override:
        return override
    now = time.monotonic()
    if _cache["val"] is not None and (now - _cache["at"]) < _CACHE_TTL_S:
        return _cache["val"]
    # CIRCUIT-1 lot 3.1 — le MANIFESTE (config/served_manifest.json) fait foi quand il existe ;
    # served_run.txt devient sa vue dérivée (écrite par bascule_flux seul). Tant qu'il n'est pas
    # posé, l'ancien fichier fait foi. GARDE TESTS : le manifeste n'est consulté que s'il vit
    # dans le MÊME dossier que _SERVED_FILE — un test qui pointe _SERVED_FILE vers un tmp
    # retrouve le comportement fichier pur (attrapé par test_run_hot_swap_s3 à la 1re pose réelle).
    from . import manifeste as _manifeste
    m = _manifeste.lire() if _manifeste.chemin().parent == _SERVED_FILE.parent else None
    val = (m or {}).get("scoring_run") or _lire_fichier()
    _cache["val"] = val
    _cache["at"] = now
    return val


def precedent() -> str:
    """DONNEES-2 (B4) — le run servi PRÉCÉDENT (cible du retour arrière), relu À LA REQUÊTE de
    config/run_precedent.txt (cache court, comme `current()`). L'override DEV `LABUSE_RUN_PRECEDENT`
    est prioritaire et non caché. Remplace la constante figée `score_v_constants.RUN_PRECEDENT`, qui
    ne suivait pas la bascule (elle datait de l'import du process)."""
    override = os.environ.get("LABUSE_RUN_PRECEDENT")
    if override:
        return override
    now = time.monotonic()
    if _cache_prec["val"] is not None and (now - _cache_prec["at"]) < _CACHE_TTL_S:
        return _cache_prec["val"]
    from . import manifeste as _manifeste
    m = _manifeste.lire() if _manifeste.chemin().parent == _PRECEDENT_FILE.parent else None
    val = (((m or {}).get("precedent") or {}).get("scoring_run")
           or _lire(_PRECEDENT_FILE, "config/run_precedent.txt"))
    _cache_prec["val"] = val
    _cache_prec["at"] = now
    return val


def invalidate() -> None:
    """À appeler juste après une bascule (réécriture du manifeste et de ses vues dérivées) : la
    prochaine lecture relit tout. Rend la bascule effective SANS redémarrage."""
    _cache["val"] = None
    _cache["at"] = 0.0
    _cache_prec["val"] = None
    _cache_prec["at"] = 0.0
    from . import manifeste as _manifeste
    _manifeste.invalidate()
