"""QV22-1 (mandat Vic) — le POINTEUR du candidat du calcul de nuit, et son ARCHIVE.

Pourquoi : jusqu'ici le calcul de nuit visait un label FIXE (`LABUSE_CALCUL_NUIT_LABEL`, défaut
`q_v21`). Un candidat déjà complet mais REFUSÉ (contrôles en échec — ex. comptes divergents) restait
le candidat visé : chaque nuit `_run_complet` le voyait complet, sautait le recalcul, remesurait, et
RE-ÉCHOUAIT — il bloquait indéfiniment (constat du 08/11 : calcul-nuit « ok » en 20 s, `calcul_saute`,
verdict REFUS comptes). Règle Vic : un candidat refusé ne bloque JAMAIS la nuit suivante — il est
ARCHIVÉ (il reste en base, non servi) et un run FRAIS est calculé sous le label suivant.

Ce module tient un petit pointeur JSON (`config/candidat_courant.json`) : le label courant + la liste
des labels archivés avec leur motif. Écriture atomique. Le fichier vit dans `config/` (exclu du rsync
de déploiement, comme les manifestes — cf. deploy_app.sh), donc il SURVIT aux déploiements.

Le label courant est initialisé depuis `LABUSE_CALCUL_NUIT_LABEL` (la graine) tant que le pointeur
n'existe pas ; ensuite c'est le pointeur qui gouverne (l'archivage l'avance). Le jugement « label
suivant » et « candidat refusé » est PUR (labuse.autonomie) ; ici vit le seul effet de bord (fichier).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import autonomie

_CONFIG = Path(__file__).resolve().parents[2] / "config"
_FICHIER = _CONFIG / "candidat_courant.json"
_ARCHIVES = _CONFIG / "candidats_archives"


def chemin() -> Path:
    return _FICHIER


def lire() -> dict:
    try:
        return json.loads(_FICHIER.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — absent/illisible → pointeur vide, la graine gouverne
        return {}


def label_courant(graine: str) -> str:
    """Le label visé par le calcul de nuit : le pointeur s'il existe, sinon la GRAINE (env).
    Jamais vide : une graine absente serait un bug de config, on retombe sur `q_v21` (1er run)."""
    etat = lire()
    label = etat.get("label")
    return label if isinstance(label, str) and label else (graine or "q_v21")


def _ecrire(etat: dict) -> None:
    _CONFIG.mkdir(parents=True, exist_ok=True)
    tmp = _FICHIER.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(etat, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, _FICHIER)   # atomique : jamais un pointeur à moitié écrit


def _archiver_manifeste(label: str) -> None:
    """Best-effort : copie le manifeste candidat du run archivé sous `config/candidats_archives/<label>.json`
    (attestation de ce qui a été refusé). Jamais bloquant."""
    try:
        from . import manifeste
        m = manifeste.lire_candidat()
        if m and m.get("scoring_run") == label:
            _ARCHIVES.mkdir(parents=True, exist_ok=True)
            (_ARCHIVES / f"{label}.json").write_text(
                json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def archiver_et_avancer(label: str, raison: str, *, le: str | None = None) -> str:
    """Archive le candidat REFUSÉ `label` (il reste en base, on ne touche à aucune table — on ne fait que
    décrocher le pointeur) et AVANCE au label suivant. Renvoie le nouveau label (à calculer frais).

    Idempotent au sens utile : si le pointeur vise déjà un label != `label` (déjà avancé), on n'archive
    pas deux fois le même — on renvoie le label courant."""
    courant = lire()
    if courant.get("label") and courant.get("label") != label:
        return courant["label"]   # déjà avancé par un passage précédent
    nouveau = autonomie.label_suivant(label)
    archives = list(courant.get("archives", []))
    archives.append({
        "label": label,
        "raison": raison,
        "le": le or datetime.now(timezone.utc).isoformat(),
    })
    _ecrire({"label": nouveau, "archives": archives})
    _archiver_manifeste(label)
    return nouveau
