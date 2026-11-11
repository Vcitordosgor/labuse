"""DEPLOY-GROUPE-3 — scénarios V2 MODE RAPIDE (enrich=False) pour un run : conservation exacte +
reconstruction « Calcul à compléter ». Usage : python scripts/q23_scenarios_fast.py <run_label>
Lit les parcel_ids depuis score_labuse WHERE run_label=<run>. Mesure et imprime la durée."""
from __future__ import annotations
import sys, time
from labuse.db import session_scope
from sqlalchemy import text
from labuse.scoring import scenarios_v2_persist as P


def main() -> int:
    run = sys.argv[1]
    with session_scope() as s:
        P.ensure_table(s)
        ids = [r[0] for r in s.execute(
            text("SELECT parcel_id FROM score_labuse WHERE run_label=:r ORDER BY parcel_id"),
            {"r": run})]
        print(f"[{run}] {len(ids)} parcelles — mode RAPIDE (enrich=False)…", flush=True)
        t = time.time()
        b = P.compute_scenarios_v2_batch(s, ids, run_label=run, enrich=False,
                                         log=lambda m: print("  " + m, flush=True))
        dt = time.time() - t
        n = s.execute(text("SELECT count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r"),
                      {"r": run}).scalar()
        print(f"[{run}] FAIT : {b['parcelles']} parcelles · {int(dt)}s · table {n} lignes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
