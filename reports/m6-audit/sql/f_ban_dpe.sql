SET statement_timeout='300s';
\echo === adresses ===
SELECT count(*) n, count(DISTINCT id_ban) nk,
 count(*) FILTER (WHERE idu IS NULL) idu_null,
 count(*) FILTER (WHERE geom IS NULL) geom_null,
 count(*) FILTER (WHERE voie IS NULL OR voie='') voie_null,
 count(DISTINCT insee) n_insee, min(refreshed_at)::date rmin, max(refreshed_at)::date rmax
FROM adresses;
\echo === adresses orphelins idu ===
SELECT count(*) lignes_orphelines FROM adresses a LEFT JOIN parcels p ON p.idu=a.idu
WHERE a.idu IS NOT NULL AND p.idu IS NULL;
\echo === adresse_parcelles ===
SELECT count(*) n, count(DISTINCT idu) nk, count(DISTINCT id_ban) n_ban FROM adresse_parcelles;
\echo === adresse_parcelles orphelins + couverture ===
SELECT count(DISTINCT t.idu) FILTER (WHERE p.idu IS NULL) idu_orphelins,
 count(DISTINCT t.idu) FILTER (WHERE p.idu IS NOT NULL) parcelles_couvertes
FROM adresse_parcelles t LEFT JOIN parcels p ON p.idu=t.idu;
\echo === adresse_parcelles id_ban orphelins vs adresses ===
SELECT count(DISTINCT t.id_ban) ban_orphelins
FROM adresse_parcelles t LEFT JOIN adresses a ON a.id_ban=t.id_ban WHERE a.id_ban IS NULL;
\echo === dpe_records ===
SELECT count(*) n, count(DISTINCT numero_dpe) nk,
 count(*) FILTER (WHERE parcelle_idu IS NULL) idu_null,
 count(*) FILTER (WHERE etiquette_dpe IS NULL) etiq_null,
 min(date_etablissement) dmin, max(date_etablissement) dmax,
 count(*) FILTER (WHERE date_etablissement > now()) dates_futures,
 min(surface_habitable) surf_min, max(surface_habitable) surf_max,
 count(*) FILTER (WHERE surface_habitable<=0 OR surface_habitable>2000) surf_aberrante,
 min(annee_construction) an_min, max(annee_construction) an_max,
 count(*) FILTER (WHERE annee_construction < 1900 OR annee_construction > 2026) an_aberrant
FROM dpe_records;
\echo === dpe_records orphelins idu ===
SELECT count(*) lignes_orphelines FROM dpe_records d LEFT JOIN parcels p ON p.idu=d.parcelle_idu
WHERE d.parcelle_idu IS NOT NULL AND p.idu IS NULL;
\echo === rnic_coproprietes ===
SELECT count(*) n, count(DISTINCT numero_immatriculation) nk,
 count(*) FILTER (WHERE parcelle_idu IS NULL) idu_null,
 count(*) FILTER (WHERE nb_lots_total IS NULL) lots_null,
 min(nb_lots_total) lots_min, max(nb_lots_total) lots_max,
 count(*) FILTER (WHERE nb_lots_total<=0) lots_le0,
 count(*) FILTER (WHERE geom IS NULL) geom_null,
 count(DISTINCT insee) n_insee
FROM rnic_coproprietes;
\echo === rnic orphelins idu ===
SELECT count(*) lignes_orphelines FROM rnic_coproprietes r LEFT JOIN parcels p ON p.idu=r.parcelle_idu
WHERE r.parcelle_idu IS NOT NULL AND p.idu IS NULL;
\echo === rpls_commune ===
SELECT count(*) n, count(DISTINCT insee) n_insee, min(millesime) mmin, max(millesime) mmax,
 min(nb_logements) log_min, max(nb_logements) log_max, sum(nb_logements) log_total
FROM rpls_commune;
\echo === filosofi_carreaux_200m ===
SELECT count(*) n, count(DISTINCT idcar_200m) nk,
 count(*) FILTER (WHERE geom IS NULL) geom_null,
 count(*) FILTER (WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)) geom_inval,
 min(ind) ind_min, max(ind) ind_max, count(*) FILTER (WHERE ind<0) ind_neg,
 min(men) men_min, max(men) men_max,
 count(*) FILTER (WHERE men_pauv > men) pauv_gt_men
FROM filosofi_carreaux_200m;
\echo === catnat_arretes ===
SELECT count(*) n, min(date_arrete) dmin, max(date_arrete) dmax,
 count(DISTINCT insee) n_insee,
 count(*) FILTER (WHERE insee NOT LIKE '974%') insee_hors_974,
 count(*) FILTER (WHERE type_peril IS NULL) peril_null
FROM catnat_arretes;
