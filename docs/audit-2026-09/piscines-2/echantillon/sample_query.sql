\set QUIET on
SET statement_timeout='240s';
CREATE TEMP TABLE _flair AS
  SELECT id, geom_2975, confiance FROM ortho_detections
  WHERE type='piscine' AND (validation='ok' OR (validation IS NULL AND juge_flair>=0.30 AND probe_score>=0.50));
CREATE INDEX ON _flair USING gist(geom_2975);
CREATE TEMP TABLE _cos AS
  SELECT ctid AS cid, subtype, (attrs->>'surface_m2')::numeric AS surf, geom_2975,
    EXISTS(SELECT 1 FROM _flair f WHERE ST_DWithin(f.geom_2975, tuyau_piscines.geom_2975, 5)) AS has_flair
  FROM tuyau_piscines;
CREATE TEMP TABLE _samp AS
WITH
f AS (SELECT id::text key, geom_2975, confiance surf, 'flair' src, confiance,
        CASE WHEN confiance>=0.80 THEN '1_FLAIR_haute' ELSE '2_FLAIR_incertaine' END cls FROM _flair),
c AS (SELECT cid::text key, geom_2975, surf, 'cosia' src, NULL::numeric confiance,
        CASE
          WHEN subtype='confirmee' AND has_flair THEN '3_CoSIA_conf_avecFLAIR'
          WHEN subtype='confirmee' AND NOT has_flair THEN '4_CoSIA_conf_sansFLAIR'
          WHEN subtype='rare' AND NOT has_flair THEN '5_CoSIA_rare_sansFLAIR'
          WHEN subtype='probable' AND surf>=8 AND NOT has_flair THEN '6_CoSIA_prob_ge8_sansFLAIR'
          WHEN subtype='probable' AND surf<8 THEN '7_CoSIA_prob_lt8'
          ELSE NULL END cls FROM _cos),
u AS (SELECT * FROM f UNION ALL SELECT * FROM c),
r AS (SELECT cls, key, src, round(surf::numeric,1) surf_m2,
        round(ST_X(ST_Centroid(ST_Transform(geom_2975,4326)))::numeric,6) lon,
        round(ST_Y(ST_Centroid(ST_Transform(geom_2975,4326)))::numeric,6) lat,
        row_number() OVER (PARTITION BY cls ORDER BY md5(key||'p2seed7')) rn
      FROM u WHERE cls IS NOT NULL)
SELECT cls, rn, key, src, surf_m2, lon, lat FROM r WHERE rn<=30 ORDER BY cls, rn;
\copy (SELECT cls,rn,key,src,surf_m2,lon,lat FROM _samp ORDER BY cls,rn) TO '/tmp/piscines_sample.csv' WITH CSV HEADER
SELECT cls, count(*) FROM _samp GROUP BY cls ORDER BY cls;
