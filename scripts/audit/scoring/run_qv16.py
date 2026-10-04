"""SCORING-8 · le run candidat `q_v16` par le PIPELINE réel, étage 0 = cascade REMISE AU JOUR.

Calqué sur `run_qv15.py`. SEULE différence : l'étage 0 réutilisé n'est plus la cascade du 07/09
(`q_v13_sources1`, antérieure à ORACLE-FIX-1 / SUP-ER-EBC repris / 50 pas) mais la cascade
rejouée avec le code et les données du jour, sous le label `cascade_2026_10` (lot B.3). La
cascade est LUE (override non destructif `LABUSE_ETAGE0_RUN`), jamais recalculée ici.

Le MODÈLE est inchangé : q_v16 réutilise la recette `q_v15` (p_v2/qv15.py, `recette inconnue`
pour toute autre valeur — m36 | q_v12 | q_v14 | q_v15). q_v16 = modèle q_v15 + étage 0 du jour.
Seul le `run_id` (label) devient `q_v16` ; c'est lui qui porte le nouvel étage 0.

⚠ PRÉ-REQUIS (gestes de Vic, lot B.3) — à faire AVANT de lancer ce script :
  1. La cascade île `cascade_2026_10` est écrite dans `dryrun_parcel_evaluations` +
     `dryrun_cascade_results` (sinon `resoudre_cascade_run` refuse : « étage 0 absent »).
     → `scripts/audit/scoring/run_cascade_2026_10.py` (≈ 3 h 26 – 4 h 13, 431 663 parcelles).
  2. Le run_id `q_v16` ne doit PAS déjà exister (run_score_v2 refuse un run_id présent) :
     purger q_v16 de p_score_v2_runs / parcel_p_score_v2 / score_labuse AVANT.

Doctrine INCHANGÉE : rien de servi ne bouge (`q_v11_m137` reste servi) ; AUCUN promote, AUCUNE
écriture sur config/served_run.txt, AUCUN merge. `etage0_run = cascade_2026_10` est gravé dans
`p_score_v2_runs.params` → `resoudre_cascade_run` le lit et le run passe la garde de complétude.

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<worktree>/src \
        python scripts/audit/scoring/run_qv16.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))  # piège worktree : l'editable pointe ailleurs

ETAGE0 = "cascade_2026_10"   # ← SCORING-8 lot B : cascade remise au jour (vs q_v13_sources1)
RUN_ID = "q_v16"
RECETTE = "q_v15"            # modèle INCHANGÉ (q_v16 = q_v15 + étage 0 du jour)
ANNEE = 2026


def main() -> None:
    os.environ["LABUSE_ETAGE0_RUN"] = ETAGE0  # cascade réutilisée, jamais rejouée
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    from labuse.db import session_scope
    from labuse.scoring.p_v2.pipeline import run_score_v2

    t0 = time.time()
    print(f"[run_qv16] scoring q_v16 (recette q_v16, étage 0 = {ETAGE0}, "
          f"rebuild=False, année {ANNEE})…", flush=True)
    with session_scope() as s:
        res = run_score_v2(s, run_id=RUN_ID, rebuild=False, snapshot=False,
                           recette=RECETTE, annee=ANNEE)
    print(f"[run_qv16] terminé : {res['n']} parcelles scorées, tiers {res.get('tiers')} "
          f"({time.time() - t0:.0f}s). NON servi — {ETAGE0} réutilisé (gravé dans "
          "params.etage0_run), q_v11_m137 reste le run servi.", flush=True)


if __name__ == "__main__":
    main()
