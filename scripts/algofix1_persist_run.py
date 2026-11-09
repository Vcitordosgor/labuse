"""ALGO-FIX-1 (suite) — peuple la table de run `parcel_scenario_v2_runs` (lecture seule depuis
l'endpoint). Conservation EXACTE sur toute l'île (rapide) + reconstruction EXACTE (enrich) sur
Entre-Deux et un échantillon de Saint-Denis (dont les deux cas réels).

Usage : LABUSE_REEL_DATABASE_URL=… python scripts/algofix1_persist_run.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine, text          # noqa: E402
from sqlalchemy.orm import Session                   # noqa: E402

from labuse.scoring import scenarios_v2_persist as P  # noqa: E402

RUN = "q_v20"
ENRICH_CASES = ["97411000EH0043", "97411000EI0085"]


def _session() -> Session:
    url = (os.environ.get("LABUSE_REEL_DATABASE_URL")
           or "postgresql+psycopg://openclaw@localhost:5432/labuse")
    return Session(bind=create_engine(url))


def main() -> int:
    with _session() as s:
        P.ensure_table(s)
        # 1) CONSERVATION exacte sur TOUTE L'ÎLE (rapide, ~3 min) + statut de reconstruction.
        all_ids = [r[0] for r in s.execute(
            text("SELECT parcel_id FROM score_labuse WHERE run_label=:r ORDER BY parcel_id"),
            {"r": RUN})]
        t = time.time()
        b = P.compute_scenarios_v2_batch(s, all_ids, run_label=RUN, enrich=False,
                                         log=lambda m: None)
        print(f"[fast île] {b['parcelles']} parcelles en {time.time()-t:.0f}s")

        # 2) RECONSTRUCTION exacte (enrich) : Entre-Deux + échantillon Saint-Denis + cas réels.
        ed = [r[0] for r in s.execute(
            text("SELECT parcel_id FROM score_labuse WHERE run_label=:r AND commune='Entre-Deux' "
                 "ORDER BY parcel_id"), {"r": RUN})]
        sd = [r[0] for r in s.execute(
            text("SELECT parcel_id FROM score_labuse WHERE run_label=:r AND commune='Saint-Denis' "
                 "ORDER BY parcel_id LIMIT 3000"), {"r": RUN})]
        cas = [r[0] for r in s.execute(
            text("SELECT id FROM parcels WHERE idu = ANY(:i)"), {"i": ENRICH_CASES})]
        enrich_ids = list(dict.fromkeys(ed + sd + cas))
        t = time.time()
        b = P.compute_scenarios_v2_batch(s, enrich_ids, run_label=RUN, enrich=True,
                                         log=lambda m: print("  " + m) if False else None)
        print(f"[enrich Entre-Deux+SD] {b['parcelles']} parcelles en {time.time()-t:.0f}s")

        n = s.execute(text("SELECT count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r"),
                      {"r": RUN}).scalar()
        ne = s.execute(text("SELECT count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r "
                            "AND scenario='rebuild' AND enriched"), {"r": RUN}).scalar()
        print(f"table: {n} lignes ; reconstruction enrichie : {ne} parcelles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
