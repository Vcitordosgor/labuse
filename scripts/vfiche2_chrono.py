"""VITESSE-FICHE-2 — chronomètre /parcels/{idu} par étape (SQL / Python / sérialisation / pool).

Appelle le VRAI builder `parcel_fiche` (route) avec une session réelle, instrumente chaque
requête SQL via les events SQLAlchemy, mesure la sérialisation JSON (jsonable_encoder+dumps)
et la compression gzip. Pool wait mesuré par le temps d'acquisition d'une connexion.
Lecture seule. Aucun écrit.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from collections import defaultdict

from sqlalchemy import event, text

from labuse.db import engine, session_factory
from labuse import runs
from labuse.api import app as A
from fastapi.encoders import jsonable_encoder

# ── Instrumentation SQL ────────────────────────────────────────────────────
_SQL = {"n": 0, "t": 0.0, "stmts": []}
_bucket = defaultdict(lambda: [0, 0.0])  # statement normalisé -> [count, total_s]


def _norm(sql: str) -> str:
    s = " ".join(sql.split())
    return s[:90]


@event.listens_for(engine(), "before_cursor_execute")
def _before(conn, cursor, statement, parameters, context, executemany):
    context._q_t0 = time.perf_counter()


@event.listens_for(engine(), "after_cursor_execute")
def _after(conn, cursor, statement, parameters, context, executemany):
    dt = time.perf_counter() - getattr(context, "_q_t0", time.perf_counter())
    _SQL["n"] += 1
    _SQL["t"] += dt
    b = _bucket[_norm(statement)]
    b[0] += 1
    b[1] += dt


def _reset():
    _SQL["n"] = 0
    _SQL["t"] = 0.0
    _bucket.clear()


def measure(idu: str, run: str) -> dict:
    _reset()
    Sess = session_factory()
    # pool wait = acquisition connexion
    t_pool0 = time.perf_counter()
    s = Sess()
    s.connection()  # force l'acquisition réelle d'une connexion du pool
    t_pool = time.perf_counter() - t_pool0
    try:
        t0 = time.perf_counter()
        payload = A.parcel_fiche(idu, source=run, db=s, request=None, trace=0)
        t_build = time.perf_counter() - t0
        sql_t = _SQL["t"]
        sql_n = _SQL["n"]
        # sérialisation comme FastAPI JSONResponse : jsonable_encoder puis json.dumps
        t0 = time.perf_counter()
        enc = jsonable_encoder(payload)
        body = json.dumps(enc, ensure_ascii=False).encode("utf-8")
        t_ser = time.perf_counter() - t0
        # gzip (middleware, minimum_size=1024)
        t0 = time.perf_counter()
        gz = gzip.compress(body)
        t_gz = time.perf_counter() - t0
    finally:
        s.close()
    return {
        "idu": idu,
        "build_s": t_build,
        "sql_s": sql_t,
        "sql_n": sql_n,
        "py_s": t_build - sql_t,
        "ser_s": t_ser,
        "gz_s": t_gz,
        "pool_s": t_pool,
        "bytes": len(body),
        "gz_bytes": len(gz),
        "buckets": {k: tuple(v) for k, v in _bucket.items()},
    }


def main():
    run = runs.current()
    with session_factory()() as s:
        cr = A._cascade_run(s, run)
        idus = s.execute(text(
            """SELECT p.idu FROM parcels p
               JOIN dryrun_parcel_evaluations d ON d.parcel_id=p.id AND d.run_label=:r
               WHERE p.commune IS NOT NULL
               ORDER BY md5(p.idu) LIMIT 12"""), {"r": cr}).scalars().all()
    print(f"run servi={run} cascade={cr} · {len(idus)} parcelles", file=sys.stderr)

    # warm-up : 1 fiche jetée (chauffe les mémos de process + PG) — on mesure ensuite des
    # parcelles JAMAIS vues (froides côté parcelle), process en régime établi comme en prod.
    if idus:
        measure(idus[0], run)

    rows = [measure(idu, run) for idu in idus[1:11]]
    # agrégats
    import statistics as st
    def med(k): return st.median(r[k] for r in rows)
    def mx(k): return max(r[k] for r in rows)
    print("\n=== PAR PARCELLE (ms) ===")
    print(f"{'idu':16} {'build':>7} {'sql':>7} {'py':>7} {'ser':>6} {'gz':>5} {'pool':>5} {'nq':>4} {'kB':>6}")
    for r in rows:
        print(f"{r['idu']:16} {r['build_s']*1e3:7.0f} {r['sql_s']*1e3:7.0f} {r['py_s']*1e3:7.0f} "
              f"{r['ser_s']*1e3:6.1f} {r['gz_s']*1e3:5.1f} {r['pool_s']*1e3:5.1f} {r['sql_n']:4d} {r['bytes']/1024:6.0f}")
    print("\n=== MÉDIANE / MAX (ms) ===")
    for k, lab in [("build_s","build total"),("sql_s","SQL"),("py_s","Python"),
                   ("ser_s","sérialisation"),("gz_s","gzip"),("pool_s","pool wait")]:
        print(f"{lab:16} médiane {med(k)*1e3:8.1f}   max {mx(k)*1e3:8.1f}")
    print(f"{'requêtes SQL':16} médiane {med('sql_n'):8.0f}   max {mx('sql_n'):8.0f}")

    # top buckets agrégés sur toutes les parcelles mesurées
    agg = defaultdict(lambda: [0, 0.0])
    for r in rows:
        for k, (n, t) in r["buckets"].items():
            agg[k][0] += n
            agg[k][1] += t
    print("\n=== TOP 25 REQUÊTES (total sur 10 fiches : n appels, temps total ms, ms/appel) ===")
    for k, (n, t) in sorted(agg.items(), key=lambda kv: -kv[1][1])[:25]:
        print(f"{t*1e3:8.1f}ms  n={n:4d}  {t/n*1e3:6.1f}ms/ap  {k}")


if __name__ == "__main__":
    main()
