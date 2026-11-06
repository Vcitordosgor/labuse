-- NU5-FIX-1 — GESTES PROD RADAR (préparés, à appliquer au déploiement, go Vic).
-- À jouer SUR PROD en lecture-écrite, hors fenêtre 01 h–05 h, APRÈS déploiement du code corrigé
-- (le code servant « a_reverifier » à la passe de confirmation + la lecture de surface Leboncoin).
-- Chaque bloc est en transaction avec un SELECT de contrôle AVANT COMMIT : on vérifie le compte
-- attendu, puis on COMMIT (ou ROLLBACK si l'écart est suspect).
-- Rejouable sur prod : ssh labuse-vps 'sudo -u postgres psql -d labuse'

-- ════════════════════════════════════════════════════════════════════════════════════════════
-- D-F1 — Rétablir en « à revérifier » les 88 biens retirés à tort le 26/09.
--   Signature du blocage (passe id 4, 107/107 = 100 %), SANS garde des 30 % (postérieure), jamais
--   re-vérifiés, aucune preuve de retrait logée (`pige:retiree:<bien_id>` absent). Remis en
--   `a_reverifier` : la prochaine passe de confirmation les re-vérifie un à un (code D-F1) —
--   présents → réactivés `active`, vraiment partis → retirés SOUS la garde des 30 % (preuve logée).
-- ════════════════════════════════════════════════════════════════════════════════════════════
BEGIN;
-- Contrôle AVANT : combien de candidats ? (attendu ≈ 88)
SELECT count(*) AS candidats_26_09
FROM pige_biens b
WHERE b.statut = 'retiree'
  AND (b.retiree_le AT TIME ZONE 'Indian/Reunion')::date = DATE '2026-09-26'
  AND NOT EXISTS (SELECT 1 FROM event_log e WHERE e.dedup = 'pige:retiree:' || b.bien_id);

UPDATE pige_biens b SET statut = 'a_reverifier'
WHERE b.statut = 'retiree'
  AND (b.retiree_le AT TIME ZONE 'Indian/Reunion')::date = DATE '2026-09-26'
  AND NOT EXISTS (SELECT 1 FROM event_log e WHERE e.dedup = 'pige:retiree:' || b.bien_id);

-- trace de l'intervention (une ligne, idempotente par le dedup)
INSERT INTO event_log (kind, titre, detail, source, dedup)
SELECT 'pige.statut_change',
       'Radar — 88 biens du 26/09 remis en « à revérifier » (NU5-FIX-1 D-F1)',
       'Retraits du 26/09 sur passe 100 % (blocage), sans preuve logée, jamais re-vérifiés.',
       'Radar', 'nu5fix1:d-f1:reverifier-26-09'
WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE dedup = 'nu5fix1:d-f1:reverifier-26-09');

-- Contrôle APRÈS : doit refléter le compte ci-dessus
SELECT count(*) AS a_reverifier_total FROM pige_biens WHERE statut = 'a_reverifier';
-- COMMIT;   -- ← décommenter après vérification du compte. Sinon : ROLLBACK;

-- ════════════════════════════════════════════════════════════════════════════════════════════
-- D-F2 — Requalifier les ~49 terrains Leboncoin dont `square` (surface du terrain) avait été
--   recopié en surface habitable → flagués « a_qualifier » (terrain portant une surface habitable)
--   → hors médianes/veilles. Le code est corrigé (html_next.aplatir) ; pour l'EXISTANT, on vide
--   surface_hab là où elle est égale à la surface terrain sur un terrain, puis on re-déroule la
--   cohérence (CLI) pour que ces biens repassent « sains ».
-- ════════════════════════════════════════════════════════════════════════════════════════════
BEGIN;
SELECT count(*) AS terrains_a_requalifier
FROM pige_faits f JOIN pige_biens b ON b.bien_id = f.bien_id
WHERE b.type_bien = 'terrain' AND f.surface_hab IS NOT NULL
  AND f.surface_terrain IS NOT NULL AND f.surface_hab = f.surface_terrain;

UPDATE pige_faits f SET surface_hab = NULL
FROM pige_biens b
WHERE b.bien_id = f.bien_id AND b.type_bien = 'terrain'
  AND f.surface_hab IS NOT NULL AND f.surface_terrain IS NOT NULL
  AND f.surface_hab = f.surface_terrain;
-- COMMIT;   -- ← puis re-dérouler la cohérence : `labuse radar coherence --recalcul` (ou le job de nuit),
--             qui repassera ces terrains de « a_qualifier » à sain (surface_hab absente, cohérent).

-- ════════════════════════════════════════════════════════════════════════════════════════════
-- D-F6 — 24 biens `type_bien = NULL` (code real_estate_type inconnu) : donnée dégradée, pas fausse.
--   On NE DEVINE PAS le type. Geste : les lister pour inspection manuelle du code portail inconnu ;
--   si un code récurrent est identifié, l'ajouter à `_RET` (html_next.py) et re-ingérer.
-- ════════════════════════════════════════════════════════════════════════════════════════════
SELECT b.bien_id, f.brut->>'real_estate_type' AS code_portail, b.commune, f.prix
FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
WHERE b.type_bien IS NULL AND b.statut IN ('active', 'en_vente_longue')
ORDER BY code_portail;

-- ════════════════════════════════════════════════════════════════════════════════════════════
-- D-F7 — 42 « pistes » périmées (rattachement_etat = 'piste', idu NULL, héritées pré-RADAR-4).
--   Inertes (aucun automatisme ne lit une piste) mais incohérentes avec la doctrine « plus de
--   pistes ». Geste : les remettre à `non_rattachee` (le rattachement est désormais 100 % manuel).
-- ════════════════════════════════════════════════════════════════════════════════════════════
BEGIN;
SELECT count(*) AS pistes_perimees
FROM pige_biens WHERE rattachement_etat = 'piste' AND idu IS NULL;

UPDATE pige_biens SET rattachement_etat = 'non_rattachee', rattachement_pistes = NULL
WHERE rattachement_etat = 'piste' AND idu IS NULL;
-- COMMIT;   -- ← après vérification du compte (attendu ≈ 42).
