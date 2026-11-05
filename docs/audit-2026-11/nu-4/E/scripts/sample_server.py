#!/usr/bin/env python3
"""NU4-E — échantillonneur serveur : RSS des workers uvicorn + état PostgreSQL.

Toutes les ~2 s, écrit une ligne CSV : horodatage, RSS total/ workers (Mo), nb connexions app,
connexions actives, en attente de verrou (lock waits), idle_in_transaction, transaction la plus
longue (s). 100 % lecture (ps + pg_stat_activity/pg_locks). Usage :
  PY sample_server.py <out.csv> <duree_s> [db_url]
"""
import csv, os, subprocess, sys, time
from sqlalchemy import create_engine, text

OUT = sys.argv[1]
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 1800.0
DB = sys.argv[3] if len(sys.argv) > 3 else os.environ.get(
    "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
eng = create_engine(DB)

def workers_rss_mb():
    # parent uvicorn + all its forked workers (children don't carry the full cmdline on macOS)
    try:
        parent = subprocess.check_output(
            "pgrep -f 'uvicorn labuse.api.app:app' | head -1", shell=True, text=True).strip()
        if not parent:
            return 0.0, 0
        pids = [parent] + subprocess.check_output(
            f"pgrep -P {parent}", shell=True, text=True).split()
        out = subprocess.check_output(
            "ps -o rss= -p " + ",".join(pids), shell=True, text=True)
        kb = [int(x) for x in out.split() if x.strip()]
        return round(sum(kb)/1024, 1), len(kb)
    except Exception:
        return 0.0, 0

Q = text("""
  SELECT
    count(*) FILTER (WHERE application_name NOT LIKE 'psql%') AS app_conns,
    count(*) FILTER (WHERE state='active') AS active,
    count(*) FILTER (WHERE state='idle in transaction') AS idle_in_tx,
    count(*) FILTER (WHERE wait_event_type='Lock') AS lock_waits,
    coalesce(round(extract(epoch FROM max(now()-xact_start))::numeric,1),0) AS longest_tx_s,
    (SELECT count(*) FROM pg_locks WHERE NOT granted) AS ungranted_locks
  FROM pg_stat_activity WHERE datname='labuse'""")

def main():
    t0 = time.time()
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "rss_mb", "n_workers", "app_conns", "active",
                    "idle_in_tx", "lock_waits", "longest_tx_s", "ungranted_locks"])
        while time.time() - t0 < DUR:
            rss, nw = workers_rss_mb()
            try:
                with eng.connect() as c:
                    r = c.execute(Q).first()
                    row = [round(time.time()-t0, 1), rss, nw, r[0], r[1], r[2], r[3], float(r[4]), r[5]]
            except Exception as e:
                row = [round(time.time()-t0, 1), rss, nw, -1, -1, -1, -1, -1, f"ERR:{type(e).__name__}"]
            w.writerow(row); f.flush()
            time.sleep(2.0)

main()
