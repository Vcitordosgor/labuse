"""M135 Phase C — premier run réel : recalcule l'ÎLE ENTIÈRE dans un run NEUF (run 2),
sans toucher au run servi (1). Écrit dans parcel_residuel_runs via compute_residuel_batch
(garde-fou : écrire au run servi est une erreur). Progression + métadonnées + ANALYZE.

Lancé en arrière-plan (~90 min). Le diff run 1 ↔ run 2 se fait APRÈS (attendu : zéro, M134).
"""
import os
import subprocess
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.residuel import compute_residuel_batch
from labuse.faisabilite.residuel_runs import create_run, served_run_seq

eng = create_engine(os.environ["LABUSE_DATABASE_URL"])
CHUNK = 500

with Session(eng) as s:
    ids = [r[0] for r in s.execute(text("SELECT id FROM parcels ORDER BY idu")).all()]
    servi = served_run_seq(s)
sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                     capture_output=True, text=True).stdout.strip() or "?"
with eng.begin() as c:
    run_seq = create_run(c, "m135-run2-ile", communes=None, code_commit=sha)
print(f"run île run_seq={run_seq} (servi={servi}, intact) — {len(ids)} parcelles, commit {sha}", flush=True)

t0 = time.time()
total = 0
causes: dict = {}
for k in range(0, len(ids), CHUNK):
    with Session(eng) as s:
        r = compute_residuel_batch(s, ids[k:k + CHUNK], run_seq)
        s.commit()
    total += r["calcules"]
    for cz, n in r["causes"].items():
        causes[cz] = causes.get(cz, 0) + n
    if (k // CHUNK) % 50 == 0:
        done = min(k + CHUNK, len(ids))
        eta = (time.time() - t0) / max(1, done) * (len(ids) - done)
        print(f"  {done}/{len(ids)}  ({time.time()-t0:.0f}s, ETA {eta/60:.0f} min)", flush=True)

dur = int(time.time() - t0)
with Session(eng) as s:
    s.execute(text(
        "UPDATE residuel_runs SET duree_s=:d,"
        " computed_at_min=(SELECT min(computed_at) FROM parcel_residuel_runs WHERE run_seq=:rs),"
        " computed_at_max=(SELECT max(computed_at) FROM parcel_residuel_runs WHERE run_seq=:rs)"
        " WHERE run_seq=:rs"), {"d": dur, "rs": run_seq})
    s.commit()
with eng.begin() as c:
    c.execute(text("ANALYZE parcel_residuel_runs"))
print(f"✓ run {run_seq} ÎLE terminé : {total} calculées · {sum(causes.values())} avec cause · {dur}s "
      f"({dur/60:.0f} min). Run servi TOUJOURS {servi} — service intact.", flush=True)
