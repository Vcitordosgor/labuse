#!/usr/bin/env python
"""O12-PARTIEL-2 revue 2 — RE-RUN île complet, ordonné :
  1. SNAPSHOT des tracés découpés revus (avant toute destruction) — pour distinguer au re-run
     un tracé inchangé (déjà revu / exclusion liée-géométrie tenue) d'un tracé modifié (à revoir) ;
  2. run RÉSIDUEL (TRUNCATE + build_divisions, 24 communes) ;
  3. run DÉCOUPE (build_divisions_partiel, 24 communes) — lit le snapshot.
N communes en parallèle (O12_WORKERS, défaut 5), grosses d'abord. Table MASQUÉE (EXPOSE=False)."""
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

    session.execute(text(division_or.DDL))
    n_snap = division_or.snapshot_review_lots(session)
    print(f"── 1. Snapshot des tracés revus : {n_snap} découpes ──", flush=True)

    print(f"── 2. Run RÉSIDUEL : TRUNCATE + build_divisions ({WORKERS} parallèle) ──", flush=True)
    session.execute(text("TRUNCATE division_or_candidates"))
    session.commit()

    def _res(nom: str) -> None:
        s = Session()
        try:
            division_or.build_divisions(s, [nom], log=lambda m: print(f"  [R] {m}", flush=True))
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(_res, noms))

    print(f"── 3. Run DÉCOUPE : build_divisions_partiel ({WORKERS} parallèle) ──", flush=True)

    def _dec(nom: str) -> None:
        s = Session()
        try:
            division_or.build_divisions_partiel(s, [nom], log=lambda m: print(f"  [D] {m}", flush=True))
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(_dec, noms))

    fam = session.execute(text(
        "SELECT type_division, count(*) FROM division_or_candidates GROUP BY 1 ORDER BY 1")).all()
    print("\n## Familles finales : " + " · ".join(f"{t}={n}" for t, n in fam))
    print("\n| Commune | Découpe | Résiduel |")
    print("|---|---:|---:|")
    stats = session.execute(text(
        """SELECT commune, count(*) FILTER (WHERE type_division='decoupe') d,
                  count(*) FILTER (WHERE type_division<>'decoupe') r
           FROM division_or_candidates GROUP BY commune ORDER BY commune""")).all()
    for c, d_, r_ in stats:
        print(f"| {c} | {d_} | {r_} |")
    td, tr = sum(x[1] for x in stats), sum(x[2] for x in stats)
    print(f"| **Total** | **{td}** | **{tr}** |")
    for col in ("residuel_m2", "solidite", "compacite", "residuel_facade_m"):
        dist = session.execute(text(
            f"""SELECT min({col}), percentile_cont(0.5) WITHIN GROUP (ORDER BY {col}), max({col})
                FROM division_or_candidates WHERE type_division='decoupe'""")).one()
        if dist[0] is not None:
            print(f"decoupe.{col} : min={dist[0]} · médiane={dist[1]:.3f} · max={dist[2]}")
    statut = session.execute(text(
        """SELECT revue_statut, count(*) FROM (
             SELECT CASE WHEN c.type_division<>'decoupe' THEN 'residuel'
                         WHEN s.idu IS NULL OR s.lot_geom IS NULL THEN 'nouveau'
                         WHEN ST_Area(ST_SymDifference(c.lot_geom, s.lot_geom)) < 0.02*ST_Area(s.lot_geom)
                           THEN 'inchange' ELSE 'modifie' END revue_statut
             FROM division_or_candidates c
             LEFT JOIN division_or_revue_snapshot s ON s.idu=c.idu) t
           GROUP BY 1 ORDER BY 1""")).all()
    print("statut de tracé (vs revue précédente) : " + " · ".join(f"{k}={v}" for k, v in statut))


if __name__ == "__main__":
    main()
