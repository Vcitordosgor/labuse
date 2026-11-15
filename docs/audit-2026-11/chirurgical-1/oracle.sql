-- ORACLE — AUDIT-CHIRURGICAL-1, LOT 3
-- Recalcul INDÉPENDANT, par requêtes brutes sur les tables, SANS passer par le code de l'app.
-- La liste des 38 IDU est injectée par le runner dans la table temporaire ech(idu) avant ce fichier.
-- Toutes les aires en m² sur geom_2975 (projection métrique locale EPSG:2975).
-- LECTURE SEULE. Exécuté via: psql -f oracle_prelude.sql -f oracle.sql

\pset footer off

-- 1) SURFACE : géométrie recalculée vs valeurs stockées
\echo '=== 1. SURFACE (ST_Area geom_2975) vs surface_m2 vs contenance_m2 ==='
SELECT p.idu, p.commune,
       round(ST_Area(p.geom_2975)::numeric,1)  AS surface_sql_m2,
       round(p.surface_m2::numeric,1)          AS surface_stockee_m2,
       p.contenance_m2                          AS contenance_cadastre_m2,
       round((ST_Area(p.geom_2975)-p.surface_m2)::numeric,1) AS ecart_m2
FROM ech e JOIN parcels p USING(idu)
ORDER BY p.idu;

-- 2) PARTS DE ZONE PLU : fraction de la parcelle par famille de zone (typezone)
\echo '=== 2. PARTS DE ZONE par famille (intersection plu_gpu_zone) ==='
WITH inter AS (
  SELECT e.idu, z.attrs->>'typezone' AS fam,
         SUM(ST_Area(ST_Intersection(p.geom_2975, z.geom_2975))) AS a
  FROM ech e JOIN parcels p USING(idu)
  JOIN spatial_layers z ON z.kind='plu_gpu_zone' AND ST_Intersects(p.geom_2975, z.geom_2975)
  GROUP BY e.idu, z.attrs->>'typezone'
)
SELECT i.idu, i.fam,
       round((i.a/NULLIF(ST_Area(p.geom_2975),0)*100)::numeric,1) AS part_pct
FROM inter i JOIN parcels p USING(idu)
WHERE i.a > 1
ORDER BY i.idu, part_pct DESC;

-- 3) PART DE ZONE ROUGE PAR NIVEAU D'ALÉA (georisque_alea niveau fort/moyen/faible)
\echo '=== 3. PART ALÉA par niveau (georisque_alea, fraction de la parcelle) ==='
WITH inter AS (
  SELECT e.idu, a.subtype AS risque, a.attrs->>'niveau' AS niveau,
         SUM(ST_Area(ST_Intersection(p.geom_2975, a.geom_2975))) AS a
  FROM ech e JOIN parcels p USING(idu)
  JOIN spatial_layers a ON a.kind='georisque_alea' AND ST_Intersects(p.geom_2975, a.geom_2975)
  GROUP BY e.idu, a.subtype, a.attrs->>'niveau'
)
SELECT i.idu, i.risque, i.niveau,
       round((i.a/NULLIF(ST_Area(p.geom_2975),0)*100)::numeric,1) AS part_pct
FROM inter i JOIN parcels p USING(idu)
WHERE i.a > 1
ORDER BY i.idu, i.risque, i.niveau;

-- 3bis) PART ZONE ROUGE PPR RÉGLEMENTAIRE (ppr INTERDICTION)
\echo '=== 3bis. PART PPR INTERDICTION (zone rouge réglementaire) ==='
WITH inter AS (
  SELECT e.idu,
         SUM(ST_Area(ST_Intersection(p.geom_2975, r.geom_2975))) AS a
  FROM ech e JOIN parcels p USING(idu)
  JOIN spatial_layers r ON r.kind='ppr' AND r.subtype='INTERDICTION' AND ST_Intersects(p.geom_2975, r.geom_2975)
  GROUP BY e.idu
)
SELECT i.idu, round((i.a/NULLIF(ST_Area(p.geom_2975),0)*100)::numeric,1) AS part_rouge_ppr_pct
FROM inter i JOIN parcels p USING(idu) WHERE i.a>1 ORDER BY i.idu;

-- 4) EMPRISE BÂTIE : surface bâtie / surface parcelle
\echo '=== 4. EMPRISE BÂTIE (intersection batiment) ==='
WITH inter AS (
  SELECT e.idu,
         SUM(ST_Area(ST_Intersection(p.geom_2975, b.geom_2975))) AS a,
         count(*) AS n_bati
  FROM ech e JOIN parcels p USING(idu)
  JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(p.geom_2975, b.geom_2975)
  GROUP BY e.idu
)
SELECT p.idu,
       COALESCE(i.n_bati,0) AS n_batiments,
       round(COALESCE(i.a,0)::numeric,1) AS emprise_m2,
       round((COALESCE(i.a,0)/NULLIF(ST_Area(p.geom_2975),0)*100)::numeric,1) AS emprise_pct
FROM ech e JOIN parcels p USING(idu) LEFT JOIN inter i USING(idu)
ORDER BY p.idu;

-- 5) VENTES : dernière vente de la parcelle + nb ventes & prix médian commune (toutes dates)
\echo '=== 5a. DERNIÈRE VENTE de la parcelle (dvf_mutations_parcelle) ==='
SELECT e.idu,
       max(d.date_mutation) AS derniere_vente,
       (array_agg(d.valeur_fonciere ORDER BY d.date_mutation DESC))[1] AS derniere_valeur,
       count(*) AS n_mutations_parcelle
FROM ech e JOIN dvf_mutations_parcelle d ON d.id_parcelle=e.idu
GROUP BY e.idu ORDER BY e.idu;

-- Le périmètre annoncé par l'app = SECTEUR = left(idu,10) (commune+section) ; fenêtre 2021-2025 ; par type_bien.
-- On recalcule le médian €/m2 TERRAIN sur les mutations brutes et on le met face à la valeur servie (dvf_secteur_medianes).
\echo '=== 5b. MARCHÉ SECTEUR terrain : recompute brut vs servi (dvf_secteur_medianes) ==='
WITH sect AS (SELECT DISTINCT left(idu,10) AS secteur FROM ech),
recompute AS (
  SELECT left(d.id_parcelle,10) AS secteur,
         count(*) AS n_ventes_terrain,
         round(percentile_cont(0.5) WITHIN GROUP (
           ORDER BY d.valeur_fonciere/NULLIF(d.surface_terrain,0))::numeric,0) AS prix_m2_terrain_recompute
  FROM dvf_mutations_parcelle d
  WHERE left(d.id_parcelle,10) IN (SELECT secteur FROM sect)
    AND d.type_local IS NULL AND d.surface_terrain>0 AND d.valeur_fonciere>0
    AND d.date_mutation BETWEEN '2021-01-01' AND '2025-12-31'
  GROUP BY 1)
SELECT s.secteur,
       r.n_ventes_terrain AS n_recompute, r.prix_m2_terrain_recompute,
       m.n_ventes AS n_servi, m.mediane_prix_m2 AS prix_m2_servi, m.fenetre
FROM sect s
LEFT JOIN recompute r ON r.secteur=s.secteur
LEFT JOIN dvf_secteur_medianes m ON m.secteur=s.secteur AND m.type_bien='terrain'
ORDER BY s.secteur;

-- 6) PENTE : pente moyenne pondérée par l'aire des polygones pente intersectant
\echo '=== 6. PENTE moyenne pondérée (slope_pct) ==='
WITH inter AS (
  SELECT e.idu,
         SUM((s.attrs->>'slope_pct')::float * ST_Area(ST_Intersection(p.geom_2975, s.geom_2975))) AS num,
         SUM(ST_Area(ST_Intersection(p.geom_2975, s.geom_2975))) AS den
  FROM ech e JOIN parcels p USING(idu)
  JOIN spatial_layers s ON s.kind='pente' AND ST_Intersects(p.geom_2975, s.geom_2975)
  GROUP BY e.idu
)
SELECT idu, round((num/NULLIF(den,0))::numeric,1) AS pente_moy_pct
FROM inter ORDER BY idu;
