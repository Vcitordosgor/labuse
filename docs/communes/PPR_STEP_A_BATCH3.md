# Généralisation Étape A PPR — mini-batch 3 (6 communes gold) — ⏸️ **en attente de validation**

> **Mini-batch 3 de généralisation de l'Étape A PPR** (règle déjà mergée : périmètre PM1 marginal < 10 % →
> flag `faible` informatif). **Re-cascade SEULE** de 6 communes gold (`run_all.evaluate_commune`, **sans
> ré-import, sans changement de code/config/scoring/seuil 65**) : **Bras-Panon, Les Avirons, Le Port,
> Sainte-Suzanne, Petite-Île, Sainte-Marie**. **Saint-Denis & Saint-André exclus** (décision).
> **Effet dominant = re-homogénéisation** de communes cascadées plus anciennement (06-22/06-23) au code courant :
> assainissement `declassement` (−205) et **re-scoring** (Le Port **+157**). L'Étape A propre est **minime** (+9,
> 0 perte). Net opportunités **1 581 → 1 538 (−43)**.
> **Rapport de travail — NON commité, NON mergé, aucun backup stable créé. Stop pour validation.**

## 1. Objectif & méthode

- **Généraliser l'Étape A** à 6 communes gold qui la précédaient (PPR faible = 0, `rules 2b45db742f40`).
- **Re-cascade séquentielle** (ordre imposé), transaction indépendante par commune, **baseline pré-batch 3 = backup
  stable post-batch 2** (pas de nouveau backup). Aucun import, aucun reload, aucune Étape B, aucun passage gold,
  aucun changement code/config/scoring/seuil 65. **Saint-Denis & Saint-André non inclus.**
- **Exit 0 (RC=0)**, ~2 h 20 wall-time.

| # | Commune | INSEE | Parcelles | Durée |
|---|---|---|---:|---:|
| 1 | Bras-Panon | 97402 | 6 041 | 387 s |
| 2 | Les Avirons | 97401 | 8 611 | 481 s |
| 3 | Le Port | 97407 | 10 195 | 361 s |
| 4 | Sainte-Suzanne | 97420 | 12 527 | 4 638 s (dense) |
| 5 | Petite-Île | 97405 | 13 137 | 889 s |
| 6 | Sainte-Marie | 97418 | 16 746 | 1 651 s |

## 2. Résultats par commune (avant → après, 100 % évaluées)

| Commune | Opp avant | Opp après | Net | Gain Étape A (marg) | Autres gains | Retrait | PPR fort | PPR faible |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| Bras-Panon | 210 | **155** | **−55** | +1 | 0 | −56 | 1 624→1 425 | 0→437 |
| Les Avirons | 104 | **93** | **−11** | +1 | 0 | −12 | 3 883→3 403 | 0→1 013 |
| **Le Port** | 74 | **236** | **+162** | +5 | **+157** | 0 | 836→761 | 0→112 |
| Sainte-Suzanne | 321 | **231** | **−90** | +1 | 0 | −91 | 5 633→4 988 | 0→1 157 |
| Petite-Île | 115 | **116** | **+1** | +1 | 0 | 0 | 5 650→4 856 | 0→1 453 |
| Sainte-Marie | 757 | **707** | **−50** | 0 | +4 | −54 | 9→1 | 0→41 |
| **Total** | **1 581** | **1 538** | **−43** | **+9** | **+161** | **−213** | — | 0→**4 213** |

Verdicts détaillés (avant → après) :

| Commune | À creuser | Écartée | Faux positif probable |
|---|---|---|---|
| Bras-Panon | 1 624 → 808 | 253 → 287 | 3 954 → 4 791 |
| Les Avirons | 1 260 → 906 | 794 → 810 | 6 453 → 6 802 |
| Le Port | 2 281 → 2 119 | 912 → 912 | 6 928 → 6 928 |
| Sainte-Suzanne | 3 475 → 1 817 | 212 → 260 | 8 519 → 10 219 |
| Petite-Île | 1 685 → 1 684 | 217 → 217 | 11 120 → 11 120 |
| Sainte-Marie | 5 142 → 4 210 | 424 → 444 | 10 423 → 11 385 |

## 3. ⚠️ Constat notable — Le Port (+162, dont +157 NON imputables à l'Étape A)

- **Les 162 gains de Le Port étaient tous `à creuser`** et ont tous **monté en score** : **49–64 → 65–72**
  (franchissement du seuil 65 par le haut). **Score inchangé = 0, score baissé = 0.**
- **Seulement 5 / 162 portent le flag marginal** (Étape A) ; **les 157 autres sont un pur effet de RE-SCORING** :
  Le Port a été cascadée pour la dernière fois le **2026-06-22**, à un code de scoring **antérieur** ; la
  re-cascade le **ré-homogénéise au scoring courant**, qui note ces 157 parcelles plus haut (Le Port = zone
  portuaire à forte valeur DVF). **Ce n'est PAS un effet Étape A**, et **pas une incohérence** (162 `à creuser`
  → `opportunité`, exactement ; `écartée`/`fpp` inchangés).
- **À valider** : ces 157 opportunités « retrouvées » reflètent le scoring **actuel** (cohérent avec le reste du
  portefeuille) que la cascade 06-22 sous-estimait. Effet **qualité** plausible, mais c'est une **dérive de
  scoring inter-versions** à connaître — à confirmer dans le chantier d'homogénéisation/optimisation.

## Contrôle ciblé Le Port — +157 re-scoring hors Étape A

> Contrôle **read-only** demandé avant validation (aucun rollback, aucune correction code).

**Cause racine identifiée — amélioration de complétude à l'échelle de la commune.** Les **157 gains hors Étape A**
étaient tous `à creuser` (score 49–64) → `opportunité` (65–72) par **montée de score**, sans déflag PPR. Cause :
le **score de complétude monte uniformément +10 (74 → 84) sur 9 903 / 10 195 parcelles de Le Port** (toute la
commune, +9,7 en moyenne) → **une couche de données absente à la cascade du 2026-06-22 est désormais présente**.
Plus de données ⇒ score d'opportunité plus haut ⇒ les parcelles borderline franchissent 65. **Ce n'est ni
l'Étape A (5/162 seulement portent le flag marginal), ni un déclassement levé, ni parcelle-spécifique.**

**Échantillon (40 parcelles : 20 top score, 10 au seuil 65, 10 aléatoires) — profils homogènes et sains :**

| Critère | Constat sur l'échantillon |
|---|---|
| Score avant → après | 57–64 → 65–72 (franchissement du seuil 65) |
| Complétude avant → après | **74 → 84** (uniforme, +10) |
| Zonage | **100 % zone U / AUc** (urbain constructible) |
| PPR | **aucun** (0 risque) sur tout l'échantillon |
| Déclassement | **non** (aucun : ni déjà-bâti, ni micro) |
| Surface | 284 m² à 21 849 m² (majorité > 1 000 m², au-dessus du seuil 250 m²) |
| DVF / marché | **POSITIVE** (mutations récentes ≤ 1 000 m, ex. médiane ~869 €/m²) |
| Accès | OK (POSITIVE/PASS, aucune parcelle enclavée) |
| Facteur suspect | **aucun** |

**Verdict :** les **+157 sont ACCEPTABLES** comme **re-homogénéisation au scoring/complétude courant** — ce sont
de **vraies opportunités** (parcelles constructibles, non bâties, sans risque, avec marché) que la cascade du
06-22 **sous-estimait faute d'une couche de données**. **À DOCUMENTER comme dérive de complétude inter-version**
(non bloquante). **NON suspect — aucun stop requis.** Recommandation : traiter cette ré-homogénéisation dans le
**chantier d'homogénéisation/optimisation cascade** (re-cascader le portefeuille à complétude/scoring courant).

## 4. Synthèse globale (6 communes)

| Indicateur | Valeur |
|---|---:|
| Parcelles re-cascadées | 67 257, 100 % évaluées |
| **Opportunités avant → après** | **1 581 → 1 538** |
| **Gains totaux** | **+170** |
| — via flag Étape A (PPR marginal) | **+9** |
| — via re-scoring montant (dont Le Port +157, Sainte-Marie +4) | **+161** |
| **Retraits totaux** | **−213** |
| — via `declassement` (déjà bâti / micro) | −205 |
| — via re-scoring descendant (borderline sous 65) | −8 |
| **Net opportunités** | **−43  (= 170 − 213 = 1 538 − 1 581)** |
| **Perte imputable à l'Étape A** (flag marginal) | **0** |
| PPR faible créé (flag informatif Étape A) | 0 → 4 213 |
| Taux d'opportunité global | 2,35 % → 2,29 % |

> **Contrôle de cohérence (read-only).** `net = gains − retraits` vérifié par commune et au total ;
> `gained`/`lost` disjoints. **170 − 213 = −43 = 1 538 − 1 581.** **0 perte via le flag marginal** sur les 6 communes.

- **L'Étape A propre est MINIME ici (+9, 0 perte)** : ces communes ont peu de parcelles d'opportunité au bord
  marginal d'un périmètre PPR. Le batch est en réalité une **re-homogénéisation** de communes cascadées en 06-22/23 :
  - **Assainissement `declassement` −205** (faux positifs déjà bâtis / micro) sur Bras-Panon (−56), Sainte-Suzanne
    (−91), Sainte-Marie (−49), Les Avirons (−9) → **qualité ↑** ;
  - **Re-scoring +161** dont **Le Port +157** (cf. §3) → opportunités sous-estimées retrouvées.
- **4 213 parcelles** nouvellement annotées **PPR faible** (informatif, non bloquant) ; PPR fort baisse partout.

## 5. Conservation / intégrité

- **DB globale inchangée : 431 663 parcelles / 24 communes** · **gold 17 inchangé** (aucun passage gold).
- **Seules les 6 communes du batch** ont reçu de nouvelles évaluations (26/06 23:10 → 27/06 01:29) ; **18 autres
  communes intactes**, **Saint-Denis & Saint-André NON touchés**, aucun autre INSEE.
- **Aucun changement de code / config / tests / scripts** : `git status` propre, `HEAD = origin/main = 6590ed1`.
- Aucun import, aucune couche rechargée, aucune Étape B, aucun rollback, aucun changement de seuil/scoring.

## 6. Recommandation

- **Mini-batch 3 propre** (RC=0, conservation OK) mais **moins « Étape A » que re-homogénéisation** : le constat
  **Le Port (+157 re-scoring)** confirme que les communes cascadées anciennement ont des **baselines de scoring
  hétérogènes**.
- **Avant tout nouveau batch** : ouvrir le **chantier d'optimisation/homogénéisation cascade** (perf + scoring
  inter-versions), d'autant que **Saint-Denis (38 138)** et **Saint-André (PPR 92 %)** restants seraient **lents**
  et porteraient la même dérive de re-scoring.
- **Décision attendue** : valider l'état re-cascadé (pas de rollback) — notamment **accepter les +157 de Le Port**
  comme re-scoring courant — puis, sur GO séparé : commit docs-only, merge, backup stable post-batch 3.

---

### Provenance (lecture seule, hors les 6 mutations re-cascade autorisées)
- Mutations **autorisées** : re-cascade des 6 communes (`evaluate_commune`), baseline = backup stable post-batch 2.
- Avant/après : snapshot Phase 1 (avant) + état courant (après) ; transitions reconstruites via versions
  `parcel_evaluations` (avant = dernière éval < 26/06 23:00, après = dernière éval), scores `opportunity_score`,
  attribution via `cascade_results`.
- Aucun import, aucune couche modifiée, aucune autre commune touchée (Saint-Denis/Saint-André exclus), aucun
  rollback, aucun passage gold, aucun changement code/config/scoring/tests.
