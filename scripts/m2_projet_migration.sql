-- =====================================================================================
-- M2 — Refonte « Projet » : migration ADDITIVE et RÉVERSIBLE (fenêtre pré-M7).
-- =====================================================================================
-- Ajoute la colonne `hors_criteres` à projet_parcelles : une décision (retenue…) qui ne
-- matche plus les critères du jour au rejeu RESTE, marquée « hors critères actuels » —
-- jamais évincée en silence (règle de non-perte étendue au rejeu).
--
-- ADDITIF : aucune ligne modifiée, aucun statut touché (défaut false). RÉVERSIBLE : voir rollback.
-- Zéro touche au scoring / runs servis / golden.
-- =====================================================================================

ALTER TABLE projet_parcelles
  ADD COLUMN IF NOT EXISTS hors_criteres boolean NOT NULL DEFAULT false;

-- Contrôle : compter les statuts (doit être IDENTIQUE avant/après — la migration n'ajoute qu'une colonne)
-- SELECT statut, count(*) FROM projet_parcelles GROUP BY statut ORDER BY statut;

-- ─── ROLLBACK (réversible) ───────────────────────────────────────────────────────────
-- ALTER TABLE projet_parcelles DROP COLUMN IF EXISTS hors_criteres;
