#!/usr/bin/env python3
"""TUILES-TX-1 — preuve locale : 200 tuiles (dont des requêtes ANNULÉES) → 0 « idle in transaction ».

Lance un vrai serveur uvicorn contre la base `labuse`, tire 200 tuiles MVT (parcelles +
couches), dont ~40 % annulées côté client EN PLEIN vol (déconnexion), puis interroge
`pg_stat_activity` (filtré sur l'application_name de CE serveur) pendant et après la rafale.

Usage : lancé par reports/run_tuiles_tx_proof.sh (fixe PYTHONPATH + venv + DATABASE_URL).
"""
from __future__ import annotations

import asyncio
import os
import random
import subprocess
import sys
import time

import httpx
import psycopg

APP_NAME = "tuiles_tx_proof"
PORT = int(os.environ.get("PROOF_PORT", "8791"))
BASE = f"http://127.0.0.1:{PORT}"
PG = os.environ["PROOF_PG_DSN"]           # dsn libpq pour la sonde pg_stat_activity
N_TILES = 200
random.seed(1234)                          # déterministe (pas de Date.now/random libre)

# Couches servies par le tuyau (route /map/tiles/{kind}/…) — quelques kinds réels fréquents.
COUCHES = ["ppr", "alea_mvt", "limites_parcelles", "zonage_parcelle"]


def _tiles_parcelles(n: int) -> list[str]:
    """Tuiles PARCELLES z12-z15 (générées à la volée, assez lourdes pour être annulables),
    réparties sur l'emprise réelle de l'île (La Réunion, Web-Mercator)."""
    out = []
    # bbox île en tuiles XYZ (approx, large) : La Réunion ~ lon 55.2-55.85, lat -21.4..-20.8
    for _ in range(n):
        z = random.choice([12, 13, 14, 15])
        # plages XYZ larges couvrant l'île à chaque zoom
        rng = {12: (2546, 2549, 2305, 2308), 13: (5092, 5099, 4611, 4617),
               14: (10185, 10199, 9223, 9235), 15: (20371, 20399, 18447, 18471)}[z]
        x = random.randint(rng[0], rng[1]); y = random.randint(rng[2], rng[3])
        out.append(f"/map/tiles/{z}/{x}/{y}.pbf")
    return out


def _tiles_couches(n: int) -> list[str]:
    out = []
    for _ in range(n):
        k = random.choice(COUCHES)
        z = random.choice([10, 11, 12, 13])
        rng = {10: (636, 638, 576, 578), 11: (1273, 1275, 1152, 1154),
               12: (2546, 2549, 2305, 2308), 13: (5092, 5099, 4611, 4617)}[z]
        x = random.randint(rng[0], rng[1]); y = random.randint(rng[2], rng[3])
        out.append(f"/map/tiles/{k}/{z}/{x}/{y}.pbf")
    return out


def pg_states() -> dict[str, int]:
    """Compte par state des connexions de CE serveur (application_name) — hors la sonde elle-même."""
    with psycopg.connect(PG, autocommit=True) as c, c.cursor() as cur:
        cur.execute(
            "SELECT coalesce(state,'<null>'), count(*) FROM pg_stat_activity "
            "WHERE application_name = %s AND pid <> pg_backend_pid() GROUP BY 1 ORDER BY 1",
            (APP_NAME,))
        return {r[0]: r[1] for r in cur.fetchall()}


async def fire(paths: list[str], cancel_frac: float) -> dict:
    """Tire les requêtes en concurrence ; annule une fraction EN PLEIN VOL (déconnexion client).
    Retourne un compte {ok, status_204, cancelled, errors}."""
    res = {"ok": 0, "s204": 0, "cancelled": 0, "errors": 0}
    peak = {"idle in transaction": 0}

    async def sample_peak():
        while True:
            st = pg_states()
            peak["idle in transaction"] = max(peak["idle in transaction"],
                                              st.get("idle in transaction", 0))
            await asyncio.sleep(0.03)

    sampler = asyncio.create_task(sample_peak())

    limits = httpx.Limits(max_connections=40, max_keepalive_connections=0)
    async with httpx.AsyncClient(base_url=BASE, limits=limits, timeout=30.0) as client:
        async def one(path: str, cancel: bool):
            try:
                if cancel:
                    # annulation EN PLEIN VOL : on lance la requête puis on coupe après un délai
                    # minuscule et aléatoire → le serveur reçoit la déconnexion pendant le traitement.
                    task = asyncio.create_task(client.get(path))
                    await asyncio.sleep(random.uniform(0.002, 0.03))
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, httpx.HTTPError):
                        res["cancelled"] += 1
                        return
                    # terminée avant l'annulation : compte comme normale
                    r = task.result()
                    res["s204" if r.status_code == 204 else "ok"] += 1
                else:
                    r = await client.get(path)
                    res["s204" if r.status_code == 204 else "ok"] += 1
            except httpx.HTTPError:
                res["errors"] += 1

        tasks = []
        for p in paths:
            tasks.append(asyncio.create_task(one(p, random.random() < cancel_frac)))
        await asyncio.gather(*tasks, return_exceptions=True)

    sampler.cancel()
    try:
        await sampler
    except asyncio.CancelledError:
        pass
    res["peak_idle_in_tx"] = peak["idle in transaction"]
    return res


def main() -> int:
    env = dict(os.environ)
    # application_name distinct → la sonde isole les connexions de CE serveur.
    url = env["LABUSE_DATABASE_URL"]
    sep = "&" if "?" in url else "?"
    env["LABUSE_DATABASE_URL"] = f"{url}{sep}application_name={APP_NAME}"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "labuse.api.app:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--workers", "1", "--log-level", "warning"],
        env=env)
    try:
        # attendre /healthz
        deadline = time.monotonic() + 40
        with httpx.Client(timeout=2.0) as c:
            while time.monotonic() < deadline:
                try:
                    if c.get(f"{BASE}/healthz").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.4)
            else:
                print("ERREUR : serveur pas prêt", file=sys.stderr); return 2

        paths = _tiles_parcelles(N_TILES // 2) + _tiles_couches(N_TILES // 2)
        random.shuffle(paths)
        print(f"→ {len(paths)} tuiles tirées (parcelles + couches), ~40 % annulées en plein vol\n")

        before = pg_states()
        res = asyncio.run(fire(paths, cancel_frac=0.4))

        # drain : laisser les threads serveur finir, puis échantillonner la stabilité
        samples = []
        for _ in range(12):            # ~2,4 s
            time.sleep(0.2)
            samples.append(pg_states())
        after = samples[-1]
        max_idle_after = max(s.get("idle in transaction", 0) for s in samples)

        print("Requêtes :", res)
        print("\npg_stat_activity (application_name =", APP_NAME + ") :")
        print("  avant rafale      :", before)
        print("  pic PENDANT rafale:", {"idle in transaction": res["peak_idle_in_tx"]})
        print("  max idle-in-tx APRÈS (drain 2,4 s):", max_idle_after)
        print("\n  SELECT state, count(*) — snapshot final :")
        if not after:
            print("    (aucune connexion résiduelle de ce serveur)")
        for st, n in sorted(after.items()):
            print(f"    {st:<20} {n}")
        idle_final = after.get("idle in transaction", 0)
        verdict = "OK" if (idle_final == 0 and max_idle_after == 0) else "FUITE"
        print(f"\n  idle in transaction (final) = {idle_final} · max après drain = {max_idle_after}"
              f"  →  {verdict}")
        return 0 if verdict == "OK" else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
