"""CHASSE-CALCULS-FIX-1 · Signal p_v2 candidat `q_v19` — étape P-RUN du run q_v19.

Copie paramétrée de run_qv18.py. Les SOURCES n'ont PAS changé depuis q_v18 → on RÉUTILISE la
cascade `q_v18_sources` comme étage 0 (pas de nouveau run de cascade). Ce run q_v19 sert à
matérialiser les correctifs CHASSE-CALCULS-FIX-1 qui dépendent d'un recalcul (E-B1 : backfill de
`parcel_residuel_runs.surface_terrain_m2` ; E-B3/5.1-5.3 : réaffectation `assiette_source`
gabarit↔residuel_legacy, migration des parcelles que le gabarit sert désormais).

⚠ PRÉALABLES (à faire DANS L'ORDRE avant ce script) :
  1. `compute-residuel --ile --assiette-clippee --new-run q_v19 --chunk 500` → nouveau run_seq ;
  2. `residuel-runs` (relever le run_seq neuf) puis `residuel-serve <run_seq q_v19>` : le pipeline
     p_v2 LIT LE RÉSIDUEL SERVI (vue `parcel_residuel` = WHERE run_seq = is_served) — SANS cette
     bascule, le refresh du cache résiduel et l'univers travailleraient sur l'ancien run (q_v18/seq 15).

Ce script : (a0) reconstruit le SOCLE (`build_all` : frame→static→dataset) sur le PARC VIVANT courant ;
(a) rafraîchit le cache statique du résiduel (`refresh_static_residuel`) sur le résiduel SERVI (q_v19) ;
(b) lance `run_score_v2` avec **rebuild=True** (features ext DVF/SITADEL frais), recette `q_v15`,
étage 0 = cascade RÉUTILISÉE `q_v18_sources`. NON servi, AUCUNE bascule served_run.txt, AUCUN merge.

⚠ L'étage 0 ne définit PAS l'univers (il ne pose qu'un drapeau `ecartee_etage0`) : l'univers du
Signal = `p_model_frame`, d'où l'importance du pas (a0).

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<repo>/src \
        python scripts/audit/scoring/run_qv19.py [--etage0 q_v18_sources] \
            [--no-rebuild] [--no-rebuild-base]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

ETAGE0_DEFAUT = "q_v18_sources"    # cascade RÉUTILISÉE (sources inchangées depuis q_v18).
RUN_ID = "q_v19"
RECETTE = "q_v15"                  # modèle inchangé (comme q_v16/q_v18)
ANNEE = 2026


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--etage0", default=os.environ.get("LABUSE_ETAGE0_RUN", ETAGE0_DEFAUT),
                    help=f"run cascade (étage 0) LU par le score (défaut {ETAGE0_DEFAUT} ; "
                         "sources inchangées depuis q_v18 → on réutilise q_v18_sources).")
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--annee", type=int, default=ANNEE)
    ap.add_argument("--no-rebuild", action="store_true",
                    help="ne PAS re-matérialiser les features ext (déconseillé : SITADEL a changé).")
    ap.add_argument("--no-rebuild-base", action="store_true",
                    help="ne PAS reconstruire le socle frame/static/dataset. À N'UTILISER que si le "
                         "parc n'a pas bougé depuis le dernier build_all : sinon l'univers du Signal "
                         "reste gelé (les nouvelles parcelles cadastrales n'ont pas de frame → pas de "
                         "Signal, les disparues restent scorées). Défaut : on reconstruit.")
    args = ap.parse_args()

    os.environ["LABUSE_ETAGE0_RUN"] = args.etage0
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

    from sqlalchemy import text
    from labuse.db import session_scope
    from labuse.scoring.p_model import sql as p_sql
    from labuse.scoring.p_model.sql import refresh_static_residuel
    from labuse.scoring.p_v2.pipeline import run_score_v2

    # (a0) SOCLE : reconstruire frame→mutations→permits→bâti→static→dataset sur le PARC VIVANT courant.
    # Indispensable après un différentiel cadastre : `build_frame` prend `parcels` moins les disparues =
    # EXACTEMENT l'univers du run résiduel île. Sans ce pas, l'univers du Signal reste gelé au parc
    # périmé (`rebuild=True` ne refait QUE les features ext, pas le frame/static). Coût : ≈ 2 h (spatial).
    if not args.no_rebuild_base:
        print("[run_qv19] socle : build_all (frame→static→dataset) sur le parc vivant courant "
              "(≈ 2 h, build_static spatial)…", flush=True)
        with session_scope() as s:
            p_sql.build_all(s)
            s.commit()
        with session_scope() as s:
            n_frame = s.execute(text("SELECT count(*) FROM p_model_frame")).scalar()
        print(f"[run_qv19] socle reconstruit : p_model_frame = {n_frame} parcelles (= univers du run).",
              flush=True)

    # (a) le cache statique du résiduel doit refléter le résiduel SERVI (après residuel-serve q_v19)
    with session_scope() as s:
        n = refresh_static_residuel(s)
    print(f"[run_qv19] refresh_static_residuel : {n} ligne(s) réalignée(s) sur le résiduel servi.",
          flush=True)

    # (b) Signal p_v2 — rebuild des features (DVF/SITADEL frais), recette q_v15, étage 0 = args.etage0
    t0 = time.time()
    print(f"[run_qv19] Signal {args.run_id} (recette {RECETTE}, étage 0 = {args.etage0}, "
          f"rebuild={not args.no_rebuild}, année {args.annee})…", flush=True)
    with session_scope() as s:
        res = run_score_v2(s, run_id=args.run_id, rebuild=not args.no_rebuild, snapshot=False,
                           recette=RECETTE, annee=args.annee)
    print(f"[run_qv19] terminé : {res['n']} parcelles scorées, tiers {res.get('tiers')} "
          f"({time.time() - t0:.0f}s). NON servi — aucune bascule.", flush=True)


if __name__ == "__main__":
    main()
