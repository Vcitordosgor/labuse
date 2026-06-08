# DIAGNOSTIC — Complétude figée (62) & opportunité en paliers

*Commune analysée : Saint-Paul (97415), 3 000 parcelles, dernière évaluation.*
*Diagnostic seul — aucun fichier de logique modifié.*

## Résumé exécutif

| Symptôme | Cause racine (en une phrase) |
|---|---|
| **Complétude = 62 partout** | Elle mesure *« la couche est ingérée et a tourné pour la commune »*, **pas** *« y a-t-il de la donnée sur CETTE parcelle »*. L'ingestion étant uniforme sur la commune, le score est constant. |
| **Opportunité en paliers** | Score = `50 + Σ bonus PLATS {8,3,6,12} − pénalités plates`. **Aucune variable continue** (surface, prix DVF, taille d'îlot) n'entre. Mêmes drapeaux ⇒ même score, à la parcelle près. |

Distribution réelle (preuve) : la complétude ne prend que **2 valeurs** sur toute la commune (62 ×2915, 52 ×85) ; l'opportunité agglutine **2 195 parcelles sur la seule valeur 58**.

---

## 1. Complétude figée à 62

### 1.1 Calcul réel (tel que codé — `scoring/completeness.py` + `config/completeness_weights.yaml`)

```
score = Σ poids(famille) pour chaque famille « couverte »
famille couverte  ⇔  au moins une de ses couches a rendu un verdict ≠ UNKNOWN
cadastre          ⇔  couvert dès que la parcelle est ingérée (géométrie connue)
```

12 familles, somme des poids = 100. État à Saint-Paul (identique pour les 2 915 survivantes) :

| Famille | Poids | Couche cascade | Saint-Paul |
|---|--:|---|---|
| cadastre | 8 | *(ingérée)* | ✅ |
| zonage_plu_gpu | 12 | `zonage_plu_gpu` | ✅ |
| agricole_safer | 8 | `safer` | ✅ |
| parc_national | 6 | `parc_national` | ✅ |
| pente | 8 | `pente` | ✅ |
| dvf | 10 | `dvf` | ✅ |
| ocs_ge | 5 | `ocs_ge` | ✅ |
| acces | 5 | `acces` | ✅ |
| **sar** | 10 | `sar` | ❌ non ingéré |
| **risques_georisques_ppr** | 12 | `risques` | ❌ non ingéré |
| **sitadel** | 8 | `sitadel` | ❌ non ingéré |
| **proprietaire** | 8 | `proprietaire` | ❌ FF non branché |
| | | | **= 62 couvert / 38 manquant** |

### 1.2 Preuve chiffrée — 6 parcelles de 63 m² à 9 723 m²

Toutes affichent **exactement le même couvert (62) et le même manquant (38)** :

| Parcelle | Surface | Complétude | Couvert | Manquant |
|---|--:|--:|---|---|
| 97415000BO0877 | 63 m² | **62** | cadastre, zonage, safer, parc, pente, dvf, ocs, acces | sar, risques, sitadel, proprietaire |
| 97415000BO0853 | 419 m² | **62** | *(idem)* | *(idem)* |
| 97415000BO0885 | 668 m² | **62** | *(idem)* | *(idem)* |
| 97415000BO0886 | 1 372 m² | **62** | *(idem)* | *(idem)* |
| 97415000BV1431 | 2 274 m² | **62** | *(idem)* | *(idem)* |
| 97415000BK0023 | 9 723 m² | **62** | *(idem)* | *(idem)* |

Distribution sur toute la commune : **62 → 2 915 parcelles**, **52 → 85 parcelles**.
Les 85 à *52* sont exactement les **exclues** : un `HARD_EXCLUDE` court-circuite la **phase 2**, donc `dvf` ne tourne pas → la famille dvf (10) tombe → 62 − 10 = **52**. (Effet de bord : être *exclue* fait baisser la complétude, alors que rien n'est moins « connu ».)

### 1.3 Votre hypothèse : **CONFIRMÉE.**

Oui — toutes les parcelles ont le **même jeu de couches présentes** (cadastre, zonage, SAFER, pente, parc, OCS, accès, DVF) et les **mêmes trous** (SAR, risques/PPR, SITADEL, propriétaire). Elles atterrissent donc **mécaniquement à 62**. (Nuance : ABF est dans la cascade mais **n'est pas** une famille de complétude — son absence ne pèse pas ; les 4 trous pondérés sont sar/risques/sitadel/proprietaire = 38.)

### 1.4 Le cœur du problème : « source a répondu » vs « donnée sur CETTE parcelle »

**La complétude mesure le premier.** Un `PASS` du type *« Hors forêt publique »* compte comme **couvert** — la couche a tourné et conclu « non concerné », ce qui est une vraie information, mais **identique pour toute la commune**. Le score ne regarde donc pas s'il existe de la donnée *spécifique* à la parcelle : il regarde **quelles couches sont ingérées**. Comme l'ingestion est commune-wide, la complétude est un invariant.

> En l'état, **62 est honnête** : on ne sait réellement pas plus sur une parcelle que sur sa voisine. La complétude *fait son travail d'alerte* (« il manque SAR/risques/propriétaire »). Elle n'est pas *fausse* — elle est *non discriminante parce que la donnée sous-jacente est uniforme*.

### 1.5 Proposition (sans la coder)

1. **Levier principal, honnête : ingérer les couches à couverture *partielle*.** La complétude ne *peut* diverger entre parcelles que si une source ne couvre qu'une *partie* de la commune. SAR/risques-PPR/propriétaire-FF sont précisément de ce type (le PPR ne touche que certaines zones, l'indivision est parcellaire). Tant qu'elles manquent, viser une complétude « variée » serait **artificiel**.
2. **Rendre 2–3 familles réellement parcellaires** (quand la donnée le permet) :
   - `proprietaire` : déjà correct (UNKNOWN si FF n'a rien sur la parcelle) — à brancher.
   - `dvf` : pondérer la *certitude* par le nombre de comparables réels dans le rayon (0 mutation = information faible ; ≥N = forte), au lieu de « ingéré = +10 » binaire.
   - `risques` : une fois ingéré, « concerné/hors champ » variera naturellement par géométrie.
3. **Optionnel — qualité/fraîcheur** : nuancer une famille couverte par l'âge/résolution de la donnée (DVF ancien, pente grossière) pour un dégradé fin.
4. **Garder la règle d'or** : complétude < 50 plafonne le verdict ; la complétude reste affichée *à côté* de l'opportunité, jamais cachée.

---

## 2. Opportunité en paliers

### 2.1 Calcul réel (`scoring/opportunity.py` + `config/opportunity_weights.yaml`)

```
si un HARD_EXCLUDE       → score = 0
sinon  score = clamp( 50 − Σ pénalités + Σ bonus + ai_adjustment , 1 , 100 )
   pénalité = 5 × mult(sévérité)   avec mult = {faible:1, moyen:2, fort:3}  → −5/−10/−15
   bonus    = valeur PLATE lue dans la table, une par couche POSITIVE
```

**Bonus réellement déclenchables à Saint-Paul** (comptage sur la dernière éval) :

| bonus_key | Valeur | Parcelles qui le déclenchent | Remarque |
|---|--:|--:|---|
| `zonage_u_au` | +8 | **2 696** | binaire (zone U/AU) |
| `acces_direct_voirie` | +3 | 485 | binaire |
| `contexte_dvf_favorable` | +6 | 166 | **plat** : déclenché si ≥3 mutations ; **le prix médian est calculé puis jeté** |
| `potentiel_foncier_region` | +12 | 20 | **plat** : taille/recouvrement de l'îlot ignorés |
| `permis_sitadel_recent_proximite` | +8 | 0 | SITADEL non ingéré |
| `proprietaire_morale_acquerable` | +12 | 0 | FF non branché |
| `proximite_equipements_bpe` | +4 | **0** | **bonus mort : aucune couche ne l'émet** |

### 2.2 Décompte ligne par ligne — 6 opportunités, surfaces 63 → 9 723 m²

| Parcelle | Surface | Décompte | Opp |
|---|--:|---|--:|
| BO0877 | **63 m²** | 50 +12 potentiel +8 zonage | **70** |
| BO0853 | 419 m² | 50 +3 accès +6 dvf +8 zonage | 67 |
| BO0885 | 668 m² | 50 +12 potentiel +8 zonage | 70 |
| BO0886 | **1 372 m²** | 50 +12 potentiel +8 zonage | **70** |
| BV1431 | 2 274 m² | 50 +3 accès +12 potentiel +8 zonage | 73 |
| BK0023 | **9 723 m²** | 50 +3 accès **−5 ocs** +12 potentiel +8 zonage | **68** |

**Lecture :** 63 m² et 1 372 m² obtiennent **le même 70** (mêmes deux bonus). La plus grande parcelle (9 723 m²) tombe à **68** — uniquement à cause d'un `−5` OCS, **pas** de sa taille. La surface **n'entre jamais** dans le calcul.

**Distribution (paliers) :** `58 → 2 195` · `61 → 289` · `64 → 70` · `67 → 10` · `70 → 13` · `73 → 3` … La valeur modale **58 = 50 + 8** (zone U seule, sans autre signal) concentre **2 195 parcelles**.

### 2.3 Facteurs différenciants IGNORÉS alors que la donnée existe en base

| Facteur | Donnée disponible ? | Utilisé dans le score ? |
|---|---|---|
| **Surface** (`parcels.surface_m2`) | ✅ sur chaque parcelle | ❌ jamais |
| **Prix / € DVF** (médiane calculée par `DvfLayer`) | ✅ calculé, affiché dans la fiche | ❌ jeté (seul le *compte ≥ 3* compte, +6 plat) |
| **Taille / recouvrement de l'îlot Potentiel foncier** (`ctx.intersections().coverage`) | ✅ calculé | ❌ jeté (+12 plat) |
| **Densité / contexte bâti** (`ocs_ge`) | ✅ | ⚠️ binaire (pénalité tout-ou-rien) |
| **Proximité équipements (BPE)** | ❌ couche non écrite | ❌ bonus défini (+4) mais mort |
| **Ajustement IA ±20** | — | ❌ l'éval app a tourné **sans IA réelle** (`ai_payload` vide) → 0 partout |

### 2.4 Proposition (sans la coder) — rendre l'opportunité discriminante, **en restant traçable**

Le mécanisme est déjà bon (chaque facteur = une **ligne de cascade** avec un `weight_applied` signé). Il suffit de **remplacer des poids constants par des poids calculés bornés**, sans casser la traçabilité :

1. **Surface / taille du gisement** → bonus **gradué borné** (courbe saturante : peu d'effet sous le seuil de constructibilité, plafonné pour les très grandes parcelles), tracé `surface : +X`.
2. **DVF** → remplacer le `+6` binaire par un signal **continu borné** = f(nombre de comparables, niveau de prix vs médiane commune). Tracé `marché : +X (médiane Y €, N comparables ≤ R m)`.
3. **Potentiel foncier** → pondérer par le **recouvrement de l'îlot** déjà calculé → `+0…12` au lieu de `+12` plat.
4. **Brancher BPE** (distance aux équipements) → le bonus mort devient vivant et **gradué** par la distance.
5. **OCS** → graduer (sol nu/agricole/déjà bâti) plutôt que tout-ou-rien.

**Garde-fous à conserver (non négociables) :**
- Chaque composante reste **bornée** et **écrite dans la cascade** (`weight_applied`) → la fiche reste auditable ligne à ligne.
- **Règle d'or intacte** : l'opportunité ne s'affiche jamais seule ; `complétude < 50` plafonne le verdict ; un facteur continu ne doit pas franchir le seuil d'« opportunité » sans complétude suffisante.
- **Normaliser** pour éviter qu'un seul facteur (surface) écrase les autres ; garder les poids **tunables** et nourris par le feedback terrain (déjà prévu §10).
- **Ne pas fabriquer de précision** : n'introduire un facteur que si sa donnée est réelle pour la parcelle (surface : oui tout de suite ; BPE : seulement une fois ingéré).

**Effet attendu :** les 2 195 parcelles aujourd'hui collées à 58 s'**étaleraient** selon surface / marché / îlot → un tri enfin utile au promoteur, sans rien inventer ni rompre la traçabilité.

---

## Ce que je propose de valider avant toute correction

1. **Cause complétude** : non-discriminante car *coverage commune-wide* (≠ donnée parcellaire). → corriger surtout par **ingestion de couches à couverture partielle**, pas par un trucage de formule.
2. **Cause opportunité** : score = somme de **bonus binaires plats**, **surface/prix/îlot ignorés**. → introduire des **composantes continues bornées et tracées**, règle d'or préservée.

*Dis-moi quelle(s) cause(s) et quelle approche tu valides — je ne coderai qu'ensuite.*
