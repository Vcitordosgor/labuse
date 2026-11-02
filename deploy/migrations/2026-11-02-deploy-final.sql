-- ============================================================================
-- DEPLOY-FINAL — migration de schéma tracée (prod labuse-vps)
-- Posée AVANT le redémarrage, hors charge (aucune session client, aucun VACUUM).
-- Cible : 153c95032 -> origin/main (4e7c9d29f).
--
-- Chaque écart est idempotent et RÉTRO-COMPATIBLE avec le code ANCIEN encore
-- en service (colonnes/fonction neuves non lues par l'ancien code ; le RENAME
-- parcel_p_score_v2 n'a aucun lecteur de service — scoring seul).
--
-- PART A (léger, une transaction) : comptes grâce, projets.version,
--   labuse_ppr_couleur, parcel_p_score_v2 rename, dvf.millesime_dvf.
-- PART B (lourd, séparé, chronométré) : adresses.suggest_norm (GENERATED STORED,
--   réécrit 339 915 lignes ~30 s, ACCESS EXCLUSIVE) + index GIN trigram.
-- ============================================================================

\timing on

-- ---------------------------------------------------------------------------
-- PART A — léger (transaction)
-- ---------------------------------------------------------------------------
BEGIN;

-- comptes : champs de grâce (FIX-NU3-2) — ajouts nullable, instantanés.
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS paiement_requis_at timestamptz;
ALTER TABLE comptes ADD COLUMN IF NOT EXISTS acces_fin_at       timestamptz;

-- projets.version : verrou optimiste (FIX-NU3-2, H-D03). integer NOT NULL
-- DEFAULT 1 = ajout instantané sur PG11+ (défaut constant, pas de réécriture).
ALTER TABLE projets ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;

-- labuse_ppr_couleur : fonction SQL requise au boot (PPR-UNIQUE-1).
-- CREATE OR REPLACE ne prend aucun verrou de table. Corps EXACT = models.PPR_COULEUR_FN.
CREATE OR REPLACE FUNCTION labuse_ppr_couleur(subtype text, attrs jsonb) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
SELECT CASE
WHEN upper(coalesce($1,'')) = 'INTERDICTION' THEN 'rouge'
WHEN upper(coalesce($1,'')) = 'PRESCRIPTION' THEN 'bleu'
WHEN coalesce($2->>'code_degre','') ~ '^[rb]?R' THEN 'rouge'
WHEN coalesce($2->>'code_degre','') ~ '^[rb]?B' THEN 'bleu'
ELSE 'autre' END $$;

-- parcel_p_score_v2 : rename sectoriel -> communal (MARCHE-UNIQUE-1, NU-E-014).
-- Métadonnée seule (instantané), aucun lecteur de service. Garde idempotente.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_name='parcel_p_score_v2' AND column_name='prix_secteur_eur_m2')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_name='parcel_p_score_v2' AND column_name='prix_commune_eur_m2')
  THEN
    EXECUTE 'ALTER TABLE parcel_p_score_v2 RENAME COLUMN prix_secteur_eur_m2 TO prix_commune_eur_m2';
  END IF;
END $$;

-- dvf : millésime de la donnée source du cache de médianes (ajouts nullable).
ALTER TABLE dvf_prix_sortie_neuf ADD COLUMN IF NOT EXISTS millesime_dvf date;
ALTER TABLE dvf_secteur_medianes ADD COLUMN IF NOT EXISTS millesime_dvf date;

COMMIT;

-- ---------------------------------------------------------------------------
-- PART B — lourd : adresses.suggest_norm (VITESSE-3, NU-B-004)
-- Expression GÉNÉRÉE = EXACTEMENT constants.sql_plie_lit_suggest(ADRESSE_SUGGEST_EXPR)
-- de la révision déployée (calculée localement). La valeur stockée == l'expression
-- => résultats de recherche identiques à l'octet (repli expression devient inutile).
-- lock_timeout borne l'ACQUISITION du verrou (la réécriture elle-même n'est pas bornée).
-- ---------------------------------------------------------------------------
SET lock_timeout = '30s';

ALTER TABLE adresses ADD COLUMN IF NOT EXISTS suggest_norm text
  GENERATED ALWAYS AS (btrim(regexp_replace(lower(translate(replace(replace(replace(replace(coalesce(numero,'') || ' ' || coalesce(rep,'') || ' ' || voie || ' ' || coalesce(code_postal,'') || ' ' || coalesce(commune,''), 'œ', 'oe'), 'Œ', 'OE'), 'æ', 'ae'), 'Æ', 'AE'), 'àâäéèêëïîôöùûüçóÿ’ÀÂÄÉÈÊËÏÎÔÖÙÛÜÇÓŸ', 'aaaeeeeiioouuucoy''AAAEEEEIIOOUUUCOY')), '[[:space:],-]+', ' ', 'g'))) STORED;

CREATE INDEX IF NOT EXISTS ix_adresses_suggest_norm_trgm ON adresses
  USING gin (suggest_norm gin_trgm_ops)
  WHERE idu IS NOT NULL AND geom IS NOT NULL;

RESET lock_timeout;
\timing off
