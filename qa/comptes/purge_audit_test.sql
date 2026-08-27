-- AUDIT COMPTES · FIN — purge INTÉGRALE des comptes [AUDIT-TEST] (patron GB-063 : zéro orphelin).
-- On purge explicitement TOUTES les tables à compte_id (y compris les 12 SANS FK cascade, AC-003),
-- puis les comptes, puis les parcelles de test. Idempotent.
DO $$
DECLARE ids int[];
DECLARE t text;
DECLARE scoped text[] := ARRAY[
  'projets','pipeline_entries','crm_columns','saved_searches','saved_filters','signalements',
  'watched_parcels','watch_zones','alertes','veilles','veille_reprise','event_log','event_seen',
  'notif_prefs','notif_canaux','copilote_conversations','agent_runs','ia_log','usage_events',
  'courrier_demandes','lettre_zonage_refs','share_links','retours','licence_mails','evenements_compte'];
BEGIN
  SELECT array_agg(id) INTO ids FROM comptes WHERE nom LIKE '%AUDIT-TEST%';
  IF ids IS NOT NULL THEN
    -- copilote_messages via conversation (pas de compte_id direct)
    DELETE FROM copilote_messages WHERE conversation_id IN
      (SELECT id FROM copilote_conversations WHERE compte_id = ANY(ids));
    FOREACH t IN ARRAY scoped LOOP
      IF to_regclass(t) IS NOT NULL THEN
        EXECUTE format('DELETE FROM %I WHERE compte_id = ANY($1)', t) USING ids;
      END IF;
    END LOOP;
    DELETE FROM sessions_auth WHERE utilisateur_id IN (SELECT id FROM utilisateurs WHERE compte_id = ANY(ids));
    DELETE FROM utilisateurs WHERE compte_id = ANY(ids);
    DELETE FROM comptes WHERE id = ANY(ids);
  END IF;
  DELETE FROM parcels WHERE idu LIKE '974AUD%' OR idu LIKE '974A7%';
END $$;
