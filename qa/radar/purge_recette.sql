-- RADAR-CATÉGORIE (T6) — PURGE du jeu de recette [RADAR-TEST]. Idempotent.
-- Retire toute donnée de test (bien_id >= 900000) des 5 tables pige_*, dans l'ordre des FK.
BEGIN;
DELETE FROM pige_prix_historique WHERE bien_id >= 900000;
DELETE FROM pige_clics           WHERE bien_id >= 900000;
DELETE FROM pige_captures        WHERE bien_id >= 900000;
DELETE FROM pige_annonces        WHERE bien_id >= 900000;
DELETE FROM pige_faits           WHERE bien_id >= 900000;
DELETE FROM pige_biens           WHERE bien_id >= 900000;
-- veilles Radar créées par la recette (compte NULL, désactivées) — jamais les veilles d'un client
-- réel (compte_id non NULL) ni une veille active.
DELETE FROM veilles WHERE type = 'radar' AND compte_id IS NULL AND NOT actif;
COMMIT;
