-- ============================================================================
-- OUTIL-PERMIS-FIX-10 (LOT 3) — ARRÊT de l'alimentation résiduelle des délais fictifs.
-- Migration de mise en ligne (prod labuse-vps). À poser hors charge (aucune session
-- client, aucune passe d'ingestion Sitadel en cours). Une seule transaction.
--
-- CONTEXTE. La couche `m10_permit_delais` (délais dépôt→autorisation) est DÉCOMMISSIONNÉE
-- depuis FIX-8 : plus aucun calcul ni écran ne la LIT (axe vélocité retiré du composite,
-- copilote/caducs/dvf/défisc repointés sur la source). Mais le DÉCLENCHEUR
-- `trg_m10_permit_delais_sync` sur `sitadel_permits` restait ACTIF : chaque INSERT/UPDATE/
-- DELETE d'un permis ré-écrivait encore cette table (contre-audit ASTRA-5, point 3).
--
-- GESTE. On supprime CE déclencheur, ET LUI SEUL (le déclencheur frère
-- `trg_via_permits_geo_sync`, qui entretient la couche de voisinage SERVIE, n'est PAS
-- touché). La TABLE `m10_permit_delais` n'est PAS supprimée (décision Vic : on arrête la
-- production, on garde la table — vide de sens mais non détruite).
--
-- RÉVERSIBLE. La définition complète du déclencheur ET de sa fonction est donnée en bas
-- de ce fichier (section « RECRÉATION ») pour pouvoir le remettre à l'identique si besoin.
-- La fonction `m10_permit_delais_sync()` est laissée en place (orpheline, jamais appelée).
-- ============================================================================

BEGIN;

-- Garde : ne rien faire si le déclencheur a déjà été retiré (idempotent).
DROP TRIGGER IF EXISTS trg_m10_permit_delais_sync ON sitadel_permits;

COMMIT;

-- Vérification (hors transaction) — doit renvoyer 0 ligne :
--   SELECT tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
--   WHERE c.relname = 'sitadel_permits' AND tgname = 'trg_m10_permit_delais_sync';

-- ============================================================================
-- RECRÉATION (si un jour on veut ré-alimenter m10 — NON souhaité) — à l'identique de
-- la définition capturée le 25/11/2026 sur la base `labuse` :
--
-- CREATE OR REPLACE FUNCTION public.m10_permit_delais_sync() RETURNS trigger
--  LANGUAGE plpgsql AS $function$
-- BEGIN
--     IF to_regclass('m10_permit_delais') IS NULL THEN RETURN COALESCE(NEW, OLD); END IF;
--     IF (TG_OP = 'DELETE') THEN
--         DELETE FROM m10_permit_delais WHERE permit_id = OLD.permit_id; RETURN OLD;
--     END IF;
--     DELETE FROM m10_permit_delais WHERE permit_id = NEW.permit_id;
--     INSERT INTO m10_permit_delais
--       (permit_id, commune, nature, famille, date_depot, date_autorisation,
--        date_achevement, delai_mois, valide, computed_at)
--     SELECT s.permit_id, s.commune, s.type AS nature, s.raw->>'famille' AS famille,
--       CASE WHEN s.raw->>'an_depot' ~ '^[0-9]{4}$' THEN ((s.raw->>'an_depot')||'-01-01')::date END AS date_depot,
--       s.date::date AS date_autorisation,
--       CASE WHEN s.raw->>'daact' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN (left(s.raw->>'daact',10))::date END AS date_achevement,
--       CASE WHEN COALESCE(s.date::date >= (CASE WHEN s.raw->>'an_depot' ~ '^[0-9]{4}$' THEN ((s.raw->>'an_depot')||'-01-01')::date END), false)
--            THEN (EXTRACT(YEAR FROM s.date)::int - (s.raw->>'an_depot')::int) * 12 + (EXTRACT(MONTH FROM s.date)::int - 1) END AS delai_mois,
--       COALESCE(s.date::date >= (CASE WHEN s.raw->>'an_depot' ~ '^[0-9]{4}$' THEN ((s.raw->>'an_depot')||'-01-01')::date END), false) AS valide,
--       now()
--     FROM sitadel_permits s WHERE s.permit_id = NEW.permit_id;
--     RETURN NEW;
-- END;
-- $function$;
--
-- CREATE TRIGGER trg_m10_permit_delais_sync
--   AFTER INSERT OR UPDATE OR DELETE ON sitadel_permits
--   FOR EACH ROW EXECUTE FUNCTION m10_permit_delais_sync();
-- ============================================================================
