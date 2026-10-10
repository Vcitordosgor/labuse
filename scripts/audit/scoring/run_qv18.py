"""SOURCES-MAJ-1 · Signal p_v2 candidat `q_v18` — étape P-RUN du run q_v18.

⚠ PRÉALABLES (RAPPORT.md §5.5, à faire DANS L'ORDRE avant ce script) :
  1. couches rafraîchies : `refresh-rpg` (10) [+ érosion/classement sonore si prêts] ;
  2. `reevaluer-cascade --ile` (cascade LIVE sur parcelles courantes, inclut les nouvelles) ;
  3. snapshot étage 0 pour le SCORE (dry-run labellisé, ex. `cascade_2026_10`) si on veut que
     28/46/10 + les nouvelles parcelles pèsent sur le score (sinon l'étage 0 reste q_v13_sources1,
     gelé — cf. --etage0) ;
  4. `compute-residuel --ile --new-run q_v18 --assiette-clippee` → nouveau run_seq ;
  5. `residuel-serve <run_seq q_v18>` : le pipeline p_v2 LIT LE RÉSIDUEL SERVI
     (vue `parcel_residuel` = WHERE run_seq = is_served) — SANS cette bascule, le Signal scorerait
     sur l'ancien résiduel. (C'est un geste de bascule du RÉSIDUEL, distinct de served_run.txt.)

Ce script : (a) rafraîchit le cache statique du résiduel (`refresh_static_residuel`) pour qu'il
reflète le résiduel SERVI courant ; (b) lance `run_score_v2` avec **rebuild=True** (re-matérialise
les features ext DVF/SITADEL — SITADEL a été mis à jour), recette `q_v15`. NON servi, AUCUNE
bascule served_run.txt, AUCUN merge.

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<repo>/src \
        python scripts/audit/scoring/run_qv18.py [--etage0 q_v13_sources1|cascade_2026_10] [--no-rebuild]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

ETAGE0_DEFAUT = "q_v13_sources1"   # gelé ; passer un snapshot frais (cascade_2026_10) pour variante (b)
RUN_ID = "q_v18"
RECETTE = "q_v15"                  # modèle inchangé (comme q_v16)
ANNEE = 2026


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--etage0", default=os.environ.get("LABUSE_ETAGE0_RUN", ETAGE0_DEFAUT),
                    help=f"run cascade (étage 0) LU par le score (défaut {ETAGE0_DEFAUT} ; "
                         "passer un snapshot frais pour que 28/46/10 + nouvelles parcelles comptent).")
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--annee", type=int, default=ANNEE)
    ap.add_argument("--no-rebuild", action="store_true",
                    help="ne PAS re-matérialiser les features ext (déconseillé : SITADEL a changé).")
    args = ap.parse_args()

    os.environ["LABUSE_ETAGE0_RUN"] = args.etage0
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

    from labuse.db import session_scope
    from labuse.scoring.p_model.sql import refresh_static_residuel
    from labuse.scoring.p_v2.pipeline import run_score_v2

    # (a) le cache statique du résiduel doit refléter le résiduel SERVI (après residuel-serve q_v18)
    with session_scope() as s:
        n = refresh_static_residuel(s)
    print(f"[run_qv18] refresh_static_residuel : {n} ligne(s) réalignée(s) sur le résiduel servi.",
          flush=True)

    # (b) Signal p_v2 — rebuild des features (DVF/SITADEL frais), recette q_v15, étage 0 = args.etage0
    t0 = time.time()
    print(f"[run_qv18] Signal {args.run_id} (recette {RECETTE}, étage 0 = {args.etage0}, "
          f"rebuild={not args.no_rebuild}, année {args.annee})…", flush=True)
    with session_scope() as s:
        res = run_score_v2(s, run_id=args.run_id, rebuild=not args.no_rebuild, snapshot=False,
                           recette=RECETTE, annee=args.annee)
    print(f"[run_qv18] terminé : {res['n']} parcelles scorées, tiers {res.get('tiers')} "
          f"({time.time() - t0:.0f}s). NON servi — aucune bascule.", flush=True)


if __name__ == "__main__":
    main()
