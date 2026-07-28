#!/usr/bin/env python
"""O12-PARTIEL-2 revue 3 — RE-RUN CIBLÉ. Les changements de cette itération ne font que RETIRER
des candidats (corrections d'exclusions) : une commune à 0 candidat au run précédent reste à 0.
On ne relance donc le détecteur (lourd) que sur les communes qui AVAIENT des candidats — le
reste est garanti vide. Ordre : snapshot → résiduel (7 communes) → découpe (14 communes).
Chrono par commune. Table MASQUÉE (EXPOSE=False)."""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labuse.ingestion import division_or  # noqa: E402

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
WORKERS = int(os.environ.get("O12_WORKERS", "5"))

# Communes ayant produit des candidats au dernier run complet (superset — les exclusions ne
# font que retirer). Résiduel : table finale (14). Découpe : run 45 (superset des filtres actuels).
RESIDUEL_COMMUNES = ["L'Étang-Salé", "Saint-Joseph", "Saint-Leu", "Saint-Paul", "Saint-Pierre",
                     "Sainte-Marie", "Sainte-Suzanne"]
DECOUPE_COMMUNES = ["Saint-Louis", "Saint-Pierre", "Saint-Denis", "Saint-Paul", "Saint-Leu",
                    "Saint-André", "Le Tampon", "Saint-Joseph", "Saint-Benoît", "Sainte-Marie",
                    "Cilaos", "Entre-Deux", "La Possession", "Les Trois-Bassins"]


def main() -> None:
    engine = create_engine(DB, pool_size=WORKERS + 2)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.execute(text(division_or.DDL))
    n_snap = division_or.snapshot_review_lots(session)
    print(f"── 1. Snapshot des tracés revus : {n_snap} découpes ──", flush=True)

    print(f"── 2. RÉSIDUEL sur {len(RESIDUEL_COMMUNES)} communes ({WORKERS} parallèle) ──", flush=True)
    session.execute(text("TRUNCATE division_or_candidates"))
    session.commit()

    def _res(nom: str) -> None:
        s = Session()
        try:
            t0 = time.time()
            division_or.build_divisions(s, [nom], log=lambda *_: None)
            n = s.execute(text("SELECT count(*) FROM division_or_candidates WHERE commune=:c"),
                          {"c": nom}).scalar()
            print(f"  [R] {nom:<22} {n:>2} résiduels  ({time.time()-t0:.0f}s)", flush=True)
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(_res, sorted(RESIDUEL_COMMUNES)))

    print(f"── 3. DÉCOUPE sur {len(DECOUPE_COMMUNES)} communes ({WORKERS} parallèle) ──", flush=True)

    def _dec(nom: str) -> None:
        s = Session()
        try:
            t0 = time.time()
            division_or.build_divisions_partiel(s, [nom], log=lambda *_: None)
            n = s.execute(text("SELECT count(*) FROM division_or_candidates "
                               "WHERE commune=:c AND type_division='decoupe'"), {"c": nom}).scalar()
            print(f"  [D] {nom:<22} {n:>2} découpes  ({time.time()-t0:.0f}s)", flush=True)
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(_dec, sorted(DECOUPE_COMMUNES)))

    fam = session.execute(text(
        "SELECT type_division, count(*) FROM division_or_candidates GROUP BY 1 ORDER BY 1")).all()
    print("\n## Familles finales : " + " · ".join(f"{t}={n}" for t, n in fam), flush=True)
    statut = session.execute(text(
        """SELECT revue_statut, count(*) FROM (
             SELECT CASE WHEN c.type_division<>'decoupe' THEN 'residuel'
                         WHEN s.idu IS NULL OR s.lot_geom IS NULL THEN 'nouveau'
                         WHEN ST_Area(ST_SymDifference(c.lot_geom,s.lot_geom)) < 0.02*ST_Area(s.lot_geom)
                           THEN 'inchange' ELSE 'modifie' END revue_statut
             FROM division_or_candidates c
             LEFT JOIN division_or_revue_snapshot s ON s.idu=c.idu) t
           GROUP BY 1 ORDER BY 1""")).all()
    print("statut de tracé : " + " · ".join(f"{k}={v}" for k, v in statut), flush=True)
    # contrôle : aucune exclusion de revue ne doit reparaître
    excl = [e["idu"] for e in division_or._exclusions_revue()]
    present = session.execute(text(
        "SELECT idu FROM division_or_candidates WHERE idu = ANY(:x)"), {"x": excl}).scalars().all()
    print(f"VERROU exclusions : {len(present)} exclu(s) reparu(s) {list(present) or '— aucun ✓'}", flush=True)


if __name__ == "__main__":
    main()
