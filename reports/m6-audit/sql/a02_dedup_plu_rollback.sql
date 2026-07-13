-- Rollback A-02 : réinsère les lignes supprimées depuis la sauvegarde.
BEGIN;
INSERT INTO spatial_layers SELECT * FROM m6_a02_backup_plu_dup;
DROP TABLE m6_a02_backup_plu_dup;
COMMIT;
