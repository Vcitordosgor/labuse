-- V8-VERIF — requêtes de provenance (POINT A), lecture seule. Aucune écriture.
-- Usage : psql <dsn> -f scripts/verif_v8_provenance.sql

-- A.1/A.2 — horodatage + rules_version par commune (reprises vs post-refonte)
SELECT p.commune, count(*) n,
       min(d.created_at) premier, max(d.created_at) dernier,
       count(DISTINCT d.rules_version) n_rulesver
FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
WHERE d.run_label = 'q_v8_calibre'
GROUP BY p.commune ORDER BY premier;

-- rules_version : valeur unique sur tout le run ?
SELECT d.rules_version, count(DISTINCT p.commune) n_communes, count(*) n_lignes,
       min(d.created_at) premier, max(d.created_at) dernier
FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
WHERE d.run_label = 'q_v8_calibre' GROUP BY d.rules_version ORDER BY premier;

-- trous d'horodatage entre communes (frontière éventuelle de deux exécutions)
WITH e AS (SELECT p.commune, min(d.created_at) mn, max(d.created_at) mx
           FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
           WHERE d.run_label = 'q_v8_calibre' GROUP BY p.commune)
SELECT commune, mn, mx, mn - lag(mx) OVER (ORDER BY mn) AS trou_depuis_precedente
FROM e ORDER BY mn;

-- A.3 — header du run de score (sha champion figé, horodatage, durée)
SELECT run_id, model_version, left(model_sha256, 16) sha, computed_at, duration_s, params
FROM p_score_v2_runs WHERE run_id = 'q_v8_calibre';

-- écart signalé : horodatage de migration de parcel_residuel (lu par residuel_socle)
SELECT date_trunc('minute', computed_at) minute, count(*) FROM parcel_residuel GROUP BY 1 ORDER BY 1;

-- ─────────────────────────────────────────────────────────────────────────────
-- CONTRÔLE DE SUBSTITUTION (A.4) — PROPOSÉ, NON EXÉCUTÉ (interdit : recalcul sans validation).
-- Recalcul à blanc de 50 reprises Saint-Paul dans un label isolé, comparaison des champs
-- DÉTERMINISTES aux valeurs stockées. À lancer via un script Python dédié SEULEMENT sur feu vert.
-- ─────────────────────────────────────────────────────────────────────────────
