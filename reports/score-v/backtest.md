# Backtest Score V — lift du décile supérieur

- Cohorte : **20768** parcelles vendues (DVF 'Vente' 2023-01-01 → 2025-12-31) vs **83072** non-vendues (stratifiées commune, ×4, seed 974).
- Recalcul V à **T−12 mois** avant vente (signaux datés ≤ T uniquement) ; non-vendues à T réf. = 2023-05-31 (médiane des ventes −12 mois). 12049 parcelles V=NULL exclues (publics/bailleurs).
- Taux de vente de base : 0.201.

## Résultat : lift top décile = **1.36×**

🔴 **LIFT < 1.5× : poids à retravailler avant tout usage commercial du score.**

| Décile | V min–max | n | Taux de vente | Lift |
|---|---|---|---|---|
| D1 | 8–73 | 9179 | 0.274 | **1.36×** |
| D2 | 8–8 | 9179 | 0.186 | **0.92×** |
| D3 | 8–8 | 9179 | 0.178 | **0.89×** |
| D4 | 8–8 | 9179 | 0.170 | **0.85×** |
| D5 | 8–8 | 9179 | 0.184 | **0.91×** |
| D6 | 8–8 | 9179 | 0.177 | **0.88×** |
| D7 | 8–8 | 9179 | 0.180 | **0.89×** |
| D8 | 8–8 | 9179 | 0.181 | **0.90×** |
| D9 | 8–8 | 9179 | 0.179 | **0.89×** |
| D10 | 0–8 | 9180 | 0.300 | **1.49×** |

## Lift par bande de score (coupe produit, sans artefact d'ex æquo)

| Bande | n | Taux de vente | Lift |
|---|---|---|---|
| V ≥ 50 (fort) | 54 | 0.130 | **0.64×** |
| V 25-49 (présents) | 2342 | 0.203 | **1.01×** |
| V 9-24 (faible, au-delà de la tenure seule) | 3298 | 0.428 | **2.13×** |
| V = 8 (tenure seule) | 81217 | 0.179 | **0.89×** |
| V 0-7 | 4880 | 0.410 | **2.04×** |

![lift](backtest_lift.svg)

## Caveats (à lire avant tout usage commercial)
- **DGFiP PM = millésime 2025** : pour une vente 2023-2025, le fichier peut déjà porter l'acheteur → fuite temporelle familles A/B/C (elle joue plutôt CONTRE le lift).
- Fenêtre DVF 2021+ : tenure OBS5 tronquée à T (2-4 ans d'observation).
- Friches et siège : millésimes courants, pas d'historique public.
- Famille E (DPE) non testée à T−12 : 43 F/G sur l'île — volume insuffisant pour peser.
## Lecture des résultats (calibration v1.1)

Le lift global est plombé par la **masse des V=8** (81 217 parcelles « tenure seule », lift 0,89× —
du bruit) : le signal `DVF_TENURE_OBS5` sur une fenêtre de 2-4 ans d'observation à T ne discrimine
pas. En revanche :

- **V 9-24 (signaux au-delà de la tenure seule) : lift 2,13×** — le cœur informatif du score
  (friche, dirigeant âgé, hors-île… combinés) **bat la cible 2×**.
- **V 0-7 : lift 2,04×** — ce sont les parcelles frappées du **malus « achat récent »** : une
  parcelle déjà mutée récemment RE-vend plus souvent (marché actif / marchands de biens). Le malus
  est CONTRE-prédictif tel quel : à repenser (le retirer, ou en faire un signal positif « marché
  actif » dans une famille dédiée).
- **V ≥ 50 (fort) : 0,64× sur n=54** — la détresse juridique lourde à T−12 ne se convertit pas en
  vente DVF sous 12-24 mois (procédures longues + fuite millésime PM qui joue contre). Échantillon
  trop petit pour conclure.

**Recommandation v1.1** (barème v1 verrouillé D1, non modifié) : réduire fortement le poids de la
tenure OBS5 (ou l'exiger en COMBINAISON), repenser le malus achat récent, re-backtester après le
chargement d'un historique DVF plus profond (mandat data à venir).
