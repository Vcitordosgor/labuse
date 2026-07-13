SET statement_timeout='580s';
\echo === ortho_detections ===
SELECT type, count(*) n, count(*) FILTER (WHERE idu IS NULL) idu_null,
 min(surface_m2) s_min, max(surface_m2) s_max,
 min(confiance) c_min, max(confiance) c_max,
 count(*) FILTER (WHERE confiance NOT BETWEEN 0 AND 1) c_aberrant
FROM ortho_detections GROUP BY type ORDER BY 2 DESC;
\echo === ortho_detections orphelins idu ===
SELECT count(*) lignes_orphelines, count(DISTINCT o.idu) idu_orphelins
FROM ortho_detections o LEFT JOIN parcels p ON p.idu=o.idu
WHERE o.idu IS NOT NULL AND p.idu IS NULL;
\echo === ortho_detections validation ===
SELECT validation, count(*) FROM ortho_detections GROUP BY validation ORDER BY 2 DESC;
\echo === ortho_tiles ===
SELECT count(*) n, count(DISTINCT millesime) n_mill, min(millesime) m_min, max(millesime) m_max,
 count(*) FILTER (WHERE traite_at IS NULL) non_traitees,
 count(*) FILTER (WHERE pv_traite_at IS NULL) pv_non_traitees,
 count(*) FILTER (WHERE veg_traite_at IS NULL) veg_non_traitees,
 count(*) FILTER (WHERE geom IS NULL) geom_null
FROM ortho_tiles;
\echo === parkings_aper ===
SELECT count(*) n, min(surface_m2) s_min, max(surface_m2) s_max,
 count(*) FILTER (WHERE surface_m2<500) s_lt500,
 min(echeance) e_min, max(echeance) e_max,
 count(*) FILTER (WHERE echeance < current_date) echeance_depassee,
 count(*) FILTER (WHERE geom IS NULL) geom_null,
 count(*) FILTER (WHERE idus IS NULL OR jsonb_array_length(idus)=0) sans_idu
FROM parkings_aper;
\echo === parkings_aper orphelins idus ===
SELECT count(*) idu_refs, count(*) FILTER (WHERE p.idu IS NULL) idu_orphelins
FROM parkings_aper a, jsonb_array_elements_text(a.idus) j
LEFT JOIN parcels p ON p.idu=j;
\echo === pv_registry ===
SELECT count(*) n, min(puissance_kw) p_min, max(puissance_kw) p_max,
 count(*) FILTER (WHERE puissance_kw<=0) p_le0,
 min(date_mise_service) d_min, max(date_mise_service) d_max,
 count(*) FILTER (WHERE date_mise_service > current_date) d_futures,
 count(*) FILTER (WHERE geom IS NULL) geom_null, count(DISTINCT insee) n_insee
FROM pv_registry;
\echo === solar_grid ===
SELECT count(*) n, min(prod_spec_kwh_kwc) prod_min, max(prod_spec_kwh_kwc) prod_max,
 count(*) FILTER (WHERE prod_spec_kwh_kwc NOT BETWEEN 800 AND 2500) prod_aberrant,
 min(ghi_kwh_m2_an) ghi_min, max(ghi_kwh_m2_an) ghi_max,
 count(*) FILTER (WHERE geom IS NULL) geom_null
FROM solar_grid;
\echo === grid_capacity ===
SELECT count(*) n, min(capa_dispo_mw) c_min, max(capa_dispo_mw) c_max,
 count(*) FILTER (WHERE capa_dispo_mw<0) c_neg, count(*) FILTER (WHERE geom IS NULL) geom_null
FROM grid_capacity;
\echo === anru_quartiers ===
SELECT count(*) n, count(DISTINCT insee) n_insee, count(*) FILTER (WHERE code_qpv IS NULL) qpv_null
FROM anru_quartiers;
\echo === rgealti_pente_5m ===
SELECT count(*) n_tuiles FROM rgealti_pente_5m;
\echo === anc_maille_taux ===
SELECT count(*) n, count(DISTINCT insee) n_insee, min(taux_non_racc) t_min, max(taux_non_racc) t_max,
 count(*) FILTER (WHERE taux_non_racc NOT BETWEEN 0 AND 1) t_aberrant, min(millesime) m_min, max(millesime) m_max
FROM anc_maille_taux;
\echo === mvt_overlays ===
SELECT kind, count(*), count(*) FILTER (WHERE geom_3857 IS NULL) geom_null FROM mvt_overlays GROUP BY kind;
\echo === mvt_parcels bornes ===
SELECT count(*) n, count(*) FILTER (WHERE status IS NULL) status_null,
 count(*) FILTER (WHERE tier_v2 IS NULL) tier_null,
 count(*) FILTER (WHERE geom_3857 IS NULL) geom_null,
 count(*) FILTER (WHERE vue_mer='oui') vue_mer_oui
FROM mvt_parcels;
\echo === scoring derives (volumetries + orphelins) ===
SELECT 'parcel_evaluations' t, count(*) n, count(DISTINCT parcel_id) nk FROM parcel_evaluations
UNION ALL SELECT 'dryrun_parcel_evaluations', count(*), count(DISTINCT parcel_id) FROM dryrun_parcel_evaluations
UNION ALL SELECT 'parcel_p_score_v2', count(*), count(DISTINCT parcel_id) FROM parcel_p_score_v2
UNION ALL SELECT 'parcel_v_score', count(*), count(DISTINCT parcel_id) FROM parcel_v_score
UNION ALL SELECT 'cascade_results', count(*), count(DISTINCT parcel_id) FROM cascade_results;
\echo === cascade_results orphelins parcel_id ===
SELECT count(DISTINCT c.parcel_id) orphelins
FROM cascade_results c LEFT JOIN parcels p ON p.id=c.parcel_id WHERE p.id IS NULL;
\echo === parcel_p_score_v2 doublons parcel_id ===
SELECT count(*) - count(DISTINCT parcel_id) doublons FROM parcel_p_score_v2;
