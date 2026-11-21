"""MISE-EN-LIGNE-1 — la révision du code DÉPLOYÉ, lisible SANS dépôt git.

La prod est un rsync sans `.git` : `git rev-parse` y échoue, et les deux tampons de version
(`_commit_build` des PDF d'étude, `_FICHE_CODE_REV` des fiches) retombaient sur « rien » ou sur
une constante datée. Or `deploy_app.sh` écrit déjà, à CHAQUE déploiement, le marqueur
`config/deploiement.json` : `{"sha": …, "deploye_le": …, "par": …}`. Ce module le lit — c'est le
repli officiel quand ni `LABUSE_BUILD_COMMIT` ni git ne répondent.
"""
from __future__ import annotations

import json
from pathlib import Path

#: racine du dépôt/de l'app : src/labuse/build_rev.py → parents[2] (= /opt/labuse/app en prod).
_RACINE = Path(__file__).resolve().parents[2]
_MARQUEUR = _RACINE / "config" / "deploiement.json"


def deploiement_sha(marqueur: Path | None = None) -> str | None:
    """Le sha (12 car.) du dernier déploiement d'après `config/deploiement.json`, sinon None.

    Best-effort : fichier absent / illisible / sans sha → None, jamais une exception (les tampons
    de version ne doivent jamais faire échouer un rendu)."""
    p = marqueur or _MARQUEUR
    try:
        sha = (json.loads(p.read_text(encoding="utf-8")).get("sha") or "").strip()
        return sha[:12] or None
    except Exception:  # noqa: BLE001 — stamp best-effort, jamais bloquant
        return None
