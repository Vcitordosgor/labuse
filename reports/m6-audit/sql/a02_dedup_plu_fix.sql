-- M6 Phase 2b (A-02) — dédoublonnage des géométries PLU dupliquées inter-communes
-- ---------------------------------------------------------------------------------
-- Cause (audit M5.1 A1 + M6 §1.3b B1) : ingestion GPU par BBOX de commune → les
-- polygones chevauchant une limite communale sont ingérés une fois PAR commune ;
-- la cascade (prime() sans filtre commune) SOMME les intersections → recouvrements
-- gonflés (témoin 97423000AB1341 : « N 95 % » au lieu de N 47,5 %), 1 386 HARD_EXCLUDE
-- zonage infondés, 967 zones majoritaires fausses.
-- Règle de conservation VÉRIFIÉE : dans chaque groupe md5(geom), l'exemplaire légitime
-- est celui rattaché à la commune dont le document GPU l'a produit
-- (attrs->>'partition' = 'DU_' || insee(commune)). Les copies « débordement bbox »
-- rattachées aux voisines sont supprimées.
-- Périmètre : kind IN ('plu_gpu_zone', 'plu_gpu_prescription') — la famille PLU (A-02).
-- parc_national (A2 M5.1) et les autres kinds (M6-01) restent consignés (mandat séparé).
-- Réversible : lignes supprimées sauvegardées dans m6_a02_backup_plu_dup ;
-- rollback = a02_dedup_plu_rollback.sql.

BEGIN;

CREATE TABLE m6_a02_backup_plu_dup AS
WITH com AS (SELECT commune, min(left(idu,5)) AS insee FROM parcels GROUP BY commune),
dup AS (
  SELECT sl.id, sl.kind, md5(ST_AsBinary(sl.geom)) AS h,
         (sl.attrs->>'partition' = 'DU_'||c.insee) AS legit
  FROM spatial_layers sl JOIN com c ON c.commune = sl.commune
  WHERE sl.kind IN ('plu_gpu_zone', 'plu_gpu_prescription')
),
grp AS (
  SELECT kind, h FROM dup GROUP BY kind, h
  HAVING count(*) > 1 AND bool_or(legit)   -- au moins un légitime, sinon on ne touche pas
)
SELECT sl.* FROM spatial_layers sl
JOIN dup d ON d.id = sl.id JOIN grp g ON g.kind = d.kind AND g.h = d.h
WHERE NOT d.legit;

DELETE FROM spatial_layers WHERE id IN (SELECT id FROM m6_a02_backup_plu_dup);

-- contrôles : plus aucun doublon avec légitime ; volumes attendus ~458 (zones) + ~7 2xx (prescriptions)
SELECT kind, count(*) AS supprimees FROM m6_a02_backup_plu_dup GROUP BY kind;

COMMIT;
