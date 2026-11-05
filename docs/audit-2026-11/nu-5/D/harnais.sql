-- ════════════════════════════════════════════════════════════════════════════════════════
-- NU-5-D — HARNAIS DE COHÉRENCE DU RADAR (annonce par annonce)
-- Lecture seule, rejouable chaque nuit. Vérité de fraîcheur = pige_annonces ; vérité de capture =
-- pige_faits.source_brute (le payload portail tel qu'archivé à la capture).
--
-- Usage (prod, read-only) :
--   sudo -u postgres psql -d labuse -X -f harnais.sql
-- ou local/dev :
--   psql "$LABUSE_DATABASE_URL" -X -f harnais.sql
--
-- Chaque bloc nomme la VÉRITÉ attendue ; un compteur de violations > 0 = à regarder. Rien n'écrit.
-- ════════════════════════════════════════════════════════════════════════════════════════
SET default_transaction_read_only = on;
\set ON_ERROR_STOP on
\pset footer off

\echo ══ 0. SOCLE — volumétrie ══
SELECT 'biens' obj, count(*) n FROM pige_biens
UNION ALL SELECT 'annonces', count(*) FROM pige_annonces
UNION ALL SELECT 'faits', count(*) FROM pige_faits
UNION ALL SELECT 'biens servis client (non copro, validé)', count(*)
  FROM pige_biens b JOIN pige_faits f ON f.bien_id=b.bien_id WHERE NOT b.est_copro AND f.valide_at IS NOT NULL
UNION ALL SELECT 'copros embasées (jamais servies)', count(*) FROM pige_biens WHERE est_copro
UNION ALL SELECT 'communes couvertes', count(DISTINCT commune) FROM pige_biens;

\echo
\echo ══ 1. FIDÉLITÉ CAPTURE — champ servi vs source_brute (portail), par portail ══
\echo    (mismatch = la valeur servie diffère du payload archivé — extraction infidèle)
WITH der AS (
  SELECT DISTINCT ON (bien_id) bien_id, portail FROM pige_annonces ORDER BY bien_id, date_saisie DESC),
num AS (
  SELECT d.portail, f.bien_id, f.source_brute sb,
    f.surface_hab, f.surface_terrain, f.pieces, f.prix_m2,
    CASE WHEN d.portail='leboncoin' THEN f.source_brute->>'square' ELSE f.source_brute->>'surfaceArea' END AS src_hab,
    CASE WHEN d.portail='leboncoin' THEN f.source_brute->>'land_plot_surface' ELSE f.source_brute->>'landSurfaceArea' END AS src_terr,
    CASE WHEN d.portail='leboncoin' THEN f.source_brute->>'rooms' ELSE f.source_brute->>'roomsQuantity' END AS src_pieces,
    CASE WHEN d.portail='leboncoin' THEN f.source_brute->>'price_per_square_meter' ELSE f.source_brute->>'pricePerSquareMeter' END AS src_m2
  FROM pige_faits f JOIN der d ON d.bien_id=f.bien_id
  WHERE f.source_brute IS NOT NULL AND f.source_brute <> '{}'::jsonb AND f.provenance='json_riche')
SELECT portail, champ,
       sum(verifiable) AS verifiables,
       sum(match) AS concordants,
       CASE WHEN sum(verifiable)>0 THEN round(100.0*sum(match)/sum(verifiable),1) END AS taux_pct
FROM (
  SELECT portail, 'surface_hab' champ,
    (src_hab ~ '^[0-9.]+$')::int verifiable,
    (src_hab ~ '^[0-9.]+$' AND surface_hab IS NOT NULL AND round(surface_hab)=round(src_hab::numeric))::int match FROM num
  UNION ALL SELECT portail, 'surface_terrain',
    (src_terr ~ '^[0-9.]+$')::int,
    (src_terr ~ '^[0-9.]+$' AND surface_terrain IS NOT NULL AND round(surface_terrain)=round(src_terr::numeric))::int FROM num
  UNION ALL SELECT portail, 'pieces',
    (src_pieces ~ '^[0-9]+$')::int,
    (src_pieces ~ '^[0-9]+$' AND pieces IS NOT NULL AND pieces=src_pieces::int)::int FROM num
  UNION ALL SELECT portail, 'prix_m2(portail)',
    (src_m2 ~ '^[0-9.]+$')::int,
    (src_m2 ~ '^[0-9.]+$' AND prix_m2 IS NOT NULL AND abs(prix_m2-round(src_m2::numeric)) <= 1)::int FROM num
) t GROUP BY portail, champ ORDER BY portail, champ;

\echo
\echo ══ 2. PRIX/m² SERVI — recalcul prix/surface (base = terrain pour terrain, sinon habitable) ══
\echo    cohérence avec prix_m2 portail (écart > 3 % = base de surface différente du portail)
SELECT b.type_bien,
  count(*) FILTER (WHERE f.prix IS NOT NULL AND COALESCE(NULLIF(f.surface_terrain,0),NULLIF(f.surface_hab,0)) IS NOT NULL) AS calculables,
  count(*) FILTER (WHERE f.prix_m2 IS NOT NULL
     AND abs(f.prix_m2 - f.prix / CASE WHEN b.type_bien='terrain' THEN NULLIF(f.surface_terrain,0) ELSE NULLIF(f.surface_hab,0) END) > 0.03*f.prix_m2) AS ecart_sup3pct_vs_portail
FROM pige_faits f JOIN pige_biens b ON b.bien_id=f.bien_id
WHERE NOT b.a_qualifier GROUP BY 1 ORDER BY 2 DESC NULLS LAST;

\echo
\echo ══ 3. DÉDOUBLONNAGE — doublons EXACTS résiduels (même commune+type+prix+surface, biens distincts) ══
\echo    VÉRITÉ : 0 (la dédup exact-only doit tout fusionner)
SELECT b.commune, b.type_bien, f.prix, COALESCE(f.surface_hab,f.surface_terrain) surf,
       count(DISTINCT b.bien_id) n_biens, string_agg(DISTINCT b.bien_id::text,',' ORDER BY b.bien_id::text) ids
FROM pige_biens b JOIN pige_faits f ON f.bien_id=b.bien_id
WHERE f.prix IS NOT NULL AND COALESCE(f.surface_hab,f.surface_terrain) IS NOT NULL
GROUP BY 1,2,3,4 HAVING count(DISTINCT b.bien_id)>1 ORDER BY 5 DESC LIMIT 20;

\echo -- composition des biens multi-annonces (fusions réalisées)
SELECT portails_set, count(*) biens FROM (
  SELECT bien_id, string_agg(DISTINCT portail,'+' ORDER BY portail) portails_set
  FROM pige_annonces GROUP BY bien_id HAVING count(*)>1) t GROUP BY 1 ORDER BY 2 DESC;

\echo
\echo ══ 4. RETRAITS — intégrité ══
\echo -- 4a. garde multi-annonces : AUCUN bien retiré ne doit avoir une annonce vue APRÈS son retrait (VÉRITÉ 0)
SELECT count(*) AS retiree_avec_annonce_revue_apres
FROM pige_biens b WHERE b.statut='retiree'
  AND EXISTS (SELECT 1 FROM pige_annonces a WHERE a.bien_id=b.bien_id AND a.date_saisie > b.retiree_le);
\echo -- 4b. retraits par jour + tracés (event pige:retiree:) vs non tracés (hérités, hors garde 30 %)
SELECT (b.retiree_le AT TIME ZONE 'Indian/Reunion')::date jour, count(*) n,
  count(*) FILTER (WHERE EXISTS(SELECT 1 FROM event_log e WHERE e.dedup='pige:retiree:'||b.bien_id)) traces,
  count(*) FILTER (WHERE NOT EXISTS(SELECT 1 FROM event_log e WHERE e.dedup='pige:retiree:'||b.bien_id)) non_traces
FROM pige_biens b WHERE b.statut='retiree' GROUP BY 1 ORDER BY 1;
\echo -- 4c. passes de confirmation : taux de retrait apparent + verdict garde 30 %
SELECT (captured_at AT TIME ZONE 'Indian/Reunion')::date jour, n_pages liens_verifies,
  n_supprimees retires_ecrits, n_non_verifiees,
  CASE WHEN n_pages>=5 AND n_supprimees=0 AND n_non_verifiees=0 THEN 'rien retiré (bloqué ou RAS)'
       WHEN n_supprimees>0 THEN 'retraits écrits' ELSE '—' END note
FROM pige_passes WHERE passe='confirmation' ORDER BY captured_at DESC;

\echo
\echo ══ 5. RATTACHEMENT ══
\echo -- 5a. état des rattachements (auto retiré RADAR-4 : tout doit être idu NULL sauf geste humain)
SELECT CASE WHEN idu IS NULL THEN 'idu NULL' ELSE 'idu posé' END etat_idu,
       rattachement_etat, rattachement_humain, count(*)
FROM pige_biens GROUP BY 1,2,3 ORDER BY 4 DESC;
\echo -- 5b. lifecycle DVF/Courrier EXIGE un idu → inerte si 0 rattaché
SELECT 'biens rattachés (idu)' k, count(*) v FROM pige_biens WHERE idu IS NOT NULL
UNION ALL SELECT 'vendue (DVF)', count(*) FROM pige_biens WHERE statut='vendue'
UNION ALL SELECT 'retiree_sans_vente (cible Courrier)', count(*) FROM pige_biens WHERE statut='retiree_sans_vente';
\echo -- 5c. piste périmée : rattachement_etat='piste' mais idu NULL (état hérité non nettoyé)
SELECT count(*) AS pistes_sans_idu FROM pige_biens WHERE rattachement_etat='piste' AND idu IS NULL;

\echo
\echo ══ 6. QUALITÉ DES FAITS ══
\echo -- 6a. biens de type inconnu (NULL) servis au flux (ni médiane bâti ni terrain)
SELECT count(*) AS type_null_servis FROM pige_biens b JOIN pige_faits f ON f.bien_id=b.bien_id
WHERE b.type_bien IS NULL AND NOT b.est_copro AND f.valide_at IS NOT NULL;
\echo -- 6b. à-qualifier : motifs (exclus des stats et des veilles)
SELECT motif, count(*) FROM (SELECT jsonb_array_elements_text(a_qualifier_motifs) motif
  FROM pige_biens WHERE a_qualifier) t GROUP BY 1 ORDER BY 2 DESC;
\echo -- 6c. terrains perdus pour les stats à cause de surface_hab = surface_terrain (quirk Leboncoin square)
SELECT a.portail,
  count(*) FILTER (WHERE NOT b.a_qualifier) terrains_sains,
  count(*) FILTER (WHERE b.a_qualifier) terrains_a_qualifier
FROM pige_biens b JOIN pige_faits f ON f.bien_id=b.bien_id
  JOIN LATERAL (SELECT portail FROM pige_annonces WHERE bien_id=b.bien_id ORDER BY date_saisie DESC LIMIT 1) a ON true
WHERE b.type_bien='terrain' GROUP BY 1;

\echo
\echo ══ 7. COMPTEUR DE LA NUIT — un seul chiffre par nuit et par portail (pige_annonces.created_at) ══
SELECT (created_at AT TIME ZONE 'Indian/Reunion')::date nuit, portail, count(*) nouvelles_annonces
FROM pige_annonces GROUP BY 1,2 ORDER BY 1 DESC, 2 LIMIT 30;

\echo
\echo ══ 8. NUITS — 14 dernières (passes auto/manuel/test) : présence, portée ══
WITH jours AS (
  SELECT generate_series((now() AT TIME ZONE 'Indian/Reunion')::date - 13,
                         (now() AT TIME ZONE 'Indian/Reunion')::date, '1 day')::date nuit)
SELECT j.nuit,
  count(DISTINCT p.passe) passes_distinctes,
  string_agg(DISTINCT p.passe||'/'||p.source, ',' ORDER BY p.passe||'/'||p.source) detail,
  CASE WHEN count(p.*)=0 THEN 'NUIT MANQUÉE' ELSE 'ok' END etat
FROM jours j LEFT JOIN pige_passes p
  ON (p.captured_at AT TIME ZONE 'Indian/Reunion')::date = j.nuit
GROUP BY j.nuit ORDER BY j.nuit DESC;
\echo -- 8b. comptes-rendus de soirée (K-RAD-04) : veille Mac détectée ?
SELECT (ts AT TIME ZONE 'Indian/Reunion')::date jour, left(titre,40) titre, left(detail,90) detail
FROM event_log WHERE dedup LIKE 'pige:soiree:%' ORDER BY ts DESC LIMIT 14;
