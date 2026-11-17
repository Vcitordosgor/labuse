-- VERITE-TERRAIN-3 — LOT 1 : cohortes H / hors-règles / R / T, entonnoir chiffré.
-- Lecture seule : tables TEMPORAIRES de session uniquement, sorties en CSV (\copy).
-- Rejouer : psql -U openclaw -d labuse -v dir="<dossier de sortie>" -f cohortes.sql

\set ON_ERROR_STOP on

-- Date des règles actuelles par commune = millésime du règlement MODÉLISÉ par LABUSE
-- (config/plu_destinations/<insee>_*.yaml, meta.millesime — même source que VERITE-TERRAIN-2).
-- 97417 Saint-Philippe est au RNU : pas de date, commune EXCLUE de H (décrite à part).
CREATE TEMP TABLE t_millesime (insee text PRIMARY KEY, millesime date);
INSERT INTO t_millesime VALUES
 ('97401','2024-12-06'),('97402','2026-04-28'),('97403','2024-09-24'),('97404','2025-09-17'),
 ('97405','2023-06-09'),('97406','2023-05-27'),('97407','2024-12-09'),('97408','2025-12-17'),
 ('97409','2019-02-28'),('97410','2020-02-06'),('97411','2026-08-05'),('97412','2025-12-10'),
 ('97413','2007-02-26'),('97414','2025-12-18'),('97415','2025-12-17'),('97416','2024-06-25'),
 ('97418','2025-11-26'),('97419','2019-05-04'),('97420','2025-09-29'),('97421','2022-05-24'),
 ('97422','2023-08-11'),('97423','2022-06-02'),('97424','2024-02-13');

-- ── Étape 0 → 5 : du stock brut aux PC logements créateurs non annulés ──────────────────
CREATE TEMP TABLE t_base AS
SELECT permit_id, type,
       raw->>'insee'                          AS insee,
       commune,
       COALESCE(date::date, date_depot)       AS d_aut,
       raw->>'etat'                           AS etat,
       CASE WHEN raw->>'surf_hab' ~ '^[0-9.]+$' THEN (raw->>'surf_hab')::float ELSE 0 END AS surf_hab,
       CASE WHEN raw->>'nb_lgt'  ~ '^[0-9]+$'  THEN (raw->>'nb_lgt')::int     ELSE 0 END AS nb_lgt,
       idu_codes,
       idu_codes::text                        AS ic,
       jsonb_array_length(idu_codes)          AS n_parc,
       raw->>'daact'                          AS daact
FROM sitadel_permits;

SELECT 'E0 stock sitadel_permits' AS etape, count(*) FROM t_base
UNION ALL SELECT 'E1 type PC', count(*) FROM t_base WHERE type='PC'
UNION ALL SELECT 'E2 + famille logements', count(*) FROM sitadel_permits WHERE type='PC' AND raw->>'famille'='logements'
UNION ALL SELECT 'E3 + crée surface ou logements', count(*) FROM t_base b
  WHERE type='PC' AND EXISTS (SELECT 1 FROM sitadel_permits s WHERE s.permit_id=b.permit_id AND s.raw->>'famille'='logements')
    AND (surf_hab>0 OR nb_lgt>0)
UNION ALL SELECT 'E4 + non annulé (etat<>4)', count(*) FROM t_base b
  WHERE type='PC' AND EXISTS (SELECT 1 FROM sitadel_permits s WHERE s.permit_id=b.permit_id AND s.raw->>'famille'='logements')
    AND (surf_hab>0 OR nb_lgt>0) AND COALESCE(etat,'')<>'4'
UNION ALL SELECT 'E5 + date connue et insee connu', count(*) FROM t_base b
  WHERE type='PC' AND EXISTS (SELECT 1 FROM sitadel_permits s WHERE s.permit_id=b.permit_id AND s.raw->>'famille'='logements')
    AND (surf_hab>0 OR nb_lgt>0) AND COALESCE(etat,'')<>'4' AND d_aut IS NOT NULL AND insee IS NOT NULL;

CREATE TEMP TABLE t_e5 AS
SELECT b.* FROM t_base b
WHERE type='PC'
  AND EXISTS (SELECT 1 FROM sitadel_permits s WHERE s.permit_id=b.permit_id AND s.raw->>'famille'='logements')
  AND (surf_hab>0 OR nb_lgt>0) AND COALESCE(etat,'')<>'4'
  AND d_aut IS NOT NULL AND insee IS NOT NULL;

-- ── Étape 6 : dédoublonnage ──────────────────────────────────────────────────────────────
-- 6a doublons EXACTS (mêmes parcelles + même surface + mêmes logements) → garde le permit_id min.
-- 6b resoumission/modificatif (même assiette ic, projets ≠) → garde le PLUS RÉCENT (d_aut max,
--    départage permit_id max). Les « M » Sit@del n'ont pas de base en table (mesuré : 131, 0 base).
CREATE TEMP TABLE t_dedup AS
SELECT DISTINCT ON (ic) *
FROM (
  SELECT DISTINCT ON (ic, surf_hab, nb_lgt) * FROM t_e5
  ORDER BY ic, surf_hab, nb_lgt, permit_id
) exacts
ORDER BY ic, d_aut DESC, permit_id DESC;

SELECT 'E6 dédoublonné (exacts puis même assiette→plus récent)' AS etape, count(*) FROM t_dedup;

-- ── Étape 7 : toutes les parcelles du permis existent au cadastre actuel ────────────────
CREATE TEMP TABLE t_e7 AS
SELECT d.* FROM t_dedup d
WHERE NOT EXISTS (
  SELECT 1 FROM jsonb_array_elements_text(d.idu_codes) i
  WHERE NOT EXISTS (SELECT 1 FROM parcels p WHERE p.idu = i AND p.cadastre_disparue_le IS NULL));

SELECT 'E7 + toutes parcelles au cadastre actuel' AS etape, count(*) FROM t_e7;

-- ── Étape 8 : post-règles actuelles → H ; antérieurs → hors-règles (décrits à part) ─────
CREATE TEMP TABLE t_h AS
SELECT e.*, m.millesime,
       (e.n_parc = 1)                            AS mono,
       CASE WHEN e.nb_lgt >= 2 THEN 'collectif_ou_groupe'
            WHEN e.nb_lgt = 1 THEN 'individuel'
            ELSE 'surface_sans_logement' END     AS type_projet
FROM t_e7 e JOIN t_millesime m USING (insee)
WHERE e.d_aut > m.millesime;

CREATE TEMP TABLE t_horsregles AS
SELECT e.*, m.millesime FROM t_e7 e JOIN t_millesime m USING (insee)
WHERE e.d_aut <= m.millesime;

SELECT 'E8a H (post-règles actuelles)' AS etape, count(*) FROM t_h
UNION ALL SELECT 'E8b hors-règles (antérieurs, décrits à part)', count(*) FROM t_horsregles
UNION ALL SELECT 'E8c exclus 97417 St-Philippe RNU (sans date de règles)', count(*) FROM t_e7 WHERE insee='97417';

SELECT 'H mono-parcelle' AS coupe, count(*) FROM t_h WHERE mono
UNION ALL SELECT 'H multi-parcelles', count(*) FROM t_h WHERE NOT mono
UNION ALL SELECT 'H individuel (1 logt)', count(*) FROM t_h WHERE type_projet='individuel'
UNION ALL SELECT 'H collectif/groupé (≥2 logts)', count(*) FROM t_h WHERE type_projet='collectif_ou_groupe'
UNION ALL SELECT 'H surface sans logement compté', count(*) FROM t_h WHERE type_projet='surface_sans_logement';
-- NB : la typologie Sit@del individuel/collectif/résidence N'EST PAS dans la donnée ingérée
-- (pas de NB_LGT_IND/COL/RES) → approximation par nb_lgt, dite telle quelle.

-- ── Cohorte R : permis récents de H dont le projet n'est PAS encore dans le bâti connu ──
-- mono-parcelle, jamais commencé (etat='2', seul état sans DAACT ni chantier), autorisé
-- depuis le 2025-01-01, ET parcelle encore NUE dans le bâti que LABUSE connaît
-- (p_model_bati : absente ou emprise < 20 m²) — double verrou état Sit@del × bâti LABUSE.
CREATE TEMP TABLE t_r AS
SELECT h.*, (SELECT i FROM jsonb_array_elements_text(h.idu_codes) i LIMIT 1) AS idu,
       COALESCE(pb.emprise_bati_m2, 0) AS emprise_bati_m2,
       p.surface_m2
FROM t_h h
JOIN parcels p ON p.idu = (SELECT i FROM jsonb_array_elements_text(h.idu_codes) i LIMIT 1)
LEFT JOIN p_model_bati pb ON pb.idu = p.idu
WHERE h.mono AND h.etat = '2' AND h.d_aut >= DATE '2025-01-01'
  AND COALESCE(pb.emprise_bati_m2, 0) < 20;

SELECT 'R (H mono, etat=2, ≥2025-01-01, bâti LABUSE <20 m²)' AS etape, count(*) FROM t_r;

-- ── Cohorte T : 3 comparables SANS permis par parcelle de R, graine fixe ────────────────
-- même commune, même famille de zone (parcel_zone_plu.zone_fam), même état nu
-- (bâti LABUSE < 20 m²), surface ± 30 %, jamais citée par AUCUN permis sitadel.
-- Tirage DÉTERMINISTE : ordre md5(idu || 'VT3-T-2026-11-15') — la « graine » est la chaîne.
CREATE TEMP TABLE t_t AS
SELECT r_idu, idu, commune, zone_fam, surface_m2 FROM (
  SELECT r.idu AS r_idu, c.idu, c.commune, zr.zone_fam, c.surface_m2,
         -- la graine entre AVEC l'idu de R : chaque parcelle de R a son propre ordre aléatoire,
         -- sinon les mêmes candidates ressortent pour tous les R voisins (mesuré : 469 uniques/1272).
         row_number() OVER (PARTITION BY r.idu ORDER BY md5(r.idu || c.idu || 'VT3-T-2026-11-15')) AS rn
  FROM t_r r
  JOIN parcel_zone_plu zr ON zr.idu = r.idu
  JOIN parcels c ON substring(c.idu,1,5) = r.insee AND c.cadastre_disparue_le IS NULL
                AND c.idu <> r.idu
                AND c.surface_m2 BETWEEN r.surface_m2*0.7 AND r.surface_m2*1.3
  JOIN parcel_zone_plu zc ON zc.idu = c.idu AND zc.zone_fam = zr.zone_fam
  LEFT JOIN p_model_bati pbc ON pbc.idu = c.idu
  WHERE COALESCE(pbc.emprise_bati_m2, 0) < 20
    AND NOT EXISTS (SELECT 1 FROM sitadel_permits s
                    WHERE s.idu_codes @> to_jsonb(ARRAY[c.idu]))
) q WHERE rn <= 3;

SELECT 'T (3 comparables par parcelle de R)' AS etape, count(*) FROM t_t
UNION ALL SELECT 'parcelles R sans 3 comparables', count(*) FROM (
  SELECT r_idu FROM t_t GROUP BY r_idu HAVING count(*)<3) x;

-- ── Sorties CSV (exécuter psql DEPUIS le dossier de sortie : cd cohortes/) ─────────────
\copy (SELECT permit_id, insee, commune, d_aut, millesime, etat, daact, nb_lgt, surf_hab, n_parc, mono, type_projet, replace(replace(replace(ic,'[',''),']',''),'"','') AS idus FROM t_h ORDER BY insee, permit_id) TO 'H.csv' CSV HEADER
\copy (SELECT permit_id, insee, commune, d_aut, millesime, etat, nb_lgt, surf_hab, n_parc, replace(replace(replace(ic,'[',''),']',''),'"','') AS idus FROM t_horsregles ORDER BY insee, permit_id) TO 'HORS-REGLES.csv' CSV HEADER
\copy (SELECT permit_id, insee, commune, d_aut, etat, nb_lgt, surf_hab, idu, emprise_bati_m2, surface_m2 FROM t_r ORDER BY insee, permit_id) TO 'R.csv' CSV HEADER
\copy (SELECT r_idu, idu, commune, zone_fam, surface_m2 FROM t_t ORDER BY r_idu, idu) TO 'T.csv' CSV HEADER
