-- M6 §1.3 — chiffrage LECTURE SEULE : parcelles dont le centroïde tombe dans une zone
-- PLU à vocation économique/activités (candidates par libellé), croisées avec
-- le statut cascade (parcel_evaluations, dernière éval) et le tier p_v2 (run courant).
WITH eco(commune, lib) AS (VALUES
  ('Bras-Panon','Ue'),('Bras-Panon','1AUe'),('Bras-Panon','1AUec'),('Bras-Panon','2AUec'),
  ('Entre-Deux','AUe'),
  ('L''Étang-Salé','UE'),('L''Étang-Salé','AUe'),
  ('La Plaine-des-Palmistes','Ue'),('La Plaine-des-Palmistes','AUe'),
  ('La Possession','UE'),('La Possession','UEm'),('La Possession','AUEm'),
  ('Le Port','Ue'),('Le Port','Uem'),('Le Port','Umi'),('Le Port','1AUe'),('Le Port','1AUem'),('Le Port','2AUem'),
  ('Le Tampon','Ue'),('Le Tampon','1AUe'),('Le Tampon','2AUe'),
  ('Les Avirons','Ue'),('Les Avirons','AUec'),('Les Avirons','AUes'),
  ('Les Trois-Bassins','Ue'),('Les Trois-Bassins','1AUe'),('Les Trois-Bassins','AUse'),
  ('Petite-Île','UE'),('Petite-Île','UEa'),('Petite-Île','UZ'),('Petite-Île','1AUz'),('Petite-Île','2AUe'),('Petite-Île','AUE'),
  ('Saint-André','UE'),('Saint-André','US'),('Saint-André','1AUe'),('Saint-André','2AUe'),
  ('Saint-Benoît','Ue'),('Saint-Benoît','AUe3'),
  ('Saint-Denis','Ui'),('Saint-Denis','Uicm'),('Saint-Denis','Uip'),('Saint-Denis','AUx'),
  ('Saint-Denis','UEa'),('Saint-Denis','UEc'),('Saint-Denis','UEp'),
  ('Saint-Leu','UE'),('Saint-Leu','UF'),('Saint-Leu','UFe'),('Saint-Leu','AUE'),
  ('Saint-Louis','UE'),('Saint-Louis','US'),('Saint-Louis','UZ'),('Saint-Louis','1AUe'),
  ('Saint-Louis','1AUe oap1'),('Saint-Louis','1AUste'),('Saint-Louis','2AUe'),('Saint-Louis','2AUste'),
  ('Saint-Paul','U1e'),('Saint-Paul','U1ec'),('Saint-Paul','U1lec'),('Saint-Paul','U2e'),('Saint-Paul','U3e'),
  ('Saint-Paul','AU1e'),('Saint-Paul','AU1ec'),('Saint-Paul','AU1est'),('Saint-Paul','AU1lec'),
  ('Saint-Paul','AU3e'),('Saint-Paul','AU5e'),('Saint-Paul','AUse'),
  ('Saint-Paul','UE'),('Saint-Paul','UEm'),('Saint-Paul','AUEm'),('Saint-Paul','Ue'),('Saint-Paul','1AUe'),
  ('Saint-Pierre','Uaza'),('Saint-Pierre','Uazc'),('Saint-Pierre','Uazi'),('Saint-Pierre','Uazp'),
  ('Saint-Pierre','Uazpc'),('Saint-Pierre','AUazi'),('Saint-Pierre','AUazc'),('Saint-Pierre','Uemi'),
  ('Sainte-Marie','UAz'),('Sainte-Marie','UEa'),('Sainte-Marie','UEc'),('Sainte-Marie','UEm'),
  ('Sainte-Marie','UEp'),('Sainte-Marie','1AUep'),
  ('Sainte-Rose','Ue'),('Sainte-Rose','1AUe'),
  ('Sainte-Suzanne','UE'),('Sainte-Suzanne','1AUe'),
  ('Salazie','AUe')
),
zones AS (
  SELECT sl.id, sl.commune, sl.attrs->>'libelle' AS lib, sl.geom_2975
  FROM spatial_layers sl
  JOIN eco e ON e.commune = sl.commune AND e.lib = sl.attrs->>'libelle'
  WHERE sl.kind = 'plu_gpu_zone'
),
pz AS (
  SELECT DISTINCT ON (p.id) p.id, p.idu, z.commune, z.lib
  FROM parcels p
  JOIN zones z ON p.geom_2975 && z.geom_2975
             AND ST_Contains(z.geom_2975, ST_Centroid(p.geom_2975))
  ORDER BY p.id
),
ev AS (
  SELECT DISTINCT ON (parcel_id) parcel_id, status, opportunity_score
  FROM parcel_evaluations
  ORDER BY parcel_id, evaluated_at DESC
),
v2 AS (
  SELECT parcelle_id, tier, rang
  FROM parcel_p_score_v2 WHERE run_id = 'm36-l2f-2026-2026-07-12'
)
SELECT pz.commune, pz.lib,
       count(*) AS n_parcelles,
       count(*) FILTER (WHERE ev.status = 'opportunite')  AS ev_opportunite,
       count(*) FILTER (WHERE ev.status = 'a_creuser')    AS ev_a_creuser,
       count(*) FILTER (WHERE ev.status IN ('exclue','faux_positif_probable')) AS ev_exclue_fp,
       count(*) FILTER (WHERE v2.tier = 'brulante')       AS v2_brulante,
       count(*) FILTER (WHERE v2.tier = 'chaude')         AS v2_chaude,
       count(*) FILTER (WHERE v2.tier = 'a_creuser')      AS v2_a_creuser,
       count(*) FILTER (WHERE v2.tier = 'reserve_fonciere') AS v2_reserve
FROM pz
LEFT JOIN ev ON ev.parcel_id = pz.id
LEFT JOIN v2 ON v2.parcelle_id = pz.idu
GROUP BY 1, 2
ORDER BY 1, 2;
