SET statement_timeout='300s';
\echo === dvf_mutations ===
SELECT count(*) n, min(date_mutation)::date dmin, max(date_mutation)::date dmax,
 count(*) FILTER (WHERE date_mutation IS NULL) d_null,
 count(*) FILTER (WHERE valeur_fonciere IS NULL) vf_null,
 count(*) FILTER (WHERE valeur_fonciere<=0) vf_le0,
 round(min(valeur_fonciere)::numeric) vf_min, round(max(valeur_fonciere)::numeric) vf_max,
 count(*) FILTER (WHERE valeur_fonciere>20e6) vf_gt20m,
 count(*) FILTER (WHERE geom IS NULL) geom_null,
 count(*) FILTER (WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)) geom_inval,
 count(*) FILTER (WHERE surface_terrain IS NULL) st_null,
 count(DISTINCT commune) ncom
FROM dvf_mutations;
\echo === dvf_mutations_parcelle ===
SELECT count(*) n, min(date_mutation) dmin, max(date_mutation) dmax,
 min(millesime) mmin, max(millesime) mmax,
 count(DISTINCT id_parcelle) nk,
 count(*) FILTER (WHERE id_parcelle IS NULL) idu_null,
 count(*) FILTER (WHERE valeur_fonciere IS NULL) vf_null,
 count(*) FILTER (WHERE valeur_fonciere<=0) vf_le0,
 round(max(valeur_fonciere)::numeric) vf_max
FROM dvf_mutations_parcelle;
\echo === dvf_mutations_parcelle orphelins vs parcels ===
SELECT count(DISTINCT t.id_parcelle) idu_orphelins, count(*) lignes_orphelines
FROM dvf_mutations_parcelle t LEFT JOIN parcels p ON p.idu=t.id_parcelle
WHERE t.id_parcelle IS NOT NULL AND p.idu IS NULL;
\echo === dvf_mutations_parcelle couverture parcelles ===
SELECT count(DISTINCT t.id_parcelle) parcelles_couvertes
FROM dvf_mutations_parcelle t JOIN parcels p ON p.idu=t.id_parcelle;
\echo === dvf_mutations_histo ===
SELECT count(*) n, min(date_mutation) dmin, max(date_mutation) dmax,
 min(millesime) mmin, max(millesime) mmax,
 count(DISTINCT id_parcelle) nk,
 count(*) FILTER (WHERE id_parcelle IS NULL) idu_null,
 count(*) FILTER (WHERE valeur_fonciere IS NULL) vf_null,
 count(*) FILTER (WHERE valeur_fonciere<=0) vf_le0,
 round(max(valeur_fonciere)::numeric) vf_max
FROM dvf_mutations_histo;
\echo === dvf_mutations_histo orphelins vs parcels ===
SELECT count(DISTINCT t.id_parcelle) idu_orphelins, count(*) lignes_orphelines
FROM dvf_mutations_histo t LEFT JOIN parcels p ON p.idu=t.id_parcelle
WHERE t.id_parcelle IS NOT NULL AND p.idu IS NULL;
\echo === dvf_secteur_medianes ===
SELECT count(*) n, count(DISTINCT secteur) n_secteurs,
 min(mediane_prix_m2) pm2_min, max(mediane_prix_m2) pm2_max,
 count(*) FILTER (WHERE mediane_prix_m2 IS NULL) pm2_null,
 min(n_ventes) nv_min, max(n_ventes) nv_max, max(computed_at)::date maj
FROM dvf_secteur_medianes;
\echo === sitadel_permits ===
SELECT count(*) n, count(DISTINCT permit_id) nk,
 min(date)::date dmin, max(date)::date dmax,
 count(*) FILTER (WHERE date > now()) dates_futures,
 count(*) FILTER (WHERE date IS NULL) d_null,
 count(*) FILTER (WHERE commune IS NULL) com_null,
 count(DISTINCT commune) ncom,
 count(*) FILTER (WHERE geom IS NULL) geom_null,
 count(*) FILTER (WHERE idu_codes IS NULL OR jsonb_array_length(idu_codes)=0) sans_idu
FROM sitadel_permits;
\echo === sitadel_permits orphelins idu ===
SELECT count(*) idu_refs, count(*) FILTER (WHERE p.idu IS NULL) idu_orphelins,
 count(DISTINCT j) FILTER (WHERE p.idu IS NULL) idu_orphelins_distincts
FROM sitadel_permits s, jsonb_array_elements_text(s.idu_codes) j
LEFT JOIN parcels p ON p.idu=j;
\echo === sitadel couverture parcelles ===
SELECT count(DISTINCT p.idu) parcelles_couvertes
FROM sitadel_permits s, jsonb_array_elements_text(s.idu_codes) j
JOIN parcels p ON p.idu=j;
