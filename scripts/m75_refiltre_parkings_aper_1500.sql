-- M75 Phase 1 — REFILTRAGE de parkings_aper au SEUIL LÉGAL APER (1 500 m²). EXÉCUTÉ 2026-08-13.
--
-- Loi APER n° 2023-175 du 10/03/2023, art. 40 ; décret n° 2024-1023 du 13/11/2024. L'obligation
-- d'ombrières photovoltaïques vise les parkings extérieurs de PLUS DE 1 500 m² (ombrières sur ≥50 %
-- de la surface). Calendrier (parcs existants au 01/07/2023) : > 10 000 m² → 01/07/2026 ;
-- 1 500–10 000 m² → 01/07/2028 (extension possible 2030).
--
-- La donnée ingérée classait à tort dès 1 000 m² (tranche « 1000_10000 »). Doctrine Vic : « si le
-- seuil légal diverge du seuil de la donnée, c'est la donnée qu'on refiltre, pas le texte qu'on
-- arrondit. » Mesuré avant : 286 parkings de 1 000–1 500 m² portaient une tranche à tort.
--
-- Après refiltrage : ≤ 1 500 m² → NON soumis (tranche/échéance NULL) ; 1 500–10 000 → 2028 ;
-- > 10 000 → 2026. La surface (ST_Area OSM) n'est PAS touchée — seule la classification d'obligation.
BEGIN;
UPDATE parkings_aper SET tranche = NULL, echeance = NULL
 WHERE surface_m2 <= 1500;
UPDATE parkings_aper SET tranche = '1500_10000', echeance = DATE '2028-07-01'
 WHERE surface_m2 > 1500 AND surface_m2 <= 10000;
UPDATE parkings_aper SET tranche = 'sup_10000', echeance = DATE '2026-07-01'
 WHERE surface_m2 > 10000;
COMMIT;
-- Contrôle attendu : 451 sans tranche (≤1500), 426 en 1500_10000, 24 en sup_10000.
