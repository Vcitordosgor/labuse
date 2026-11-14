-- ORACLE compact → CSV (idu,fait,valeur). Union-based (pas de double-compte). LECTURE SEULE.
-- ech(idu) peuplée par le prélude. Sortie: psql -t -A -F',' -> oracle.csv
SET statement_timeout='240s'; SET max_parallel_workers_per_gather=0;

-- surface recalculée
SELECT p.idu,'surface_sql_m2',round(ST_Area(p.geom_2975)::numeric,1)::text FROM ech e JOIN parcels p USING(idu);
-- emprise bâtie BD TOPO (UNION, correct)
SELECT p.idu,'emprise_bdtopo_union_m2',
  round(COALESCE(ST_Area(ST_Union(ST_Intersection(b.geom_2975,p.geom_2975))),0)::numeric,1)::text
FROM ech e JOIN parcels p USING(idu)
LEFT JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(b.geom_2975,p.geom_2975)
GROUP BY p.idu,p.geom_2975;
-- emprise pct BD TOPO
SELECT p.idu,'emprise_bdtopo_pct',
  round((COALESCE(ST_Area(ST_Union(ST_Intersection(b.geom_2975,p.geom_2975))),0)/NULLIF(ST_Area(p.geom_2975),0)*100)::numeric,1)::text
FROM ech e JOIN parcels p USING(idu)
LEFT JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(b.geom_2975,p.geom_2975)
GROUP BY p.idu,p.geom_2975;
-- nb bâtiments BD TOPO
SELECT p.idu,'n_batiments_bdtopo',count(b.id)::text
FROM ech e JOIN parcels p USING(idu)
LEFT JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(b.geom_2975,p.geom_2975)
GROUP BY p.idu;
-- pente moyenne pondérée
SELECT q.idu,'pente_moy_pct',round((num/NULLIF(den,0))::numeric,1)::text FROM (
  SELECT p.idu, SUM((s.attrs->>'slope_pct')::float*ST_Area(ST_Intersection(p.geom_2975,s.geom_2975))) num,
         SUM(ST_Area(ST_Intersection(p.geom_2975,s.geom_2975))) den
  FROM ech e JOIN parcels p USING(idu)
  JOIN spatial_layers s ON s.kind='pente' AND ST_Intersects(p.geom_2975,s.geom_2975)
  GROUP BY p.idu) q;
-- parts de zone PLU par famille (typezone) — union par famille
SELECT q.idu, 'zone_part_'||q.fam, round((q.a/NULLIF(q.surf,0)*100)::numeric,1)::text FROM (
  SELECT p.idu, z.attrs->>'typezone' fam,
    ST_Area(ST_Union(ST_Intersection(p.geom_2975,z.geom_2975))) a, ST_Area(p.geom_2975) surf
  FROM ech e JOIN parcels p USING(idu)
  JOIN spatial_layers z ON z.kind='plu_gpu_zone' AND ST_Intersects(p.geom_2975,z.geom_2975)
  GROUP BY p.idu,z.attrs->>'typezone',p.geom_2975) q WHERE q.a>1;
-- part aléa fort (union) par risque
SELECT q.idu,'alea_fort_'||q.risque, round((q.a/NULLIF(q.surf,0)*100)::numeric,1)::text FROM (
  SELECT p.idu, a.subtype risque,
    ST_Area(ST_Union(ST_Intersection(p.geom_2975,a.geom_2975))) a, ST_Area(p.geom_2975) surf
  FROM ech e JOIN parcels p USING(idu)
  JOIN spatial_layers a ON a.kind='georisque_alea' AND a.attrs->>'niveau'='fort' AND ST_Intersects(p.geom_2975,a.geom_2975)
  GROUP BY p.idu,a.subtype,p.geom_2975) q WHERE q.a>1;
-- dernière vente parcelle
SELECT e.idu,'derniere_vente',COALESCE(max(d.date_mutation)::text,'(aucune)')
FROM ech e LEFT JOIN dvf_mutations_parcelle d ON d.id_parcelle=e.idu GROUP BY e.idu;
-- marché secteur terrain recompute vs servi
SELECT s.secteur,'prix_m2_terrain_recompute',COALESCE(r.px::text,'(n/a)') FROM
 (SELECT DISTINCT left(idu,10) secteur FROM ech) s
 LEFT JOIN (SELECT left(id_parcelle,10) secteur, round(percentile_cont(0.5) WITHIN GROUP(ORDER BY valeur_fonciere/NULLIF(surface_terrain,0))::numeric,0) px, count(*) n
            FROM dvf_mutations_parcelle WHERE type_local IS NULL AND surface_terrain>0 AND valeur_fonciere>0 AND date_mutation BETWEEN '2021-01-01' AND '2025-12-31'
            GROUP BY 1) r ON r.secteur=s.secteur;
SELECT m.secteur,'prix_m2_terrain_servi',m.mediane_prix_m2::text FROM
 (SELECT DISTINCT left(idu,10) secteur FROM ech) s JOIN dvf_secteur_medianes m ON m.secteur=s.secteur AND m.type_bien='terrain';
