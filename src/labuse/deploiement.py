"""DASHBOARD-4 (P3) — « Déployer » : de combien de commits `main` est-elle en avance sur la PROD ?

La prod tourne un checkout de `main`. Le « dernier deploy connu » est un marqueur posé par
`deploy.sh` à chaque déploiement réussi : `config/deploiement.json` = {sha, iso, par}. L'avance est
alors un fait git pur : `git rev-list --count <sha>..main`. Aucun nombre inventé — si le marqueur
est absent, on le dit (avance = None), la ligne Pilotage invite à le poser au prochain deploy.

Ce module est LU par le Pilotage (ligne « Déployer », rouge tant que l'avance > 0) et n'écrit rien :
le seul rédacteur du marqueur est `deploy.sh` (voir sa dernière étape).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

_RACINE = Path(__file__).resolve().parents[2]
_MARQUEUR = _RACINE / "config" / "deploiement.json"
#: branche servie en production (le déploiement met à jour ce ref).
BRANCHE_PROD = "main"


def _git(*args: str) -> str | None:
    """Sortie d'une commande git dans le checkout, ou None si git/le ref est indisponible.
    Jamais d'exception : le Pilotage ne casse pas si git manque (ex. archive sans .git)."""
    try:
        out = subprocess.run(("git", *args), cwd=_RACINE, capture_output=True,
                             text=True, timeout=5)
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except Exception:  # noqa: BLE001 — git absent / timeout → la ligne dit « inconnu »
        return None


def lire_marqueur() -> dict | None:
    """Le marqueur du dernier deploy (`config/deploiement.json`) ou None s'il n'existe pas encore."""
    if not _MARQUEUR.exists():
        return None
    try:
        return json.loads(_MARQUEUR.read_text())
    except Exception:  # noqa: BLE001 — marqueur illisible → traité comme absent
        return None


def etat() -> dict:
    """État de déploiement LU pour le Pilotage.

    Retour : {marqueur_present, sha, depuis, avance, branche}
      - marqueur_present : le dernier deploy a-t-il été enregistré ?
      - sha / depuis     : commit + date ISO du dernier deploy connu ;
      - avance           : nombre de commits de `main` en avance sur ce sha (None si inconnu) ;
      - branche          : la branche servie en prod (`main`).
    """
    marq = lire_marqueur()
    base = {"marqueur_present": marq is not None, "sha": None, "depuis": None,
            "avance": None, "branche": BRANCHE_PROD}
    if not marq:
        return base
    sha = (marq.get("sha") or "").strip() or None
    base["sha"] = sha
    base["depuis"] = marq.get("iso")
    if not sha:
        return base
    # avance = commits de main non encore déployés (sha..main). Repli sur HEAD si `main` absent
    # (ex. checkout détaché) — on compte alors depuis le sha jusqu'à la tête courante.
    cible = BRANCHE_PROD if _git("rev-parse", "--verify", "--quiet", BRANCHE_PROD) else "HEAD"
    n = _git("rev-list", "--count", f"{sha}..{cible}")
    if n is not None and n.isdigit():
        base["avance"] = int(n)
    # date du deploy : préfère la date du commit déployé si le marqueur ne la porte pas.
    if not base["depuis"]:
        base["depuis"] = _git("show", "-s", "--format=%cI", sha)
    return base
