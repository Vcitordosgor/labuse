SET statement_timeout='300s';
\echo === parcelle_personne_morale ===
SELECT count(*) n, count(DISTINCT idu) nk,
 count(*) FILTER (WHERE siren IS NULL OR siren='') siren_null,
 count(*) FILTER (WHERE denomination IS NULL OR denomination='') denom_null,
 count(DISTINCT millesime) n_millesimes, min(millesime) mmin, max(millesime) mmax
FROM parcelle_personne_morale;
\echo === parcelle_personne_morale orphelins + couverture ===
SELECT count(DISTINCT t.idu) FILTER (WHERE p.idu IS NULL) idu_orphelins,
 count(DISTINCT t.idu) FILTER (WHERE p.idu IS NOT NULL) parcelles_couvertes
FROM parcelle_personne_morale t LEFT JOIN parcels p ON p.idu=t.idu;
\echo === pm_proprietaires_millesimes par millesime + idu obsoletes ===
SELECT t.millesime, count(*) n, count(DISTINCT t.idu) nk,
 count(DISTINCT t.idu) FILTER (WHERE p.idu IS NULL) idu_obsoletes,
 count(*) FILTER (WHERE t.siren IS NULL OR t.siren='') siren_null
FROM pm_proprietaires_millesimes t LEFT JOIN parcels p ON p.idu=t.idu
GROUP BY t.millesime ORDER BY t.millesime;
\echo === bodacc_procedures ===
SELECT count(*) n, min(date_annonce) dmin, max(date_annonce) dmax,
 count(*) FILTER (WHERE siren IS NULL OR siren='') siren_null,
 count(DISTINCT siren) n_siren,
 count(*) FILTER (WHERE type_procedure IS NULL) type_null
FROM bodacc_procedures;
\echo === bodacc_procedures raccord siren proprietaires ===
SELECT count(DISTINCT b.siren) siren_matches
FROM bodacc_procedures b JOIN parcelle_personne_morale ppm ON ppm.siren=b.siren;
\echo === bodacc_annonces_owner ===
SELECT count(*) n, min(date_annonce) dmin, max(date_annonce) dmax,
 count(DISTINCT siren) n_siren, count(*) FILTER (WHERE famille IS NULL) fam_null
FROM bodacc_annonces_owner;
\echo === pm_dirigeants ===
SELECT count(*) n, count(DISTINCT siren) n_siren,
 count(*) FILTER (WHERE nom IS NULL OR nom='') nom_null,
 count(*) FILTER (WHERE date_naissance IS NULL OR date_naissance='') ddn_null,
 count(*) FILTER (WHERE actif) actifs
FROM pm_dirigeants;
\echo === pm_dirigeants raccord siren ===
SELECT count(DISTINCT d.siren) siren_matches
FROM pm_dirigeants d JOIN parcelle_personne_morale ppm ON ppm.siren=d.siren;
\echo === pm_dirigeant_gigogne ===
SELECT count(*) n, count(DISTINCT siren) n_siren FROM pm_dirigeant_gigogne;
\echo === owner_enrichment ===
SELECT count(*) n, count(DISTINCT siren) n_siren, source, count(*) FILTER (WHERE denomination IS NULL) denom_null
FROM owner_enrichment GROUP BY source;
\echo === owner_denom_lookup ===
SELECT status, count(*) FROM owner_denom_lookup GROUP BY status ORDER BY 2 DESC;
\echo === parcel_veille_succession ===
SELECT count(*) n, count(DISTINCT parcelle_id) nk,
 min(dirigeant_age) age_min, max(dirigeant_age) age_max,
 count(*) FILTER (WHERE dirigeant_age IS NULL) age_null,
 count(*) FILTER (WHERE dirigeant_age NOT BETWEEN 18 AND 110) age_aberrant,
 count(*) FILTER (WHERE sci_dormante) sci_dormantes
FROM parcel_veille_succession;
\echo === parcel_veille_succession orphelins ===
SELECT count(DISTINCT t.parcelle_id) idu_orphelins
FROM parcel_veille_succession t LEFT JOIN parcels p ON p.idu=t.parcelle_id
WHERE p.idu IS NULL;
