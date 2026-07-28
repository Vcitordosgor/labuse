#!/usr/bin/env python
"""O12-ÎLE — bilan AVANT/APRÈS des correctifs du détecteur Division en or, sur les 24 communes.

Phase 1 (lecture seule) : rejoue l'ANCIENNE formule (celle de la revue Entre-Deux/Bras-Panon,
sans les correctifs) annotée avec les trois critères ajoutés — ratio lot/parcelle > 50 %,
zone dominante du lot A/N, commune RNU hors PAU estimée — pour attribuer chaque élimination.
Détail par candidat → reports/o12-ile/bilan_avant.csv (gitignoré si exports, sinon versionnable).

Phase 2 : TRUNCATE division_or_candidates puis `build_divisions` (formule CORRIGÉE) sur les
24 communes — la table finale ne contient QUE des candidats post-correctifs.

Sortie stdout : tableau markdown avant/après par commune + distribution des surfaces de lot.
La table reste MASQUÉE (EXPOSE=False) — la décision d'exposition suit la nouvelle revue.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labuse.ingestion import division_or  # noqa: E402
from labuse.ingestion.run_all import REUNION_COMMUNES  # noqa: E402

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
WORKERS = int(os.environ.get("O12_WORKERS", "5"))   # communes en parallèle (PostGIS = CPU-bound)

# ANCIENNE formule (pré-correctifs), annotée : mêmes CTE que le _DETECT d'avant O12-ÎLE,
# + zone dominante du lot et flags d'élimination — AUCUN des nouveaux filtres n'est appliqué.
_OLD_ANNOTATED = """
WITH cand AS (
  SELECT p.id, p.idu, p.commune, p.geom_2975, p.surface_m2 FROM parcels p
  WHERE p.commune = :commune AND p.surface_m2 BETWEEN 1000 AND 6000
    AND EXISTS (SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975))),
bat AS (
  SELECT c.id, ST_Union(b.geom_2975) AS bgeom,
         sum(ST_Area(ST_Intersection(b.geom_2975, c.geom_2975))) AS bat_m2
  FROM cand c JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(b.geom_2975, c.geom_2975)
  GROUP BY c.id),
freed AS (
  SELECT c.id, c.idu, c.commune, c.surface_m2, c.geom_2975, bat.bgeom, bat.bat_m2,
         lg.geom AS free_geom, ST_Area(lg.geom) AS free_m2,
         (ST_MaximumInscribedCircle(lg.geom)).radius AS rad
  FROM cand c JOIN bat ON bat.id = c.id
  CROSS JOIN LATERAL (SELECT g.geom FROM ST_Dump(ST_Difference(c.geom_2975, ST_Buffer(bat.bgeom, 3))) g
                      ORDER BY ST_Area(g.geom) DESC LIMIT 1) lg
  WHERE bat.bat_m2 / c.surface_m2 BETWEEN 0.08 AND 0.45),
acces AS (
  SELECT *,
    (SELECT coalesce(sum(ST_Length(ST_Intersection(ST_Buffer(v.geom_2975,1.5), ST_Boundary(free_geom)))),0)
       FROM spatial_layers v WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975, free_geom, 2)) AS facade_free
  FROM freed
  WHERE free_m2 >= 500 AND free_m2 <= surface_m2 - 400 AND rad >= 9),
zon AS (
  SELECT a.*, z.subtype AS zone
  FROM acces a
  LEFT JOIN LATERAL (
    SELECT z2.subtype FROM spatial_layers z2
    WHERE z2.kind='plu_gpu_zone' AND ST_Intersects(z2.geom_2975, a.free_geom)
    ORDER BY ST_Area(ST_Intersection(z2.geom_2975, a.free_geom)) DESC LIMIT 1) z ON true)
SELECT idu, commune, round(surface_m2)::int AS surface_m2, round(free_m2)::int AS residuel_m2,
       round((free_m2 / surface_m2)::numeric, 3) AS ratio_lot,
       round(facade_free::numeric, 1) AS facade_m, zone,
       (free_m2 > surface_m2 * 0.5)                            AS elim_ratio,
       (zone IN ('A', 'N'))                                    AS elim_zone_an,
       (zone IS NULL AND NOT EXISTS
          (SELECT 1 FROM parcel_pau pp WHERE pp.idu = zon.idu)) AS elim_rnu_hors_pau
FROM zon WHERE facade_free >= 12
"""


def main() -> None:
    engine = create_engine(DB, pool_size=WORKERS + 2)
    Session = sessionmaker(bind=engine)
    session = Session()
    out_dir = Path(__file__).resolve().parents[1] / "reports" / "o12-ile"
    out_dir.mkdir(parents=True, exist_ok=True)

    # grosses communes d'abord (meilleur équilibrage du pool)
    tailles = dict(session.execute(text("SELECT commune, count(*) FROM parcels GROUP BY 1")).all())
    session.rollback()
    noms = sorted((nom for _insee, nom in REUNION_COMMUNES), key=lambda n: -tailles.get(n, 0))
    avant: dict[str, int] = {}
    elim = {"ratio": 0, "zone_an": 0, "rnu_hors_pau": 0}
    rows_all: list[dict] = []

    def _phase1(nom: str) -> tuple[str, list[dict], float]:
        s = Session()
        try:
            t0 = time.time()
            rows = [dict(r) for r in s.execute(text(_OLD_ANNOTATED), {"commune": nom}).mappings()]
            return nom, rows, time.time() - t0
        finally:
            s.rollback()   # aucune écriture en phase 1
            s.close()

    print(f"── Phase 1 : ancienne formule annotée (lecture seule, {WORKERS} communes en parallèle) ──", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for nom, rows, dt in pool.map(_phase1, noms):
            avant[nom] = len(rows)
            for r in rows:
                rows_all.append(r)
                elim["ratio"] += bool(r["elim_ratio"])
                elim["zone_an"] += bool(r["elim_zone_an"])
                elim["rnu_hors_pau"] += bool(r["elim_rnu_hors_pau"])
            print(f"  {nom:<24} avant={len(rows):>4}  ({dt:.0f}s)", flush=True)

    csv_path = out_dir / "bilan_avant.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_all[0].keys()) if rows_all else
                           ["idu", "commune", "surface_m2", "residuel_m2", "ratio_lot",
                            "facade_m", "zone", "elim_ratio", "elim_zone_an", "elim_rnu_hors_pau"])
        w.writeheader()
        w.writerows(rows_all)
    print(f"  détail → {csv_path}", flush=True)

    print(f"── Phase 2 : TRUNCATE + build_divisions (formule corrigée, {WORKERS} communes en parallèle) ──", flush=True)
    session.execute(text(division_or.DDL))   # DDL une fois AVANT le pool (pas de course CREATE/ALTER)
    session.execute(text("TRUNCATE division_or_candidates"))
    session.commit()

    def _phase2(nom: str) -> None:
        s = Session()
        try:
            division_or.build_divisions(s, [nom], log=lambda m: print(f"  {m}", flush=True))
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(_phase2, noms))

    apres = dict(session.execute(text(
        "SELECT commune, count(*) FROM division_or_candidates GROUP BY commune")).all())

    print("\n## Effectifs par commune — avant / après correctifs\n")
    print("| Commune | Avant | Après | Éliminés |")
    print("|---|---:|---:|---:|")
    for nom in sorted(noms):
        a, b = avant.get(nom, 0), apres.get(nom, 0)
        print(f"| {nom} | {a} | {b} | {a - b} |")
    ta, tb = sum(avant.values()), sum(apres.values())
    print(f"| **Total** | **{ta}** | **{tb}** | **{ta - tb}** |")
    print(f"\nÉliminations (non exclusives) : ratio>50 % = {elim['ratio']} · "
          f"zone A/N = {elim['zone_an']} · RNU hors PAU = {elim['rnu_hors_pau']}")

    dist = session.execute(text(
        """SELECT count(*), min(residuel_m2), percentile_cont(0.25) WITHIN GROUP (ORDER BY residuel_m2),
                  percentile_cont(0.5) WITHIN GROUP (ORDER BY residuel_m2),
                  percentile_cont(0.75) WITHIN GROUP (ORDER BY residuel_m2), max(residuel_m2)
           FROM division_or_candidates""")).one()
    print(f"\nSurfaces de lot (après) : n={dist[0]} · min={dist[1]} · P25={dist[2]:.0f} · "
          f"médiane={dist[3]:.0f} · P75={dist[4]:.0f} · max={dist[5]} m²")
    zones = session.execute(text(
        "SELECT coalesce(zone,'RNU-PAU'), count(*) FROM division_or_candidates GROUP BY 1 ORDER BY 2 DESC")).all()
    print("Zones (après) : " + " · ".join(f"{z}={n}" for z, n in zones))


if __name__ == "__main__":
    main()
