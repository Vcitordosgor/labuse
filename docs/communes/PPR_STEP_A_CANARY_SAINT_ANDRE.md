# Canari urbain Étape A PPR — Saint-André (re-homogénéisation) — ⏸️ **en attente de validation**

> **2ᵉ canari** du chantier d'homogénéisation cascade, sur commune **urbaine sous-scorée** : re-cascade **SEULE** de
> **Saint-André (97409)** (`labuse evaluate --commune`, **sans ré-import, sans changement de code/config/scoring/seuil
> 65, sans --ai**), pour tester l'hypothèse « commune urbaine ancienne = gros gisement d'opportunités latentes ».
> **Baseline rollback = backup stable post-batch 3** (aucun backup pré-canari dédié ; *NB* : Les Trois-Bassins a été
> re-cascadée depuis post-batch 3). **Saint-Denis NON touché.** **Rapport de travail — NON commité, aucun backup
> post-canari créé. Stop pour validation.**

## 1. Méthode & exécution

- Commune : **Saint-André** uniquement (97409, 22 600 parcelles). Aucun autre INSEE. **Pas Saint-Denis.**
- `labuse evaluate --commune "Saint-André"` → cascade + scoring par lots de 2 000. **RC=0.**
- Avant/après par cutoff `evaluated_at` = `2026-06-27 10:54:31 UTC` (`parcel_evaluations` append-only ; PPR « avant »
  = snapshot `cascade_results` lu **avant** le run, table remplacée à la re-cascade).
- Aucun import, aucune couche rechargée, aucune Étape B, aucun passage gold, aucun rollback, aucun changement de code.

| Mesure | Valeur |
|---|---:|
| Durée totale | **2 099 s (35 min)** |
| **Temps / parcelle** | **0,093 s** |
| Parcelles évaluées | 22 600 (100 %) |

## 2. Résultats — verdicts avant → après

| Verdict | Avant (06-23) | Après (canari) | Δ |
|---|---:|---:|---:|
| 🎯 **opportunité** | 54 | **56** | **+2** |
| à creuser | 6 851 | 6 849 | −2 |
| exclue | 548 | 548 | 0 |
| faux positif probable | 15 147 | 15 147 | 0 |
| **complétude moyenne** | **82,9** | **82,9** | **0** |

**Seule transition** : `a_creuser → opportunité` **×2**. **Aucun autre mouvement** (pas d'assainissement `a_creuser →
fpp`, contrairement à Les Trois-Bassins). Distribution de score : `≥65` 295→293, `60-64` 781→799, `55-59` 816→876
(re-scoring **marginal**, quasi aucune traversée du seuil 65).

## 3. PPR fort / faible (effet Étape A marginal)

| | Avant | Après | Δ |
|---|---:|---:|---:|
| PPR **fort** | 20 900 | 20 135 | **−765** |
| PPR **faible** (flag marginal) | **0** | **765** | **+765** |

Commune **urbaine très contrainte** : 20 900 / 22 600 (**92 %**) en PPR fort avant. L'Étape A a **déflagué 765
parcelles** PM1-marginales fort → faible (`20 135 + 765 = 20 900`, conservation exacte). **Mais des 765 déflaguées,
2 seulement deviennent opportunité** ; les 763 autres restent fpp (583) / à creuser (169) / exclue (11) — **bloquées
par d'autres facteurs** (score < 65, zonage, surface, emplacements réservés…), pas par le PPR.

## 4. Attribution du gain net (+2) & pertes

| Source | Opportunités |
|---|---:|
| **Gain via Étape A** (déflag marginal) | **+2** |
| Autres gains re-scoring **pur** | **0** |
| **Retraits / pertes d'opportunité** | **0** |
| **Net** | **+2** |

- Les **2 gains** = parcelles **125537** et **139194** : score **62 → 72** **ET** PPR fort → **faible**. Les deux
  étaient nécessaires (sans le déflag, bloquées par le PPR fort même à 72) → attribué **Étape A**.
- **0 perte d'opportunité** · **0 perte imputable au flag marginal** (le déflag ne fait que lever un blocage).

## 5. ⭐⭐ Comparaison à 3 — l'hypothèse « urbaine sous-scorée = gros gisement » est **RÉFUTÉE**

| | Le Port (urbain, fait 06-26) | Les Trois-Bassins (rural, canari 1) | **Saint-André (urbain, canari 2)** |
|---|---:|---:|---:|
| Parcelles | 10 195 | 5 314 | **22 600** |
| Temps / parcelle | 0,035 s | 0,092 s | **0,093 s** |
| **Net opportunités** | **+162** | **+1** | **+2** |
| dont Étape A (marginal) | +5 | +1 | **+2** |
| dont **re-scoring pur** | **+157** | 0 | **0** |
| **Complétude Δ** | **+10** (74→84) | **0** (79,9) | **0** (82,9) |
| PPR déflaguées (fort→faible) | ~101 | 183 | **765** |
| Pertes | 0 | 0 | **0** |

> **Conclusions empiriques (2 canaris) :**
> 1. **Aucune dérive de complétude** ni en rural ni en **urbain** (Saint-André 82,9 → 82,9) → le **+157 de Le Port
>    était bien un événement LOCAL** (couche de données spécifique), **pas une dérive systématique**. **Confirmé sur
>    le cas urbain**, qui était le vrai test.
> 2. **L'« upside near-threshold urbain » ne se matérialise pas** : Saint-André avait 781 parcelles à 60-64 et 92 %
>    de PPR fort, mais re-cascader n'en convertit que **2**. Le déflag marginal touche 765 parcelles mais quasi
>    aucune n'est à la fois ≥ 65 **et** débloquée par ailleurs.
> 3. **La re-cascade des communes *stale* est un travail de COHÉRENCE/qualité, pas de découverte d'opportunités.**

## 6. Perf — extrapolation Saint-Denis confirmée

Cadence urbaine mesurée **0,093 s/parcelle** (≈ identique au canari rural 0,092). **Saint-Denis (38 138 parc.) ≈
59 min** ; même au pire cas dense ~3,9 h. **Optimisation code non justifiée** — confirmé sur 2 communes.

## 7. Recommandation pour la suite

- **Saint-Denis** : profil **identique** à Saint-André (urbain, stale, PPR élevé). Attendu = **rendement faible
  (poignée d'opportunités), 0 perte, complétude stable, ~1 h**. Le faire relève de la **cohérence du portefeuille**
  (tout sur règles courantes `fb6a5478b2bf`), **pas d'un ROI d'opportunités**.
- **3 non-gold restantes** (La Plaine-des-Palmistes, Sainte-Rose ; Les Trois-Bassins déjà faite) : rendement
  attendu **quasi nul**, rapides — cohérence uniquement.
- **Décision (sous GO séparé)** : (a) finir l'homogénéisation pour la cohérence — Saint-Denis puis les 2 non-gold ;
  **ou** (b) s'arrêter là, l'hétérogénéité résiduelle étant désormais **mesurée comme bénigne** (pas de gisement
  caché, pas de risque). **Pas d'optimisation, pas de backup, pas de Saint-Denis sans ton GO.**

## 8. Conservation / intégrité

- **Mutation = re-cascade Saint-André uniquement** (22 600 parcelles, 27/06 10:55→11:30 UTC). DB globale : 24
  communes / 431 663 parcelles inchangées, **17 gold inchangé**, **aucune autre commune touchée** (ni Saint-Denis).
- **Aucun backup post-canari créé** (attente GO). **Rollback = baseline `post-batch3`** (contient Saint-André à
  l'état 06-23 ; *NB* : Les Trois-Bassins y est aussi à l'état 06-23, donc un rollback global annulerait aussi le
  canari 1). Aucun rollback appliqué.
- `main = origin/main = 6866dbd` ; ce rapport est **non commité**.

---

### Provenance (lecture seule, hors la mutation re-cascade autorisée)
- Avant = dernière `parcel_evaluations` < `2026-06-27 10:54:31 UTC` ; après = éval canari. PPR avant = snapshot
  `cascade_results` lu avant le run ; après = état courant. Attribution via `cascade_results.layer_name='risques'`
  (severity `faible` = déflag marginal). Aucune autre commune, aucun code, aucun import, aucun passage gold.
