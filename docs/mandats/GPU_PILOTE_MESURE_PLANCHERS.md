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

---
# ADDENDUM — arbitrage Vic : libellé 3 corrigé + 2 mesures

## Libellé 3 CORRIGÉ (ne pas déclasser)
Une parcelle sous plancher est une **candidate à l'assemblage** (LABUSE porte `/assemblages`,
`/assemblage/study`). La déclasser ferait l'erreur symétrique : transformer « pas seule » en « pas du
tout ». → **statut `au_sous_plancher`, SERVIE, mention en tête de fiche** :
> « Cette parcelle est trop petite pour l'opération d'ensemble minimale imposée par le règlement
> (X logements à Y log/ha, soit Z m² minimum). Elle n'est pas constructible SEULE, mais peut l'être
> en assemblage avec une ou plusieurs parcelles voisines. » + **surface manquante affichée** (Z − surface).
Les 3 traitements : `declasse_au_fermee` (fermée) · `au_sous_plancher` servie+mention (sous plancher) ·
`declasse_au_statut_inconnu` (phasage, vrai inconnu).

## Mesure A — assemblage (« segment, pas dette »)
Combien des sous-seuil ont un voisin CONTIGU de même zone qui atteindrait le seuil (own + voisins
`ST_DWithin` 0,5 m, même `zone_lib`) :
| | sous seuil | **assemblables** |
|---|---|---|
| total | 708 | **399 (56 %)** |
| en tête | 72 | **48 (66 %)** |
| brûlantes | 8 | **7 / 8** |
→ **Significatif : c'est un SEGMENT** (candidates à l'assemblage), pas une dette. Réserve : mesure
GÉOMÉTRIQUE (contiguïté + surface) ; ne teste pas la propriété (voisin acquérable ?) — couche suivante.

## Mesure B — « opération d'ensemble » dans les 9 communes densité-seule (verbatim, sans conclure)
Les 9 imposent «  opération d'aménagement d'ensemble » MAIS **en option** :
> « soit par opération d'aménagement d'ensemble, **soit au fur et à mesure de la réalisation des
> équipements** » (La Possession, Le Port, Les Avirons, Bras-Panon, Sainte-Rose, Sainte-Marie,
> Sainte-Suzanne, Le Tampon — verbatim quasi identique ; Saint-Louis : source indisponible).
→ L'opération d'ensemble n'est PAS obligatoire (« soit… soit ») → **pas de taille minimale implicite**.
La conclusion « les 9 densité-seule n'ont pas de seuil-taille » TIENT. (À reconfirmer sur Saint-Louis.)

## Point d'arrêt
Deux mesures rendues. **Le re-run ne démarre pas.** Ordre validé : Saint-Paul, La Possession,
Saint-Leu (ouverture) ; Les Trois-Bassins (8 brûlantes sous plancher, dont 7 assemblables). NB :
Saint-Paul (PLH) + La Possession (densité seule) → enjeu OUVERTURE, pas plancher.
