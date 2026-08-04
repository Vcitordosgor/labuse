-- Étape 2 — mouvements servi (q_v8_calibre) → q_v11_regle_apres (max emprise)
\echo '=== matrice de mouvements ==='
SELECT a.tier avant, b.tier apres, count(*)
FROM parcel_p_score_v2 a
JOIN parcel_p_score_v2 b ON b.parcelle_id=a.parcelle_id AND b.run_id='q_v11_regle_apres'
WHERE a.run_id='q_v8_calibre' AND a.tier IS DISTINCT FROM b.tier
GROUP BY 1,2 ORDER BY 3 DESC LIMIT 15;
\echo '=== sorties de tête ==='
SELECT count(*) FILTER (WHERE a.tier='brulante' AND b.tier NOT IN ('brulante','chaude')) brul_sorties,
       count(*) FILTER (WHERE a.tier='chaude' AND b.tier NOT IN ('brulante','chaude')) chaudes_sorties,
       count(*) FILTER (WHERE a.tier NOT IN ('brulante','chaude') AND b.tier IN ('brulante','chaude')) entrees
FROM parcel_p_score_v2 a
JOIN parcel_p_score_v2 b ON b.parcelle_id=a.parcelle_id AND b.run_id='q_v11_regle_apres'
WHERE a.run_id='q_v8_calibre';
\echo '=== LE SORT DES REVELEES : les 346 têtes à emprise révélée >20 — où vont-elles ? ==='
WITH rev AS (
  SELECT a.parcelle_id idu, a.tier avant
  FROM parcel_p_score_v2 a
  LEFT JOIN p_model_bati bb ON bb.idu=a.parcelle_id
  JOIN p_model_bati_cosia c ON c.idu=a.parcelle_id
  WHERE a.run_id='q_v8_calibre' AND a.tier IN ('brulante','chaude')
    AND COALESCE(bb.emprise_bati_m2,0) < 20 AND c.emprise_cosia_m2 > 20)
SELECT r.avant, b.tier apres, count(*)
FROM rev r JOIN parcel_p_score_v2 b ON b.parcelle_id=r.idu AND b.run_id='q_v11_regle_apres'
GROUP BY 1,2 ORDER BY 1,3 DESC;
\echo '=== effectifs finaux ==='
SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id='q_v11_regle_apres' GROUP BY 1 ORDER BY 2;
\echo '=== les 17 ex-exceptions dans q_v11 (attendu : declasse_bati_revele) ==='
SELECT b.tier, count(*) FROM served_run_exceptions e
JOIN parcel_p_score_v2 b ON b.parcelle_id=e.idu AND b.run_id='q_v11_regle_apres'
WHERE e.run_id='q_v8_calibre' GROUP BY 1;
\echo '=== ENTRANTES en tête par recomposition (jamais revues) ==='
SELECT a.tier avant, b.tier apres, count(*)
FROM parcel_p_score_v2 a
JOIN parcel_p_score_v2 b ON b.parcelle_id=a.parcelle_id AND b.run_id='q_v11_regle_apres'
WHERE a.run_id='q_v8_calibre' AND a.tier NOT IN ('brulante','chaude')
  AND b.tier IN ('brulante','chaude') GROUP BY 1,2 ORDER BY 3 DESC;
