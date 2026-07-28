#!/usr/bin/env python
"""O12 — run île entière du détecteur Division en or : TRUNCATE + build_divisions (formule
courante) sur les 24 communes, N en parallèle (O12_WORKERS, défaut 5), grosses communes
d'abord. Sortie : effectifs par commune et type, distributions. Table MASQUÉE (EXPOSE=False)."""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labuse.ingestion import division_or  # noqa: E402
from labuse.ingestion.run_all import REUNION_COMMUNES  # noqa: E402

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
WORKERS = int(os.environ.get("O12_WORKERS", "5"))


def main() -> None:
    engine = create_engine(DB, pool_size=WORKERS + 2)
    Session = sessionmaker(bind=engine)
    session = Session()
    tailles = dict(session.execute(text("SELECT commune, count(*) FROM parcels GROUP BY 1")).all())
    session.rollback()
    noms = sorted((nom for _insee, nom in REUNION_COMMUNES), key=lambda n: -tailles.get(n, 0))

    print(f"── TRUNCATE + build_divisions ({WORKERS} communes en parallèle) ──", flush=True)
    session.execute(text(division_or.DDL))
    session.execute(text("TRUNCATE division_or_candidates"))
    session.commit()

    def _run(nom: str) -> None:
        s = Session()
        try:
            division_or.build_divisions(s, [nom], log=lambda m: print(f"  {m}", flush=True))
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(_run, noms))

    print("\n| Commune | Libre | Démolition | Total |")
    print("|---|---:|---:|---:|")
    stats = session.execute(text(
        """SELECT commune, count(*) FILTER (WHERE type_division='libre'),
                  count(*) FILTER (WHERE type_division='demolition'), count(*)
           FROM division_or_candidates GROUP BY commune ORDER BY commune""")).all()
    for c, li, de, tot in stats:
        print(f"| {c} | {li} | {de} | {tot} |")
    tl, td = sum(r[1] for r in stats), sum(r[2] for r in stats)
    print(f"| **Total** | **{tl}** | **{td}** | **{tl + td}** |")
    for col in ("residuel_m2", "compacite"):
        dist = session.execute(text(
            f"""SELECT min({col}), percentile_cont(0.25) WITHIN GROUP (ORDER BY {col}),
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY {col}),
                       percentile_cont(0.75) WITHIN GROUP (ORDER BY {col}), max({col})
                FROM division_or_candidates""")).one()
        print(f"{col} : min={dist[0]} · P25={dist[1]:.3f} · médiane={dist[2]:.3f} · "
              f"P75={dist[3]:.3f} · max={dist[4]}")


if __name__ == "__main__":
    main()
