"""PALIERS-1 · Lot B — RECALCUL des paliers de q_v14 (p_raw INTACT).

Ré-étiquette la colonne `tier` du run candidat q_v14 avec la politique v2
(statuts.assign_paliers — SOURCE UNIQUE, la même que le pipeline) : palier en
probabilité ABSOLUE (seuils config/scoring_client.yaml), Écartée = cascade étage 0
conservée telle quelle. p_raw, rang, contributions, top5 : RIEN d'autre n'est touché.

Les déclassements (ex-tiers declasse_*) deviennent des MOTIFS (statuts.motifs_parcelle),
la réserve foncière un DRAPEAU (statuts.reserve_fonciere) — dérivés à la lecture, jamais
stockés dans le tier. Une bâtie saturée à p ≥ 0,20 devient donc « Priorité » (avec le
motif « bâti saturé »), plus « Faible ».

INTERDITS respectés : aucun promote, aucune écriture served_run.txt, aucun rescoring
(p_raw inchangé), aucun autre run touché (WHERE run_id='q_v14' STRICT). Idempotent.

Usage : python paliers1_lotB.py [--run q_v14] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import engine  # noqa: E402
from labuse.scoring.p_v2.statuts import assign_paliers, charger_paliers_config  # noqa: E402


def recompute(run_id: str, dry_run: bool) -> dict:
    eng = engine()
    cfg = charger_paliers_config()
    with eng.begin() as conn:
        rows = pd.read_sql(text(
            "SELECT parcelle_id, p_raw, tier FROM parcel_p_score_v2 WHERE run_id = :r"),
            conn, params={"r": run_id})
        if not len(rows):
            raise SystemExit(f"run {run_id!r} absent de parcel_p_score_v2")

        # Écartée = les parcelles déjà écartées par la cascade du run (stored tier='ecartee').
        # p_raw INTACT ; on ne recalcule QUE l'étiquette de palier.
        df = pd.DataFrame({"p": rows["p_raw"],
                           "ecartee_etage0": rows["tier"] == "ecartee"})
        nouveau = assign_paliers(df, cfg, prev_palier=None)

        avant = rows["tier"].value_counts().to_dict()
        apres = nouveau.value_counts().to_dict()
        n_change = int((rows["tier"].to_numpy() != nouveau.to_numpy()).sum())

        if not dry_run:
            upd = pd.DataFrame({"parcelle_id": rows["parcelle_id"], "tier": nouveau})
            conn.execute(text(
                "CREATE TEMP TABLE _pal1 (parcelle_id varchar(14), tier varchar(32)) "
                "ON COMMIT DROP"))
            upd.to_sql("_pal1", conn, if_exists="append", index=False, method="multi",
                       chunksize=10000)
            res = conn.execute(text(
                "UPDATE parcel_p_score_v2 p SET tier = t.tier FROM _pal1 t "
                "WHERE p.run_id = :r AND p.parcelle_id = t.parcelle_id "
                "  AND p.tier IS DISTINCT FROM t.tier"), {"r": run_id})
            n_maj = res.rowcount
        else:
            n_maj = None

    return {"run": run_id, "n_parcelles": len(rows), "dry_run": dry_run,
            "avant": avant, "apres": apres, "n_change_calcule": n_change,
            "n_lignes_mises_a_jour": n_maj, "seuils": cfg.__dict__}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="q_v14")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    out = recompute(a.run, a.dry_run)
    import json
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
