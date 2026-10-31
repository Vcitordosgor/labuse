-- SDP-UNIQUE-1 — Étape 0 : RESTAURATION de l'état d'avant bascule (base locale).
-- Remet le pointeur servi sur le run 1 et retire la métadonnée du run 17 (ses données
-- restent intactes dans parcel_residuel_runs). État cible = residuel_runs_AVANT.csv.
BEGIN;
UPDATE residuel_runs SET is_served = false WHERE is_served;
UPDATE residuel_runs SET is_served = true  WHERE run_seq = 1;
DELETE FROM residuel_runs WHERE run_seq = 17;
COMMIT;
