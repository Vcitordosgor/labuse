"""SCORING-9 · le Signal candidat `q_v16` par le PIPELINE réel, sur le RÉSIDUEL run 13 servi.

Décision Vic (SCORING-9) : on NE rejoue PAS la cascade — l'étage 0 reste `q_v13_sources1`
(dérive mesurée nulle par SCORING-8 lot B). L'étage 0 est néanmoins PARAMÉTRABLE
(`--etage0 cascade_2026_10` ou `LABUSE_ETAGE0_RUN=…`) pour garder l'option ouverte sans toucher
le code. La cascade est LUE (override non destructif), jamais recalculée ici.

Le MODÈLE est inchangé : q_v16 réutilise la recette `q_v15`. Seul le `run_id` (label) devient
`q_v16`. La recette q_v15 lit le RÉSIDUEL EN DIRECT depuis la vue `parcel_residuel`
(`qv12.charger_residuel`), donc le Signal reflète le run servi COURANT (run 13) — pas une copie
figée dans un cache de features.

PREUVE DE FRAÎCHEUR DES CACHES (mandat SCORING-9) — avant de scorer, ce script :
  1. rafraîchit le cache statique du feature store (`refresh_static_residuel`, quelques secondes :
     `labuse.cli rebuild` reconstruit les couches spatiales / tuiles / fiches mais NE touche PAS
     les colonnes résiduel de `p_model_static` — mesuré STALE au run 13) ;
  2. PROUVE, sur 5 parcelles dont la SDP a changé entre le run servi précédent (run_seq 10) et le
     run servi courant (run_seq 13), que la vue `parcel_residuel` ET le cache `p_model_static`
     portent désormais la valeur du RUN 13 (≠ run 10).
Si la preuve échoue, le script S'ARRÊTE (aucun scoring sur cache périmé).

⚠ PRÉ-REQUIS : le run_id `q_v16` ne doit PAS déjà exister (run_score_v2 refuse un run_id présent) :
purger q_v16 de p_score_v2_runs / parcel_p_score_v2 / score_labuse AVANT (voir purge_qv16.py).

Doctrine INCHANGÉE : rien de servi ne bouge ; AUCUN promote, AUCUNE écriture sur
config/served_run.txt, AUCUN merge.

Usage :
  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<worktree>/src \
      python scripts/audit/scoring/run_qv16.py [--etage0 q_v13_sources1] [--verify-only]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))  # piège worktree : l'editable pointe ailleurs

ETAGE0_DEFAUT = "q_v13_sources1"   # SCORING-9 : cascade du 07/09 réutilisée (pas de rejeu)
RUN_ID = "q_v16"
RECETTE = "q_v15"                  # modèle INCHANGÉ (q_v16 = q_v15 + résiduel run 13)
ANNEE = 2026
RUN_SERVI_PREC = 10                # run_seq du run servi précédent (q_v15)
RUN_SERVI_COURANT = 13             # run_seq du run servi courant (q_v16)


def prouver_caches_run13(session) -> bool:
    """Rafraîchit le cache statique résiduel puis PROUVE qu'il porte le run 13 servi, sur
    5 parcelles dont la SDP a changé entre run_seq 10 et 13. Renvoie True si la preuve passe."""
    from sqlalchemy import text

    from labuse.scoring.p_model.sql import refresh_static_residuel

    # (0) run servi courant = celui que la vue parcel_residuel sert (doit être 13).
    servi = session.execute(
        text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
    print(f"[caches] run résiduel servi = run_seq {servi} "
          f"(attendu {RUN_SERVI_COURANT}).", flush=True)
    if servi != RUN_SERVI_COURANT:
        print(f"  ⛔ le run servi n'est pas {RUN_SERVI_COURANT} — ABANDON.", flush=True)
        return False

    # (1) rafraîchir le cache statique du feature store depuis la vue servie (run 13).
    n = refresh_static_residuel(session)
    session.commit()
    print(f"[caches] refresh_static_residuel : {n} lignes p_model_static mises à jour "
          "depuis parcel_residuel (run 13).", flush=True)

    # (2) preuve sur 5 parcelles dont la SDP a changé entre run 10 et run 13.
    rows = session.execute(text("""
        WITH chg AS (
          SELECT a.parcel_id,
                 a.sdp_residuelle_m2 AS sdp10,
                 b.sdp_residuelle_m2 AS sdp13
          FROM parcel_residuel_runs a
          JOIN parcel_residuel_runs b USING (parcel_id)
          WHERE a.run_seq = :s10 AND b.run_seq = :s13
            AND a.sdp_residuelle_m2 IS DISTINCT FROM b.sdp_residuelle_m2
          ORDER BY a.parcel_id
          LIMIT 5)
        SELECT p.idu, c.sdp10, c.sdp13,
               pr.sdp_residuelle_m2  AS vue_sdp,
               st.sdp_residuelle_m2  AS cache_sdp
        FROM chg c
        JOIN parcels p            ON p.id = c.parcel_id
        LEFT JOIN parcel_residuel pr ON pr.parcel_id = c.parcel_id
        LEFT JOIN p_model_static st  ON st.idu = p.idu
    """), {"s10": RUN_SERVI_PREC, "s13": RUN_SERVI_COURANT}).all()

    print(f"\n  {'IDU':<16} {'run10':>8} {'run13':>8} {'vue':>8} {'cache':>8}  verdict")
    ok = True
    for r in rows:
        vue_ok = r.vue_sdp == r.sdp13
        cache_ok = r.cache_sdp == r.sdp13
        verdict = "✓ run13" if (vue_ok and cache_ok) else "⛔ PÉRIMÉ"
        if not (vue_ok and cache_ok):
            ok = False
        print(f"  {r.idu:<16} {str(r.sdp10):>8} {str(r.sdp13):>8} "
              f"{str(r.vue_sdp):>8} {str(r.cache_sdp):>8}  {verdict}")
    print("\n[caches] " + ("✓ vue + cache portent le run 13 (≠ run 10) sur les 5 parcelles — "
                           "le Signal q_v16 scorera sur le résiduel servi courant."
                           if ok else
                           "⛔ vue ou cache encore périmé — ABANDON (pas de scoring)."), flush=True)
    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--etage0", default=os.environ.get("LABUSE_ETAGE0_RUN", ETAGE0_DEFAUT),
                    help=f"run cascade lu pour l'étage 0 (défaut {ETAGE0_DEFAUT} ; "
                         "cascade_2026_10 en option).")
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--annee", type=int, default=ANNEE)
    ap.add_argument("--verify-only", action="store_true",
                    help="n'exécute que la preuve de fraîcheur des caches, sans scorer.")
    args = ap.parse_args()

    os.environ["LABUSE_ETAGE0_RUN"] = args.etage0   # cascade réutilisée, jamais rejouée
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    from labuse.db import session_scope

    with session_scope() as s:
        if not prouver_caches_run13(s):
            raise SystemExit(2)

    if args.verify_only:
        print("[run_qv16] --verify-only : caches prouvés, scoring NON lancé.", flush=True)
        return

    from labuse.scoring.p_v2.pipeline import run_score_v2
    t0 = time.time()
    print(f"\n[run_qv16] Signal q_v16 (recette {RECETTE}, étage 0 = {args.etage0}, "
          f"rebuild=False, année {args.annee})…", flush=True)
    with session_scope() as s:
        res = run_score_v2(s, run_id=args.run_id, rebuild=False, snapshot=False,
                           recette=RECETTE, annee=args.annee)
    print(f"[run_qv16] terminé : {res['n']} parcelles scorées, tiers {res.get('tiers')} "
          f"({time.time() - t0:.0f}s). NON servi — étage 0 = {args.etage0} (gravé dans "
          "params), q_v11_m137 reste le Signal servi.", flush=True)


if __name__ == "__main__":
    main()
