"""SCORING-8 lot B.3 — CASCADE ÎLE remise au jour, sous le label `cascade_2026_10`.

GESTE DE VIC (gros calcul ≈ 3 h 26 – 4 h 13, 431 663 parcelles). Rejoue la cascade SEULE (pas de
scoring, pas de fit) avec le code + les données + le cache `spatial_layers_sub` du jour, sur les
24 communes, et l'écrit dans les tables dryrun_* sous un label NEUF `cascade_2026_10`. Ce label
devient un étage 0 VALIDE : `dryrun_parcel_evaluations` porte un statut par parcelle, donc
`resoudre_cascade_run` / la garde de complétude l'acceptent quand `run_qv16.py` le réutilise.

Reprend la logique EXACTE de la phase cascade de `flux-run` (cli.flux_run_cmd), SANS l'étape de
scoring : aucune réécriture du pipeline, aucune bascule, aucun promote. Rien de servi ne change
(`q_v11_m137` reste servi ; on écrit dans des tables parallèles).

Reprenable : relancé, il saute les parcelles déjà évaluées sous ce label.

Mesure SCORING-8 lot B.2 (échantillon 3 000, stratifié) : vs `q_v13_sources1` la cascade du jour
ne change AUCUNE exclusion (0 exclue↔non), seulement ~1,1 % de reclassements a_creuser↔opportunité
À L'INTÉRIEUR des non-exclues, et l'accès est stable. La remise au jour est donc de l'HYGIÈNE de
fraîcheur (SUP/ER/EBC repris, ORACLE-FIX-1, 50 pas, couches informatives neuves), à faible risque.

⚠ Un rejeu PARTIEL (seulement les parcelles touchées) NE suffit PAS : la garde de complétude exige
une ligne `dryrun_parcel_evaluations` pour CHAQUE parcelle de l'île sous le label → couverture
TOTALE (431 663) obligatoire. Le faible drift mesuré ne réduit donc pas le périmètre du rejeu.

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<worktree>/src \
        python scripts/audit/scoring/run_cascade_2026_10.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

LABEL = "cascade_2026_10"
CHUNK = 2000


def main() -> None:
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    from sqlalchemy import text

    from labuse import models
    from labuse.cascade import evaluate_parcels
    from labuse.cascade.cablage import check_cablage_scoring
    from labuse.cli import _parcel_ids, _resolve_commune
    from labuse.db import engine, session_scope
    from labuse.ingestion.run_all import REUNION_COMMUNES

    t0 = time.time()
    # Prime de la cascade : reconstruit le cache pré-subdivisé APRÈS les ré-ingestions (doctrine
    # flux-run — sinon les couches neuves seraient évaluées AVEUGLE). Idempotent.
    n_sub = models.ensure_spatial_layers_sub(engine(), force=True)
    print(f"[cascade_2026_10] cache spatial_layers_sub reconstruit : {n_sub} pièces", flush=True)
    with session_scope() as s:
        check_cablage_scoring(session=s)   # garde de câblage AVANT (bloquante, nomme le fautif)

    total_fait = 0
    for insee, _ in REUNION_COMMUNES:
        nom = _resolve_commune(insee)
        with session_scope() as s:
            ids = _parcel_ids(s, nom)
            if not ids:
                print(f"  · {nom} ({insee}) : 0 parcelle, ignorée", flush=True)
                continue
            done = {r[0] for r in s.execute(text(
                "SELECT parcel_id FROM dryrun_parcel_evaluations WHERE run_label=:r"),
                {"r": LABEL}).all()}
            todo = [i for i in ids if i not in done]
            print(f"  · {nom} ({insee}) : {len(ids)} parcelles, {len(todo)} à évaluer "
                  f"({time.time()-t0:.0f}s)", flush=True)
            for k in range(0, len(todo), CHUNK):
                evaluate_parcels(todo[k:k + CHUNK], s, persist=True, dryrun_label=LABEL)
                s.commit()
                s.expunge_all()
            total_fait += len(todo)
    print(f"[cascade_2026_10] terminé : {total_fait} parcelles évaluées sous « {LABEL} » "
          f"({time.time()-t0:.0f}s). Étage 0 prêt pour run_qv16.py. NON servi.", flush=True)


if __name__ == "__main__":
    main()
