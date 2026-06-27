# Homogénéisation Étape A PPR — 2 dernières non-gold *stale* (La Plaine-des-Palmistes + Sainte-Rose) — ⏸️ **en attente de validation**

> **Fin de l'homogénéisation** : re-cascade des **2 dernières communes *stale*** (non-gold) — **La Plaine-des-Palmistes
> (97406)** puis **Sainte-Rose (97419)** — des vieilles règles `2b45db742f40` (06-22/06-23) au code courant
> `fb6a5478b2bf` (avec Étape A). `labuse evaluate --commune`, **sans ré-import, sans changement de code/config/scoring/
> seuil 65, sans --ai, aucun passage gold**. **Baseline rollback = backup stable post-Saint-Denis** (aucun backup
> pré-run dédié). **Aucune autre commune touchée.** **Rapport de travail — NON commité, aucun backup post-run créé.
> Stop pour validation.**

## 1. Méthode & exécution

- Communes : **La Plaine-des-Palmistes** (6 450 parc.) puis **Sainte-Rose** (6 287 parc.), dans cet ordre. Aucun autre INSEE.
- `labuse evaluate --commune` (cascade + scoring par lots de 2 000). **RC=0 sur chacune.**
- Avant/après par cutoff `evaluated_at` = `2026-06-27 13:29:33 UTC` (`parcel_evaluations` append-only ; PPR « avant »
  = snapshot lu avant le run, `cascade_results` remplacé à la re-cascade).
- Aucun import, aucune couche rechargée, aucune Étape B, aucun passage gold, aucun rollback, aucun changement de code.

| Commune | Parcelles | Durée | Temps / parcelle |
|---|---:|---:|---:|
| La Plaine-des-Palmistes | 6 450 | 491 s | **0,076 s** |
| Sainte-Rose | 6 287 | 511 s | **0,081 s** |
| **Total** | **12 737** | **1 002 s (17 min)** | — |

## 2. Résultats — verdicts avant → après

| Verdict | La Plaine av. | La Plaine ap. | Sainte-Rose av. | Sainte-Rose ap. |
|---|---:|---:|---:|---:|
| 🎯 opportunité | 0 | **0** | 8 | **9 (+1)** |
| à creuser | 2 013 | 1 283 | 1 818 | 1 817 |
| exclue | 415 | 421 | 764 | 764 |
| faux positif probable | 4 022 | 4 746 | 3 697 | 3 697 |
| **complétude moyenne** | 80,7 | **80,7** | 79,5 | **79,5** |

- **La Plaine-des-Palmistes** : transitions = `a_creuser → fpp` **732** · `fpp → exclue` 6 · `fpp → a_creuser` 2.
  **Assainissement pur** (730 faux positifs écartés), **0 opportunité** (commune **100 % PPR fort**, **0 parcelle ≥ 65**).
- **Sainte-Rose** : **seule transition** = `a_creuser → opportunité` **×1**. Rien d'autre.

## 3. PPR fort / faible (effet Étape A marginal)

| | La Plaine av. → ap. | Sainte-Rose av. → ap. |
|---|---|---|
| PPR **fort** | 6 450 → **6 128** (−322) | 3 029 → **2 529** (−500) |
| PPR **faible** (marginal) | 0 → **322** | 0 → **500** |

Déflag marginal Étape A : **322** parcelles (La Plaine, conservation `6 128+322=6 450`) et **500** (Sainte-Rose,
`2 529+500=3 029`). **Des déflaguées : La Plaine 0/322 → opportunité ; Sainte-Rose 1/500 → opportunité** (le reste
reste fpp/à creuser/exclue, bloqué ailleurs ou score < 65).

## 4. Attribution & pertes

| | La Plaine-des-Palmistes | Sainte-Rose |
|---|---:|---:|
| Gain via **Étape A** (déflag marginal) | **0** | **+1** |
| Gain **re-scoring pur** | 0 | 0 |
| **Retraits / pertes d'opportunité** | **0** | **0** |
| **Net** | **0** | **+1** |

- **Sainte-Rose +1** = parcelle **688274** : score **56 → 66** **ET** PPR fort → **faible** → attribué **Étape A**.
- **0 perte** sur les 2 communes ⇒ **0 perte imputable au flag marginal** (le déflag ne retire jamais d'opportunité).

## 5. Vérifications de conservation

- ✅ **Aucun autre INSEE touché** : seules **La Plaine-des-Palmistes** et **Sainte-Rose** ont des évaluations après
  le cutoff (`13:29:33 UTC`). Les 22 autres communes **intactes**.
- ✅ **Statut gold inchangé** : **17 gold** (ces 2 communes **restent non-gold** — aucun passage gold).
- ✅ DB globale : **24 communes / 431 663 parcelles** inchangées. Opportunités globales **9 102 → 9 103** (+1).
- ✅ Aucun import, aucune Étape B, aucun changement de code/config/scoring, aucun rollback.

## 6. Conclusion — **0 commune *stale* restante : homogénéisation TOTALE** ✅

- **`SELECT` de contrôle** : **0 parcelle** sur les vieilles règles `2b45db742f40`. **Les 24/24 communes** sont
  désormais sur le code courant `fb6a5478b2bf`.
- Bilan : ces 2 non-gold confirment le pattern des canaris — **re-cascade = cohérence/qualité, rendement
  d'opportunités ≈ nul** (net **+1** sur 12 737 parcelles), **0 perte**, complétude plate, assainissement (La Plaine
  −730 faux positifs). **Le chantier d'homogénéisation est terminé pour l'ensemble du portefeuille.**

## 7. Conservation / intégrité

- **Mutation = re-cascade La Plaine-des-Palmistes + Sainte-Rose uniquement** (12 737 parcelles, 27/06 13:31→13:47 UTC).
- **Aucun backup post-run créé** (attente GO). **Rollback = baseline `post-saint-denis`** (contient ces 2 communes à
  l'état 06-22/06-23). Aucun rollback appliqué.
- `main = origin/main = 4ad984e` ; ce rapport est **non commité**.

---

### Provenance (lecture seule, hors les 2 mutations re-cascade autorisées)
- Avant = dernière `parcel_evaluations` < `2026-06-27 13:29:33 UTC` ; après = éval re-cascade. PPR avant = snapshot
  lu avant le run ; après = état courant. Attribution via `cascade_results.layer_name='risques'` (severity `faible`
  = déflag marginal). Aucune autre commune, aucun code, aucun import, aucun passage gold.
