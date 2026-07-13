-- P1-03 (M6 Phase 2a) — correction des surfaces bâties double-comptées de dvf_mutations
-- ------------------------------------------------------------------------------------
-- Cause (audit §1.1b B4) : geo-DVF répète la ligne d'un même local pour chaque
-- subdivision fiscale (nature_culture) / disposition ; _geo_dvf_aggregate (layers_ingest.py)
-- sommait toutes les lignes résidentielles sans dédoublonner → 1 440 mutations avec
-- surface gonflée (facteur moyen ×2,6). Le code d'ingestion est corrigé (P1-03) ; ce
-- script re-fabrique les surfaces DÉJÀ stockées, en SQL pur depuis dvf_mutations_parcelle
-- (fidèle ligne à ligne à la source, vérifié BLOC A) — AUCUNE ré-ingestion externe.
--
-- Clé de dédoublonnage disponible en base (a minima, sans disposition/lot non conservés) :
-- DISTINCT (id_mutation, id_parcelle, type_local, surface_reelle_bati). Limite : deux
-- locaux identiques (même parcelle/type/surface) seraient fusionnés — borne basse
-- assumée, cas concentré sur la VEFA multi-lots, désormais EXCLUE du Baromètre.
--
-- Réversible : sauvegarde des valeurs remplacées dans m6_p103_backup_dvf_surfaces,
-- rollback = p1_03_dvf_surfaces_rollback.sql. Seule la colonne surface_reelle_bati est
-- touchée (la cascade ne lit que valeur_fonciere / surface_terrain / date / geom).

BEGIN;

CREATE TABLE m6_p103_backup_dvf_surfaces AS
SELECT m.id, m.mutation_id, m.surface_reelle_bati
FROM dvf_mutations m
JOIN (SELECT id_mutation, round(sum(surface_reelle_bati)::numeric, 2) AS sb_corr
      FROM (SELECT DISTINCT id_mutation, id_parcelle, type_local, surface_reelle_bati
            FROM dvf_mutations_parcelle
            WHERE type_local IN ('Maison', 'Appartement') AND surface_reelle_bati > 0) d
      GROUP BY id_mutation) s ON s.id_mutation = m.mutation_id
WHERE abs(m.surface_reelle_bati - s.sb_corr) > 0.01;

UPDATE dvf_mutations m
SET surface_reelle_bati = s.sb_corr
FROM (SELECT id_mutation, round(sum(surface_reelle_bati)::numeric, 2) AS sb_corr
      FROM (SELECT DISTINCT id_mutation, id_parcelle, type_local, surface_reelle_bati
            FROM dvf_mutations_parcelle
            WHERE type_local IN ('Maison', 'Appartement') AND surface_reelle_bati > 0) d
      GROUP BY id_mutation) s
WHERE s.id_mutation = m.mutation_id
  AND abs(m.surface_reelle_bati - s.sb_corr) > 0.01;

-- attendu : 1 440 lignes sauvegardées puis mises à jour (état du 13/07/2026)
SELECT count(*) AS lignes_sauvegardees FROM m6_p103_backup_dvf_surfaces;

COMMIT;
