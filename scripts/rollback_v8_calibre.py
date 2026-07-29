"""ROLLBACK de la bascule v8 — retour INTÉGRAL à `q_v7_defisc` comme run servi.

Réversible et testé (arbitrage Vic, contrôle 1) :
  1. supprime le run q_v8_calibre de TOUTES les tables clés-run (parcel_p_score_v2, dryrun_*,
     p_score_v2_runs) → q_v7_defisc redevient le « dernier run » (fiche) ;
  2. restaure parcel_residuel et p_model_static depuis les sauvegardes pré-bascule ;
  3. re-pointer les surfaces (hors DB, opérateur) : export LABUSE_SERVED_RUN=q_v7_defisc ;
     VITE_RUN_LABEL=q_v7_defisc npm run build ; labuse build-mvt --label q_v7_defisc.

q_v7_defisc n'ayant JAMAIS été touché en base, le rollback ne re-matérialise rien — il retire la
cible et restaure les deux tables de features. Idempotent.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import text
from labuse.db import engine

TARGET = "q_v8_calibre"
RUN_TABLES = [("parcel_p_score_v2", "run_id"), ("dryrun_parcel_evaluations", "run_label"),
              ("dryrun_cascade_results", "run_label"), ("score_snapshot_parcelles", None)]


def main():
    with engine().begin() as c:
        # 1) purge du run cible
        for tbl, col in RUN_TABLES:
            if col is None:
                continue
            if c.execute(text("SELECT to_regclass(:t)"), {"t": tbl}).scalar():
                n = c.execute(text(f"DELETE FROM {tbl} WHERE {col} = :t"), {"t": TARGET}).rowcount
                print(f"  purge {tbl:28s} : {n} lignes")
        # snapshot lié au run : le lien snapshot_parcelles→snapshot est par snapshot_id (PAS
        # run_label) — purger via score_snapshots.run_label=TARGET, sinon 431 663 lignes orphelines
        # survivent (bug rollback 29/07, corrigé). Idempotent.
        snap_ids = [r[0] for r in c.execute(text(
            "SELECT id FROM score_snapshots WHERE run_label = :t"), {"t": TARGET}).fetchall()]
        if snap_ids:
            c.execute(text("DELETE FROM score_snapshot_parcelles WHERE snapshot_id = ANY(:ids)"),
                      {"ids": snap_ids})
            c.execute(text("DELETE FROM score_snapshots WHERE run_label = :t"), {"t": TARGET})
            print(f"  purge snapshots {snap_ids} + leurs parcelles")
        c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id = :t"), {"t": TARGET})
        # 2) restauration des features pré-bascule
        for src, bak in [("parcel_residuel", "parcel_residuel_pre_v8"),
                         ("p_model_static", "p_model_static_pre_v8")]:
            if not c.execute(text("SELECT to_regclass(:b)"), {"b": bak}).scalar():
                raise SystemExit(f"SAUVEGARDE ABSENTE : {bak} — rollback impossible, STOP.")
            c.execute(text(f"TRUNCATE {src}"))
            c.execute(text(f"INSERT INTO {src} SELECT * FROM {bak}"))
            n = c.execute(text(f"SELECT count(*) FROM {src}")).scalar()
            print(f"  restauré {src:20s} : {n} lignes (depuis {bak})")
        # 3) vérif : q_v7_defisc intact + redevenu dernier run
        dist = c.execute(text("SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id='q_v7_defisc' GROUP BY tier ORDER BY count(*)")).all()
        last = c.execute(text("SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()
    print("\nROLLBACK EFFECTUÉ. q_v7_defisc (tiers de référence) :")
    for tier, n in dist:
        print(f"  {tier:20s} {n}")
    print(f"  dernier run (fiche) = {last}")
    print(f"\n  SURFACES : export LABUSE_SERVED_RUN=q_v7_defisc ; VITE_RUN_LABEL=q_v7_defisc npm run build ; labuse build-mvt --label q_v7_defisc")


if __name__ == "__main__":
    main()
