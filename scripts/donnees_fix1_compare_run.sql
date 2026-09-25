-- DONNEES-FIX-1 lot C — comparaison run de test (LiDAR) vs run 10 (servi), Saint-Denis.
-- Usage : psql ... -v newrun=11 -f scripts/donnees_fix1_compare_run.sql
\set insee '97411'

-- bande potentiel (input résiduel-driven de q_v15) depuis pct_potentiel
-- fort <40 · modéré 40-70 · faible 70-100 · nul >=100
WITH a AS (
  SELECT parcel_id, sdp_residuelle_m2 s, pct_potentiel p, taux_emprise_pct t
  FROM parcel_residuel_runs WHERE run_seq = 10),
n AS (
  SELECT parcel_id, sdp_residuelle_m2 s, pct_potentiel p, taux_emprise_pct t, hauteur_source
  FROM parcel_residuel_runs WHERE run_seq = :newrun),
j AS (
  SELECT p.idu, a.s s10, n.s s11, a.p p10, n.p p11, n.t t11, n.hauteur_source,
         (n.s - a.s) AS delta
  FROM n JOIN a USING (parcel_id) JOIN parcels p ON p.id = n.parcel_id
  WHERE left(p.idu,5) = :'insee'
    AND a.s IS NOT NULL AND n.s IS NOT NULL     -- disponibles dans les deux runs
    AND (a.t > 0 OR n.t > 0))                    -- bâti
SELECT
  count(*) AS bati_compares,
  count(*) FILTER (WHERE delta < 0) AS restant_baisse,
  count(*) FILTER (WHERE delta > 0) AS restant_monte,
  count(*) FILTER (WHERE delta = 0) AS inchange,
  round(avg(delta) FILTER (WHERE delta < 0)) AS baisse_moy,
  round(percentile_cont(0.5) WITHIN GROUP (ORDER BY delta) FILTER (WHERE delta < 0)) AS baisse_med,
  sum(delta) FILTER (WHERE delta < 0) AS baisse_totale_m2,
  count(*) FILTER (WHERE hauteur_source='lidar') AS src_lidar,
  count(*) FILTER (WHERE hauteur_source='bdtopo') AS src_bdtopo,
  count(*) FILTER (WHERE hauteur_source='sans') AS src_sans
FROM j;

-- changements de bande potentiel
WITH a AS (SELECT parcel_id, pct_potentiel p, taux_emprise_pct t FROM parcel_residuel_runs WHERE run_seq=10),
n AS (SELECT parcel_id, pct_potentiel p, taux_emprise_pct t FROM parcel_residuel_runs WHERE run_seq=:newrun),
b AS (
  SELECT CASE WHEN a.p<40 THEN 'fort' WHEN a.p<70 THEN 'modere' WHEN a.p<100 THEN 'faible' ELSE 'nul' END b10,
         CASE WHEN n.p<40 THEN 'fort' WHEN n.p<70 THEN 'modere' WHEN n.p<100 THEN 'faible' ELSE 'nul' END b11
  FROM n JOIN a USING (parcel_id) JOIN parcels p ON p.id=n.parcel_id
  WHERE left(p.idu,5)=:'insee' AND a.p IS NOT NULL AND n.p IS NOT NULL AND (a.t>0 OR n.t>0))
SELECT count(*) bati, count(*) FILTER (WHERE b10<>b11) AS bande_change,
       round(100.0*count(*) FILTER (WHERE b10<>b11)/count(*),1) AS pct_bande_change
FROM b;

-- 10 plus gros écarts (baisses) avec la hauteur qui les explique
WITH a AS (SELECT parcel_id, sdp_residuelle_m2 s, pct_potentiel p FROM parcel_residuel_runs WHERE run_seq=10),
n AS (SELECT parcel_id, sdp_residuelle_m2 s, pct_potentiel p, hauteur_source FROM parcel_residuel_runs WHERE run_seq=:newrun)
SELECT p.idu, l.egout_m, l.faitage_m, n.hauteur_source,
       a.s AS rest_run10, n.s AS rest_test, (n.s-a.s) AS delta
FROM n JOIN a USING (parcel_id) JOIN parcels p ON p.id=n.parcel_id
LEFT JOIN batiment_hauteur_lidar l ON l.idu=p.idu
WHERE left(p.idu,5)=:'insee' AND a.s IS NOT NULL AND n.s IS NOT NULL
ORDER BY (n.s-a.s) ASC LIMIT 10;
