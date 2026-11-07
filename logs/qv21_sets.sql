\pset pager off
\echo '=== run_ids reels dans parcel_p_score_v2 (q_v2x) ==='
SELECT run_id, count(*) AS n, min(model_version) AS model
FROM parcel_p_score_v2
WHERE run_id LIKE 'q_v2%'
GROUP BY run_id ORDER BY run_id;

\echo '=== metadonnees runs q_v20 / q_v21 ==='
SELECT run_id, model_version, left(model_sha256,16) AS sha, n_parcelles, computed_at
FROM p_score_v2_runs WHERE run_id IN ('q_v20','q_v21') ORDER BY run_id;

\echo '=== A=q_v20, B=q_v21 : tailles et differences symetriques ==='
WITH a AS (SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id='q_v20'),
     b AS (SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id='q_v21')
SELECT
  (SELECT count(*) FROM a) AS n_q_v20,
  (SELECT count(*) FROM b) AS n_q_v21,
  (SELECT count(*) FROM a WHERE parcelle_id NOT IN (SELECT parcelle_id FROM b)) AS a_moins_b,
  (SELECT count(*) FROM b WHERE parcelle_id NOT IN (SELECT parcelle_id FROM a)) AS b_moins_a;

\echo '=== univers cadastre : vivantes vs disparues ==='
SELECT
  count(*) AS parcels_total,
  count(*) FILTER (WHERE cadastre_disparue_le IS NULL) AS vivantes,
  count(*) FILTER (WHERE cadastre_disparue_le IS NOT NULL) AS disparues
FROM parcels;

\echo '=== cadastre VIVANT non score en q_v21 (ce qui compte pour le gate comptes) ==='
SELECT count(*) AS cadastre_vivant_sans_qv21
FROM parcels p
WHERE p.cadastre_disparue_le IS NULL
  AND NOT EXISTS (SELECT 1 FROM parcel_p_score_v2 s WHERE s.run_id='q_v21' AND s.parcelle_id=p.idu);
