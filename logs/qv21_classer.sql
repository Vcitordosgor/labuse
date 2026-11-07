\pset pager off

\echo '=== (1) q_v20 NOT q_v21 (2919) : classees par etat cadastre ACTUEL ==='
WITH perdu AS (
  SELECT s.parcelle_id
  FROM parcel_p_score_v2 s
  WHERE s.run_id='q_v20'
    AND NOT EXISTS (SELECT 1 FROM parcel_p_score_v2 b WHERE b.run_id='q_v21' AND b.parcelle_id=s.parcelle_id)
)
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE p.idu IS NULL) AS absente_de_parcels,
  count(*) FILTER (WHERE p.cadastre_disparue_le IS NOT NULL) AS disparue_datee,
  count(*) FILTER (WHERE p.idu IS NOT NULL AND p.cadastre_disparue_le IS NULL) AS vivante
FROM perdu x LEFT JOIN parcels p ON p.idu = x.parcelle_id;

\echo '=== (2) q_v21 NOT q_v20 (1353) : classees par etat cadastre ACTUEL ==='
WITH gagne AS (
  SELECT s.parcelle_id
  FROM parcel_p_score_v2 s
  WHERE s.run_id='q_v21'
    AND NOT EXISTS (SELECT 1 FROM parcel_p_score_v2 a WHERE a.run_id='q_v20' AND a.parcelle_id=s.parcelle_id)
)
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE p.idu IS NULL) AS absente_de_parcels,
  count(*) FILTER (WHERE p.cadastre_disparue_le IS NOT NULL) AS disparue_datee,
  count(*) FILTER (WHERE p.idu IS NOT NULL AND p.cadastre_disparue_le IS NULL) AS vivante
FROM gagne x LEFT JOIN parcels p ON p.idu = x.parcelle_id;

\echo '=== (3) LE SET CLE : cadastre VIVANT (disparue_le NULL) non score q_v21 (2919) par etat ==='
WITH manque AS (
  SELECT p.idu, p.commune, p.cadastre_disparue_le, p.contenance_m2, p.origine
  FROM parcels p
  WHERE p.cadastre_disparue_le IS NULL
    AND NOT EXISTS (SELECT 1 FROM parcel_p_score_v2 s WHERE s.run_id='q_v21' AND s.parcelle_id=p.idu)
)
SELECT
  count(*) AS vivantes_sans_qv21,
  count(*) FILTER (WHERE EXISTS (SELECT 1 FROM parcel_p_score_v2 a WHERE a.run_id='q_v20' AND a.parcelle_id=manque.idu)) AS dont_etaient_en_qv20,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM parcel_p_score_v2 a WHERE a.run_id='q_v20' AND a.parcelle_id=manque.idu)) AS dont_jamais_en_qv20
FROM manque;

\echo '=== (3b) repartition par commune des vivantes sans qv21 (top 15) ==='
WITH manque AS (
  SELECT p.idu, p.commune
  FROM parcels p
  WHERE p.cadastre_disparue_le IS NULL
    AND NOT EXISTS (SELECT 1 FROM parcel_p_score_v2 s WHERE s.run_id='q_v21' AND s.parcelle_id=p.idu)
)
SELECT commune, count(*) AS n FROM manque GROUP BY commune ORDER BY n DESC LIMIT 15;

\echo '=== (4) les 1353 q_v21-not-q_v20 : sont-elles les disparues ? recoupement ==='
WITH gagne AS (
  SELECT s.parcelle_id FROM parcel_p_score_v2 s
  WHERE s.run_id='q_v21'
    AND NOT EXISTS (SELECT 1 FROM parcel_p_score_v2 a WHERE a.run_id='q_v20' AND a.parcelle_id=s.parcelle_id)
)
SELECT count(*) AS gagne_total,
       count(*) FILTER (WHERE p.cadastre_disparue_le IS NOT NULL) AS gagne_et_disparue
FROM gagne g LEFT JOIN parcels p ON p.idu=g.parcelle_id;
