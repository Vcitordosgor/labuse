"""VITESSE-PROD-1 — rafale de tuiles « comme un zoom » : N requêtes concurrentes de tuiles froides,
la moitié AVORTÉES à 300 ms (MapLibre annule les tuiles périmées pendant le zoom). Reproduit la
mécanique de l'effondrement de prod du 06/10 (75 connexions idle in transaction, QueuePool timeout).

Mesure : durées (p50/p95/max), erreurs HTTP, et pic d'« idle in transaction » + connexions totales
côté Postgres pendant la rafale.

Usage : python rafale_tuiles.py http://127.0.0.1:8745 [zoom_offset]
        (zoom_offset décale les x/y pour garantir des tuiles JAMAIS vues → froides)
"""
from __future__ import annotations

import asyncio
import statistics
import sys
import time

import httpx
import psycopg

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8745"
OFF = int(sys.argv[2]) if len(sys.argv) > 2 else 0
DSN = "dbname=labuse"

KINDS = ["limites_parcelles", "ppr", "sup", "alea_mvt", "batiment", "zonage_parcelle"]
# z13 Saint-Paul→Saint-Pierre : 10 colonnes × 2 lignes de tuiles réelles (zones habitées)
TUILES = [(13, 5352 + i + OFF, 4586 + j) for i in range(10) for j in range(2)]


async def une(client: httpx.AsyncClient, url: str, abort_ms: float | None):
    t0 = time.perf_counter()
    try:
        if abort_ms is None:
            r = await client.get(url)
            return (time.perf_counter() - t0) * 1000, r.status_code
        try:
            await asyncio.wait_for(client.get(url), abort_ms / 1000)
            return (time.perf_counter() - t0) * 1000, 200
        except asyncio.TimeoutError:
            return (time.perf_counter() - t0) * 1000, -1  # avortée (comme MapLibre)
    except Exception:
        return (time.perf_counter() - t0) * 1000, -2      # erreur transport


async def sonde_pg(stop: asyncio.Event, out: dict):
    with psycopg.connect(DSN, autocommit=True) as conn:
        while not stop.is_set():
            row = conn.execute(
                "SELECT count(*) FILTER (WHERE state = 'idle in transaction'), count(*) "
                "FROM pg_stat_activity WHERE datname = 'labuse'").fetchone()
            out["idle_tx_max"] = max(out.get("idle_tx_max", 0), row[0])
            out["conn_max"] = max(out.get("conn_max", 0), row[1])
            await asyncio.sleep(0.2)


async def main():
    urls = [f"{BASE}/map/tiles/{k}/{z}/{x}/{y}.pbf" for k in KINDS for (z, x, y) in TUILES]
    # moitié avortées à 300 ms (zoom), moitié menées au bout — entrelacées
    jobs = [(u, 300.0 if i % 2 else None) for i, u in enumerate(urls)]
    pg: dict = {}
    stop = asyncio.Event()
    async with httpx.AsyncClient(timeout=120) as client:
        sonde = asyncio.create_task(sonde_pg(stop, pg))
        t0 = time.perf_counter()
        res = await asyncio.gather(*(une(client, u, a) for u, a in jobs))
        total = time.perf_counter() - t0
        # une 2e vague immédiate, NON avortée : « l'utilisateur re-pan » pendant que le pool digère
        t1 = time.perf_counter()
        res2 = await asyncio.gather(*(une(client, u, None) for u, _ in jobs[: len(KINDS) * 4]))
        total2 = time.perf_counter() - t1
        await asyncio.sleep(2)
        stop.set()
        await sonde
    ok = [d for d, s in res if s == 200]
    err = sum(1 for _, s in res if s not in (200, -1, 304, 204))
    ab = sum(1 for _, s in res if s == -1)
    ok2 = [d for d, s in res2 if s == 200]
    err2 = sum(1 for _, s in res2 if s not in (200, -1, 304, 204))
    def pct(v, p):
        return statistics.quantiles(v, n=100)[p - 1] if len(v) > 1 else (v[0] if v else 0)
    print(f"vague1: {len(res)} req ({ab} avortées) en {total:.1f}s · "
          f"p50={pct(ok,50):.0f}ms p95={pct(ok,95):.0f}ms max={max(ok) if ok else 0:.0f}ms · erreurs={err}")
    print(f"vague2 (re-pan, {len(res2)} req) en {total2:.1f}s · "
          f"p50={pct(ok2,50):.0f}ms p95={pct(ok2,95):.0f}ms max={max(ok2) if ok2 else 0:.0f}ms · erreurs={err2}")
    print(f"postgres: pic idle-in-transaction={pg.get('idle_tx_max', 0)} · pic connexions={pg.get('conn_max', 0)}")


asyncio.run(main())
