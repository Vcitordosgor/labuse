#!/usr/bin/env python
"""MISE-EN-LIGNE-7 LOT 4 — correction des PRESCRIPTIONS seules sur le Mac.

Ré-ingère les prescriptions (ER/EBC/mixité…) d'une commune avec l'OUTIL RÉPARÉ
(`ingest_gpu_prescriptions`, requête PAR PARTITION `DU_<insee>` — LOT 1), pour les
communes dont le contrôle indépendant (LOT 2, le ZIP fait foi) a rendu « DIFFÉRENT ».

Garde-fous (décision Vic) :
  · SAUVEGARDE D'ABORD : archive datée de l'état courant (zonage + prescriptions + DPU)
    dans `plu_layer_archive` via `archiver_couches_plu` — avant toute purge.
  · ZONES PAS TOUCHÉES : on ne purge/ré-ingère QUE `kind='plu_gpu_prescription'`.
    Le zonage et les informations (DPU) restent intacts.
  · DRY-RUN par défaut : sans `--appliquer`, la transaction est ANNULÉE (rollback) —
    on voit le compte avant/après sans rien écrire. `--appliquer` committe.

Preuve attendue (Vic) : après `--appliquer`, le contrôle LOT 2 (ZIP) rend « identique »
pour la commune corrigée, les autres communes inchangées.

Usage :
  python scripts/corriger_prescriptions_lot4.py 97402 "Bras-Panon"            # dry-run
  python scripts/corriger_prescriptions_lot4.py 97402 "Bras-Panon" --appliquer
"""
import sys

from sqlalchemy import text

from labuse import controle_plu
from labuse.db import session_scope
from labuse.ingestion import layers_ingest, run_all, seed_sources


def _compte(db, insee: str, commune: str) -> dict:
    rows = db.execute(text(
        "SELECT coalesce(attrs->>'geom_kind','?') gk, count(*) n "
        "FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune=:c "
        "GROUP BY gk ORDER BY gk"), {"c": commune}).fetchall()
    return {r[0]: r[1] for r in rows}


def corriger(insee: str, commune: str, appliquer: bool) -> None:
    with session_scope() as db:
        cat = controle_plu._catalogue().get(insee) or {}
        commune = commune or cat.get("commune")
        if cat.get("statut") == "rnu":
            raise SystemExit(f"{commune} est au RNU — pas de PLU à corriger")

        avant = _compte(db, insee, commune)
        print(f"=== {commune} ({insee}) — prescriptions AVANT : {avant} ===")

        # 0) SAUVEGARDE — archive datée (zonage + prescriptions + DPU) avant toute purge.
        ancien_ref = controle_plu.etat_commune(db, insee).reference
        arch = controle_plu.archiver_couches_plu(
            db, insee, commune, motif=f"LOT4 avant correction prescriptions — ancien {ancien_ref or '?'}")
        print(f"  archive datée : {arch} (ancien réf {ancien_ref or '?'})")

        # sources + bbox (comme appliquer_plu), pour l'outil réparé.
        seed_sources.seed(db)
        sids = layers_ingest._source_ids(db)
        bbox = run_all._commune_bbox(db, commune)
        if bbox is None:
            raise SystemExit(f"aucune parcelle en base pour {commune}")

        # 1) ZONES PAS TOUCHÉES — on purge UNIQUEMENT les prescriptions de la commune.
        db.execute(text("DELETE FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune=:c"),
                   {"c": commune})
        # 2) ré-ingestion PAR PARTITION (outil réparé, LOT 1).
        n = layers_ingest.ingest_gpu_prescriptions(db, bbox, commune, None, sids, insee=insee)
        db.flush()

        apres = _compte(db, insee, commune)
        print(f"  ré-ingéré {n} objet(s) par partition DU_{insee} → prescriptions APRÈS : {apres}")

        if appliquer:
            db.commit()
            print("  ✓ COMMIT — correction appliquée. Vérifier via le contrôle LOT 2 (identique attendu).")
        else:
            db.rollback()
            print("  (dry-run) ROLLBACK — rien écrit. Relancer avec --appliquer pour committer.")


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--appliquer"]
    appliquer = "--appliquer" in sys.argv[1:]
    if len(args) < 2:
        raise SystemExit("usage: corriger_prescriptions_lot4.py <insee> <commune> [--appliquer]")
    corriger(args[0], args[1], appliquer)


if __name__ == "__main__":
    main()
