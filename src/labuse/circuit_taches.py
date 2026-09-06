"""CIRCUIT-P2 (lot 3.2/3.3) — L'ÉTAT & LA PROGRESSION des tâches longues de la page Circuit
(« Vérifier que tout coule », « Envoyer les agents »), dans un fichier JSON lu par l'API.

Même mécanique que `run_progress` (fichier partagé, écriture atomique, lecture qui ne lève jamais) :
la tâche tourne dans un thread détaché qui écrit sa progression ; l'API la lit pour la ligne de
progression sous les onglets, le message final, et — pour les agents — les réservoirs « en route »
(état mauve). Un fichier par KIND (`verifier`, `agents`), dans `LABUSE_RUN_STATE_DIR` (défaut /tmp),
là où vivent déjà les états de run. Cross-worker : tous les workers uvicorn partagent /tmp.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

EN_COURS = "en_cours"
TERMINE = "termine"
ECHEC = "echec"

_SAFE = re.compile(r"[^A-Za-z0-9_.:-]")


def _dir() -> Path:
    d = Path(os.environ.get("LABUSE_RUN_STATE_DIR", "/tmp"))
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(kind: str) -> Path:
    return _dir() / f"labuse-circuit-tache-{_SAFE.sub('_', kind)}.json"


def lire(kind: str) -> dict | None:
    """L'état d'une tâche (jamais une exception : un fichier illisible/absent = None)."""
    p = _path(kind)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _ecrire(kind: str, data: dict) -> dict:
    p = _path(kind)
    tmp = p.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)
    except OSError:
        pass
    return data


def demarrer(kind: str, *, total: int, par: str, message: str = "") -> dict:
    return _ecrire(kind, {"kind": kind, "etat": EN_COURS, "fait": 0, "total": max(0, int(total)),
                          "par": par, "message": message, "en_route": [],
                          "debut": _now(), "maj": _now()})


def avancer(kind: str, *, fait: int, message: str | None = None,
            en_route: list | None = None) -> dict:
    d = lire(kind) or {"kind": kind, "etat": EN_COURS, "total": 0, "par": "système"}
    d["fait"] = int(fait)
    if message is not None:
        d["message"] = message
    if en_route is not None:
        d["en_route"] = list(en_route)
    d["etat"] = EN_COURS
    d["maj"] = _now()
    return _ecrire(kind, d)


def terminer(kind: str, *, message: str, resultat: dict | None = None) -> dict:
    d = lire(kind) or {"kind": kind, "total": 0, "par": "système"}
    d.update({"etat": TERMINE, "fait": d.get("total", 0), "message": message,
              "resultat": resultat or {}, "en_route": [], "maj": _now(), "fin": _now()})
    return _ecrire(kind, d)


def echouer(kind: str, *, message: str) -> dict:
    d = lire(kind) or {"kind": kind, "total": 0, "par": "système"}
    d.update({"etat": ECHEC, "message": message, "en_route": [], "maj": _now(), "fin": _now()})
    return _ecrire(kind, d)


def en_cours(kind: str) -> bool:
    d = lire(kind)
    return bool(d and d.get("etat") == EN_COURS)


def reservoirs_en_route() -> set:
    """Les identifiants de réservoirs qu'un agent visite en ce moment (état mauve « agent en route »)."""
    d = lire("agents")
    if not d or d.get("etat") != EN_COURS:
        return set()
    return set(d.get("en_route") or [])


def etats() -> dict:
    """Les deux tâches de la page, pour l'endpoint /admin/circuit/taches (null si jamais lancée)."""
    return {"verifier": lire("verifier"), "agents": lire("agents")}
