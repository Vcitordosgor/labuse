\pset pager off
\echo '=========================================================='
\echo 'CONTROLE COMPTES — q_v21 vs UNIVERS SERVI DU CADASTRE ACTUEL'
\echo '=========================================================='
\echo '--- univers vivant servi (parcels, cadastre_disparue_le NULL) ---'
SELECT count(*) AS univers_vivant FROM parcels WHERE cadastre_disparue_le IS NULL;

\echo '--- q_v21 : total / vivantes / disparues portees ---'
SELECT
  count(*) AS qv21_total,
  count(*) FILTER (WHERE p.cadastre_disparue_le IS NULL) AS qv21_vivantes,
  count(*) FILTER (WHERE p.cadastre_disparue_le IS NOT NULL) AS qv21_disparues_portees,
  count(*) FILTER (WHERE p.idu IS NULL) AS qv21_absentes_cadastre
FROM parcel_p_score_v2 s LEFT JOIN parcels p ON p.idu = s.parcelle_id
WHERE s.run_id='q_v21';

\echo '--- ECART 1 : VIVANTES SERVIES NON SCOREES q_v21 (a noter) = deficit vs univers ---'
WITH manque AS (
  SELECT p.idu, p.commune FROM parcels p
  WHERE p.cadastre_disparue_le IS NULL
    AND NOT EXISTS (SELECT 1 FROM parcel_p_score_v2 s WHERE s.run_id='q_v21' AND s.parcelle_id=p.idu)
)
SELECT count(*) AS vivantes_non_scorees,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM parcel_p_score_v2 a WHERE a.run_id='q_v20' AND a.parcelle_id=manque.idu)) AS dont_servies_qv20
FROM manque;

\echo '--- ECART 2 : DISPARUES PORTEES PAR q_v21 (normales, hors univers vivant) ---'
SELECT count(*) AS disparues_portees, p.cadastre_disparue_le
FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id
WHERE s.run_id='q_v21' AND p.cadastre_disparue_le IS NOT NULL
GROUP BY p.cadastre_disparue_le;

\echo '--- SYNTHESE : couverture vivante q_v21 ---'
WITH u AS (SELECT count(*) n FROM parcels WHERE cadastre_disparue_le IS NULL),
     c AS (SELECT count(*) n FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id
           WHERE s.run_id='q_v21' AND p.cadastre_disparue_le IS NULL)
SELECT u.n AS univers_vivant, c.n AS qv21_couvre_vivant, u.n-c.n AS deficit,
       round(100.0*c.n/u.n,3) AS couverture_pct FROM u,c;

\echo '--- commune des 2919 vivantes non scorees (toutes) ---'
\copy (WITH manque AS (SELECT p.idu, p.commune FROM parcels p WHERE p.cadastre_disparue_le IS NULL AND NOT EXISTS (SELECT 1 FROM parcel_p_score_v2 s WHERE s.run_id='q_v21' AND s.parcelle_id=p.idu)) SELECT idu, commune FROM manque ORDER BY idu) TO '/tmp/qv21_2919_vivantes_a_noter.csv' WITH CSV HEADER

\echo '--- liste des 1353 disparues portees ---'
\copy (SELECT s.parcelle_id AS idu, p.commune, p.cadastre_disparue_le FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id WHERE s.run_id='q_v21' AND p.cadastre_disparue_le IS NOT NULL ORDER BY s.parcelle_id) TO '/tmp/qv21_1353_disparues.csv' WITH CSV HEADER

\echo 'listes ecrites dans /tmp.'
