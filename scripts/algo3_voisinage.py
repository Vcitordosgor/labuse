#!/usr/bin/env python
"""ALGO-3 LOT A — features de VOISINAGE HYPER-LOCAL (as-of, cible exclue).

RÈGLES ABSOLUES : champion INTOUCHÉ ; écritures UNIQUEMENT préfixées algo3_ ;
as-of strict (< 01/01/Y, clampé 2014) ; **la parcelle cible est exclue de son
propre voisinage À DEUX NIVEAUX** : (1) parcelle voisine ≠ cible, (2) toute
mutation À LAQUELLE LA CIBLE PARTICIPE (multi-parcelles) est exclue — sinon le
RR exploserait artificiellement (le piège central du mandat, testé AVANT
entraînement par tests/test_algo3_antifuite.py).

Rayons testés : 50 / 100 / 200 m (centroïde-à-centroïde, EPSG:2975).
Manquants : densité 0 voisin → ratios NULL (bin « manquant ») — DISTINCT du
« 0 vente avec voisins » (= 0.0) : leçon ALGO-2 (deux absences ≠ une).
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import create_engine, text

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

STEPS = [
("centroides", """
DROP TABLE IF EXISTS algo3_c;
CREATE TABLE algo3_c AS SELECT idu, ST_Centroid(geom_2975) AS c FROM parcels;
CREATE INDEX ON algo3_c USING gist (c);
CREATE UNIQUE INDEX ON algo3_c (idu);
ANALYZE algo3_c"""),

("mutations_geo", """
DROP TABLE IF EXISTS algo3_mut;
CREATE TABLE algo3_mut AS
SELECT m.id_mutation, m.idu, m.date_mutation, c.c
FROM p_model_ext_mut_l2 m JOIN algo3_c c ON c.idu = m.idu
WHERE NOT m.exclue_l2f;
CREATE INDEX ON algo3_mut USING gist (c);
ANALYZE algo3_mut"""),

("paires_mutations", """
DROP TABLE IF EXISTS algo3_pairs_mut;
CREATE TABLE algo3_pairs_mut AS
SELECT a.idu, m.id_mutation, m.date_mutation,
       ST_Distance(a.c, m.c) AS dist
FROM algo3_c a
JOIN algo3_mut m ON ST_DWithin(a.c, m.c, 200)
WHERE m.idu <> a.idu                                   -- exclusion NIVEAU 1 : pas soi-même
  AND NOT EXISTS (SELECT 1 FROM p_model_ext_mut_l2 x   -- exclusion NIVEAU 2 : pas une mutation
                  WHERE x.id_mutation = m.id_mutation  --   à laquelle la CIBLE participe
                    AND x.idu = a.idu);
CREATE INDEX ON algo3_pairs_mut (idu, date_mutation);
ANALYZE algo3_pairs_mut"""),

("paires_permis", """
DROP TABLE IF EXISTS algo3_pairs_permis;
CREATE TABLE algo3_pairs_permis AS
SELECT a.idu, s.permit_id, s.date::date AS date_autorisation,
       ST_Distance(a.c, ST_Transform(s.geom, 2975)) AS dist
FROM algo3_c a
JOIN sitadel_permits s ON s.geom IS NOT NULL
  AND ST_DWithin(a.c, ST_Transform(s.geom, 2975), 200)
WHERE NOT (s.idu_codes ? a.idu);                       -- exclusion : permis rattaché à la cible
CREATE INDEX ON algo3_pairs_permis (idu, date_autorisation);
ANALYZE algo3_pairs_permis"""),

("densites", """
DROP TABLE IF EXISTS algo3_dens;
CREATE TABLE algo3_dens AS
SELECT a.idu,
  count(*) FILTER (WHERE ST_DWithin(a.c, b.c, 50))  AS n50,
  count(*) FILTER (WHERE ST_DWithin(a.c, b.c, 100)) AS n100,
  count(*)                                          AS n200
FROM algo3_c a JOIN algo3_c b ON ST_DWithin(a.c, b.c, 200) AND b.idu <> a.idu
GROUP BY a.idu;
CREATE UNIQUE INDEX ON algo3_dens (idu);
ANALYZE algo3_dens"""),

("mitoyens", """
DROP TABLE IF EXISTS algo3_touch;
CREATE TABLE algo3_touch AS
SELECT p.idu AS idu, q.idu AS idu_voisin
FROM parcels p JOIN parcels q
  ON p.id <> q.id AND p.geom_2975 && q.geom_2975 AND ST_Touches(p.geom_2975, q.geom_2975);
CREATE INDEX ON algo3_touch (idu);
ANALYZE algo3_touch"""),

("features", """
DROP TABLE IF EXISTS algo3_voisinage;
CREATE TABLE algo3_voisinage AS
WITH years(annee) AS (VALUES (2017),(2018),(2019),(2020),(2021),(2022),(2023),(2024),(2025),(2026)),
win AS (SELECT annee, make_date(annee,1,1) AS asof,
               greatest(make_date(annee-2,1,1), DATE '2014-01-01') AS w24,
               greatest(make_date(annee-3,1,1), DATE '2014-01-01') AS w36 FROM years),
mut AS (
  SELECT pm.idu, w.annee,
    count(DISTINCT pm.id_mutation) FILTER (WHERE pm.dist<=50  AND pm.date_mutation>=w.w24) AS v50_24,
    count(DISTINCT pm.id_mutation) FILTER (WHERE pm.dist<=100 AND pm.date_mutation>=w.w24) AS v100_24,
    count(DISTINCT pm.id_mutation) FILTER (WHERE pm.date_mutation>=w.w24)                  AS v200_24,
    count(DISTINCT pm.id_mutation) FILTER (WHERE pm.dist<=100 AND pm.date_mutation>=w.w36) AS v100_36,
    max(pm.date_mutation) FILTER (WHERE pm.dist<=100)                                      AS last100
  FROM algo3_pairs_mut pm CROSS JOIN win w
  WHERE pm.date_mutation < w.asof
  GROUP BY pm.idu, w.annee),
per AS (
  SELECT pp.idu, w.annee,
    count(DISTINCT pp.permit_id) FILTER (WHERE pp.dist<=100 AND pp.date_autorisation>=w.w24) AS p100_24,
    count(DISTINCT pp.permit_id) FILTER (WHERE pp.date_autorisation>=w.w36)                  AS p200_36,
    min(pp.dist) FILTER (WHERE pp.date_autorisation>=w.w24)                                  AS dmin_p24
  FROM algo3_pairs_permis pp CROSS JOIN win w
  WHERE pp.date_autorisation < w.asof
  GROUP BY pp.idu, w.annee),
vm AS (
  SELECT t.idu, w.annee, true AS voisin_mute_36
  FROM algo3_touch t
  JOIN p_model_ext_mut_l2 m ON m.idu = t.idu_voisin AND NOT m.exclue_l2f
  CROSS JOIN win w
  WHERE m.date_mutation < w.asof AND m.date_mutation >= w.w36
  GROUP BY t.idu, w.annee),
nv AS (SELECT idu, count(*) AS nb_voisins FROM algo3_touch GROUP BY idu),
rot AS (SELECT idu, annee, coalesce(rot_nu_brute,0)+coalesce(rot_bati_brute,0) AS rot_secteur
        FROM p_model_ext_dataset)
SELECT c.idu, w.annee,
  CASE WHEN d.n50  > 0 THEN coalesce(mut.v50_24 ,0)::float / d.n50  END AS ventes_50m_24m,
  CASE WHEN d.n100 > 0 THEN coalesce(mut.v100_24,0)::float / d.n100 END AS ventes_100m_24m,
  CASE WHEN d.n200 > 0 THEN coalesce(mut.v200_24,0)::float / d.n200 END AS ventes_200m_24m,
  CASE WHEN mut.last100 IS NOT NULL
       THEN (w.asof - mut.last100::date) / 30.44 END                    AS delai_derniere_vente_voisine,
  CASE WHEN d.n100 > 0 THEN coalesce(per.p100_24,0)::float / d.n100 END AS permis_100m_24m,
  CASE WHEN d.n200 > 0 THEN coalesce(per.p200_36,0)::float / d.n200 END AS permis_200m_36m,
  per.dmin_p24                                                          AS distance_permis_recent,
  coalesce(vm.voisin_mute_36, false)                                    AS voisin_direct_mute_36m,
  coalesce(nv.nb_voisins, 0)                                            AS nb_voisins_directs,
  CASE WHEN d.n100 > 0
       THEN coalesce(mut.v100_36,0)::float / d.n100 / 3.0 * 1.0
            - coalesce(r.rot_secteur, 0) END                            AS ecart_rotation_local_secteur
FROM algo3_c c
CROSS JOIN win w
LEFT JOIN algo3_dens d ON d.idu = c.idu
LEFT JOIN mut ON mut.idu = c.idu AND mut.annee = w.annee
LEFT JOIN per ON per.idu = c.idu AND per.annee = w.annee
LEFT JOIN vm  ON vm.idu  = c.idu AND vm.annee  = w.annee
LEFT JOIN nv  ON nv.idu  = c.idu
LEFT JOIN rot r ON r.idu = c.idu AND r.annee = w.annee;
CREATE UNIQUE INDEX ON algo3_voisinage (idu, annee);
ANALYZE algo3_voisinage"""),
]


def main() -> int:
    eng = create_engine(DB)
    times = {}
    for name, sql in STEPS:
        t0 = time.time()
        with eng.begin() as cx:
            for stmt in sql.split(";"):
                if stmt.strip():
                    cx.execute(text(stmt))
        times[name] = round(time.time() - t0, 1)
        print(f"  {name}: {times[name]}s", flush=True)
    with eng.connect() as cx:
        print("── COUVERTURE (POINT D'ARRÊT A) ──", flush=True)
        for q, lbl in [
            ("SELECT count(*) FROM algo3_pairs_mut", "paires cible↔mutation ≤200 m"),
            ("SELECT count(*) FROM algo3_pairs_permis", "paires cible↔permis ≤200 m"),
            ("SELECT count(*) FROM algo3_touch", "paires mitoyennes"),
            ("""SELECT round(avg(n50)),round(avg(n100)),round(avg(n200)),
                 count(*) FILTER (WHERE n100=0) FROM algo3_dens""", "voisins moy 50/100/200 + isolées(100m)"),
            ("""SELECT annee,
                 count(*) FILTER (WHERE ventes_100m_24m IS NULL) AS dens0,
                 count(*) FILTER (WHERE ventes_100m_24m = 0) AS zero_vente,
                 count(*) FILTER (WHERE ventes_100m_24m > 0) AS avec_ventes,
                 count(*) FILTER (WHERE voisin_direct_mute_36m) AS mitoyen_mute,
                 round(avg(nb_voisins_directs),1) AS nb_vois_moy
               FROM algo3_voisinage WHERE annee IN (2020,2025) GROUP BY annee ORDER BY annee""",
             "répartition 2020/2025"),
        ]:
            rows = cx.execute(text(q)).all()
            print(f"  {lbl}: {[tuple(r) for r in rows]}", flush=True)
    print(f"TEMPS TOTAL: {sum(times.values()):.0f}s · détail {times}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
