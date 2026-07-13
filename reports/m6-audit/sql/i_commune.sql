SET statement_timeout='120s';
\echo === commune_insee_logement ===
SELECT count(*) n, count(DISTINCT insee) n_insee, min(millesime) m_min, max(millesime) m_max,
 count(*) FILTER (WHERE logements IS NULL) log_null, min(logements) log_min, max(logements) log_max
FROM commune_insee_logement;
\echo === commune_contexte_sru ===
SELECT count(*) n, count(DISTINCT insee) n_insee, min(millesime) m_min, max(millesime) m_max,
 count(*) FILTER (WHERE taux_lls IS NULL) taux_null, min(taux_lls) t_min, max(taux_lls) t_max
FROM commune_contexte_sru;
\echo === plh_epci ===
SELECT count(*) n, count(DISTINCT epci) n_epci, count(*) FILTER (WHERE obj_logements_an IS NULL) obj_null,
 min(obj_logements_an) o_min, max(obj_logements_an) o_max
FROM plh_epci;
\echo === conso_baseline_commune ===
SELECT count(*) n, count(DISTINCT insee) n_insee, min(annee) a_min, max(annee) a_max,
 min(kwh_an_logement) k_min, max(kwh_an_logement) k_max,
 count(*) FILTER (WHERE kwh_an_logement NOT BETWEEN 500 AND 15000) k_aberrant
FROM conso_baseline_commune;
\echo === data_sources apercu ===
SELECT count(*) n, count(*) FILTER (WHERE true) FROM data_sources;
\echo === qpv generation (attrs) ===
SELECT DISTINCT jsonb_object_keys(attrs) FROM spatial_layers WHERE kind='qpv' LIMIT 20;
\echo === georisque_alea subtypes ===
SELECT subtype, count(*) FROM spatial_layers WHERE kind='georisque_alea' GROUP BY subtype ORDER BY 2 DESC;
\echo === ppr subtypes ===
SELECT subtype, count(*), count(DISTINCT commune) FROM spatial_layers WHERE kind='ppr' GROUP BY subtype ORDER BY 2 DESC;
