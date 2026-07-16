# NUIT — Mode bailleur (point 33) · `feat/nuit-bailleur`

**NON mergée.** Back + front. Zéro touche scoring. Données SRU réelles (aucune invention).

## Lot 0
M06 remontait les parcelles promues en **QPV** (leviers LLS/TVA), sans contexte SRU ni déficit.
`commune_contexte_sru` existe (statut, taux_lls, objectif_pct, detail.nb_lls, prélèvement).

## Fait
- **Backend** (`/modules/bailleur`) : join `commune_contexte_sru` → renvoie le **bloc SRU** de la commune
  active (statut, taux LLS, objectif, **déficit LLS DÉRIVÉ** des chiffres sourcés :
  `nb_lls × (objectif − taux) / taux`), marque chaque parcelle `carencee`, **priorise les carencées**
  (ORDER BY), et compte les communes carencées en mode île.
- **Frontend** (M06) : **carte SRU** en tête (statut carencée en ambre + « Besoin estimé : N logements
  sociaux »), badge « SRU carencée » sur les parcelles, ligne « N en communes carencées » (île).

## Preuve
`nuit-bailleur-sru.png` — Saint-Leu : **SRU carencée · LLS 12,26 % / objectif 25 % · Besoin estimé
1 814 logements** (311 parcelles carencées). Testé : Saint-Denis conforme (LLS 38,6 % > 20 %, déficit None).

## Garanties
`tsc`/build verts, endpoint testé (île + carencée + conforme). Déficit = calcul transparent depuis
données SRU sourcées, jamais inventé. `git diff` = `modules.py` (bailleur) + `ModulePanel.tsx` (M06) + QA.

## Merge
`git -C /Users/openclaw/Desktop/labuse checkout main && git merge --no-ff feat/nuit-bailleur`
**État : ✅ prêt à merger.**
