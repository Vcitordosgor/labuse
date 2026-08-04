-- TRAIN 1 — analyse de la mesure à blanc pondération (lecture seule).
-- AVANT = q_v9_pond_avant (pond OFF, contrôle) · APRÈS = q_v9_pond_apres (pond ON).

\echo '=== 0. DÉRIVE contrôle : q_v8_calibre vs AVANT (attendu ≈ 0 mouvement) ==='
SELECT count(*) FILTER (WHERE a.tier IS DISTINCT FROM s.tier) AS tiers_differents,
       count(*) AS total
FROM parcel_p_score_v2 s
JOIN parcel_p_score_v2 a ON a.parcelle_id=s.parcelle_id AND a.run_id='q_v9_pond_avant'
WHERE s.run_id='q_v8_calibre';

\echo '=== 1. MATRICE de mouvements AVANT → APRÈS (toutes parcelles) ==='
SELECT a.tier AS avant, b.tier AS apres, count(*)
FROM parcel_p_score_v2 a
JOIN parcel_p_score_v2 b ON b.parcelle_id=a.parcelle_id AND b.run_id='q_v9_pond_apres'
WHERE a.run_id='q_v9_pond_avant' AND a.tier IS DISTINCT FROM b.tier
GROUP BY 1,2 ORDER BY count(*) DESC;

\echo '=== 2. Population au_sous_plancher : mouvements par commune ==='
WITH pop AS (SELECT a2.idu FROM parcel_au_statut a2 WHERE a2.classe='au_sous_plancher')
SELECT p.commune,
       count(*) AS sous_plancher,
       count(*) FILTER (WHERE a.tier IS DISTINCT FROM b.tier) AS bougees,
       count(*) FILTER (WHERE a.tier IN ('brulante','chaude') AND b.tier NOT IN ('brulante','chaude')) AS sorties_de_tete,
       string_agg(DISTINCT a.tier || '→' || b.tier, ', ') FILTER (WHERE a.tier IS DISTINCT FROM b.tier) AS types
FROM pop JOIN parcels p ON p.idu=pop.idu
JOIN parcel_p_score_v2 a ON a.parcelle_id=pop.idu AND a.run_id='q_v9_pond_avant'
JOIN parcel_p_score_v2 b ON b.parcelle_id=pop.idu AND b.run_id='q_v9_pond_apres'
GROUP BY 1 ORDER BY bougees DESC;

\echo '=== 3. MOUVEMENTS EN TÊTE (brûlante/chaude concernées, toutes causes) ==='
SELECT a.parcelle_id AS idu, p.commune, a.tier AS avant, b.tier AS apres,
       a.rang AS rang_avant, b.rang AS rang_apres,
       (SELECT classe FROM parcel_au_statut x WHERE x.idu=a.parcelle_id) AS au_statut
FROM parcel_p_score_v2 a
JOIN parcel_p_score_v2 b ON b.parcelle_id=a.parcelle_id AND b.run_id='q_v9_pond_apres'
JOIN parcels p ON p.idu=a.parcelle_id
WHERE a.run_id='q_v9_pond_avant' AND a.tier IS DISTINCT FROM b.tier
  AND (a.tier IN ('brulante','chaude') OR b.tier IN ('brulante','chaude'))
ORDER BY LEAST(COALESCE(a.rang,999999), COALESCE(b.rang,999999));

\echo '=== 4. CX2555 : où la pondération la classe NATURELLEMENT ==='
SELECT run_id, tier, rang, percentile, round(p_raw::numeric,6) AS p_raw
FROM parcel_p_score_v2
WHERE parcelle_id='97413000CX2555' AND run_id IN ('q_v8_calibre','q_v9_pond_avant','q_v9_pond_apres')
ORDER BY run_id;

\echo '=== 5. Effectifs de tiers AVANT vs APRÈS (santé du run) ==='
SELECT run_id, tier, count(*) FROM parcel_p_score_v2
WHERE run_id IN ('q_v9_pond_avant','q_v9_pond_apres')
GROUP BY 1,2 ORDER BY 2,1;
