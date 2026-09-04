"""DONNEES-2 (B2/B3) — ÉTAT & PROGRESSION d'un run lancé, dans un fichier JSON lu par l'API.

Un run de scoring est lancé DÉTACHÉ (subprocess `flux-run`, start_new_session). Jusqu'ici l'API ne
savait rien de lui : ni où il en était, ni comment l'arrêter, ni s'il avait été tué. Ce module donne
au run un ÉTAT partagé, écrit par le process du run et lu par l'API :

  · le run écrit sa PROGRESSION (phase, commune, done/total, %) au fil des communes puis du scoring ;
  · l'API lit cet état pour la barre de l'étape 2 et le STATUT (en cours / terminé / abandonné) ;
  · `stop()` envoie un SIGTERM PROPRE au groupe de process et marque « abandonné » ;
  · `reconcile()` : au chargement, tout « en cours » dont le PROCESSUS A DISPARU passe « abandonné »
    (un run tué, un serveur redémarré — plus de run fantôme « en cours » éternel).

Un fichier par label : ``<dir>/labuse-run-<label>.json`` (dir = ``LABUSE_RUN_STATE_DIR`` ou ``/tmp``,
là où vivent déjà les logs `labuse-flux-run-*.log`). Écriture atomique (tmp + replace). Ne lève
jamais en lecture (un état illisible = absent)."""
from __future__ import annotations

import json
import os
import re
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

STATUT_EN_COURS = "en_cours"
STATUT_TERMINE = "termine"
STATUT_ABANDONNE = "abandonne"

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


def path(label: str) -> Path:
    return _dir() / f"labuse-run-{_SAFE.sub('_', label)}.json"


def read(label: str) -> dict | None:
    p = path(label)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write(label: str, **fields) -> dict:
    """Fusionne `fields` dans l'état du label (crée si absent) et l'écrit atomiquement."""
    data = read(label) or {"label": label}
    data.update(fields)
    data["updated_at"] = _now()
    p = path(label)
    tmp = p.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(p)
    except OSError:
        pass
    return data


def pid_alive(pid) -> bool:
    """Le processus `pid` existe-t-il ? (kill 0). PermissionError = vivant mais pas à nous."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def start(label: str, *, pid, kind: str = "run", recette: str | None = None,
          total: int | None = None, log: str | None = None) -> dict:
    """Ouvre l'état d'un run/reconstruction qui démarre (statut « en cours »)."""
    return write(label, kind=kind, pid=int(pid) if pid else None, recette=recette,
                 statut=STATUT_EN_COURS, phase="démarrage", total=total, done=0, pct=0,
                 started_at=_now(), finished_at=None, error=None, log=log)


def progress(label: str, *, phase: str | None = None, commune: str | None = None,
             done: int | None = None, total: int | None = None, pct: int | None = None) -> dict:
    fields = {k: v for k, v in (("phase", phase), ("commune", commune), ("done", done),
                                ("total", total), ("pct", pct)) if v is not None}
    return write(label, **fields)


def finish(label: str, **fields) -> dict:
    return write(label, statut=STATUT_TERMINE, pct=100, phase="terminé",
                 finished_at=_now(), **fields)


def abandon(label: str, error: str | None = None) -> dict:
    return write(label, statut=STATUT_ABANDONNE, finished_at=_now(), error=error)


def stop(label: str) -> dict:
    """ARRÊT PROPRE : SIGTERM au GROUPE de process du run (il est start_new_session → chef de groupe),
    puis marque « abandonné ». Retourne {ok, tue}. Idempotent (un run déjà mort → tue=False)."""
    st = read(label)
    if not st:
        return {"ok": False, "motif": f"run « {label} » inconnu (aucun état)."}
    pid = st.get("pid")
    tue = False
    if pid and pid_alive(pid):
        try:
            os.killpg(os.getpgid(int(pid)), signal.SIGTERM)
            tue = True
        except (ProcessLookupError, PermissionError, OSError):
            try:
                os.kill(int(pid), signal.SIGTERM)
                tue = True
            except OSError:
                pass
    abandon(label, error="arrêté par l'admin")
    return {"ok": True, "tue": tue}


def list_states() -> list[dict]:
    out: list[dict] = []
    for p in _dir().glob("labuse-run-*.json"):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return out


def en_cours() -> dict | None:
    """Le run de scoring actuellement EN COURS (pid vivant), s'il y en a un. Réconcilie d'abord."""
    for st in list_states():
        if (st.get("kind") == "run" and st.get("statut") == STATUT_EN_COURS
                and pid_alive(st.get("pid"))):
            return st
    return None


def reconcile(complete_labels: set[str]) -> None:
    """Au chargement : un état « en cours » dont le processus a disparu passe « abandonné » ; s'il est
    entre-temps devenu complet (présent dans p_score_v2_runs) il passe « terminé ». En plus, on
    RÉCUPÈRE les runs lancés AVANT ce mécanisme : un log `labuse-flux-run-<label>.log` sans état et
    absent des runs complets = un run tué autrefois → on l'inscrit « abandonné » (D3)."""
    known = set()
    for st in list_states():
        lab = st.get("label")
        known.add(lab)
        if st.get("statut") == STATUT_EN_COURS:
            if lab in complete_labels:
                finish(lab)
            elif not pid_alive(st.get("pid")):
                abandon(lab, error="processus disparu")
    for p in _dir().glob("labuse-flux-run-*.log"):
        m = re.match(r"labuse-flux-run-(.+)\.log$", p.name)
        if not m:
            continue
        lab = m.group(1)
        if lab in known or lab in complete_labels:
            continue
        write(lab, kind="run", statut=STATUT_ABANDONNE, phase="abandonné", pid=None,
              started_at=None, finished_at=_now(), error="lancé avant le suivi de progression")
