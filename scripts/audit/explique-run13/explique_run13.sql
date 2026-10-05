-- EXPLIQUE-RUN13 — comparaison run servi (run_seq=10, q_v15) vs run 13 (q_v16).
-- Lecture seule. Rejouable : PGUSER=openclaw psql -d labuse -f explique_run13.sql
-- Famille de cause = split_part(cause,':',1) ; cause vide/NULL => 'calculee'.

\pset pager off
\set SERVI 10
\set QV16  13

-- Base : une ligne par parcelle avec famille + sdp + signaux des deux runs.
DROP TABLE IF EXISTS _er13;
CREATE TEMP TABLE _er13 AS
SELECT
  p.id                                         AS parcel_id,
  p.commune,
  z.zone_fam,
  z.zone_lib,
  (p.commune IS NOT NULL)                       AS _has_commune,
  CASE WHEN coalesce(a.cause,'')='' THEN 'calculee' ELSE split_part(a.cause,':',1) END AS fam_servi,
  CASE WHEN coalesce(b.cause,'')='' THEN 'calculee' ELSE split_part(b.cause,':',1) END AS fam_qv16,
  coalesce(a.cause,'')='' AS calc_servi,
  coalesce(b.cause,'')='' AS calc_qv16,
  coalesce(a.sdp_residuelle_m2,0) AS sdp_servi,
  coalesce(b.sdp_residuelle_m2,0) AS sdp_qv16,
  a.taux_emprise_pct AS te_servi,
  b.taux_emprise_pct AS te_qv16,
  b.hauteur_source   AS hsrc_qv16,
  b.assiette_source  AS asrc_qv16,
  a.assiette_source  AS asrc_servi,
  coalesce(b.regles_non_modelisees,'') AS rnm_qv16,
  b.cause AS cause_qv16,
  substring(p.idu for 5) AS insee,
  z.zone_lib AS zlib
FROM parcels p
JOIN parcel_residuel_runs a ON a.parcel_id=p.id AND a.run_seq=:SERVI
JOIN parcel_residuel_runs b ON b.parcel_id=p.id AND b.run_seq=:QV16
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu;

\echo '==================== (0) CONTROLE TOTAUX ===================='
SELECT count(*) parcelles,
       sum(sdp_servi) sdp_servi, sum(sdp_qv16) sdp_qv16,
       sum(sdp_qv16)-sum(sdp_servi) delta_sdp
FROM _er13;

\echo '==================== (1) MATRICE DE TRANSITION (famille servi -> qv16) ===================='
SELECT fam_servi, fam_qv16, count(*) AS n,
       sum(sdp_qv16-sdp_servi) AS delta_sdp
FROM _er13
GROUP BY fam_servi, fam_qv16
HAVING fam_servi IS DISTINCT FROM fam_qv16 OR TRUE
ORDER BY (fam_servi<>fam_qv16) DESC, n DESC;

\echo '---- (1b) transitions NON diagonales seulement ----'
SELECT fam_servi, fam_qv16, count(*) n, sum(sdp_qv16-sdp_servi) delta_sdp
FROM _er13 WHERE fam_servi<>fam_qv16
GROUP BY fam_servi, fam_qv16 ORDER BY n DESC;

\echo '==================== (3a) DECOMPOSITION FLUX (sommes a +14M) ===================='
SELECT
  count(*) FILTER (WHERE calc_servi AND calc_qv16)          AS stayers,
  sum(sdp_qv16-sdp_servi) FILTER (WHERE calc_servi AND calc_qv16) AS d_stayers,
  count(*) FILTER (WHERE calc_servi AND NOT calc_qv16)      AS leavers,
  sum(0-sdp_servi) FILTER (WHERE calc_servi AND NOT calc_qv16) AS d_leavers,
  count(*) FILTER (WHERE NOT calc_servi AND calc_qv16)      AS enterers,
  sum(sdp_qv16) FILTER (WHERE NOT calc_servi AND calc_qv16) AS d_enterers
FROM _er13;

\echo '==================== (3b) VENTILATION PAR COMMUNE ===================='
SELECT commune,
       sum(sdp_qv16-sdp_servi) AS delta_sdp,
       count(*) FILTER (WHERE calc_servi AND calc_qv16 AND sdp_qv16<>sdp_servi) AS n_stayers_chg,
       count(*) FILTER (WHERE calc_servi AND NOT calc_qv16) AS n_leavers
FROM _er13
GROUP BY commune ORDER BY delta_sdp DESC;

\echo '==================== (3c) VENTILATION PAR FAMILLE DE ZONE ===================='
SELECT coalesce(zone_fam,'(hors zonage)') zone_fam,
       sum(sdp_qv16-sdp_servi) AS delta_sdp,
       count(*) FILTER (WHERE calc_servi OR calc_qv16) AS n_calc_either
FROM _er13
GROUP BY zone_fam ORDER BY delta_sdp DESC;

\echo '==================== (3d) ATTRIBUTION PAR CAUSE/MECANISME (partition exclusive, somme a +14M) ===================='
-- Priorite d assignation d un bucket par parcelle :
--   LEAVER_TE        : calc->terrain_exigu           (perte)
--   LEAVER_PLU       : calc->regle_plu_non_validee   (perte, PLU-VERIF faux corriges)
--   ENTERER          : bloque->calc                  (gain, oracle AU->U / chasse)
--   EXC_PLU_BRASPANON: stayer, zone Ub/1AUb insee 97402 (exceptions PLU modifie_calcul appliquees)
--   EMPRISE          : stayer, emprise (taux_emprise_pct) changee. NB (preuve section (3) du
--                      rapport) : co-symptome du recalcul du BATI EXISTANT (LiDAR lot C : emprise
--                      toit->plancher x0,95 + niveaux egout), PAS de l'assiette max (parcelles NU
--                      a plat, -0,1M). N'attribuez pas ce bucket a pm1/gabarit.
--   HAUTEUR_LIDAR    : stayer, emprise identique, hauteur_source=lidar
--   HAUTEUR_AUTRE    : stayer, emprise identique, hauteur_source<>lidar
--   INCHANGE         : stayer, sdp identique
WITH bucketed AS (
  SELECT (sdp_qv16-sdp_servi) AS d,
    CASE
      WHEN calc_servi AND NOT calc_qv16 AND fam_qv16='terrain_exigu'         THEN '1_LEAVER_TERRAIN_EXIGU'
      WHEN calc_servi AND NOT calc_qv16 AND fam_qv16='regle_plu_non_validee' THEN '2_LEAVER_REGLE_PLU'
      WHEN calc_servi AND NOT calc_qv16                                      THEN '3_LEAVER_AUTRE'
      WHEN NOT calc_servi AND calc_qv16                                      THEN '4_ENTERER'
      WHEN calc_servi AND calc_qv16 AND insee='97402' AND zlib IN ('Ub','1AUb') THEN '5_EXC_PLU_BRASPANON'
      WHEN calc_servi AND calc_qv16 AND te_servi IS DISTINCT FROM te_qv16    THEN '6_EMPRISE'
      WHEN calc_servi AND calc_qv16 AND sdp_qv16=sdp_servi                   THEN '9_INCHANGE'
      WHEN calc_servi AND calc_qv16 AND hsrc_qv16='lidar'                    THEN '7_HAUTEUR_LIDAR'
      WHEN calc_servi AND calc_qv16                                          THEN '8_HAUTEUR_AUTRE'
      ELSE '0_AUTRE'
    END AS bucket
  FROM _er13
)
SELECT bucket, count(*) n, sum(d) AS delta_sdp,
       count(*) FILTER (WHERE d>0) n_up, count(*) FILTER (WHERE d<0) n_down
FROM bucketed GROUP BY bucket ORDER BY bucket;

\echo '---- (3d-total) controle : somme des buckets ----'
WITH bucketed AS (
  SELECT (sdp_qv16-sdp_servi) AS d FROM _er13
)
SELECT sum(d) AS total_delta_doit_etre_13987424 FROM bucketed;

-- ============================================================================
-- (2) 20 EXEMPLES calculee->terrain_exigu (tirage reproductible md5(idu||seed))
--     + categorisation des 8637 bascules + part red-PPR / autres SUP.
-- (4) 30 temoins SCORING-5 : sdp run10 (servi) vs run13 (qv16).
-- Ces requetes sont documentees dans le rapport ; corps complet rejoue a la main
-- (voir docs/audit-2026-10/EXPLIQUE-RUN13.md, section Methode).
-- ============================================================================
