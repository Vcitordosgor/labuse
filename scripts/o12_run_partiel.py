#!/usr/bin/env python
"""O12-PARTIEL — run île entière du LOT DÉCOUPÉ : DELETE type 'decoupe' + build_divisions_partiel
sur les 24 communes, N en parallèle (O12_WORKERS, défaut 5), grosses communes d'abord.
Le pool RÉSIDUEL (types libre/demolition) n'est PAS touché — les deux familles restent
distinctes. Sortie : effectifs par commune, distributions (surface, compacité, façade).
Table MASQUÉE (EXPOSE=False)."""
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

    print(f"── DELETE decoupe + build_divisions_partiel ({WORKERS} communes en parallèle) ──", flush=True)
    session.execute(text(division_or.DDL))
    # SNAPSHOT des tracés revus AVANT le delete : le re-run distingue « tracé inchangé » (déjà
    # revu / exclusion liée-géométrie tenue) de « tracé modifié » (à re-revoir).
    n_snap = division_or.snapshot_review_lots(session)
    print(f"  snapshot des tracés revus : {n_snap} découpes", flush=True)
    session.execute(text("DELETE FROM division_or_candidates WHERE type_division = 'decoupe'"))
    session.commit()

    def _run(nom: str) -> None:
        s = Session()
        try:
            division_or.build_divisions_partiel(s, [nom], log=lambda m: print(f"  {m}", flush=True))
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(_run, noms))

    print("\n| Commune | Lots à découper |")
    print("|---|---:|")
    stats = session.execute(text(
        """SELECT commune, count(*) FROM division_or_candidates
           WHERE type_division='decoupe' GROUP BY commune ORDER BY commune""")).all()
    for c, n in stats:
        print(f"| {c} | {n} |")
    print(f"| **Total** | **{sum(r[1] for r in stats)}** |")
    for col in ("residuel_m2", "compacite", "residuel_facade_m", "emprise_restante"):
        dist = session.execute(text(
            f"""SELECT min({col}), percentile_cont(0.25) WITHIN GROUP (ORDER BY {col}),
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY {col}),
                       percentile_cont(0.75) WITHIN GROUP (ORDER BY {col}), max({col})
                FROM division_or_candidates WHERE type_division='decoupe'""")).one()
        if dist[0] is not None:
            print(f"{col} : min={dist[0]} · P25={dist[1]:.3f} · médiane={dist[2]:.3f} · "
                  f"P75={dist[3]:.3f} · max={dist[4]}")
    autres = session.execute(text(
        "SELECT type_division, count(*) FROM division_or_candidates GROUP BY 1 ORDER BY 1")).all()
    print("Familles en table : " + " · ".join(f"{t}={n}" for t, n in autres))


if __name__ == "__main__":
    main()
