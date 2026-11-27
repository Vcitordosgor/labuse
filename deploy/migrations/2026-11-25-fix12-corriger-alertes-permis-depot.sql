-- OUTIL-PERMIS-FIX-12 (LOT 2) — mise à niveau des anciennes alertes de zone « permis_in_zone ».
--
-- Équivalent SQL de labuse.alertes_migration.corriger() — à passer EN PRODUCTION (non exécuté par ce
-- dépôt ailleurs que sur la base de dev `labuse`). Aligne titre / détail / fait_date sur l'ÉVÉNEMENT
-- réellement daté (dépôt affichable sinon autorisation), EXACTEMENT comme labuse.alertes.compute_alertes
-- les produit aujourd'hui. N'écrit QUE dans `alertes` ; `event_log` n'est pas touché → AUCUNE réémission
-- (ni cloche, ni digest). Idempotent (ne corrige que les lignes divergentes).
--
-- Vérifié sur `labuse` le 25/11/2026 : 3 119 lignes corrigées, 0 « Permis déposé » à dépôt invalide
-- restante. Rollback testé (sauvegarde `alertes_bak_fix12__*`).

BEGIN;

-- 1 · SAUVEGARDE datée (retour arrière : restaurer label/payload par id depuis cette table).
CREATE TABLE IF NOT EXISTS alertes_bak_fix12__deploy AS
  SELECT id, label, payload FROM alertes WHERE kind = 'permis_in_zone';

-- 2 · CORRECTION. `cond` = dépôt AFFICHABLE (année = AN_DEPOT, antérieur à l'autorisation, pas un proxy
--     1er janvier) ; l'événement daté = COALESCE(dépôt affichable, autorisation).
UPDATE alertes a SET
  label = ((CASE WHEN sp.date_depot IS NOT NULL AND sp.date IS NOT NULL AND sp.date_depot < sp.date
                   AND NOT (EXTRACT(MONTH FROM sp.date_depot) = 1 AND EXTRACT(DAY FROM sp.date_depot) = 1)
                   AND sp.raw->>'an_depot' ~ '^[0-9]{4}$'
                   AND EXTRACT(YEAR FROM sp.date_depot)::int = (sp.raw->>'an_depot')::int
                 THEN 'Permis déposé dans « ' ELSE 'Permis autorisé dans « ' END)
           || coalesce(a.payload->>'zone','') || ' »'),
  payload = a.payload || jsonb_build_object(
    'fait_date',
      COALESCE(CASE WHEN sp.date_depot IS NOT NULL AND sp.date IS NOT NULL AND sp.date_depot < sp.date
                      AND NOT (EXTRACT(MONTH FROM sp.date_depot) = 1 AND EXTRACT(DAY FROM sp.date_depot) = 1)
                      AND sp.raw->>'an_depot' ~ '^[0-9]{4}$'
                      AND EXTRACT(YEAR FROM sp.date_depot)::int = (sp.raw->>'an_depot')::int
                    THEN sp.date_depot::date END, sp.date::date),
    'detail',
      coalesce(sp.type,'Permis') || ' ' || sp.permit_id ||
      CASE WHEN sp.date_depot IS NOT NULL AND sp.date IS NOT NULL AND sp.date_depot < sp.date
             AND NOT (EXTRACT(MONTH FROM sp.date_depot) = 1 AND EXTRACT(DAY FROM sp.date_depot) = 1)
             AND sp.raw->>'an_depot' ~ '^[0-9]{4}$'
             AND EXTRACT(YEAR FROM sp.date_depot)::int = (sp.raw->>'an_depot')::int
           THEN ' déposé le ' || sp.date_depot::date::text
           WHEN sp.date IS NOT NULL THEN ' autorisé le ' || sp.date::date::text
           ELSE '' END)
FROM sitadel_permits sp
WHERE a.kind = 'permis_in_zone' AND sp.permit_id = a.source_ref
  AND (
    a.label IS DISTINCT FROM ((CASE WHEN sp.date_depot IS NOT NULL AND sp.date IS NOT NULL AND sp.date_depot < sp.date
                   AND NOT (EXTRACT(MONTH FROM sp.date_depot) = 1 AND EXTRACT(DAY FROM sp.date_depot) = 1)
                   AND sp.raw->>'an_depot' ~ '^[0-9]{4}$'
                   AND EXTRACT(YEAR FROM sp.date_depot)::int = (sp.raw->>'an_depot')::int
                 THEN 'Permis déposé dans « ' ELSE 'Permis autorisé dans « ' END)
           || coalesce(a.payload->>'zone','') || ' »')
    OR (a.payload->>'fait_date') IS DISTINCT FROM
      (COALESCE(CASE WHEN sp.date_depot IS NOT NULL AND sp.date IS NOT NULL AND sp.date_depot < sp.date
                      AND NOT (EXTRACT(MONTH FROM sp.date_depot) = 1 AND EXTRACT(DAY FROM sp.date_depot) = 1)
                      AND sp.raw->>'an_depot' ~ '^[0-9]{4}$'
                      AND EXTRACT(YEAR FROM sp.date_depot)::int = (sp.raw->>'an_depot')::int
                    THEN sp.date_depot::date END, sp.date::date))::text
  );

-- 3 · CONTRÔLE (doit renvoyer 0 ; sinon ROLLBACK la transaction).
--   SELECT count(*) FROM alertes a JOIN sitadel_permits sp ON sp.permit_id = a.source_ref
--   WHERE a.kind='permis_in_zone' AND a.label ILIKE '%déposé%'
--     AND NOT (sp.date_depot IS NOT NULL AND sp.date IS NOT NULL AND sp.date_depot < sp.date
--       AND NOT (EXTRACT(MONTH FROM sp.date_depot)=1 AND EXTRACT(DAY FROM sp.date_depot)=1)
--       AND sp.raw->>'an_depot' ~ '^[0-9]{4}$'
--       AND EXTRACT(YEAR FROM sp.date_depot)::int = (sp.raw->>'an_depot')::int);

COMMIT;

-- RETOUR ARRIÈRE :
--   UPDATE alertes a SET label = b.label, payload = b.payload
--   FROM alertes_bak_fix12__deploy b WHERE a.id = b.id;
