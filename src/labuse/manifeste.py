"""CIRCUIT-1 lot 3.1 — LE MANIFESTE DE SERVICE : un seul pointeur pour tout ce qui est servi.

`config/served_manifest.json` = {scoring_run, residuel_run_seq, mvt_run, division_run,
promoted_at, par, precedent: {…}} — écrit de façon ATOMIQUE (fichier temporaire puis
os.replace). Une bascule déplace scoring, résiduel, mvt et division EN UN SEUL ÉCRIT ;
Revenir restaure le manifeste précédent ENTIER (décision Vic n° 5 : « une seule bascule
déplace tout »).

Pendant la transition, les quatre pointeurs historiques (`served_run.txt`,
`run_precedent.txt`, `mvt_meta.run_label`, `residuel_runs.is_served`) deviennent des VUES
DÉRIVÉES : écrites par `bascule_flux.basculer()` seul, jamais par un autre chemin — puis
marqués obsolètes. `runs.current()` lit le manifeste d'abord (repli served_run.txt tant que
le manifeste n'existe pas : aucun comportement ne change avant la première bascule).

Bootstrap : `construire_depuis_pointeurs(db)` fabrique le premier manifeste depuis l'état
réellement servi (migration sans bascule).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

_FICHIER = Path(__file__).resolve().parents[2] / "config" / "served_manifest.json"
_CACHE_TTL_S = 3.0
_cache: dict = {"val": None, "at": 0.0}

CHAMPS = ("scoring_run", "residuel_run_seq", "mvt_run", "division_run", "promoted_at", "par")


def chemin() -> Path:
    return _FICHIER


def existe() -> bool:
    return _FICHIER.exists()


def lire() -> dict | None:
    """Le manifeste courant (cache court, comme runs.current). None s'il n'existe pas encore."""
    now = time.monotonic()
    if _cache["val"] is not None and (now - _cache["at"]) < _CACHE_TTL_S:
        return _cache["val"]
    if not _FICHIER.exists():
        return None
    val = json.loads(_FICHIER.read_text(encoding="utf-8"))
    _cache["val"] = val
    _cache["at"] = now
    return val


def invalidate() -> None:
    _cache["val"] = None
    _cache["at"] = 0.0


def ecrire(manifest: dict) -> None:
    """Écrit ATOMIQUEMENT (tmp + os.replace) puis invalide le cache. Valide les champs :
    un manifeste incomplet ne s'écrit pas (jamais un pointeur partiel)."""
    manquants = [c for c in ("scoring_run", "mvt_run", "division_run") if not manifest.get(c)]
    if manquants:
        raise ValueError(f"manifeste incomplet — champs manquants : {manquants}")
    tmp = _FICHIER.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, _FICHIER)
    invalidate()


def construire_depuis_pointeurs(db) -> dict:
    """BOOTSTRAP (migration douce) — le premier manifeste, lu de l'état réellement servi :
    served_run.txt (scoring + mvt), residuel_runs.is_served, division = run des candidats
    s'il est UNIQUE sinon le scoring (l'état 2.3 : plus rien d'un run mort n'est servi)."""
    from sqlalchemy import text

    from . import runs
    scoring = runs.current()
    try:
        prec = runs.precedent()
    except Exception:  # noqa: BLE001 — pas de précédent connu (première pose)
        prec = None
    res_seq = None
    try:
        res_seq = db.execute(text(
            "SELECT run_seq FROM residuel_runs WHERE is_served LIMIT 1")).scalar()
    except Exception:  # noqa: BLE001 — table absente (base de test)
        pass
    return {
        "scoring_run": scoring,
        "residuel_run_seq": int(res_seq) if res_seq is not None else None,
        "mvt_run": scoring,
        "division_run": scoring,
        "promoted_at": None,
        "par": "bootstrap (construire_depuis_pointeurs)",
        "precedent": ({"scoring_run": prec, "residuel_run_seq": int(res_seq) if res_seq is not None else None,
                       "mvt_run": prec, "division_run": prec} if prec else None),
    }


def division_run() -> str | None:
    """Le run des candidats division SERVI (lot 2.3 : les lecteurs lisent le manifeste ;
    repli = scoring courant tant que le manifeste n'existe pas)."""
    m = lire()
    if m and m.get("division_run"):
        return m["division_run"]
    from . import runs
    return runs.current()
