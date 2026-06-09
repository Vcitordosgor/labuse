"""Construit les 24 communes de La Réunion (ingestion + évaluation), en PARALLÈLE
et REPRENABLE. Optimisation de `labuse ingest-island` (série) : l'évaluation
(CPU/DB) est parallélisée par commune sur N workers, en chevauchant l'ingestion
réseau des communes absentes.

Garanties :
- verdicts identiques — la cascade n'est pas touchée ; chaque commune = parcelles
  disjointes → écritures concurrentes sans conflit (pas de contrainte d'unicité) ;
- idempotent / reprenable — saute les communes déjà « ok », ré-évalue les
  « ingested », (re)ingère + évalue les absentes ; un arrêt ne reperd rien.

⚠️ BASE ÉPHÉMÈRE (environnement web) : la base PostGIS repart de l'image du
conteneur à chaque REMPLACEMENT de conteneur. Pour des 24 communes DURABLES,
exécuter ce script lors de la CONSTRUCTION de l'image puis re-snapshotter
(voir docs/BUILD_COMMUNES.md).

Usage : python scripts/build_communes.py [--workers 4]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from labuse.db import session_scope  # noqa: E402
from labuse.ingestion import run_all  # noqa: E402

WORKER = str(Path(__file__).with_name("_commune_worker.py"))
EVAL_TIMEOUT = 21600     # 6 h max / commune (garde-fou anti-hang)
INGEST_TIMEOUT = 9000    # 2,5 h max / commune


def _run(args: list[str], label: str, timeout: int) -> None:
    t = time.time()
    try:
        r = subprocess.run([sys.executable, WORKER, *args],
                           capture_output=True, text=True, timeout=timeout)
        ok = r.returncode == 0
        tail = ((r.stdout or "").strip().splitlines()[-1:] or [""])[0]
        msg = f"[{label} {'OK' if ok else 'FAIL'}] {args[-1]} {time.time() - t:.0f}s :: {tail}"
        if not ok:
            msg += f"\n  ERR {(r.stderr or '').strip()[-700:]}"
        print(msg, flush=True)
    except subprocess.TimeoutExpired:
        print(f"[{label} TIMEOUT] {args[-1]} {time.time() - t:.0f}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=4, help="évaluations parallèles (défaut 4)")
    a = ap.parse_args()

    # Auto-réparation du schéma : les colonnes pré-projetées geom_2975 (requises par
    # la cascade) peuvent manquer après un recyclage de conteneur — on les (re)crée
    # et (re)peuple, idempotent, avant toute évaluation.
    from labuse.db import engine
    from labuse.models import ensure_geom_2975
    print("Schéma : ensure_geom_2975 …", flush=True)
    ensure_geom_2975(engine())

    with session_scope() as s:
        status = {n: run_all.run_status(s, n) for _, n in run_all.REUNION_COMMUNES}
    pending = [n for _, n in run_all.REUNION_COMMUNES if status.get(n) == "ingested"]
    absent = [(i, n) for i, n in run_all.REUNION_COMMUNES if status.get(n) not in ("ok", "ingested")]
    done = [n for _, n in run_all.REUNION_COMMUNES if status.get(n) == "ok"]
    print(f"État initial : {len(done)} ok · {len(pending)} à évaluer · {len(absent)} à ingérer",
          flush=True)

    def ingest_all() -> None:
        for insee, name in absent:
            _run(["ingest", insee, name], "INGEST", INGEST_TIMEOUT)

    t0 = time.time()
    print(f"=== STAGE 1 : eval ({a.workers} parallèle) || ingest absentes (série) ===", flush=True)
    th = threading.Thread(target=ingest_all)
    th.start()
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(lambda n: _run(["eval", n], "EVAL", EVAL_TIMEOUT), pending))
    th.join()

    print(f"=== STAGE 2 : eval communes nouvellement ingérées ({a.workers} parallèle) ===",
          flush=True)
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(lambda n: _run(["eval", n], "EVAL", EVAL_TIMEOUT), [n for _, n in absent]))

    from sqlalchemy import text
    with session_scope() as s:
        ok = s.execute(
            text("SELECT count(DISTINCT commune) FROM ingestion_runs WHERE status='ok'")).scalar()
    print(f"=== DONE ({time.time() - t0:.0f}s) — {ok}/24 communes complètes ===", flush=True)


if __name__ == "__main__":
    main()
