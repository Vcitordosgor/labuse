"""SCORING-7 · le run candidat `q_v15` par le PIPELINE réel, étage 0 GRAVÉ.

Calqué sur `run_qv14.py`. Scoring SEUL (rebuild=False → pas de résiduel : il ne
bouge pas), en RÉUTILISANT la cascade de `q_v13_sources1` sous le run_id `q_v15`,
via l'override non destructif `LABUSE_ETAGE0_RUN` du pipeline (pipeline.py:376-383 ;
la cascade est LUE, jamais recalculée — aucun `flux-run`).

Différence avec q_v14 : le pipeline persiste désormais `etage0_run` dans
`p_score_v2_runs.params` (pipeline.py, COHÉRENCE-RUN-1). `resoudre_cascade_run`
le lit AVANT `prev_run`, donc l'emprunt survit même si `previous_run()` retombe
sur un run sans cascade (q_v14). Sans ce point, q_v15 restait « incomplet » et la
pompe ne le proposait jamais.

Doctrine : rien de servi ne change (`q_v11_m137` reste servi) ; AUCUN promote,
AUCUNE écriture sur config/served_run.txt, AUCUN merge. Le run est CALCULÉ.

Pré-requis : le run_id `q_v15` ne doit PAS déjà exister (run_score_v2 refuse un
run_id présent — idempotence). Purger q_v15 de p_score_v2_runs / parcel_p_score_v2
/ score_labuse AVANT (geste séparé, hors de ce script).

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<worktree>/src \
        python scripts/audit/scoring/run_qv15.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))  # piège worktree : l'editable pointe ailleurs

ETAGE0 = "q_v13_sources1"
RUN_ID = "q_v15"
ANNEE = 2026


def main() -> None:
    os.environ["LABUSE_ETAGE0_RUN"] = ETAGE0  # cascade réutilisée, jamais rejouée
    # base locale : rôle openclaw (comme le harnais _common) — le défaut config
    # (rôle « labuse ») n'existe pas en local.
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    from labuse.db import session_scope
    from labuse.scoring.p_v2.pipeline import run_score_v2

    t0 = time.time()
    print(f"[run_qv15] scoring q_v15 (recette q_v15, étage 0 = {ETAGE0}, "
          f"rebuild=False, année {ANNEE})…", flush=True)
    with session_scope() as s:
        res = run_score_v2(s, run_id=RUN_ID, rebuild=False, snapshot=False,
                           recette="q_v15", annee=ANNEE)
    print(f"[run_qv15] terminé : {res['n']} parcelles scorées, tiers {res.get('tiers')} "
          f"({time.time() - t0:.0f}s). NON servi — {ETAGE0} réutilisé (gravé dans "
          "params.etage0_run), q_v11_m137 reste le run servi.", flush=True)


if __name__ == "__main__":
    main()
