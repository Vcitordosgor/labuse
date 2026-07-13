SET statement_timeout='580s';
\echo === couverture & orphelins — tables idu ===
SELECT 'parcel_terrain' t, count(*) n, count(DISTINCT x.idu) nk,
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NULL) idu_orphelins,
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NOT NULL) parcelles_couvertes
FROM parcel_terrain x LEFT JOIN parcels p ON p.idu=x.idu
UNION ALL
SELECT 'parcel_solar', count(*), count(DISTINCT x.idu),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NULL),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NOT NULL)
FROM parcel_solar x LEFT JOIN parcels p ON p.idu=x.idu
UNION ALL
SELECT 'parcel_vegetation', count(*), count(DISTINCT x.idu),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NULL),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NOT NULL)
FROM parcel_vegetation x LEFT JOIN parcels p ON p.idu=x.idu
UNION ALL
SELECT 'parcel_anc', count(*), count(DISTINCT x.idu),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NULL),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NOT NULL)
FROM parcel_anc x LEFT JOIN parcels p ON p.idu=x.idu
UNION ALL
SELECT 'parcel_residuel_bati', count(*), count(DISTINCT x.idu),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NULL),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NOT NULL)
FROM parcel_residuel_bati x LEFT JOIN parcels p ON p.idu=x.idu
UNION ALL
SELECT 'parcel_equipements', count(*), count(DISTINCT x.idu),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NULL),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NOT NULL)
FROM parcel_equipements x LEFT JOIN parcels p ON p.idu=x.idu
UNION ALL
SELECT 'module_division', count(*), count(DISTINCT x.idu),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NULL),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NOT NULL)
FROM module_division x LEFT JOIN parcels p ON p.idu=x.idu
UNION ALL
SELECT 'vegetation_zonal_acc', count(*), count(DISTINCT x.idu),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NULL),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NOT NULL)
FROM vegetation_zonal_acc x LEFT JOIN parcels p ON p.idu=x.idu
UNION ALL
SELECT 'mvt_parcels', count(*), count(DISTINCT x.idu),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NULL),
 count(DISTINCT x.idu) FILTER (WHERE p.idu IS NOT NULL)
FROM mvt_parcels x LEFT JOIN parcels p ON p.idu=x.idu;
\echo === couverture & orphelins — tables parcel_id ===
SELECT 'parcel_vue_mer' t, count(*) n, count(DISTINCT x.parcel_id) nk,
 count(DISTINCT x.parcel_id) FILTER (WHERE p.id IS NULL) orphelins,
 count(DISTINCT x.parcel_id) FILTER (WHERE p.id IS NOT NULL) parcelles_couvertes
FROM parcel_vue_mer x LEFT JOIN parcels p ON p.id=x.parcel_id
UNION ALL
SELECT 'parcel_amenites', count(*), count(DISTINCT x.parcel_id),
 count(DISTINCT x.parcel_id) FILTER (WHERE p.id IS NULL),
 count(DISTINCT x.parcel_id) FILTER (WHERE p.id IS NOT NULL)
FROM parcel_amenites x LEFT JOIN parcels p ON p.id=x.parcel_id
UNION ALL
SELECT 'parcel_residuel', count(*), count(DISTINCT x.parcel_id),
 count(DISTINCT x.parcel_id) FILTER (WHERE p.id IS NULL),
 count(DISTINCT x.parcel_id) FILTER (WHERE p.id IS NOT NULL)
FROM parcel_residuel x LEFT JOIN parcels p ON p.id=x.parcel_id
UNION ALL
SELECT 'parcel_signals', count(*), count(DISTINCT x.parcel_id),
 count(DISTINCT x.parcel_id) FILTER (WHERE p.id IS NULL),
 count(DISTINCT x.parcel_id) FILTER (WHERE p.id IS NOT NULL)
FROM parcel_signals x LEFT JOIN parcels p ON p.id=x.parcel_id;
\echo === bornes parcel_terrain ===
SELECT min(pente_moy_deg) pmoy_min, max(pente_moy_deg) pmoy_max,
 min(pente_max_deg) pmax_min, max(pente_max_deg) pmax_max,
 count(*) FILTER (WHERE pente_moy_deg<0 OR pente_moy_deg>90) aberrants,
 count(*) FILTER (WHERE pente_moy_deg IS NULL) pmoy_null,
 count(*) FILTER (WHERE flag_terrassement_lourd) terrassement_lourd
FROM parcel_terrain;
\echo === bornes parcel_solar ===
SELECT min(prod_spec_kwh_kwc) prod_min, max(prod_spec_kwh_kwc) prod_max,
 count(*) FILTER (WHERE prod_spec_kwh_kwc IS NULL) prod_null,
 count(*) FILTER (WHERE prod_spec_kwh_kwc NOT BETWEEN 800 AND 2500) prod_aberrant,
 min(score_solaire) sc_min, max(score_solaire) sc_max,
 count(*) FILTER (WHERE pv_existant IS NOT NULL AND pv_existant<>'non') pv_existant
FROM parcel_solar;
\echo === bornes parcel_vegetation ===
SELECT min(ndvi_moyen) ndvi_min, max(ndvi_moyen) ndvi_max,
 count(*) FILTER (WHERE ndvi_moyen NOT BETWEEN -1 AND 1) ndvi_aberrant,
 min(canopee_pct) can_min, max(canopee_pct) can_max,
 count(*) FILTER (WHERE canopee_pct NOT BETWEEN 0 AND 100) can_aberrant,
 count(*) FILTER (WHERE ndvi_moyen IS NULL) ndvi_null
FROM parcel_vegetation;
\echo === bornes parcel_vue_mer ===
SELECT vue, count(*) n, min(distance_cote_m) d_min, max(distance_cote_m) d_max,
 count(*) FILTER (WHERE distance_cote_m<0) d_neg,
 min(obstruction_pct) o_min, max(obstruction_pct) o_max
FROM parcel_vue_mer GROUP BY vue;
\echo === bornes parcel_amenites ===
SELECT min(dist_ecole_m) ecole_min, max(dist_ecole_m) ecole_max,
 min(dist_sante_m) sante_min, max(dist_sante_m) sante_max,
 min(dist_commerce_m) com_min, max(dist_commerce_m) com_max,
 min(dist_tcsp_m) tcsp_min, max(dist_tcsp_m) tcsp_max,
 count(*) FILTER (WHERE least(dist_ecole_m,dist_sante_m,dist_commerce_m,dist_tcsp_m)<0) negatifs,
 count(*) FILTER (WHERE dist_ecole_m IS NULL) ecole_null
FROM parcel_amenites;
\echo === bornes parcel_anc ===
SELECT zone_anc, count(*) n, min(proba_anc) p_min, max(proba_anc) p_max,
 count(*) FILTER (WHERE proba_anc NOT BETWEEN 0 AND 100) p_aberrant
FROM parcel_anc GROUP BY zone_anc ORDER BY 2 DESC;
\echo === bornes parcel_residuel_bati ===
SELECT min(emprise_residuelle_m2) emr_min, max(emprise_residuelle_m2) emr_max,
 count(*) FILTER (WHERE emprise_residuelle_m2<0) emr_neg,
 min(hauteur_max_m) h_min, max(hauteur_max_m) h_max,
 count(*) FILTER (WHERE hauteur_bati_m>100) h_bati_aberrant,
 count(*) FILTER (WHERE surelevation_possible) surelevation
FROM parcel_residuel_bati;
\echo === bornes parcel_equipements ===
SELECT count(*) FILTER (WHERE piscine) piscines,
 count(*) FILTER (WHERE pv_detecte) pv,
 min(piscine_surface_m2) pisc_smin, max(piscine_surface_m2) pisc_smax,
 count(*) FILTER (WHERE piscine AND piscine_surface_m2 NOT BETWEEN 4 AND 400) pisc_aberrant
FROM parcel_equipements;
\echo === bornes module_division ===
SELECT min(lot_area_m2) lot_min, max(lot_area_m2) lot_max,
 count(*) FILTER (WHERE lot_area_m2<=0) lot_le0,
 min(score) sc_min, max(score) sc_max
FROM module_division;
