-- NU5-E — recomputes de cohérence (base LOCALE labuse q_v20). LECTURE SEULE.
-- Rejoue les chiffres servis de la fiche commune depuis les tables sources, pour comparaison
-- avec les payloads servis (docs/.../E/preuves/payloads/*.json). psql "postgresql://openclaw@localhost:5432/labuse" -f recompute.sql

-- 1) Risques : ppr_pct et mouvement_terrain_pct recomputés par parcelle (identique au moteur
--    registre.moteurs.commune.pct_parcelles_couche) + compte CatNat (table catnat_arretes).
WITH base AS (SELECT commune, count(*) n_parc FROM parcels GROUP BY commune)
SELECT b.commune, b.n_parc,
  (SELECT count(*) FROM catnat_arretes ca
     JOIN (SELECT DISTINCT left(idu,5) i FROM parcels p WHERE p.commune=b.commune) x ON ca.insee=x.i) AS catnat_db,
  round(100.0*(SELECT count(DISTINCT p.idu) FROM parcels p JOIN spatial_layers sl
     ON sl.kind='ppr' AND ST_Intersects(p.geom_2975,sl.geom_2975) WHERE p.commune=b.commune)/b.n_parc,1) AS ppr_pct,
  round(100.0*(SELECT count(DISTINCT p.idu) FROM parcels p JOIN spatial_layers sl
     ON sl.kind='georisque_alea' AND sl.subtype='mouvement_terrain' AND ST_Intersects(p.geom_2975,sl.geom_2975)
     WHERE p.commune=b.commune)/b.n_parc,1) AS mvt_pct
FROM base b ORDER BY b.commune;

-- 2) Saint-Denis : part de SURFACE communale couverte par l'aléa mouvement de terrain (preuve E-2).
--    Attendu ~0,04 % (trou de couche) ; comparer à une commune voisine (Sainte-Marie ~100 %).
WITH c AS (SELECT ST_Union(geom_2975) g, ST_Area(ST_Union(geom_2975)) a FROM parcels WHERE commune=:comm),
     m AS (SELECT ST_Union(geom_2975) g FROM spatial_layers WHERE kind='georisque_alea' AND subtype='mouvement_terrain')
SELECT round((c.a/1e6)::numeric,1) commune_km2,
       round((ST_Area(ST_Intersection(c.g,m.g))/1e6)::numeric,2) mvt_km2,
       round((100*ST_Area(ST_Intersection(c.g,m.g))/c.a)::numeric,2) pct_surface
FROM c,m;   -- \set comm 'Saint-Denis'  puis  'Sainte-Marie'

-- 3) Parc national : la couche 'parc_national' (cœur + aire d'adhésion) → toutes les communes
--    l'intersectent (flag non discriminant, 24/24 true). Preuve ORANGE E-?.
SELECT name, subtype, round((ST_Area(geom_2975)/1e6)::numeric,1) km2 FROM spatial_layers WHERE kind='parc_national';

-- 4) SCOT : la donnée EXISTE en base (3 périmètres) mais n'est jamais servie (bug E-1).
SELECT name, attrs->>'date_approbation' AS date_appro, attrs->>'statut' AS statut FROM spatial_layers WHERE kind='scot';

-- 5) VEFA : volume de mutations VEFA par commune (seuil d'effectif = 8) — représentativité des
--    médianes neuf (Trois-Bassins/Petite-Île, finding ORANGE prix).
SELECT code_commune, count(DISTINCT id_mutation) FILTER (WHERE nature_mutation ILIKE '%état futur%') AS vefa_mut
FROM dvf_mutations_parcelle GROUP BY code_commune ORDER BY code_commune;
