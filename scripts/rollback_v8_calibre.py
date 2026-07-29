"""ROLLBACK de la bascule v8 — retour INTÉGRAL à `q_v7_defisc` comme run servi.

Réversible, testé, idempotent (arbitrage Vic) :
  1. supprime le run cible de TOUTES les tables clés-run (parcel_p_score_v2, dryrun_parcel_
     evaluations, dryrun_cascade_results, snapshot, p_score_v2_runs) → q_v7_defisc redevient le
     « dernier run » lu par la fiche ;
  2. restaure parcel_residuel et p_model_static depuis les sauvegardes pré-bascule ;
  3. re-pointer les surfaces (hors DB, opérateur) : export LABUSE_SERVED_RUN=q_v7_defisc ;
     VITE_RUN_LABEL=q_v7_defisc npm run build ; labuse build-mvt --label q_v7_defisc.

q_v7_defisc n'ayant JAMAIS été touché en base, le rollback ne re-matérialise rien. Idempotent.
Réutilisable pour un run jetable : rollback(target=…, restore_features=False).

Usage : PYTHONPATH=src python scripts/rollback_v8_calibre.py [--target q_v8_calibre]
"""
from __future__ import annotations
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import text
from labuse.db import engine

DEFAULT_TARGET = "q_v8_calibre"
RUN_TABLES = [("parcel_p_score_v2", "run_id"), ("dryrun_parcel_evaluations", "run_label"),
              ("dryrun_cascade_results", "run_label")]


def rollback(target: str = DEFAULT_TARGET, restore_features: bool = True) -> dict:
    """Purge le run `target` et (optionnel) restaure les features. Idempotent."""
    purged = {}
    with engine().begin() as c:
        for tbl, col in RUN_TABLES:
            if c.execute(text("SELECT to_regclass(:t)"), {"t": tbl}).scalar():
                purged[tbl] = c.execute(text(f"DELETE FROM {tbl} WHERE {col} = :t"), {"t": target}).rowcount
        # snapshot : lien snapshot_parcelles→snapshot par snapshot_id (PAS run_label) — purger via
        # score_snapshots.run_label, sinon les lignes survivent orphelines (bug 29/07, corrigé).
        snap_ids = [r[0] for r in c.execute(text(
            "SELECT id FROM score_snapshots WHERE run_label = :t"), {"t": target}).fetchall()]
        if snap_ids:
            purged["snapshot_parcelles"] = c.execute(text(
                "DELETE FROM score_snapshot_parcelles WHERE snapshot_id = ANY(:ids)"), {"ids": snap_ids}).rowcount
            c.execute(text("DELETE FROM score_snapshots WHERE run_label = :t"), {"t": target})
        c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id = :t"), {"t": target})
        for k, v in purged.items():
            print(f"  purge {k:28s} : {v} lignes")
        if snap_ids:
            print(f"  purge snapshots {snap_ids}")
        if restore_features:
            for src, bak in [("parcel_residuel", "parcel_residuel_pre_v8"),
                             ("p_model_static", "p_model_static_pre_v8")]:
                if not c.execute(text("SELECT to_regclass(:b)"), {"b": bak}).scalar():
                    raise SystemExit(f"SAUVEGARDE ABSENTE : {bak} — rollback impossible, STOP.")
                c.execute(text(f"TRUNCATE {src}"))
                c.execute(text(f"INSERT INTO {src} SELECT * FROM {bak}"))
                n = c.execute(text(f"SELECT count(*) FROM {src}")).scalar()
                print(f"  restauré {src:20s} : {n} lignes (depuis {bak})")
    return purged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=DEFAULT_TARGET)
    ap.add_argument("--no-restore-features", action="store_true")
    args = ap.parse_args()
    rollback(args.target, restore_features=not args.no_restore_features)
    with engine().connect() as c:
        dist = c.execute(text("SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id='q_v7_defisc' GROUP BY tier ORDER BY count(*)")).all()
        last = c.execute(text("SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()
    print("\nROLLBACK EFFECTUÉ. q_v7_defisc (tiers de référence) :")
    for tier, n in dist:
        print(f"  {tier:20s} {n}")
    print(f"  dernier run (fiche) = {last}")
    print("\n  SURFACES : export LABUSE_SERVED_RUN=q_v7_defisc ; VITE_RUN_LABEL=q_v7_defisc npm run build ; labuse build-mvt --label q_v7_defisc")


if __name__ == "__main__":
    main()
