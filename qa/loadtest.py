#!/usr/bin/env python
"""LA BUSE — testeur de charge MAISON (M6, mandat charge-et-secrets).

Pourquoi maison : contrôle total (arrêt instantané), zéro install sur le poste, et surtout
la charge part du Mac dont l'IP est dans LABUSE_QA_ALLOWLIST → EXEMPTE de rate-limit/quota
(la garde anti-abus court-circuite les IP QA) → on mesure la capacité BRUTE, pas la protection.

Auth : basic auth Caddy (LABUSE_QA_BASIC=user:pass) + login pilote (LABUSE_QA_PASSWORD) → cookie.
Un palier = N clients concurrents (threads), chacun boucle un scénario pondéré pendant --duration.
Sortie JSON : par endpoint + global p50/p95/p99, RPS, taux d'erreur.

Usage :
  LABUSE_QA_BASIC=… LABUSE_QA_PASSWORD=… python qa/loadtest.py \
      --base https://app.labuse.immo --scenario mixte --concurrency 10 --duration 40
"""
from __future__ import annotations

import argparse
import json
import os
import random
import threading
import time

import httpx

IDUS = ("97401000AB0001,97401000AB0002,97401000AD0016,97401000AD0095,97401000AD0124,"
        "97401000AD0192,97401000AD0971,97401000AD0973,97401000AD1599,97401000AI0394").split(",")
TILES = ("/map/tiles/13/5357/4582.pbf /map/tiles/13/5353/4585.pbf /map/tiles/13/5358/4593.pbf "
         "/map/tiles/14/10715/9164.pbf /map/tiles/14/10706/9171.pbf /map/tiles/14/10716/9186.pbf "
         "/map/tiles/15/21431/18328.pbf /map/tiles/15/21412/18342.pbf /map/tiles/15/21433/18372.pbf").split()


def fiche():
    return f"/parcels/{random.choice(IDUS)}"


def nav_action():
    return random.choices(
        ["/", "/parcels?limit=50", fiche(), fiche(), fiche(), "/map/tiles/meta", "/events/count"],
        weights=[1, 1, 1, 1, 1, 1, 1])[0]


def tile_action():
    return random.choice(TILES)


def heavy_action():
    return random.choices(
        [f"/dossier-banquier/{random.choice(IDUS)}.pdf",
         "/parcels/export.csv?commune=Saint-Denis",
         "/map/parcels.geojson?commune=Saint-Denis&limit=60000&source=q_v7_defisc"],
        weights=[1, 1, 1])[0]


def pick(scenario: str) -> str:
    if scenario == "nav":
        return nav_action()
    if scenario == "tiles":
        return tile_action()
    if scenario == "heavy":
        return heavy_action()
    # mixte réaliste : 70 % nav, 20 % carte, 10 % lourds
    r = random.random()
    return nav_action() if r < 0.70 else tile_action() if r < 0.90 else heavy_action()


def label(path: str) -> str:
    if path.startswith("/parcels/9"):
        return "fiche"
    if path.startswith("/map/tiles/"):
        return "tile"
    if path.startswith("/dossier-banquier"):
        return "pdf"
    if path.startswith("/parcels/export"):
        return "csv"
    if path.startswith("/map/parcels.geojson"):
        return "geojson"
    return path.split("?")[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://app.labuse.immo")
    ap.add_argument("--scenario", default="mixte", choices=["nav", "tiles", "heavy", "mixte"])
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--duration", type=float, default=30.0)
    args = ap.parse_args()

    basic = os.environ["LABUSE_QA_BASIC"]
    user, _, pw = basic.partition(":")
    auth = (user, pw)
    # login → cookie de session
    with httpx.Client(base_url=args.base, auth=auth, timeout=30, verify=True) as c:
        r = c.post("/login", json={"identifiant": "", "password": os.environ["LABUSE_QA_PASSWORD"]},
                   follow_redirects=False)
        tok = r.cookies.get("labuse_session")
        if not tok:
            raise SystemExit(f"login KO ({r.status_code}) — pas de cookie")

    results: list[tuple[str, float, int]] = []
    lock = threading.Lock()
    stop_at = time.time() + args.duration

    def worker():
        cl = httpx.Client(base_url=args.base, auth=auth, timeout=30, verify=True,
                          cookies={"labuse_session": tok})
        local = []
        while time.time() < stop_at:
            p = pick(args.scenario)
            t0 = time.perf_counter()
            try:
                resp = cl.get(p)
                code = resp.status_code
            except Exception:
                code = 0
            local.append((label(p), (time.perf_counter() - t0) * 1000, code))
        cl.close()
        with lock:
            results.extend(local)

    threads = [threading.Thread(target=worker) for _ in range(args.concurrency)]
    t_start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - t_start

    def pct(xs, q):
        if not xs:
            return None
        xs = sorted(xs)
        return round(xs[min(len(xs) - 1, int(q * len(xs)))], 1)

    by = {}
    for lab, ms, code in results:
        d = by.setdefault(lab, {"lat": [], "err": 0, "n": 0})
        d["n"] += 1
        d["lat"].append(ms)
        if code >= 500 or code == 0 or code == 429:
            d["err"] += 1
    all_lat = [ms for _, ms, _ in results]
    all_err = sum(1 for _, _, c in results if c >= 500 or c == 0 or c == 429)
    summary = {
        "scenario": args.scenario, "concurrency": args.concurrency,
        "duration_s": round(elapsed, 1), "requests": len(results),
        "rps": round(len(results) / elapsed, 1),
        "err_pct": round(100 * all_err / max(1, len(results)), 2),
        "p50_ms": pct(all_lat, 0.50), "p95_ms": pct(all_lat, 0.95), "p99_ms": pct(all_lat, 0.99),
        "by_endpoint": {k: {"n": v["n"], "err": v["err"],
                            "p50": pct(v["lat"], 0.50), "p95": pct(v["lat"], 0.95),
                            "p99": pct(v["lat"], 0.99)} for k, v in sorted(by.items())},
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
