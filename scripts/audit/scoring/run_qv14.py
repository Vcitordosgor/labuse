"""SCORING-4 · Étape 4 — le run candidat `q_v14` par le PIPELINE réel.

Scoring SEUL (rebuild=False → pas de résiduel : il ne bouge pas), en RÉUTILISANT
la cascade de `q_v13_sources1` (ses 4 378 exclusions neuves) sous le nouveau
run_id `q_v14`, via l'override non destructif `LABUSE_ETAGE0_RUN` du pipeline
(pipeline.py:366-374 ; précédent qa/ponderation/mesure_ablanc.py). Aucun `flux-run`
(qui rejouerait la cascade en heures) — l'étage 0 est LU, jamais recalculé.

Réunit ce qui n'avait jamais été combiné :
  - gains de MODÈLE : artefact gelé q_v14 (recette q_v12 + variables as-of) ;
  - gains de DONNÉES : cascade de q_v13_sources1.

Doctrine : rien de servi ne change (`q_v11_m137` reste servi) ; AUCUN promote,
AUCUNE écriture sur config/served_run.txt, AUCUN merge. Le run est CALCULÉ.

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<worktree>/src \
        python scripts/audit/scoring/run_qv14.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))  # piège worktree : l'editable pointe ailleurs

ETAGE0 = "q_v13_sources1"
RUN_ID = "q_v14"
ANNEE = 2026


def main() -> None:
    os.environ["LABUSE_ETAGE0_RUN"] = ETAGE0  # cascade réutilisée, jamais rejouée
    from labuse.db import session_scope
    from labuse.scoring.p_v2.pipeline import run_score_v2

    t0 = time.time()
    print(f"[run_qv14] scoring q_v14 (recette q_v14, étage 0 = {ETAGE0}, "
          f"rebuild=False, année {ANNEE})…", flush=True)
    with session_scope() as s:
        res = run_score_v2(s, run_id=RUN_ID, rebuild=False, snapshot=False,
                           recette="q_v14", annee=ANNEE)
    print(f"[run_qv14] terminé : {res['n']} parcelles scorées, tiers {res.get('tiers')} "
          f"({time.time() - t0:.0f}s). NON servi — {ETAGE0} réutilisé, "
          "q_v11_m137 reste le run servi.", flush=True)


if __name__ == "__main__":
    main()
