-- ORACLE-1 — tirage des candidats (5 par slot, ordre déterministe par idu)
-- Chaque slot vise un critère du mandat ; le choix final (PARCELLES.csv) est gelé à la main
-- pour garantir 8 communes différentes et le cumul des critères.

\set QUIET on
\pset format unaligned
\pset fieldsep '|'

-- S01 — U dense (UA) + bâtie ancienne (<1970) + copropriété rattachée, Saint-Denis
SELECT 'S01_UA_ancien_copro', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), b.annee_construction
FROM parcels p
JOIN parcel_zone_plu z ON z.idu=p.idu AND z.zone_filtre='UA'
JOIN parcel_filtre_bati b ON b.idu=p.idu AND b.annee_construction < 1970
JOIN rnic_coproprietes c ON c.parcelle_idu=p.idu
WHERE p.commune='Saint-Denis'
ORDER BY p.idu LIMIT 5;

-- S02 — U pavillonnaire (UC/UD) + bâtie récente (>=2015) + personne physique (aucune PM 2024), Sainte-Marie
SELECT 'S02_Upav_recent_PP', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), b.annee_construction
FROM parcels p
JOIN parcel_zone_plu z ON z.idu=p.idu AND z.zone_filtre IN ('UC','UD')
JOIN parcel_filtre_bati b ON b.idu=p.idu AND b.annee_construction >= 2015
WHERE p.commune='Sainte-Marie'
  AND NOT EXISTS (SELECT 1 FROM pm_proprietaires_millesimes m WHERE m.idu=p.idu AND m.millesime=2024)
ORDER BY p.idu LIMIT 5;

-- S03 — AU ouverte (1AU*) nue, Saint-Paul
SELECT 'S03_1AU_nue', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
JOIN parcel_zone_plu z ON z.idu=p.idu AND z.zone_filtre LIKE '1AU%'
WHERE p.commune='Saint-Paul'
  AND COALESCE((SELECT emprise_bati_m2 FROM p_model_bati bb WHERE bb.idu=p.idu),0) < 5
  AND p.surface_m2 BETWEEN 300 AND 5000
ORDER BY p.idu LIMIT 5;

-- S04 — AU fermée (2AU*), Saint-Pierre
SELECT 'S04_2AU', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
JOIN parcel_zone_plu z ON z.idu=p.idu AND z.zone_filtre LIKE '2AU%'
WHERE p.commune='Saint-Pierre'
ORDER BY p.idu LIMIT 5;

-- S05 — zone A géante, Saint-Benoît
SELECT 'S05_A_geante', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
JOIN parcel_zone_plu z ON z.idu=p.idu AND z.zone_filtre='A'
WHERE p.commune='Saint-Benoît'
ORDER BY p.surface_m2 DESC, p.idu LIMIT 5;

-- S06 — zone N proche ravine (<15 m), Cilaos
SELECT 'S06_N_ravine', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
JOIN parcel_zone_plu z ON z.idu=p.idu AND z.zone_filtre LIKE 'N%'
WHERE p.commune='Cilaos'
  AND EXISTS (SELECT 1 FROM spatial_layers r WHERE r.kind='ravine'
              AND r.geom_2975 && ST_Expand(p.geom_2975,15)
              AND ST_DWithin(r.geom_2975, p.geom_2975, 15))
  AND p.surface_m2 BETWEEN 500 AND 20000
ORDER BY p.idu LIMIT 5;

-- S07 — à cheval sur deux zones PLU (2 zones GPU >=20 % chacune), Le Tampon
SELECT 'S07_2zones', t.idu, t.commune, string_agg(DISTINCT t.lib, '+'), round(t.surface_m2::numeric), NULL::int
FROM (
  SELECT p.idu, p.commune, p.surface_m2, s.attrs->>'libelle' AS lib,
         ST_Area(ST_Intersection(p.geom_2975, s.geom_2975)) / NULLIF(ST_Area(p.geom_2975),0) AS ratio
  FROM parcels p
  JOIN spatial_layers s ON s.kind='plu_gpu_zone' AND s.geom_2975 && p.geom_2975
       AND ST_Intersects(p.geom_2975, s.geom_2975)
  WHERE p.commune='Le Tampon' AND p.surface_m2 BETWEEN 800 AND 20000
) t
WHERE t.ratio >= 0.2
GROUP BY t.idu, t.commune, t.surface_m2
HAVING count(DISTINCT t.lib) >= 2
ORDER BY t.idu LIMIT 5;

-- S08 — géométrie chevauchant une parcelle d'une AUTRE commune (>5 m² de recouvrement)
SELECT DISTINCT ON (p1.idu) 'S08_2communes', p1.idu, p1.commune || '>' || p2.commune,
       NULL, round(p1.surface_m2::numeric), NULL::int
FROM parcels p1
JOIN parcels p2 ON p2.commune <> p1.commune
     AND p2.geom_2975 && p1.geom_2975
     AND ST_Area(ST_Intersection(p1.geom_2975, p2.geom_2975)) > 5
WHERE p1.commune IN ('Saint-Louis','Cilaos','Le Tampon','Saint-Paul')
ORDER BY p1.idu LIMIT 5;

-- S09 — PPR rouge (INTERDICTION), Le Port
SELECT 'S09_PPR_rouge', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE p.commune='Le Port'
  AND EXISTS (SELECT 1 FROM spatial_layers s WHERE s.kind='ppr' AND s.subtype='INTERDICTION'
              AND s.geom_2975 && p.geom_2975 AND ST_Intersects(s.geom_2975, p.geom_2975))
ORDER BY p.idu LIMIT 5;

-- S10 — PPR bleue (PRESCRIPTION), Saint-André
SELECT 'S10_PPR_bleue', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE p.commune='Saint-André'
  AND EXISTS (SELECT 1 FROM spatial_layers s WHERE s.kind='ppr' AND s.subtype='PRESCRIPTION'
              AND s.geom_2975 && p.geom_2975 AND ST_Intersects(s.geom_2975, p.geom_2975))
  AND NOT EXISTS (SELECT 1 FROM spatial_layers s WHERE s.kind='ppr' AND s.subtype='INTERDICTION'
              AND s.geom_2975 && p.geom_2975 AND ST_Intersects(s.geom_2975, p.geom_2975))
ORDER BY p.idu LIMIT 5;

-- S11 — littoral 50 pas, Saint-Leu
SELECT 'S11_50pas', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE p.commune='Saint-Leu'
  AND EXISTS (SELECT 1 FROM spatial_layers s WHERE s.kind='cinquante_pas'
              AND s.geom_2975 && p.geom_2975 AND ST_Intersects(s.geom_2975, p.geom_2975))
  AND p.surface_m2 > 200
ORDER BY p.idu LIMIT 5;

-- S12 — ligne HTA/MT à moins de 20 m, Le Tampon
SELECT 'S12_HTA', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE p.commune='Le Tampon' AND p.surface_m2 BETWEEN 400 AND 10000
  AND EXISTS (SELECT 1 FROM spatial_layers s WHERE s.kind IN ('ligne_mt','ligne_ht')
              AND s.geom_2975 && ST_Expand(p.geom_2975,20)
              AND ST_DWithin(s.geom_2975, p.geom_2975, 20))
ORDER BY p.idu LIMIT 5;

-- S13 — minuscule (<20 m²) en zone U
SELECT 'S13_minuscule', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric,1), NULL::int
FROM parcels p
JOIN parcel_zone_plu z ON z.idu=p.idu AND z.zone_filtre LIKE 'U%'
WHERE p.surface_m2 > 0 AND p.surface_m2 < 20
ORDER BY p.idu LIMIT 5;

-- S14 — vendue DVF depuis moins de 2 ans (>= 2024-09-28)
SELECT 'S14_DVF_recent', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
JOIN dvf_mutations_parcelle d ON d.id_parcelle=p.idu AND d.date_mutation >= '2024-09-28'
WHERE d.valeur_fonciere > 10000
GROUP BY p.idu, p.commune, z.zone_lib, p.surface_m2
ORDER BY p.idu LIMIT 5;

-- S15 — propriétaire SCI + établissement SIRENE rattaché
SELECT 'S15_SCI_siret', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
JOIN pm_proprietaires_millesimes m ON m.idu=p.idu AND m.millesime=2024 AND m.forme_juridique='SCI'
JOIN etablissement_parcelle e ON e.idu=p.idu
WHERE p.commune='Saint-Pierre'
ORDER BY p.idu LIMIT 5;

-- S16 — propriétaire EPF Réunion
SELECT 'S16_EPF', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
JOIN pm_proprietaires_millesimes m ON m.idu=p.idu AND m.millesime=2024
     AND m.denomination ILIKE '%PUBLIC FONCIER%'
ORDER BY p.idu LIMIT 5;

-- S17 — propriétaire commune (forme COM)
SELECT 'S17_commune_prop', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
JOIN pm_proprietaires_millesimes m ON m.idu=p.idu AND m.millesime=2024 AND m.forme_juridique='COM'
WHERE p.commune='Saint-Benoît' AND p.surface_m2 BETWEEN 300 AND 5000
ORDER BY p.idu LIMIT 5;

-- S18 — indivision probable (dénomination PM)
SELECT 'S18_indivision', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
JOIN pm_proprietaires_millesimes m ON m.idu=p.idu AND m.millesime=2024
     AND (m.denomination ILIKE '%INDIVIS%' OR m.denomination ILIKE '%CONSORT%' OR m.denomination ILIKE '%HERITIER%')
ORDER BY p.idu LIMIT 5;

-- S19 — permis récent (Sitadel >= 2024) rattaché à l'idu
SELECT 'S19_permis_recent', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), NULL::int
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
JOIN sitadel_permits s ON s.idu_codes @> to_jsonb(p.idu::text) AND s.date >= '2024-01-01'
WHERE p.commune='Salazie'
ORDER BY p.idu LIMIT 5;

-- S20 — permis caduc / annulé (pc_caducs)
SELECT 'S20_permis_caduc', p.idu, p.commune, z.zone_lib, round(p.surface_m2::numeric), c.pc_annee
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
JOIN pc_caducs c ON c.idu=p.idu
WHERE p.commune='Sainte-Suzanne'
ORDER BY p.idu LIMIT 5;
