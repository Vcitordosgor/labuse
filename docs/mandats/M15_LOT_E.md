# M15 — LOT E : clarté des scores et métriques

**Branche** : `fix/m15-e-scores` · Build 0 erreur · Golden 116/116 (`LABUSE_DEV_MODE=1`). Preuves `qa/m15/E/`.

## E1 — Outil « Scoring (P) » : métriques traduites (`ScoringV2.tsx`)
- Bandeau client (RG2) : « Le **classement** des parcelles par **probabilité de mutation** à 12 mois. Le **×N** dit combien la parcelle est **plus probable de muter que la moyenne** (×13 = 13 fois plus probable). » — cohérent avec « mutation ×N » (M13).
- Onglet **« Top P » → « Classement »** (jargon retiré). Brûlantes / Réserve foncière expliqués dans le bandeau.
- Preuve : `e1_scoring_explique.png` (bandeau + « Classement », « Top P » absent).

## E2 — Outil « Division parcellaire » : score + explication (`M01`)
- Ancien : « Lot candidat = approximation (plus grand cercle inscrit, recul bâti 3 m) » (incompréhensible).
- Nouveau : « Repère les **grands terrains où détacher un lot à bâtir**. Le **score (0-100)** — le nombre violet — mesure la **facilité à détacher un lot**. Le lot proposé est une **estimation** : le plus grand espace constructible restant, à 3 m des bâtiments. » Label du slider : « Score de divisibilité ≥ ».
- Preuve : `e2_division_explique.png`.

## E3 — Outil « Foncier fantôme » : « fantôme » + score expliqués (`M07`)
- Nouveau bandeau (jargon Q/RNE retiré) : « Du foncier **constructible mais « fantôme »** : potentiel réel, mais propriétaire **difficile à joindre** (société introuvable au registre, dirigeant inactif). Le **nombre violet** = le **potentiel constructible** (0-100). »
- Preuve : `e3_fantome_explique.png`.

## E4 — Outil « Comparateur de communes » : €/m² neuf (`O6Comparateur`)
- **Cause racine** : la donnée **existe** (prix_neuf = 4462, 3765… pour les 24 communes) ; le tableau à 6 colonnes **débordait le volet** (~416 px dans ~287 px) → **scroll horizontal (RG4)** qui poussait « €/m² neuf » hors champ. C'est ce que Vic voyait « vide ».
- **Correction** : plus de scroll horizontal. Une rangée de **puces de métrique** (dont « €/m² neuf ») choisit la colonne comparée ; le tableau montre **Commune · Composite · métrique choisie**. `scrollWidth == clientWidth` (287/287) après correction.
- **Absence propre** : une valeur manquante reste « — » (jamais un zéro inventé). Les **jauges recalculent** (les curseurs de poids changent la `queryKey` → refetch).
- Preuve : `e4_comparateur_prix_neuf.png` (puce « €/m² neuf » active → valeurs 4 462… visibles, aucun scroll horizontal).

## Notes
- **M07 (Foncier fantôme)** et **M06 (Mode bailleur)** lisent `commune` du store → héritent du filtre carte → **RG1 à couper en LOT G**.
- Le plafond « N gelées / N affichées » de Foncier fantôme = **LOT B** (séparé).
