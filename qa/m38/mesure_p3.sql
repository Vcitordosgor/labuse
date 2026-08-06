-- M38 Phase 3 — MESURE À BLANC : « dynamique constructive » (SitadelLayer) redatée sur le DÉPÔT.
-- Aucune écriture servie. Reproduit exactement la feature servie (config q_v8_calibre) :
--   rayon 400 m · fenêtre 60 mois · PC seuls · saturation 15 · magnitude = min(1, n/15).
-- Compare la fenêtre par date d'AUTORISATION (servie) vs par date de DÉPÔT (coalesce dépôt→auto).
\set ON_ERROR_STOP on
SET client_min_messages = warning;

-- PC géolocalisés, transformés une fois en 2975 (métrique), avec les deux dates.
CREATE TEMP TABLE _pc AS
SELECT ST_Transform(geom, 2975) AS g2,
       date::date               AS d_auth,
       coalesce(date_depot, date::date) AS d_dep
FROM sitadel_permits
WHERE type = 'PC' AND geom IS NOT NULL;
CREATE INDEX ON _pc USING gist (g2);

-- Centroïdes parcelles en 2975.
CREATE TEMP TABLE _pc_parc AS
SELECT id, commune, ST_Transform(centroid, 2975) AS c2
FROM parcels WHERE centroid IS NOT NULL;
CREATE INDEX ON _pc_parc USING gist (c2);

-- Comptes par parcelle sous les deux datations (mêmes règles NULL que la feature servie).
CREATE TEMP TABLE _dyn AS
SELECT pa.id, pa.commune,
  count(*) FILTER (WHERE pc.d_auth IS NULL OR pc.d_auth >= current_date - interval '60 months') AS n_auth,
  count(*) FILTER (WHERE pc.d_dep  IS NULL OR pc.d_dep  >= current_date - interval '60 months') AS n_dep
FROM _pc_parc pa
JOIN _pc pc ON ST_DWithin(pa.c2, pc.g2, 400)
GROUP BY pa.id, pa.commune;

-- magnitudes servies (plafond 15) ; on ne garde que les parcelles touchées par ≥1 PC.
CREATE TEMP TABLE _cmp AS
SELECT id, commune, n_auth, n_dep,
       least(1.0, n_auth/15.0) AS mag_auth,
       least(1.0, n_dep/15.0)  AS mag_dep
FROM _dyn WHERE n_auth > 0 OR n_dep > 0;

\echo '=== 1. Population touchée (au moins un PC dans 400 m sous l une des deux datations) ==='
SELECT count(*) AS parcelles_touchees,
       count(*) FILTER (WHERE n_auth <> n_dep) AS comptage_differe,
       count(*) FILTER (WHERE mag_auth <> mag_dep) AS magnitude_change,
       round(100.0*count(*) FILTER (WHERE mag_auth <> mag_dep)/count(*),2) AS pct_mag_change
FROM _cmp;

\echo '=== 2. Bascule du SIGNAL (0 <-> >0) : gagné / perdu ==='
SELECT
  count(*) FILTER (WHERE n_auth = 0 AND n_dep > 0) AS signal_gagne_depot,
  count(*) FILTER (WHERE n_auth > 0 AND n_dep = 0) AS signal_perdu_depot
FROM _cmp;

\echo '=== 3. Direction du changement de magnitude ==='
SELECT
  count(*) FILTER (WHERE mag_dep > mag_auth) AS magnitude_hausse,
  count(*) FILTER (WHERE mag_dep < mag_auth) AS magnitude_baisse,
  round(avg(mag_dep - mag_auth) FILTER (WHERE mag_auth <> mag_dep), 4) AS delta_moyen_signe
FROM _cmp;

\echo '=== 4. Amplitude des comptes (redate = plus ancien -> attendu: baisses au bord de fenetre) ==='
SELECT round(avg(n_dep - n_auth), 3) AS delta_compte_moyen,
       min(n_dep - n_auth) AS delta_min, max(n_dep - n_auth) AS delta_max
FROM _cmp;

\echo '=== 5. Communes qui bougent le plus (parcelles a magnitude changee) — top 15 ==='
SELECT commune,
       count(*) FILTER (WHERE mag_auth <> mag_dep) AS parcelles_mag_change,
       count(*) AS parcelles_touchees,
       round(100.0*count(*) FILTER (WHERE mag_auth <> mag_dep)/count(*),1) AS pct
FROM _cmp GROUP BY commune
HAVING count(*) FILTER (WHERE mag_auth <> mag_dep) > 0
ORDER BY parcelles_mag_change DESC LIMIT 15;
