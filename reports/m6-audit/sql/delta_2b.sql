-- M6 Phase 2b — DELTA q_v4_m6a → q_v5_m6b (A-02 dédoublonnage PLU + A-03 zones e Saint-Paul)
-- Par parcelle : statut, étage 0, motif. SELECT pur, à lancer après la fin du run q_v5_m6b.
WITH avant AS (
  SELECT p.idu, p.commune, d.status, (d.status IN ('exclue','faux_positif_probable')) AS etage0
  FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
  WHERE d.run_label = 'q_v4_m6a'),
apres AS (
  SELECT p.idu, d.status, (d.status IN ('exclue','faux_positif_probable')) AS etage0,
         EXISTS (SELECT 1 FROM dryrun_cascade_results cr
                 WHERE cr.parcel_id = d.parcel_id AND cr.run_label = 'q_v5_m6b'
                   AND cr.layer_name = 'zonage_plu_gpu' AND cr.result = 'HARD_EXCLUDE'
                   AND cr.detail LIKE '%vocation économique%') AS excl_eco_a03
  FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
  WHERE d.run_label = 'q_v5_m6b')
SELECT 'total_change_statut' AS indicateur, count(*)::text AS valeur
FROM avant a JOIN apres b USING (idu) WHERE a.status IS DISTINCT FROM b.status
UNION ALL
SELECT 'entrees_etage0', count(*)::text FROM avant a JOIN apres b USING (idu) WHERE NOT a.etage0 AND b.etage0
UNION ALL
SELECT 'sorties_etage0 (A-02 : HE zonage infondés sans autre exclusion)', count(*)::text
FROM avant a JOIN apres b USING (idu) WHERE a.etage0 AND NOT b.etage0
UNION ALL
SELECT 'exclusions_a03_vocation_eco', count(*)::text FROM apres WHERE excl_eco_a03;
-- export par parcelle (à \copy vers le review pack)
