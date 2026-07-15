# NUIT — Due diligence (point 42) · `feat/nuit-diligence`

**NON mergée.** Back + front. Zéro touche scoring. Privacy respectée.

## Lot 0
M10 passait une liste de parcelles au crible → renvoyait statut/scores + COMPTES de flags/exclusions,
sans détail ni score de risque.

## Fait
- **Backend** (`/modules/duediligence`) : par parcelle, `_diligence_dossier` (déterministe, facteurs
  EXISTANTS) →
  - **checklist** des points à vérifier (lignes cascade HARD_EXCLUDE / SOFT_FLAG / UNKNOWN : couche +
    sévérité + détail, triées par gravité) ;
  - **score de risque consolidé 0-100** (HARD_EXCLUDE → 100 ; sinon max sévérité SOFT_FLAG fort70/
    moyen50/faible30 ; +10 si propriétaire particulier = accès SPF) ;
  - **propriétaire** PRIVACY : personne morale nommée (SIREN public) / particulier jamais nommé.
- **Frontend** (M10) : badge **risque {faible/modéré/élevé/bloquant} · N/100**, propriétaire, et la
  **checklist** (✕ bloquant / ☐ à vérifier) par parcelle.

## Preuve
`nuit-diligence-checklist.png` — 97401000AI1188 (risque 80, 6 points), 97402000AD1052 (risque 40, 7).

## Garanties
`tsc`/build verts, endpoint testé. Risque = déterministe depuis la cascade servie (aucun re-scoring,
aucune invention). Privacy : jamais un particulier nommé. `git diff` = `modules.py` + `ModulePanel.tsx` + QA.

## Merge
`git -C /Users/openclaw/Desktop/labuse checkout main && git merge --no-ff feat/nuit-diligence`
**État : ✅ prêt à merger.**
