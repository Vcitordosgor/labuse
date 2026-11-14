-- =====================================================================
-- CHIRURGICAL-1 — Échantillon reproductible de 38 parcelles
-- =====================================================================
-- LECTURE SEULE : seules des TABLES TEMPORAIRES de session sont créées
-- (éphémères, détruites à la fin ; aucune écriture dans les tables métier).
--
-- REPRODUCTIBILITÉ (garantie forte, INDÉPENDANTE du planificateur) :
--   * Tous les tirages "aléatoires" sont un ORDRE PSEUDO-ALÉATOIRE DÉTERMINISTE
--     ORDER BY md5(idu || ':' || <sel>). Le même script redonne EXACTEMENT les
--     mêmes 38 IDU, quel que soit le plan d'exécution (contrairement à random()).
--   * setseed(0.20261114) conservé en tête (exigence du mandat) ; sans effet sur
--     le md5 — la reproductibilité ne dépend donc PAS de l'ordre de consommation RNG.
--   * Sel 'c1-20261114' dérivé de la graine ; un sel par famille (tirages décorrélés).
--
-- COMPOSITION : GROUPE A (24) 1 constructible/commune ; GROUPE B (12) 6 familles×2 ;
--   GROUPE C (2) canaris. Dédoublonnage priorité C > B > A → 38 IDU distincts visés.
-- EXÉCUTION : psql "$DBURL" -f echantillon.sql
-- =====================================================================

SET statement_timeout = '180s';
SET max_parallel_workers_per_gather = 0;
SELECT setseed(0.20261114);   -- exigence du mandat (le tirage n'en dépend pas)

-- ---- Précalcul des parcelles en zone rouge PPR (une seule fois) --------------
CREATE TEMP TABLE _ppr_rouge AS
  SELECT DISTINCT cr.parcel_id FROM cascade_results cr
  WHERE cr.layer_name='risques' AND cr.detail ILIKE '%zone rouge%';
CREATE INDEX ON _ppr_rouge(parcel_id);

-- ---- Base enrichie ----------------------------------------------------------
CREATE TEMP TABLE _base AS
  SELECT p.id, p.idu, p.commune, p.surface_m2, z.zone_fam,
         (c.parcel_id IS NOT NULL) AS declassee,
         (rr.parcel_id IS NOT NULL) AS ppr_rouge
  FROM parcels p
  LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
  LEFT JOIN parcel_constructibilite c ON c.parcel_id=p.id
  LEFT JOIN _ppr_rouge rr ON rr.parcel_id=p.id
  WHERE p.geom IS NOT NULL AND p.surface_m2 IS NOT NULL;
CREATE INDEX ON _base(id);
CREATE INDEX ON _base(commune);

-- ==================== GROUPE A : 1 constructible / commune ====================
CREATE TEMP TABLE _ga AS
WITH a_elig AS (
  SELECT id,idu,commune,surface_m2,zone_fam FROM _base
  WHERE commune<>'Saint-Philippe' AND zone_fam IN ('U','AU') AND NOT declassee AND NOT ppr_rouge
  UNION ALL
  SELECT id,idu,commune,surface_m2,zone_fam FROM _base
  WHERE commune='Saint-Philippe' AND zone_fam IS NULL AND NOT declassee AND surface_m2>300),
a_rank AS (SELECT *, row_number() OVER (PARTITION BY commune ORDER BY md5(idu||':A-c1-20261114')) rn FROM a_elig)
SELECT idu,commune,surface_m2,zone_fam,'A' groupe,'A_constructible_commune' famille FROM a_rank WHERE rn=1;

-- ==================== GROUPE B : 6 familles × 2 ==============================
-- B1 — 100 % agricole ou naturelle
CREATE TEMP TABLE _gb1 AS
SELECT idu,commune,surface_m2,zone_fam,'B' groupe,'B1_agricole_naturelle' famille
FROM _base WHERE zone_fam IN ('A','N') ORDER BY md5(idu||':B1-c1-20261114') LIMIT 2;

-- B2 — à cheval sur ≥2 FAMILLES de zones PLU (pool borné 4000, test spatial)
CREATE TEMP TABLE _b2pool AS
  SELECT id,idu,commune,surface_m2,geom_2975 FROM parcels
  WHERE surface_m2>500 AND geom_2975 IS NOT NULL
  ORDER BY md5(idu||':B2pool-c1-20261114') LIMIT 4000;
CREATE TEMP TABLE _gb2 AS
WITH inter AS (
  SELECT po.id,po.idu,po.commune,po.surface_m2,
         CASE WHEN sl.subtype LIKE 'AU%' THEN 'AU' ELSE sl.subtype END fam,
         ST_Area(ST_Intersection(po.geom_2975,sl.geom_2975)) a
  FROM _b2pool po JOIN spatial_layers sl ON sl.kind='plu_gpu_zone' AND ST_Intersects(po.geom_2975,sl.geom_2975)),
fam AS (SELECT id,idu,commune,surface_m2,fam,sum(a) fa FROM inter GROUP BY 1,2,3,4,5),
cheval AS (SELECT id,idu,commune,surface_m2 FROM fam WHERE fa>0.05*surface_m2 GROUP BY 1,2,3,4 HAVING count(*)>=2)
SELECT c.idu,c.commune,c.surface_m2,b.zone_fam,'B' groupe,'B2_a_cheval' famille
FROM cheval c JOIN _base b ON b.id=c.id
ORDER BY md5(c.idu||':B2pick-c1-20261114') LIMIT 2;

-- B3 — zone rouge PARTIELLE
CREATE TEMP TABLE _redpart AS
  SELECT DISTINCT parcel_id FROM cascade_results
  WHERE layer_name='risques' AND detail LIKE 'PPR zone rouge sur %';
CREATE TEMP TABLE _gb3 AS
SELECT b.idu,b.commune,b.surface_m2,b.zone_fam,'B' groupe,'B3_zone_rouge_partielle' famille
FROM _base b JOIN _redpart r ON r.parcel_id=b.id
ORDER BY md5(b.idu||':B3-c1-20261114') LIMIT 2;

-- B4 — > 2 ha en zone urbaine
CREATE TEMP TABLE _gb4 AS
SELECT idu,commune,surface_m2,zone_fam,'B' groupe,'B4_grande_zone_urbaine' famille
FROM _base WHERE surface_m2>20000 AND zone_fam IN ('U','AU')
ORDER BY md5(idu||':B4-c1-20261114') LIMIT 2;

-- B5 — bâtie dense / copropriété
CREATE TEMP TABLE _copro AS
  SELECT DISTINCT b.id FROM _base b
  WHERE EXISTS (SELECT 1 FROM rnic_coproprietes r WHERE r.parcelle_idu=b.idu OR r.idu_codes @> to_jsonb(b.idu));
CREATE TEMP TABLE _gb5 AS
SELECT b.idu,b.commune,b.surface_m2,b.zone_fam,'B' groupe,'B5_copropriete' famille
FROM _base b JOIN _copro c ON c.id=b.id
ORDER BY md5(b.idu||':B5-c1-20261114') LIMIT 2;

-- B6 — propriétaire public (millesime 2024)
CREATE TEMP TABLE _pub AS
  SELECT DISTINCT idu FROM pm_proprietaires_millesimes
  WHERE millesime=2024 AND forme_juridique IN ('COM','DEPT','ETAT','REGION','COLL');
CREATE TEMP TABLE _gb6 AS
SELECT b.idu,b.commune,b.surface_m2,b.zone_fam,'B' groupe,'B6_proprietaire_public' famille
FROM _base b JOIN _pub u ON u.idu=b.idu
ORDER BY md5(b.idu||':B6-c1-20261114') LIMIT 2;

-- ==================== GROUPE C : canaris imposés ============================
CREATE TEMP TABLE _gc AS
SELECT idu,commune,surface_m2,zone_fam,'C' groupe,'C_canari' famille
FROM _base WHERE idu IN ('97422000AD0887','97416000HT0538');

-- ==================== ASSEMBLAGE + DÉDOUBLONNAGE (C>B>A) ====================
CREATE TEMP TABLE _tous AS
  SELECT idu,commune,surface_m2,zone_fam,groupe,famille,1 prio FROM _gc
  UNION ALL SELECT idu,commune,surface_m2,zone_fam,groupe,famille,2 FROM _gb1
  UNION ALL SELECT idu,commune,surface_m2,zone_fam,groupe,famille,2 FROM _gb2
  UNION ALL SELECT idu,commune,surface_m2,zone_fam,groupe,famille,2 FROM _gb3
  UNION ALL SELECT idu,commune,surface_m2,zone_fam,groupe,famille,2 FROM _gb4
  UNION ALL SELECT idu,commune,surface_m2,zone_fam,groupe,famille,2 FROM _gb5
  UNION ALL SELECT idu,commune,surface_m2,zone_fam,groupe,famille,2 FROM _gb6
  UNION ALL SELECT idu,commune,surface_m2,zone_fam,groupe,famille,3 FROM _ga;

SELECT DISTINCT ON (idu) idu,commune,surface_m2,zone_fam,groupe,famille
FROM _tous ORDER BY idu, prio;
