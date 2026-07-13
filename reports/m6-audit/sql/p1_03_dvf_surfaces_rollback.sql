-- P1-03 — ROLLBACK de p1_03_dvf_surfaces_fix.sql
-- Restaure les surfaces bâties d'origine de dvf_mutations depuis la sauvegarde,
-- puis supprime la table de sauvegarde.

BEGIN;

UPDATE dvf_mutations m
SET surface_reelle_bati = b.surface_reelle_bati
FROM m6_p103_backup_dvf_surfaces b
WHERE b.id = m.id;

DROP TABLE m6_p103_backup_dvf_surfaces;

COMMIT;
