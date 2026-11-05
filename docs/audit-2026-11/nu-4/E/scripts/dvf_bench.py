#!/usr/bin/env python3
"""NU4-E — micro-banc de concurrence sur la fiche (chemin v_parcel_dvf_last).

Reproduit le symptôme NU4-C : « 5 fiches 500-timeout TRANSITOIRE sous 8 requêtes // ».
On tire des parcelles DVF FROIDES (absentes de fiche_cache) et on ouvre leur fiche
`GET /parcels/{idu}` à des niveaux de concurrence croissants, chaque requête visant un IDU
DISTINCT (pour éviter que le cache L2 n'absorbe la charge après la 1re). On mesure latence
p50/p95/p99/max, le nombre de 500 / timeouts, et le débit.

Lecture seule côté app (GET). Usage :
  PY dvf_bench.py <base_url> <pool_cold_file> [levels=1,4,8,16,32] [per_level=64]
"""
import asyncio, sys, time, statistics
import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9670"
POOL = sys.argv[2] if len(sys.argv) > 2 else "docs/audit-2026-11/nu-4/E/raw/pool_cold_dvf.txt"
LEVELS = [int(x) for x in (sys.argv[3].split(",") if len(sys.argv) > 3 else ["1","4","8","16","32"])]
PER = int(sys.argv[4]) if len(sys.argv) > 4 else 64

idus = [l.strip() for l in open(POOL) if l.strip()]

def pct(xs, p):
    if not xs: return float("nan")
    xs = sorted(xs); k = max(0, min(len(xs)-1, int(round((p/100)*(len(xs)-1)))))
    return xs[k]

async def one(client, idu):
    t = time.perf_counter()
    try:
        r = await client.get(f"{BASE}/parcels/{idu}", timeout=90.0)
        return (time.perf_counter()-t, r.status_code)
    except Exception as e:
        return (time.perf_counter()-t, f"ERR:{type(e).__name__}")

async def run_level(conc, batch):
    sem = asyncio.Semaphore(conc)
    limits = httpx.Limits(max_connections=conc+5, max_keepalive_connections=conc+5)
    async with httpx.AsyncClient(limits=limits) as client:
        async def guarded(idu):
            async with sem:
                return await one(client, idu)
        t0 = time.perf_counter()
        res = await asyncio.gather(*[guarded(i) for i in batch])
        wall = time.perf_counter()-t0
    lat = [x[0] for x in res]; codes = [x[1] for x in res]
    ok = sum(1 for c in codes if c == 200)
    c500 = sum(1 for c in codes if c == 500)
    errs = sum(1 for c in codes if isinstance(c, str))
    return dict(conc=conc, n=len(batch), ok=ok, c500=c500, errs=errs, wall=wall,
                rps=len(batch)/wall,
                p50=pct(lat,50), p95=pct(lat,95), p99=pct(lat,99), mx=max(lat))

async def main():
    print(f"# DVF/fiche concurrency bench  base={BASE}  pool={len(idus)} cold IDUs")
    print(f"{'conc':>4} {'n':>4} {'ok':>4} {'500':>4} {'err':>4} {'rps':>7} "
          f"{'p50 s':>8} {'p95 s':>8} {'p99 s':>8} {'max s':>8}")
    off = 0
    for lvl in LEVELS:
        batch = idus[off:off+PER]; off += PER
        if len(batch) < PER:  # recycle if pool too small
            batch = (idus*3)[off:off+PER]
        s = await run_level(lvl, batch)
        print(f"{s['conc']:>4} {s['n']:>4} {s['ok']:>4} {s['c500']:>4} {s['errs']:>4} "
              f"{s['rps']:>7.1f} {s['p50']:>8.2f} {s['p95']:>8.2f} {s['p99']:>8.2f} {s['mx']:>8.2f}")

asyncio.run(main())
