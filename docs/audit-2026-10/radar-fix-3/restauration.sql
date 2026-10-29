-- RADAR-FIX-3 — RESTAURATION des 60 biens faussement retirés par la passe de confirmation #274
-- (28/10, 23:03→23:17, 60/60 « supprimée »). NE S'EXÉCUTE QU'AVEC LE GO DE VIC, après sauvegarde
-- vérifiée. UNE SEULE transaction, EXACTEMENT ces 60 bien_id, garde-fous qui ANNULENT en cas d'écart.
--
-- Pré-requis (geste de Vic) : sauvegarde fraîche vérifiée juste avant, p.ex.
--   sudo -u postgres /opt/labuse/app/deploy/scripts/backup_postgres.sh   (puis pg_restore --list)
--   (une sauvegarde pleine vérifiée existe déjà : /var/backups/labuse/labuse-labuse-20261029-030308.dump,
--    1748 objets, prise APRÈS l'incident → contient les 60 en « retiree ».)
--
-- Lancement :
--   ssh labuse-vps 'sudo -u postgres psql -d labuse -v ON_ERROR_STOP=1 -1 -f -' < restauration.sql
--   (-1 = toute la commande en UNE transaction ; ON_ERROR_STOP + RAISE = annulation totale si un
--    garde-fou saute).

\set ids '114,115,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,184,185,186,187,189,207,208'

BEGIN;

-- 1) FILET de réversibilité : l'état AVANT des 60 lignes, horodaté (table d'audit conservée).
DROP TABLE IF EXISTS pige_restauration_radarfix3;
CREATE TABLE pige_restauration_radarfix3 AS
SELECT bien_id, statut, retiree_le, vendue_le, vendue_valeur, vendue_delai_j, vendue_ecart_prix,
       now() AS capture_at
FROM pige_biens
WHERE bien_id IN (:ids);

-- 2) GARDE-FOU (avant toute écriture) : EXACTEMENT 60, toutes « retiree », AUCUNE vente DVF.
--    Si l'une a acquis une vente DVF depuis la mesure (vraie vente) → on ANNULE tout, on ne l'écrase pas.
DO $$
DECLARE n int; n_pas_retiree int; n_vendue int;
BEGIN
  SELECT count(*),
         count(*) FILTER (WHERE statut <> 'retiree'),
         count(*) FILTER (WHERE statut = 'vendue' OR vendue_le IS NOT NULL)
    INTO n, n_pas_retiree, n_vendue
  FROM pige_restauration_radarfix3;
  IF n <> 60 THEN RAISE EXCEPTION 'Attendu 60 biens, trouvé % — ANNULATION.', n; END IF;
  IF n_pas_retiree <> 0 THEN RAISE EXCEPTION '% bien(s) ne sont pas « retiree » — ANNULATION.', n_pas_retiree; END IF;
  IF n_vendue <> 0 THEN RAISE EXCEPTION '% bien(s) ont une vente DVF — NE PAS écraser, ANNULATION (re-mesurer).', n_vendue; END IF;
END $$;

-- 3) RESTAURATION : on les remet TOUS en actif ; retiree_le + vendue_* à NULL. Ces 60 SEULEMENT.
UPDATE pige_biens
SET statut = 'active',
    retiree_le = NULL,
    vendue_le = NULL, vendue_valeur = NULL, vendue_delai_j = NULL, vendue_ecart_prix = NULL
WHERE bien_id IN (:ids);

-- 4) VÉRIFICATION post (doit lire : 60 | 0 | 0).
SELECT count(*) FILTER (WHERE statut = 'active') AS actifs,
       count(retiree_le)                          AS reste_retiree_le,
       count(vendue_le)                           AS reste_vendue
FROM pige_biens
WHERE bien_id IN (:ids);

COMMIT;

-- Réversibilité (si besoin de revenir en arrière) :
--   UPDATE pige_biens b SET statut = r.statut, retiree_le = r.retiree_le,
--       vendue_le = r.vendue_le, vendue_valeur = r.vendue_valeur,
--       vendue_delai_j = r.vendue_delai_j, vendue_ecart_prix = r.vendue_ecart_prix
--   FROM pige_restauration_radarfix3 r WHERE b.bien_id = r.bien_id;
