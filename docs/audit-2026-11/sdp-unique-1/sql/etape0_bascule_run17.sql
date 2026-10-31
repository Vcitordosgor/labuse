-- SDP-UNIQUE-1 — Étape 0 : aligner le Mac sur la prod (BASE LOCALE SEULEMENT).
--
-- Constat PROD-VERIF-1 point 1 : le Mac SERT le run résiduel legacy 1 (label 'servi',
-- aucune date, assiette_source NULL sur 431 663/431 663 lignes), alors que la prod sert
-- le run 17 q_v20 (calculé le 21/10/2026, 38,8 % NULL). Les DONNÉES du run 17 sont déjà
-- présentes dans parcel_residuel_runs sur le Mac (433 229 lignes, 168 106 NULL = 38,80 %,
-- chiffre IDENTIQUE à la prod) — seule la MÉTADONNÉE residuel_runs n'a pas été migrée, et
-- le pointeur is_served est resté collé au run 1.
--
-- Geste (une bascule du pointeur servi, réversible) :
--   1. enregistrer la métadonnée du run 17 (absente sur le Mac ; présente en prod) ;
--   2. flip is_served : run 1 -> run 17 (logique set_served(), deux UPDATE atomiques).
-- La vue parcel_residuel sert dès lors le run 17, comme en prod.
BEGIN;

INSERT INTO residuel_runs
  (run_seq, label, is_served, is_pinned, computed_at_min, computed_at_max, note)
VALUES
  (17, 'q_v20', false, false,
   '2026-10-21 01:42:38.931413+04', '2026-10-21 07:00:05.354582+04',
   'SDP-UNIQUE-1 étape 0 — alignement Mac sur prod : métadonnée du run servi en prod '
   '(données déjà présentes dans parcel_residuel_runs). Bascule locale réversible.')
ON CONFLICT (run_seq) DO NOTHING;

UPDATE residuel_runs SET is_served = false WHERE is_served;
UPDATE residuel_runs SET is_served = true  WHERE run_seq = 17;

COMMIT;
