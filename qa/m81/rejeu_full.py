"""M81 Phase 2 — REJEU du parc complet (431 663 parcelles) sous un nouveau label, avec toutes les
corrections (M70 ENS/BODACC/OCS/S3REnR, M71 DPE/Saint-Philippe, M79 DvfLayer terrain). Chunké,
résumable (saute les parcelles déjà évaluées pour ce label). N'écrit QUE dans les tables dryrun_*
du label donné — ne touche NI le run servi NI les tables live."""
from __future__ import annotations

import sys
import time

from sqlalchemy import text

from labuse.cascade import evaluate_parcels
from labuse.cascade.cablage import check_cablage_scoring
from labuse.db import session_scope

LABEL = sys.argv[1] if len(sys.argv) > 1 else "q_v9_m81"
CHUNK = 3000


def main() -> None:
    with session_scope() as s:
        check_cablage_scoring(session=s)                 # garde de câblage (M-B) avant le run
        ids = [r[0] for r in s.execute(text("SELECT id FROM parcels ORDER BY id")).all()]
        done = {r[0] for r in s.execute(
            text("SELECT parcel_id FROM dryrun_parcel_evaluations WHERE run_label=:l"),
            {"l": LABEL}).all()}
        todo = [i for i in ids if i not in done]
        print(f"REJEU [{LABEL}] : {len(ids)} parcelles, {len(done)} déjà faites, {len(todo)} à évaluer.",
              flush=True)
        t0 = time.time()
        n = 0
        for k in range(0, len(todo), CHUNK):
            evaluate_parcels(todo[k:k + CHUNK], s, persist=True, dryrun_label=LABEL)
            s.commit()
            s.expunge_all()                               # conso mémoire plate
            n += len(todo[k:k + CHUNK])
            print(f"  … {n}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
        print(f"✓ REJEU [{LABEL}] terminé : {len(todo)} parcelles évaluées.", flush=True)


if __name__ == "__main__":
    main()
