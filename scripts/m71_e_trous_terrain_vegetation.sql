-- M71 BLOC E — trous diffus terrain & végétation (audit M66-B) — EXÉCUTÉ le 2026-08-13.
-- Doctrine : relancer le calcul sur les SEULES manquantes ; ce qui échoue encore est
-- NEUTRALISÉ DOCUMENTÉ (contribution nulle + motif en base), jamais un zéro silencieux.
--
-- Diagnostic mesuré avant exécution :
--   terrain    : 8 211 manquantes — 0 invalide, 84 % < 25 m² (slivers < 1 pixel du raster
--                5 m ; aire médiane 10,3 m²), TOUTES couvertes par rgealti_pente_5m.
--   végétation : 5 556 manquantes — aire médiane 6 634 m², TOUTES hors de toute tuile
--                ortho_tiles (IRC/MNH jamais acquis sur ces zones — relance impossible
--                sans étendre le tuilage : acquisition lourde, hors périmètre M71).
--
-- Résultat : terrain 8 211/8 211 récupérées (zonal ST_Clip + repli ST_Value au
-- point-sur-surface pour les slivers), 0 neutralisée → parcel_terrain = 431 663 (100 %).
-- Végétation : 5 556 neutralisées documentées → parcel_vegetation = 431 663 (100 % de
-- lignes, dont 5 556 motivées). Le LEFT JOIN du scoring produit le même NULL qu'avant
-- (contribution nulle inchangée) — la différence est que l'absence est désormais DITE.

-- ── Terrain : relance sur les manquantes ────────────────────────────────────────────
BEGIN;
ALTER TABLE parcel_terrain ADD COLUMN IF NOT EXISTS motif_absence text;
WITH manq AS (
  SELECT p.idu, p.geom_2975 FROM parcels p
  LEFT JOIN parcel_terrain t ON t.idu = p.idu WHERE t.idu IS NULL
), zonal AS (
  SELECT m.idu,
         (ST_SummaryStatsAgg(ST_Clip(r.rast, m.geom_2975, true), 1, true)).mean AS pmoy,
         (ST_SummaryStatsAgg(ST_Clip(r.rast, m.geom_2975, true), 1, true)).max  AS pmax
  FROM manq m
  JOIN rgealti_pente_5m r ON ST_Intersects(r.rast::geometry, m.geom_2975)
  GROUP BY m.idu
), pointe AS (  -- repli : parcelle plus petite qu'un pixel → échantillon au point-sur-surface
  SELECT m.idu, ST_Value(r.rast, ST_PointOnSurface(m.geom_2975)) AS pval
  FROM manq m
  JOIN rgealti_pente_5m r ON ST_Intersects(r.rast::geometry, ST_PointOnSurface(m.geom_2975))
)
INSERT INTO parcel_terrain (idu, pente_moy_deg, pente_max_deg, flag_terrassement_lourd, computed_at, motif_absence)
SELECT m.idu,
       COALESCE(z.pmoy, pt.pval),
       COALESCE(z.pmax, pt.pval),
       COALESCE(z.pmoy, pt.pval) >= 15,
       now(),
       CASE WHEN COALESCE(z.pmoy, pt.pval) IS NULL
            THEN 'M71-E : zonal ET point-sur-surface sans pixel (raster nodata locale) — neutralisée, contribution nulle'
            ELSE NULL END
FROM manq m
LEFT JOIN zonal z ON z.idu = m.idu
LEFT JOIN pointe pt ON pt.idu = m.idu;
COMMIT;

-- ── Végétation : neutralisation documentée (hors emprise du tuilage ortho) ──────────
BEGIN;
ALTER TABLE parcel_vegetation ADD COLUMN IF NOT EXISTS motif_absence text;
INSERT INTO parcel_vegetation (idu, ndvi_moyen, canopee_pct, canopee_limite_pct, canopee_bati_pct, methode_hauteur, confiance, updated_at, motif_absence)
SELECT p.idu, NULL, NULL, NULL, NULL, NULL, NULL, now(),
       'M71-E : hors emprise du tuilage ortho (IRC/MNH jamais acquis sur cette zone) — neutralisée, contribution nulle'
FROM parcels p LEFT JOIN parcel_vegetation v ON v.idu = p.idu
WHERE v.idu IS NULL;
COMMIT;

-- Résiduel neutralisé végétation par commune (mesuré à l'exécution) :
--   97410 Saint-Benoît 660 · 97419 Sainte-Rose 597 (9,5 % de la commune — à surveiller) ·
--   97415 Saint-Paul 588 · 97401 Les Avirons 429 · 97418 Sainte-Marie 318 ·
--   97411 Saint-Denis 304 · 97412 Saint-Joseph 276 · 97413 Saint-Leu 265 · reste < 265.
-- Levée future : étendre le tuilage ortho_tiles à ces zones puis relancer
-- `labuse vegetation-irc` + `labuse vegetation` (les motifs M71-E seront alors écrasés
-- par de vraies valeurs — l'INSERT de vegetation.finalize fait un upsert par idu).
