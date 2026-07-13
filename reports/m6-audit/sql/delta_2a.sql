-- M6 Phase 2a — DELTA q_v3_datagap → q_v4_m6a (par parcelle : statut, étage 0, motif A-01)
-- À lancer après la fin du run île q_v4_m6a. SELECT pur.
WITH avant AS (
  SELECT p.idu, p.commune, d.status, d.matrice_statut,
         (d.status IN ('exclue','faux_positif_probable')) AS etage0
  FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
  WHERE d.run_label = 'q_v3_datagap'),
apres AS (
  SELECT p.idu, d.status, d.matrice_statut,
         (d.status IN ('exclue','faux_positif_probable')) AS etage0,
         EXISTS (SELECT 1 FROM dryrun_cascade_results cr
                 WHERE cr.parcel_id = d.parcel_id AND cr.run_label = 'q_v4_m6a'
                   AND cr.layer_name = 'emprise_routiere' AND cr.result = 'HARD_EXCLUDE') AS excl_routiere,
         EXISTS (SELECT 1 FROM dryrun_cascade_results cr
                 WHERE cr.parcel_id = d.parcel_id AND cr.run_label = 'q_v4_m6a'
                   AND cr.layer_name = 'emprise_routiere' AND cr.result = 'SOFT_FLAG') AS flag_delaisse_prive
  FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
  WHERE d.run_label = 'q_v4_m6a')
SELECT 'total_change_statut' AS indicateur, count(*)::text AS valeur
FROM avant a JOIN apres b USING (idu) WHERE a.status IS DISTINCT FROM b.status
UNION ALL
SELECT 'entrees_etage0', count(*)::text FROM avant a JOIN apres b USING (idu) WHERE NOT a.etage0 AND b.etage0
UNION ALL
SELECT 'sorties_etage0', count(*)::text FROM avant a JOIN apres b USING (idu) WHERE a.etage0 AND NOT b.etage0
UNION ALL
SELECT 'exclusions_emprise_routiere', count(*)::text FROM apres WHERE excl_routiere
UNION ALL
SELECT 'delaisses_prives_flagués', count(*)::text FROM apres WHERE flag_delaisse_prive;
