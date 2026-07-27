#!/usr/bin/env python
"""O12-ÎLE D — bilan de la variante « division avec démolition » sur les 24 communes.

Phase 1 (lecture seule) : rejoue les DEUX variantes (libre / démolition) avec les filtres
géométrie + zonage mais SANS la garde de secondarité ni le dédoublonnage, annotées :
  · crit_ok      — la garde `bati_lot × 3 ≤ bati_total` (bâti à démolir ≤ moitié du conservé)
  · libre_pass   — la parcelle passe aussi en division libre (la démolition n'apporte rien)
→ reports/o12-ile/bilan_demolition.csv + agrégats (candidats NOUVEAUX, rejets de la garde,
  distribution des surfaces à démolir).

Phase 2 : TRUNCATE + build_divisions (formule complète, avec garde et dédoublonnage) sur les
24 communes → la table finale porte type_division / bati_lot_m2.

La table reste MASQUÉE (EXPOSE=False) — la revue visuelle tranche.
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
WORKERS = int(os.environ.get("O12_WORKERS", "5"))

# Les deux variantes, filtres géométrie + zonage appliqués, SANS garde ni dédoublonnage.
_ANNOTATED = """
WITH cand AS (
  SELECT p.id, p.idu, p.commune, p.geom_2975, p.surface_m2 FROM parcels p
  WHERE p.commune = :commune AND p.surface_m2 BETWEEN 1000 AND 6000
    AND EXISTS (SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975))),
bldg AS (
  SELECT c.id, b.geom_2975 AS g, ST_Area(ST_Intersection(b.geom_2975, c.geom_2975)) AS a
  FROM cand c JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(b.geom_2975, c.geom_2975)),
bat AS (SELECT id, ST_Union(g) AS bgeom, sum(a) AS bat_m2, count(*) AS nb_bat FROM bldg GROUP BY id),
princ AS (SELECT DISTINCT ON (id) id, g AS pgeom FROM bldg ORDER BY id, a DESC),
freed AS (
  SELECT c.id, c.idu, c.commune, c.surface_m2, bat.bat_m2, v.variante,
         lg.geom AS free_geom, ST_Area(lg.geom) AS free_m2,
         (ST_MaximumInscribedCircle(lg.geom)).radius AS rad
  FROM cand c JOIN bat ON bat.id = c.id JOIN princ ON princ.id = c.id
  CROSS JOIN LATERAL (VALUES ('libre', bat.bgeom), ('demolition', princ.pgeom)) AS v(variante, sub)
  CROSS JOIN LATERAL (SELECT g.geom FROM ST_Dump(ST_Difference(c.geom_2975, ST_Buffer(v.sub, 3))) g
                      ORDER BY ST_Area(g.geom) DESC LIMIT 1) lg
  WHERE bat.bat_m2 / c.surface_m2 BETWEEN 0.08 AND 0.45
    AND NOT (v.variante = 'demolition' AND bat.nb_bat = 1)),
acces AS (
  SELECT *,
    (SELECT coalesce(sum(ST_Length(ST_Intersection(ST_Buffer(v.geom_2975,1.5), ST_Boundary(free_geom)))),0)
       FROM spatial_layers v WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975, free_geom, 2)) AS facade_free
  FROM freed
  WHERE free_m2 >= 500 AND free_m2 <= surface_m2 - 400 AND free_m2 <= surface_m2 * 0.5 AND rad >= 9),
demol AS (
  SELECT a.*, CASE WHEN a.variante = 'libre' THEN 0 ELSE coalesce(
      (SELECT round(sum(ST_Area(ST_Intersection(b.g, a.free_geom))))::int
       FROM bldg b WHERE b.id = a.id), 0) END AS bati_lot_m2
  FROM acces a),
zon AS (
  SELECT d.*, z.subtype AS zone
  FROM demol d
  LEFT JOIN LATERAL (
    SELECT z2.subtype FROM spatial_layers z2
    WHERE z2.kind='plu_gpu_zone' AND ST_Intersects(z2.geom_2975, d.free_geom)
    ORDER BY ST_Area(ST_Intersection(z2.geom_2975, d.free_geom)) DESC LIMIT 1) z ON true)
SELECT idu, commune, variante, round(surface_m2)::int AS surface_m2, round(free_m2)::int AS residuel_m2,
       round(bat_m2)::int AS bati_m2, bati_lot_m2,
       (bati_lot_m2 * 3 <= bat_m2)                                 AS crit_ok,
       bool_or(variante = 'libre') OVER (PARTITION BY idu)         AS libre_pass,
       zone
FROM zon
WHERE facade_free >= 12
  AND (zone = 'U' OR zone LIKE 'AU%' OR (zone IS NULL AND
       EXISTS (SELECT 1 FROM parcel_pau pp WHERE pp.idu = zon.idu)))
"""


def main() -> None:
    engine = create_engine(DB, pool_size=WORKERS + 2)
    Session = sessionmaker(bind=engine)
    session = Session()
    out_dir = Path(__file__).resolve().parents[1] / "reports" / "o12-ile"
    out_dir.mkdir(parents=True, exist_ok=True)

    tailles = dict(session.execute(text("SELECT commune, count(*) FROM parcels GROUP BY 1")).all())
    session.rollback()
    noms = sorted((nom for _insee, nom in REUNION_COMMUNES), key=lambda n: -tailles.get(n, 0))

    def _phase1(nom: str) -> tuple[str, list[dict], float]:
        s = Session()
        try:
            t0 = time.time()
            rows = [dict(r) for r in s.execute(text(_ANNOTATED), {"commune": nom}).mappings()]
            return nom, rows, time.time() - t0
        finally:
            s.rollback()
            s.close()

    print(f"── Phase 1 : deux variantes annotées, sans garde ({WORKERS} communes en parallèle) ──", flush=True)
    rows_all: list[dict] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for nom, rows, dt in pool.map(_phase1, noms):
            rows_all.extend(rows)
            n_demo = sum(1 for r in rows if r["variante"] == "demolition" and r["bati_lot_m2"] >= 1)
            print(f"  {nom:<24} libre={sum(1 for r in rows if r['variante']=='libre'):>3} "
                  f"demo-brut={n_demo:>3}  ({dt:.0f}s)", flush=True)

    csv_path = out_dir / "bilan_demolition.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_all[0].keys()) if rows_all else
                           ["idu", "commune", "variante", "surface_m2", "residuel_m2", "bati_m2",
                            "bati_lot_m2", "crit_ok", "libre_pass", "zone"])
        w.writeheader()
        w.writerows(rows_all)
    print(f"  détail → {csv_path}", flush=True)

    demo = [r for r in rows_all if r["variante"] == "demolition" and r["bati_lot_m2"] >= 1]
    nouveaux = [r for r in demo if not r["libre_pass"]]
    print(f"\nVariante démolition (bati_lot ≥ 1 m²) : {len(demo)} lots — dont {len(nouveaux)} "
          f"parcelles NOUVELLES (ne passaient pas en libre)")
    print(f"Garde de secondarité (bati_lot×3 ≤ bati_total) : {sum(1 for r in nouveaux if r['crit_ok'])} "
          f"gardés · {sum(1 for r in nouveaux if not r['crit_ok'])} rejetés (découpage inversé)")

    print(f"\n── Phase 2 : TRUNCATE + build_divisions (formule complète, {WORKERS} en parallèle) ──", flush=True)
    session.execute(text(division_or.DDL))
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

    print("\n## Effectifs finaux par commune et type\n")
    print("| Commune | Libre | Démolition | Total |")
    print("|---|---:|---:|---:|")
    stats = session.execute(text(
        """SELECT commune,
                  count(*) FILTER (WHERE type_division='libre') libre,
                  count(*) FILTER (WHERE type_division='demolition') demo, count(*)
           FROM division_or_candidates GROUP BY commune ORDER BY commune""")).all()
    for c, li, de, tot in stats:
        print(f"| {c} | {li} | {de} | {tot} |")
    tl = sum(r[1] for r in stats); td = sum(r[2] for r in stats)
    print(f"| **Total** | **{tl}** | **{td}** | **{tl + td}** |")

    dist = session.execute(text(
        """SELECT count(*), min(bati_lot_m2), percentile_cont(0.5) WITHIN GROUP (ORDER BY bati_lot_m2),
                  max(bati_lot_m2) FROM division_or_candidates WHERE type_division='demolition'""")).one()
    if dist[0]:
        print(f"\nBâti à démolir (type demolition) : n={dist[0]} · min={dist[1]} · "
              f"médiane={dist[2]:.0f} · max={dist[3]} m²")


if __name__ == "__main__":
    main()
