#!/usr/bin/env python
"""AUTONOMIE-2 — PREUVE readyz : A/B sous contention `event_log` + 3 redémarrages sous charge.

Reproduit la cause du flap `/readyz` (DEPLOY-1028b / DEPLOY-FINAL / DEPLOY-AUTONOMIE) et prouve le
correctif. Un lecteur tient un verrou ACCESS SHARE sur `event_log` (comme le ferait le trafic / le
réchauffage) : il bloque tout `ALTER TABLE event_log` (qui exige ACCESS EXCLUSIVE) mais PAS les
INSERT/SELECT.

  • AVANT (heal DANS le worker, LABUSE_SKIP_BOOT_HEAL absent) : l'`ALTER event_log` du heal percute
    le verrou → lock_timeout (5 s) ×3 → `schema_heal.ok=false` → /readyz 503.
  • APRÈS (heal PRÉ-SERVICE `labuse schema-heal` SANS verrou, puis workers avec
    LABUSE_SKIP_BOOT_HEAL=1) : les workers ne touchent plus au schéma → /readyz 200 STABLE même
    verrou tenu, sur 3 redémarrages consécutifs, pendant une charge HTTP concurrente.

Usage : <venv>/bin/python -m <...> ou directement avec PYTHONPATH=src et LABUSE_DATABASE_URL posés.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

PORT = int(os.environ.get("PREUVE_PORT", "8787"))
PY = sys.executable
DSN = os.environ.get("LABUSE_COHERENCE_DSN") or "postgresql://openclaw@localhost:5432/labuse"
BASE_ENV = {**os.environ, "PYTHONPATH": "src",
            "LABUSE_DATABASE_URL": os.environ.get(
                "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")}


def _get(path: str, timeout: float = 3.0) -> int:
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=timeout)
        return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def hold_lock(stop: threading.Event) -> None:
    """Tient un ACCESS SHARE sur event_log : bloque l'ALTER, pas les INSERT/SELECT."""
    import psycopg
    conn = psycopg.connect(DSN)
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM event_log LIMIT 1")
        while not stop.is_set():
            time.sleep(0.1)
    conn.rollback()
    conn.close()


def charge_http(stop: threading.Event) -> None:
    """Charge concurrente légère (healthz) pendant la fenêtre d'observation."""
    while not stop.is_set():
        _get("/healthz", timeout=2)
        time.sleep(0.05)


def start_uvicorn(skip: bool) -> subprocess.Popen:
    env = dict(BASE_ENV)
    if skip:
        env["LABUSE_SKIP_BOOT_HEAL"] = "1"
    else:
        env.pop("LABUSE_SKIP_BOOT_HEAL", None)
    return subprocess.Popen(
        [PY, "-m", "uvicorn", "labuse.api.app:app", "--host", "127.0.0.1",
         "--port", str(PORT), "--workers", "2", "--log-level", "warning"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_listen(proc: subprocess.Popen, timeout: float = 90) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return False
        if _get("/healthz", timeout=2) != 0:
            return True
        time.sleep(0.5)
    return False


def _poll(n: int, interval: float = 0.3) -> list[int]:
    out = []
    for _ in range(n):
        out.append(_get("/readyz"))
        time.sleep(interval)
    return out


def stop_proc(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main() -> int:
    echecs = []

    # ── AVANT : heal dans le worker, verrou tenu → readyz doit TOMBER (503) ──
    print("\n=== AVANT (heal dans le worker, LABUSE_SKIP_BOOT_HEAL absent) ===")
    stop = threading.Event()
    lock_t = threading.Thread(target=hold_lock, args=(stop,), daemon=True)
    lock_t.start()
    time.sleep(1.0)  # le verrou est pris
    proc = start_uvicorn(skip=False)
    listening = wait_listen(proc)
    codes = _poll(20) if listening else []
    stop_proc(proc)
    stop.set(); lock_t.join(timeout=5)
    sains = sum(1 for c in codes if c == 200)
    ko = sum(1 for c in codes if c == 503)
    print(f"   /readyz sur 20 sondes : 200×{sains} · 503×{ko} · autres×{20 - sains - ko} "
          f"({'écoute' if listening else 'JAMAIS écouté'})")
    avant_ko = (not listening) or ko > 0 or sains < 20
    print(f"   → {'ATTENDU : readyz DÉGRADÉ sous contention (heal dans le worker)' if avant_ko else 'INATTENDU : readyz sain ?!'}")
    if not avant_ko:
        echecs.append("AVANT n'a pas reproduit la dégradation")

    # ── APRÈS : heal pré-service (sans verrou), workers skip, verrou tenu, 3 redémarrages ──
    print("\n=== APRÈS (heal pré-service puis workers LABUSE_SKIP_BOOT_HEAL=1) ===")
    print("   labuse schema-heal (en série, sans verrou)…")
    env = dict(BASE_ENV)
    r = subprocess.run([PY, "-m", "labuse.cli", "schema-heal"], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print("   " + (r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
          + f" (exit {r.returncode})")
    if r.returncode != 0:
        echecs.append("schema-heal pré-service a échoué")

    stop = threading.Event()
    lock_t = threading.Thread(target=hold_lock, args=(stop,), daemon=True)
    charge_t = threading.Thread(target=charge_http, args=(stop,), daemon=True)
    lock_t.start(); time.sleep(1.0); charge_t.start()
    for tour in range(1, 4):
        proc = start_uvicorn(skip=True)
        listening = wait_listen(proc)
        codes = _poll(15) if listening else []
        stop_proc(proc)
        sains = sum(1 for c in codes if c == 200)
        ko = sum(1 for c in codes if c != 200)
        stable = listening and sains == 15 and ko == 0
        print(f"   redémarrage {tour}/3 : /readyz 200×{sains} · non-200×{ko} "
              f"→ {'STABLE ✓' if stable else 'INSTABLE ✗'}")
        if not stable:
            echecs.append(f"redémarrage {tour} instable")
    stop.set(); lock_t.join(timeout=5); charge_t.join(timeout=5)

    print("\n=== VERDICT ===")
    if echecs:
        print("✗ ÉCHEC : " + " ; ".join(echecs))
        return 1
    print("✓ readyz DÉGRADÉ sans le correctif, STABLE 200 (3/3 redémarrages) avec le correctif, "
          "verrou event_log tenu + charge HTTP concurrente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
