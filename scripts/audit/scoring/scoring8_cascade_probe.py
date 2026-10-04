"""SCORING-8 lot B.2 — MESURE de la dérive de la cascade depuis q_v13_sources1 (07/09).

Rejoue la cascade LIVE (code + données + spatial_layers_sub du jour) sur un échantillon de 3 000
parcelles STRATIFIÉ par commune × verdict actuel (graine fixe, reproductible), sous un label
jetable, puis compare parcelle à parcelle au verdict stocké de q_v13_sources1 :

  · transitions de statut (exclue/a_creuser/opportunite) ;
  · exclues → non exclues et l'inverse ;
  · verdicts cascade changés PAR COUCHE (layer_name) ;
  · accès PASS ↔ autre (le facteur mineur lu par le Score LABUSE).

N'écrit QUE sous le label jetable (dryrun_*), nettoyé avant/après. Extrapolation île en fin.

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
        ~/Desktop/labuse/.venv/bin/python scripts/audit/scoring/scoring8_cascade_probe.py
"""
from __future__ import annotations

import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

ETAGE0 = "q_v13_sources1"
PROBE = "cascade_s8b_probe"
SEED = "s8b"
N_CIBLE = 3000


def _echantillon(s) -> list[int]:
    from sqlalchemy import text
    rows = s.execute(text(f"""
        WITH base AS (
            SELECT e.parcel_id, p.commune, e.status
            FROM dryrun_parcel_evaluations e JOIN parcels p ON p.id = e.parcel_id
            WHERE e.run_label = :et),
        strata AS (
            SELECT parcel_id,
                   count(*) OVER (PARTITION BY commune, status) AS strat_n,
                   count(*) OVER () AS tot,
                   row_number() OVER (PARTITION BY commune, status
                                      ORDER BY md5(:seed || parcel_id::text)) AS rn
            FROM base)
        SELECT parcel_id FROM strata
        WHERE rn <= GREATEST(1, round(CAST(:n AS numeric) * strat_n / tot))
        ORDER BY parcel_id
    """), {"et": ETAGE0, "seed": SEED, "n": N_CIBLE})
    return [r[0] for r in rows]


def main() -> None:
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    from sqlalchemy import text

    from labuse.cascade import evaluate_parcels
    from labuse.db import session_scope

    t0 = time.time()
    with session_scope() as s:
        ids = _echantillon(s)
        print(f"[probe] échantillon stratifié : {len(ids)} parcelles (graine={SEED}).", flush=True)
        deja = s.execute(text("SELECT count(DISTINCT parcel_id) FROM dryrun_parcel_evaluations "
                              "WHERE run_label=:r"), {"r": PROBE}).scalar() or 0
        if deja >= len(ids):
            print(f"[probe] rejeu déjà présent ({deja}) — comparaison seule.", flush=True)
        else:
            for tbl in ("dryrun_cascade_results", "dryrun_parcel_evaluations"):
                s.execute(text(f"DELETE FROM {tbl} WHERE run_label=:r"), {"r": PROBE})
            s.commit()
            for k in range(0, len(ids), 1000):
                evaluate_parcels(ids[k:k + 1000], s, persist=True, dryrun_label=PROBE)
                s.commit()
                s.expunge_all()
                print(f"  … {min(k + 1000, len(ids))}/{len(ids)} ({time.time() - t0:.0f}s)", flush=True)

        # ---- 1) transitions de statut --------------------------------------------------------
        trans = s.execute(text("""
            SELECT a.status AS avant, b.status AS apres, count(*)
            FROM dryrun_parcel_evaluations a
            JOIN dryrun_parcel_evaluations b ON b.parcel_id = a.parcel_id AND b.run_label = :pr
            WHERE a.run_label = :et
            GROUP BY 1,2 ORDER BY 3 DESC
        """), {"et": ETAGE0, "pr": PROBE}).all()
        n = len(ids)
        print("\n=== TRANSITIONS DE STATUT (avant q_v13_sources1 → après code/données du jour) ===")
        exc_vers_non = non_vers_exc = inchange = 0
        for avant, apres, c in trans:
            flag = "" if avant == apres else "  ←CHANGE"
            print(f"  {avant:>12} → {apres:<12} : {c}{flag}")
            if avant == apres:
                inchange += c
            elif avant == "exclue" and apres != "exclue":
                exc_vers_non += c
            elif avant != "exclue" and apres == "exclue":
                non_vers_exc += c
        print(f"  — inchangés {inchange}/{n} ({100*inchange/n:.1f}%) ; "
              f"exclue→non {exc_vers_non} ; non→exclue {non_vers_exc}")

        # ---- 2) verdicts cascade changés PAR COUCHE ------------------------------------------
        par_couche = s.execute(text("""
            SELECT layer_name,
                   count(*) FILTER (WHERE a.result IS DISTINCT FROM b.result) AS changes,
                   count(*) AS total
            FROM (SELECT parcel_id, layer_name, result FROM dryrun_cascade_results
                  WHERE run_label=:et AND parcel_id = ANY(:ids)) a
            FULL JOIN (SELECT parcel_id, layer_name, result FROM dryrun_cascade_results
                       WHERE run_label=:pr) b
              USING (parcel_id, layer_name)
            GROUP BY layer_name HAVING count(*) FILTER (WHERE a.result IS DISTINCT FROM b.result) > 0
            ORDER BY 2 DESC
        """), {"et": ETAGE0, "pr": PROBE, "ids": ids}).all()
        print("\n=== VERDICTS CASCADE CHANGÉS PAR COUCHE (sur l'échantillon) ===")
        for layer, ch, tot in par_couche:
            print(f"  {layer:<28} {ch:>6} changements / {tot}")
        if not par_couche:
            print("  (aucun)")

        # ---- 3) accès PASS ↔ autre -----------------------------------------------------------
        acces = s.execute(text("""
            SELECT coalesce(a.result,'∅') AS avant, coalesce(b.result,'∅') AS apres, count(*)
            FROM (SELECT parcel_id, result FROM dryrun_cascade_results
                  WHERE run_label=:et AND layer_name='acces' AND parcel_id = ANY(:ids)) a
            FULL JOIN (SELECT parcel_id, result FROM dryrun_cascade_results
                       WHERE run_label=:pr AND layer_name='acces') b USING (parcel_id)
            GROUP BY 1,2 ORDER BY 3 DESC
        """), {"et": ETAGE0, "pr": PROBE, "ids": ids}).all()
        print("\n=== ACCÈS (facteur mineur Score LABUSE) avant → après ===")
        for avant, apres, c in acces:
            flag = "  ←CHANGE" if avant != apres else ""
            print(f"  {avant:>10} → {apres:<10} : {c}{flag}")

        # ---- extrapolation île ---------------------------------------------------------------
        ile = 431663
        print("\n=== EXTRAPOLATION ÎLE (échantillon × {:.1f}) ===".format(ile / n))
        print(f"  exclue→non  ~ {round(exc_vers_non * ile / n):>8} parcelles")
        print(f"  non→exclue  ~ {round(non_vers_exc * ile / n):>8} parcelles")
        print(f"  statut changé ~ {round((n-inchange) * ile / n):>8} parcelles "
              f"({100*(n-inchange)/n:.1f}%)")

        print(f"\n[probe] label jetable {PROBE} CONSERVÉ pour inspection "
              f"(nettoyer : DELETE … WHERE run_label='{PROBE}'). ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
