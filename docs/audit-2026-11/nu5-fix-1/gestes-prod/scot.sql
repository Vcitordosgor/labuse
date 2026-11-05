-- NU5-FIX-1 — GESTE PROD E-1 : corriger le STATUT/la DATE des 3 SCOT de La Réunion (spatial_layers
-- kind='scot'), puis re-dérouler le cache fiche commune. Le code sert désormais `scot` au payload
-- (app.py) et le front n'affiche « approuvé le {date} » QUE si le statut est approuvé.
--   · Grand Sud : stocké « en projet » + date 02/09/2024 (= modification simplifiée) → en réalité
--     APPROUVÉ le 18/02/2020 (la modif simplifiée ne change pas le statut « approuvé »).
--   · TCO : date stockée 03/10/2022 (= modification n°1) → approbation de base 21/12/2016.
--   · CINOR : approuvé sans date → 18/12/2013.
-- À appliquer sur prod (hors 01–05 h), puis `labuse jobs run fiche-commune-cache`.
BEGIN;
SELECT id, name, attrs->>'statut' AS statut, attrs->>'date_approbation' AS date_appro
FROM spatial_layers WHERE kind='scot' ORDER BY name;   -- AVANT

UPDATE spatial_layers SET subtype='approuve',
  attrs = jsonb_set(jsonb_set(attrs, '{statut}', '"approuvé"'),
                    '{date_approbation}', '"2020-02-18"')
WHERE kind='scot' AND name='SCOT DU GRAND SUD';

UPDATE spatial_layers SET
  attrs = jsonb_set(attrs, '{date_approbation}', '"2016-12-21"')
WHERE kind='scot' AND name='SCOT TCO';

UPDATE spatial_layers SET
  attrs = jsonb_set(attrs, '{date_approbation}', '"2013-12-18"')
WHERE kind='scot' AND name='SCOT DE LA CINOR';

SELECT id, name, attrs->>'statut' AS statut, attrs->>'date_approbation' AS date_appro
FROM spatial_layers WHERE kind='scot' ORDER BY name;   -- APRÈS
COMMIT;
