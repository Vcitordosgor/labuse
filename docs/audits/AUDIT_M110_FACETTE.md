# M110 — la facette interrogeable : état de la parité (suite de M108)

Livré le 17/08/2026. Complète la carte M108. Le filet M109 reste ; ce mandat le vide à
mesure que les critères entrent au service.

## Critères de comptage — état après M110

`compter_parcelles` appelle la facette `FiltreCriteres` (un critère = un seul endroit).
Exposés : **12** (contre 5 avant M110).

| critère | avant M110 | après M110 | preuve (gate) |
|---|---|---|---|
| commune, surface_min/max, tier, personne_morale | ✅ | ✅ | — |
| **événement rouge** | ❌ | ✅ evenement | événement SD = 1 |
| **procédure judiciaire (BODACC)** | ❌ refus (le constat) | ✅ signaux=procedure | Saint-Denis = **126** |
| **friche** | ❌ détour web | ✅ signaux=friche | Saint-Paul = **207** |
| cession, permis_actif/caduc, nu_pm | ❌ | ✅ signaux=… | (même param) |
| **sans adresse** | ❌ refus | ✅ adresse_absente | Saint-Pierre = 16 603 |
| **copropriété** | ❌ refus | ✅ copro=avec/sans | Saint-Denis = 1 157 |
| **défiscalisation** | ❌ refus | ✅ defisc | Saint-Leu = 100 |
| **renouvellement urbain** | ⚠️ miscompte muet (M109) | ✅ renouvellement | ≥5000 SD = **213** (était 1 970) |
| **zonage PLU (U/AU/A/N)** | ⚠️ miscompte total (M109) | ✅ zonage | zone U Saint-Benoît = **14 528** (était 21 671) |

Chaque critère appliqué est NOMMÉ au récap (« J'ai compris : … · procédure judiciaire
(BODACC) »). Le sélecteur ne les met plus dans `criteres_non_appliques`.

**Restent NON interrogeables (le filet M109 les avoue encore, cf. gate M78 cas cna)** :
constructibilité calibrée (le tier — « constructibles » est approximé en zone U/AU, dit),
budget/prix (charge foncière, prix marché), densité/capacité, rang, fiabilité marché.
Ce sont des critères ÉCONOMIQUES/dérivés — reste par lots pour un mandat ultérieur.

## Résolution d'entité (Phase 2)

Le token-matcher tombait sur les homonymes (« lot SIDR de Terre Sainte », 16 parcelles).
Référentiel en base `entite_acronyme` (seed versionné data/entites/acronymes_moraux.csv,
SIREN vérifiés — jamais une table dans le prompt) : l'acronyme prime sur les tokens.

| acronyme | SIREN | parcelles servies |
|---|---|---|
| SIDR | 310863592 | **4 183** (était 16) |
| SHLMR | 310895172 | 2 618 |
| SAFER | 310836309 | 844 |
| SODIAC | 378918510 | 273 |
| SEMADER | 332824242 | 1 663 |

Ambiguïté réelle (deux entités plausibles de taille comparable, aucune dominante) →
clarification (champ de réponse M107), le Copilote ne tranche pas au hasard. Le référentiel
peut s'étendre par le CSV (`labuse entites-acronymes`) — d'autres SEM/bailleurs vérifiés.

## Concepts non reconnus (Phase 3)

« Parcelles fantômes » et « bailleurs sociaux » répondaient « je ne comprends pas » avec un
champ inutile. Reconnaissance par mots-clés (`_CONCEPT_MAP`) → porte cliquable vers l'outil
qui EXISTE (fantome M07, bailleur M06). Piège écarté : « logements sociaux » nu reste le taux
SRU (stats_commune), PAS l'outil bailleur — le concept vise le PATRIMOINE des bailleurs.

Les autres invisibles de M108 (scoreur-adresse, o6-comparateur, baromètre, permis, promesses,
ZAN, o9-rareté, simulplu, o10-bascules, o7-carnet) et le guidage carte/Surveillance restent
pour M112 (guidage complet).

## Vérification

Gates toutes vertes, rien d'assoupli : véracité M78 **33/33** (dont 1 cas cna prouvant que le
filet vit encore pour un critère économique), facette M110 **11/11** (8 critères branchés +
SIDR + fantôme + bailleur), routeur **100 %** (gate_95), fil **3/3**. 1569 passed · golden
0 FAIL · tsc 0 · build. 7 tests unitaires déterministes (plumbing facette, acronyme, concepts).
