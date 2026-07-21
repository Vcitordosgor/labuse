-- =====================================================================================
-- PURGE DES RUNS OBSOLÈTES — antérieurs à q_v6_m8 (Nuit 2026-07-21, lot N7)
-- =====================================================================================
-- ⚠ PRÊT, NON EXÉCUTÉ. L'exécution est une DÉCISION DE VIC, un autre jour.
--
-- Cible : les runs SERVIS obsolètes ANTÉRIEURS à q_v6_m8 :
--     q_v2 · q_v3_datagap · q_v4_m6a · q_v5_m6b
-- CONSERVÉS (ne pas toucher) :
--     q_v6_m8      → HYSTÉRÉSIS (rollback du run servi)
--     q_v7_defisc  → SERVI (champion courant)
-- HORS PÉRIMÈTRE de cette purge (ni antérieurs, ni servis — décision séparée) :
--     q_v6_m8_Vdefisc, q_v7_defisc_Vcaduc (challengers d'audit) ;
--     baseline, etape1, etape1b, etape2, p1_gardes, q_v2_demo (runs dry-run de matrice/dev).
--
-- Ces 4 runs n'existent QUE dans dryrun_cascade_results et dryrun_parcel_evaluations
-- (absents de parcel_p_score_v2 / p_score_v2_runs — ils précèdent la table de score v2).
--
-- CE QUE ÇA LIBÈRE (mesuré le 2026-07-21) :
--   dryrun_cascade_results    : 56 661 904 lignes  (61,0 % de 92,9 M)  ≈ ~11 Go de 18 Go
--   dryrun_parcel_evaluations :  1 726 652 lignes  (46,6 % de 3,7 M)   ≈ ~367 Mo de 788 Mo
--   → ~11,3 Go récupérés APRÈS VACUUM (le DELETE seul ne rend pas l'espace disque).
--
-- SÉCURITÉ : exécuté dans une transaction qui ROLLBACK par défaut. Pour appliquer réellement,
-- remplacer « ROLLBACK; » final par « COMMIT; » (décision explicite), puis lancer les VACUUM.
-- Zones gelées : ne touche NI q_v6_m8, NI q_v7_defisc, NI parcel_p_score_v2, NI le modèle P.
-- =====================================================================================

\set ON_ERROR_STOP on

BEGIN;

-- 1) Vérification AVANT (doit lister exactement les 4 runs cibles et leurs volumes)
SELECT run_label, count(*) AS lignes
FROM dryrun_cascade_results
WHERE run_label IN ('q_v2', 'q_v3_datagap', 'q_v4_m6a', 'q_v5_m6b')
GROUP BY run_label ORDER BY run_label;

-- 2) Purge (additive → destructive : d'où la transaction ROLLBACK par défaut)
DELETE FROM dryrun_cascade_results
WHERE run_label IN ('q_v2', 'q_v3_datagap', 'q_v4_m6a', 'q_v5_m6b');

DELETE FROM dryrun_parcel_evaluations
WHERE run_label IN ('q_v2', 'q_v3_datagap', 'q_v4_m6a', 'q_v5_m6b');

-- 3) Contrôle APRÈS (les runs conservés doivent être intacts)
SELECT run_label, count(*) AS lignes
FROM dryrun_parcel_evaluations
WHERE run_label IN ('q_v6_m8', 'q_v7_defisc')
GROUP BY run_label ORDER BY run_label;

-- ⚠ PAR DÉFAUT ON ANNULE. Remplacer par COMMIT; pour appliquer (décision Vic).
ROLLBACK;

-- 4) APRÈS un COMMIT réel, récupérer l'espace disque (hors transaction) :
--    VACUUM (FULL, ANALYZE) dryrun_cascade_results;
--    VACUUM (FULL, ANALYZE) dryrun_parcel_evaluations;
--    (VACUUM FULL prend un verrou exclusif + réécrit la table — fenêtre de maintenance.)
