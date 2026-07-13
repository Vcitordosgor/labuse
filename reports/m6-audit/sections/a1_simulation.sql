-- M6 §1.3b — Anomalie A1 : simulation LECTURE SEULE du dédoublonnage plu_gpu_zone
-- Reproduit la sémantique de la cascade (cascade/context.py prime + layers/phase1.py PluZoneLayer) :
--   coverage = aire(∩)/aire(parcelle), rows cov>0, an_cov = min(1, Σ cov classe A/N),
--   HARD_EXCLUDE si an_cov ≥ 0.90 ; mixte si uau présent et an_cov ≥ 0.05.
-- Dédoublonnage simulé : DISTINCT ON (parcelle, md5(geom)) — aucune écriture.
-- Exécution : psql --csv -q -f a1_simulation.sql > 1-3b-a1-parcelles-affectees.csv
WITH dup AS (
  SELECT md5(ST_AsBinary(geom)) AS h, array_agg(id ORDER BY id) AS ids
  FROM spatial_layers WHERE kind='plu_gpu_zone'
  GROUP BY 1 HAVING count(*) > 1
),
excess AS (SELECT unnest(ids[2:]) AS id FROM dup),
aff AS (
  SELECT DISTINCT p.id
  FROM parcels p
  JOIN spatial_layers sl ON sl.id IN (SELECT id FROM excess)
   AND ST_Intersects(p.geom_2975, sl.geom_2975)
  WHERE ST_Area(ST_Intersection(p.geom_2975, sl.geom_2975)) > 0
),
b AS (SELECT p.id, p.idu, p.geom_2975 FROM parcels p JOIN aff ON aff.id = p.id),
parts AS (
  SELECT sl.id AS lid, sl.subtype, md5(ST_AsBinary(sl.geom)) AS h,
         ST_Subdivide(sl.geom_2975, 256) AS g
  FROM spatial_layers sl WHERE sl.kind = 'plu_gpu_zone'
),
inter AS (
  SELECT b.id AS pid, parts.lid, parts.subtype, parts.h,
         SUM(ST_Area(ST_Intersection(b.geom_2975, parts.g)))
           / NULLIF(MAX(ST_Area(b.geom_2975)), 0) AS cov
  FROM b JOIN parts ON ST_Intersects(b.geom_2975, parts.g)
  GROUP BY b.id, parts.lid, parts.subtype, parts.h
),
inter2 AS (
  SELECT pid, lid, h, cov, trim(coalesce(subtype,'')) AS lib,
         CASE WHEN upper(trim(coalesce(subtype,''))) LIKE 'U%'
                OR upper(trim(coalesce(subtype,''))) LIKE 'AU%' THEN 'uau'
              WHEN upper(trim(coalesce(subtype,''))) LIKE 'A%'
                OR upper(trim(coalesce(subtype,''))) LIKE 'N%' THEN 'an'
              ELSE 'autre' END AS cl
  FROM inter WHERE cov > 0
),
ded AS (SELECT DISTINCT ON (pid, h) pid, lid, h, cov, lib, cl FROM inter2 ORDER BY pid, h, lid),
agg_raw AS (
  SELECT pid, count(*) AS n_zones,
         SUM(cov) AS total_cov,
         LEAST(1.0, COALESCE(SUM(cov) FILTER (WHERE cl='an'), 0))  AS an_cov,
         LEAST(1.0, COALESCE(SUM(cov) FILTER (WHERE cl='uau'), 0)) AS uau_cov,
         bool_or(cl='an') AS has_an, bool_or(cl='uau') AS has_uau
  FROM inter2 GROUP BY pid
),
dom_raw AS (
  SELECT DISTINCT ON (pid) pid, lib AS dom
  FROM (SELECT pid, lib, SUM(cov) AS c FROM inter2 GROUP BY pid, lib) s
  ORDER BY pid, c DESC
),
agg_ded AS (
  SELECT pid, count(*) AS n_zones,
         SUM(cov) AS total_cov,
         LEAST(1.0, COALESCE(SUM(cov) FILTER (WHERE cl='an'), 0))  AS an_cov,
         LEAST(1.0, COALESCE(SUM(cov) FILTER (WHERE cl='uau'), 0)) AS uau_cov,
         bool_or(cl='an') AS has_an, bool_or(cl='uau') AS has_uau
  FROM ded GROUP BY pid
),
dom_ded AS (
  SELECT DISTINCT ON (pid) pid, lib AS dom
  FROM (SELECT pid, lib, SUM(cov) AS c FROM ded GROUP BY pid, lib) s
  ORDER BY pid, c DESC
),
verdicts AS (
  SELECT r.pid,
    r.n_zones AS n_zones_raw, d.n_zones AS n_zones_dedup,
    r.total_cov AS total_raw, d.total_cov AS total_dedup,
    r.an_cov AS an_raw, d.an_cov AS an_dedup,
    r.uau_cov AS uau_raw, d.uau_cov AS uau_dedup,
    dr.dom AS dom_raw, dd.dom AS dom_dedup,
    CASE WHEN r.has_an AND r.an_cov >= 0.9 THEN 'HARD_EXCLUDE'
         WHEN r.has_uau AND r.has_an AND r.an_cov >= 0.05 THEN 'POSITIVE_mixte'
         WHEN r.has_uau THEN 'POSITIVE'
         WHEN r.has_an THEN 'SOFT_FLAG_partiel'
         ELSE 'PASS_autre' END AS verdict_raw,
    CASE WHEN d.has_an AND d.an_cov >= 0.9 THEN 'HARD_EXCLUDE'
         WHEN d.has_uau AND d.has_an AND d.an_cov >= 0.05 THEN 'POSITIVE_mixte'
         WHEN d.has_uau THEN 'POSITIVE'
         WHEN d.has_an THEN 'SOFT_FLAG_partiel'
         ELSE 'PASS_autre' END AS verdict_dedup
  FROM agg_raw r
  JOIN agg_ded d USING (pid)
  JOIN dom_raw dr USING (pid) JOIN dom_ded dd USING (pid)
)
SELECT p.idu, p.commune,
       m.status, m.tier_v2, m.rang_v2, m.etage0,
       v.n_zones_raw, v.n_zones_dedup,
       round(v.total_raw::numeric*100, 1)  AS total_cov_raw_pct,
       round(v.total_dedup::numeric*100, 1) AS total_cov_dedup_pct,
       round(v.an_raw::numeric*100, 1)  AS an_cov_raw_pct,
       round(v.an_dedup::numeric*100, 1) AS an_cov_dedup_pct,
       round(v.uau_raw::numeric*100, 1)  AS uau_cov_raw_pct,
       round(v.uau_dedup::numeric*100, 1) AS uau_cov_dedup_pct,
       v.dom_raw AS zone_majoritaire_raw, v.dom_dedup AS zone_majoritaire_dedup,
       v.verdict_raw, v.verdict_dedup,
       (v.verdict_raw = 'HARD_EXCLUDE' AND v.verdict_dedup <> 'HARD_EXCLUDE') AS hard_exclude_infonde,
       (v.dom_raw <> v.dom_dedup) AS zone_majoritaire_change,
       (v.verdict_raw <> v.verdict_dedup) AS verdict_change
FROM verdicts v
JOIN parcels p ON p.id = v.pid
LEFT JOIN mvt_parcels m ON m.id = v.pid
ORDER BY (v.verdict_raw <> v.verdict_dedup) DESC, (v.dom_raw <> v.dom_dedup) DESC, p.idu;
