#!/usr/bin/env python3
"""NU4-E — synthèse d'un run : latences par action + erreurs + débit + pics serveur.
Usage : PY analyze.py <load.csv> [sample.csv]"""
import csv, sys, statistics
LOAD = sys.argv[1]
SAMP = sys.argv[2] if len(sys.argv) > 2 else None

def pct(xs, p):
    if not xs: return float("nan")
    xs = sorted(xs); k = max(0, min(len(xs)-1, int(round((p/100)*(len(xs)-1)))))
    return xs[k]

rows = list(csv.DictReader(open(LOAD)))
by = {}
tmax = 0.0
for r in rows:
    tmax = max(tmax, float(r["t"]))
    k = r["action"] + " " + r["endpoint"]
    by.setdefault(k, []).append(r)

print(f"# Load run: {LOAD}")
print(f"total requests: {len(rows)}   window: {tmax:.0f}s   throughput: {len(rows)/max(tmax,1):.1f} req/s")
ok = sum(1 for r in rows if r["status"] == "200")
non200 = [r for r in rows if r["status"] not in ("200", "204")]
print(f"status 200: {ok}  ({100*ok/len(rows):.1f}%)   non-2xx/err: {len(non200)}")
from collections import Counter
print("non-2xx breakdown:", dict(Counter(r["status"] for r in non200)))
print()
print(f"{'action/endpoint':32} {'n':>5} {'ok%':>5} {'p50':>7} {'p95':>7} {'p99':>7} {'max':>8}")
for k in sorted(by, key=lambda k: -len(by[k])):
    g = by[k]; lat = [float(r["ms"]) for r in g]
    okp = 100*sum(1 for r in g if r["status"] in ("200", "204"))/len(g)
    print(f"{k:32} {len(g):>5} {okp:>5.0f} {pct(lat,50):>7.0f} {pct(lat,95):>7.0f} "
          f"{pct(lat,99):>7.0f} {max(lat):>8.0f}")

if SAMP:
    s = list(csv.DictReader(open(SAMP)))
    def col(c): return [float(x[c]) for x in s if x[c] not in ("", "-1")]
    print("\n# Server samples")
    for c in ["rss_mb", "app_conns", "active", "idle_in_tx", "lock_waits", "longest_tx_s", "ungranted_locks"]:
        v = col(c)
        if v: print(f"  {c:16} max={max(v):>8.1f}  avg={statistics.mean(v):>8.1f}")
