-- INDEPENDENT ORACLE for "prix médian de secteur" (chirurgical-2) — read-only.
-- Reproduces src/labuse/faisabilite/bilan.py::sector_price WITHOUT calling app code.
-- The weighting (_mediane_ponderee) and the adaptive-plan loop (_selection_secteur)
-- are pure Python and live in oracle_prix.py; the SQL below is the data layer only.
--
-- Constants (bilan.py): MIN_N_SECTEUR=8, RAYONS_SECTEUR_M=(500,1000,1500),
-- PERIODE_SECTEUR_ANS=5, TRIM 5% extremes, domaine [1000,12000] €/m².
-- annee_ref()=2026 (today_reunion() on 2026-11-15) -> fenêtre récente: annee>=2022.
-- Parameter :idu / :pid substituted per parcelle.

-- 1) parcelle id + commune
-- SELECT id, commune FROM parcels WHERE idu = :idu;

-- 2) CANDIDATE bati sales (= _ventes_bati_dedup, before Python dedup by mutation_id)
SELECT d.mutation_id AS mid, d.valeur_fonciere AS val, d.surface_reelle_bati AS surf,
  d.valeur_fonciere / d.surface_reelle_bati AS prix,
  CASE WHEN d.type_local ILIKE '%APPARTEMENT%' THEN 'appartement' ELSE 'maison' END AS cat,
  (d.nature_mutation ILIKE '%futur%') AS vefa,
  extract(year FROM d.date_mutation)::int AS annee,
  COALESCE(d.surface_terrain, 0) AS terr,
  round(ST_Distance(d.geom::geography, p.centroid::geography)) AS dist
FROM dvf_mutations d, parcels p
WHERE p.id = :pid AND d.commune = p.commune AND d.surface_reelle_bati >= 20
  AND d.valeur_fonciere > 20000
  AND d.nature_mutation IN ('Vente', 'Vente en l''état futur d''achèvement')
  AND d.type_local ILIKE ANY(ARRAY['%APPARTEMENT%','%MAISON%']);

-- 3) type_prioritaire (tp) the fiche passes to sector_price (marche_dvf, profil banquier_adaptatif):
--    nature of the parcelle's LAST DVF sale (geo UNION histo), else bati-non-copro -> maison.
WITH u AS (
  SELECT id_mutation, date_mutation d, type_local, surface_terrain terr FROM dvf_mutations_parcelle WHERE id_parcelle = :idu
  UNION ALL
  SELECT id_mutation, date_mutation d, type_local, surface_terrain terr FROM dvf_mutations_histo    WHERE id_parcelle = :idu),
lm AS (SELECT id_mutation, d FROM u ORDER BY d DESC LIMIT 1)
SELECT count(*) FILTER (WHERE u.type_local='Maison')      AS n_maison,
       count(*) FILTER (WHERE u.type_local='Appartement') AS n_appart,
       max(u.terr)                                        AS terrain
FROM lm JOIN u ON u.id_mutation = lm.id_mutation AND u.d = lm.d;
-- fallback (if nature not maison/appartement):
SELECT (fb.idu IS NOT NULL) AS batie,
  EXISTS(SELECT 1 FROM rnic_coproprietes rc WHERE rc.parcelle_idu = p.idu) AS copro
FROM parcels p LEFT JOIN parcel_filtre_bati fb ON fb.idu = p.idu WHERE p.idu = :idu;

-- 4) SUBJECT attributes for the ressemblance weighting (= _surface_terrain_sujet):
SELECT (SELECT sum(surface_reelle_bati) FROM dvf_mutations_parcelle
          WHERE id_parcelle = p.idu AND type_local IN ('Maison','Appartement')
            AND date_mutation = (SELECT max(date_mutation) FROM dvf_mutations_parcelle
              WHERE id_parcelle = p.idu AND nature_mutation IN ('Vente','Vente terrain à bâtir'))) AS surf,
  COALESCE(p.contenance_m2, p.surface_m2) AS terr
FROM parcels p WHERE p.id = :pid;

-- The Python layer then: dedup by mid; for each period (récente>=2022, then élargie)
-- and each base_plan (typed: tp×{500,1000,1500}, then tp commune ; untyped:
-- appart×{500,1000,1500}, mixte×{500,1000,1500}, appart commune, mixte commune),
-- filter cat/annee/dist, apply domaine [1000,12000] + 5% trim, take first plan with
-- kept>=8 ; exclude VEFA for the headline ; weighted quantile = _mediane_ponderee.
