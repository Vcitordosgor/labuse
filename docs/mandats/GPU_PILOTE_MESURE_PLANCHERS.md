# GPU-PILOTE — MESURE DES PLANCHERS (préalable au re-run)

> Point d'arrêt Vic : mesurer les parcelles servies trop petites pour l'opération minimale imposée
> par le plancher, AVANT le re-run. Déterministe : surface minimale = min_logements ÷ densité.
> Run servi `q_v7_defisc`. Rien écrit en base.

## Correction méthodologique importante
Le seuil « X logements minimum ÷ densité » n'a de sens que si le règlement IMPOSE un **min-logements**.
Une **densité seule** (« X log/ha ») n'impose AUCUNE taille de parcelle minimale (une petite parcelle
peut respecter la densité avec peu de logements). Vérification par commune :

| commune | min-logements sourcé ? |
|---|---|
| L'Étang-Salé (97404) | **oui, 10** (« opération d'ensemble comportant un minimum de 10 logements ») |
| Saint-Leu (97413) | **oui, 10** |
| Les Trois-Bassins (97423) | **oui, 5** (« au moins 5 logements ») |
| Saint-Pierre (97416) | **oui, 5** |
| La Possession, Le Tampon, Le Port, Sainte-Marie, Les Avirons, Saint-Louis, Bras-Panon, Sainte-Suzanne, Sainte-Rose | **NON — densité seule** → pas de taille minimale imposée |

Un 1er calcul appliquant « 10 » partout donnait **226 têtes** — FAUX (gonflé par les 9 communes sans
min-logements, dont La Possession +57). La mesure RIGOUREUSE ne porte que sur les 4 communes sourcées.

## Mesure rigoureuse (4 communes sourcées)
Surface minimale = min_log ÷ densité (ex. L'Étang-Salé AUc : 10 ÷ 15 log/ha = 6 667 m² ; AUa : 2 000 m²).

| commune | min-log | AU servies | sous seuil | **dont tête** | brûl. |
|---|---|---|---|---|---|
| Saint-Leu | 10 | 405 | 398 | **39** | 0 |
| Les Trois-Bassins | 5 | 221 | 203 | **24** | **8** |
| L'Étang-Salé | 10 | 103 | 96 | **9** | 0 |
| Saint-Pierre | 5 | 86 | 11 | **0** | 0 |
| **TOTAL** | | 815 | 708 | **72** | **8** |

## Réponses aux questions du mandat
1. **Parcelles servies sous le minimum** : 708 (dont 72 en tête, 8 brûlantes) — sur les 4 communes où
   c'est SOURCÉ. Les 9 autres : pas de seuil de taille (densité seule).
2. **Recouvrement ou addition ?** → **RECOUVREMENT INTÉGRAL** : les 72 têtes sous-seuil sont TOUTES
   déjà dans les têtes AU (les « 534 »). Ce n'est pas une population nouvelle — c'est un sous-ensemble
   avec un motif PLUS FORT : « trop petite pour l'opération minimale » (déterministe, sourcé) plutôt
   que « ouverture subordonnée » (plus mou). Les 8 brûlantes sont toutes à Les Trois-Bassins.
3. **Poids** : moins que les 534 en nombre (72 vs 534), mais QUALITÉ de preuve supérieure : les 72
   sont non constructibles SEULES par un calcul déterministe, pas par une incertitude d'ouverture.

## RÉSERVE (gravée)
« Sous le seuil » = **non constructible SEULE**, PAS « non constructible ». Une parcelle trop petite
pour l'opération minimale peut être **assemblée** avec ses voisines (unité foncière élargie). Le
libellé doit le dire. La mesure porte sur la surface PARCELLAIRE propre (ST_Area geom_2975), pas sur
une éventuelle unité foncière assemblée.

## Trois libellés proposés (NON appliqués)
`declasse_au_statut_inconnu` était fait pour l'ignorance ; maintenant qu'on SAIT, trois traitements :

| statut d'ouverture | traitement | libellé proposé |
|---|---|---|
| **fermée** (AUs/AUst réserve) | déclassement FERME, motif sourcé | **`declasse_au_fermee`** — « Zone AU fermée à l'urbanisation (réserve, ouverture par modification/révision) — source [art., p.] » |
| **conditionnelle_operation** | servie AVEC mention ; SAUF si sous le plancher → déclassée | mention `au_ouverture_conditionnelle` (Absent) ; et si surface < min : **`declasse_au_sous_plancher`** — « Parcelle trop petite pour l'opération minimale imposée (N log ÷ densité = X m² requis) — **non constructible SEULE**, assemblage possible » |
| **conditionnelle_etat_tiers** (phasage 2AU→1AU) | reste INCONNU (dépend de l'aménagement d'autres zones) | **`declasse_au_statut_inconnu`** (existant) — « ouverture subordonnée à l'aménagement d'autres zones AU, non déductible du règlement — a_verifier, jamais supposée ouverte »|

Point clé : `conditionnelle_etat_tiers` ne devient PAS « servie avec mention » — l'ouverture y dépend
d'un ÉTAT EXTÉRIEUR (aménagement des 1AU) non lisible dans le règlement. Elle reste un vrai inconnu.

## Point d'arrêt
Mesure rendue. **Le re-run ne démarre pas.** Priorité d'exécution (ton ordre) : Saint-Paul, La
Possession, Saint-Leu (44 % des têtes) ; Saint-Paul + Les Trois-Bassins (2/3 des brûlantes). NB :
Saint-Paul (PLH) et La Possession (densité seule) n'ont pas de seuil-taille calculable — leur enjeu
est l'OUVERTURE, pas le plancher. Les 8 brûlantes sous-seuil sont à **Les Trois-Bassins**.
