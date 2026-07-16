# ASSEMBLAGE PLUS (point 35) · `feat/assemblage-plus`

**NON mergée.** Amélioration outil. **Zéro touche scoring** (`git diff` = `api/moteurs.py`,
`moteurs.tsx`, `App.tsx` hook QA, QA). Privacy tenue.

## Lot 0 — Constat
`/moteurs/assemblage` : détecte la contiguïté (graphe ST_DWithin 1 m), somme surface/SDP résiduelle,
liste propriétaires, score. **A** : SDP résiduelle par parcelle dispo (`parcel_residuel`, sortie du
moteur faisabilité). **B** : statut PM joignable (`parcelle_personne_morale` : dénomination + SIREN).
**C (tranché)** : **l'indivision n'est PAS détectable en base** — `parcelle_personne_morale` est
PM-only ; le groupe DGFiP 8 = « Associés » (pas indivision) ; aucune structure de propriété physique
n'existe en open data (doctrine RGPD). → **C abandonné, noté, pas fabriqué.**

## Lot 1 — Gain d'assemblage (A)
Affiche **SDP combinée** (assiette) **vs la meilleure parcelle seule** + le **ratio** et la **taille de
programme débloquée** (logements, hypothèse 70 m²/logt affichée). Preuve (`assemblage-plus.png`) :
*Ensemble 636 092 m² SDP · ~9 087 logements (**×1,5** vs la meilleure seule 425 674 m² / ~6 081)* — le
gain vient d'**atteindre une taille de programme qu'aucune parcelle seule ne permet**. Réutilise les
résiduels du moteur faisabilité (aucun re-scoring).

## Lot 2 — Priorité personne morale (B) + PRIVACY
Bandeau d'approche : **« ✓ Approche simplifiée »** si **tous propriétaires PM**, sinon compte les
particuliers (« approche plus lourde »). Par parcelle : **PM = dénomination + SIREN** (public) ;
**particulier = « propriétaire particulier — non communiqué »** (JAMAIS nommé). Score d'assemblage
bonifié si 100 % PM. Preuve : CBO TERRITORIA · SIREN 452038805, COMMUNE DE SAINT PAUL · SIREN 219740156
(PM nommées) ; BV1193 particulier **masqué**.

## Lot 3 — Indivision (C) — NON détectable, noté
La donnée n'existe pas en base (voir Lot 0). L'outil **note explicitement** : « Indivision : non
détectable en open data (aucune structure de propriété physique publiée) — signal non affiché plutôt
qu'inventé. » **Zéro fabrication.** (Le signal B — présence de particuliers = « approche plus lourde » —
capte déjà, honnêtement, la complexité d'approche sans prétendre détecter une indivision.)

## Non-régression & garanties
`tsc`/build verts, endpoint testé. **Zéro touche scoring/cascade/run.** Privacy prouvée (PM nommée /
particulier masqué). Hook QA `setMsel` ajouté (sans effet produit). Autres outils intacts.

## Merge
`git -C /Users/openclaw/Desktop/labuse checkout main && git merge --no-ff feat/assemblage-plus`
**Pas de merge par CC.**
