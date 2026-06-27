# Canari Étape A PPR — Les Trois-Bassins (re-homogénéisation) — ⏸️ **en attente de validation**

> **Canari** du chantier d'homogénéisation cascade : re-cascade **SEULE** de **Les Trois-Bassins (97423)**
> (`labuse evaluate --commune`, **sans ré-import, sans changement de code/config/scoring/seuil 65, sans --ai**),
> pour **mesurer en réel** l'effet de re-passer une commune *stale* (dernières règles `2b45db742f40`, cascade
> 06-23) au code courant (`fb6a5478b2bf`, avec Étape A). **Baseline rollback = backup stable post-batch 3**
> (aucun backup pré-canari dédié — la DB était identique à post-batch 3). **Saint-Denis & Saint-André NON touchés.**
> **Rapport de travail — NON commité, aucun backup post-canari créé. Stop pour validation.**

## 1. Méthode & exécution

- Commune : **Les Trois-Bassins** uniquement (97423, 5 314 parcelles). Aucun autre INSEE.
- `labuse evaluate --commune "Les Trois-Bassins"` → `run_all.evaluate_commune` (cascade + scoring par lots de 2 000,
  commit/lot). **RC=0.**
- **Avant/après reconstruits par cutoff** `evaluated_at` = `2026-06-27 10:21:58 UTC` : `parcel_evaluations` est
  **append-only** (avant = dernière éval < cutoff = état 06-23 ; après = éval canari). *NB* : `cascade_results` est
  **remplacé** à la re-cascade → PPR « avant » lu **avant** le run (snapshot read-only), PPR « après » lu sur l'état courant.
- Aucun import, aucune couche rechargée, aucune Étape B, aucun passage gold, aucun rollback, aucun changement de code.

| Mesure | Valeur |
|---|---:|
| Durée totale | **490 s (8 min 10 s)** |
| **Temps / parcelle** | **0,092 s** |
| Parcelles évaluées | 5 314 (100 %) |

## 2. Résultats — verdicts avant → après

| Verdict | Avant (06-23) | Après (canari) | Δ |
|---|---:|---:|---:|
| 🎯 **opportunité** | 1 | **2** | **+1** |
| à creuser | 1 265 | 1 149 | −116 |
| exclue | 215 | 222 | +7 |
| faux positif probable | 3 833 | 3 941 | +108 |
| **complétude moyenne** | **79,9** | **79,9** | **0** |

**Transitions (≠ avant→après)** : `a_creuser → fpp` **115** · `fpp → exclue` **7** · `a_creuser → opportunité` **1**.

> **Effet dominant = assainissement qualité**, PAS un gain d'opportunités : **115 parcelles `à creuser` reclassées
> `faux positif probable`** (le code courant les juge plus strictement) + 7 `fpp → exclue`. Volume d'opportunités
> quasi net-neutre (**+1**).

## 3. PPR fort / faible (effet Étape A marginal)

| | Avant | Après | Δ |
|---|---:|---:|---:|
| PPR **fort** | 5 260 | 5 077 | **−183** |
| PPR **faible** (flag marginal) | **0** | **183** | **+183** |

Commune **très contrainte** : 5 260 / 5 314 parcelles (**99 %**) en PPR fort avant. L'Étape A a **déflagué 183
parcelles** PM1-marginales (< 10 %) fort → faible (`5 077 + 183 = 5 260`, conservation exacte). **Des 183 déflaguées,
1 seule devient opportunité** ; les 182 autres restent fpp (156) / exclue (16) / à creuser (10) — bloquées par
d'**autres** facteurs (score, zonage, surface…), pas par le PPR.

## 4. Attribution du gain net (+1) & pertes

| Source | Opportunités |
|---|---:|
| **Gain via Étape A** (déflag marginal) | **+1** |
| Autres gains re-scoring (montant) | 0 |
| **Retraits / pertes d'opportunité** | **0** |
| **Net** | **+1** |

- **L'unique gain** = parcelle **679763** : score **55 → 65** **ET** PPR fort → **faible**. **Les deux étaient
  nécessaires** (sans le déflag, elle resterait bloquée par le PPR fort même à 65) → attribué **Étape A**.
- **0 perte d'opportunité** (l'unique opportunité d'avant est restée). **0 perte imputable au flag marginal** (le
  déflag ne fait que *lever* un blocage — il ne peut pas retirer d'opportunité).

## 5. ⭐ Comparaison Le Port — la dérive de complétude n'est PAS systématique

| | Le Port (06-26, urbain) | **Les Trois-Bassins** (canari, rural/volcanique) |
|---|---|---|
| Net opportunités | **+162** | **+1** |
| dont Étape A (marginal) | +5 | +1 |
| dont re-scoring montant | **+157** | **0** |
| **Complétude avant→après** | **74 → 84 (+10)** | **79,9 → 79,9 (0)** |
| Cause du re-scoring | couche de données **absente au 06-22, réapparue** | — |

> **Constat clé** : Les Trois-Bassins re-cascadée **sans aucune dérive de complétude** (79,9 → 79,9) et **sans gain
> de re-scoring**. Le **+157 de Le Port était donc bien un événement LOCAL** (une couche de données spécifique à
> Le Port redevenue disponible), **PAS une dérive systématique** des communes anciennement cascadées. Re-cascader
> les communes *stale* **ne reproduira pas** un +157 partout.

## 6. Perf & extrapolation (à 0,092 s/parcelle)

| Commune restante | Parcelles | Estim. @canari | Borne haute (dense, 0,37 s/p) |
|---|---:|---:|---:|
| Saint-André (97409) | 22 600 | **~35 min** | ~2,3 h |
| Saint-Denis (97411) | 38 138 | **~59 min** | ~3,9 h |

> Cadence canari (**0,092 s/p**) = intermédiaire (Le Port 0,035 · Sainte-Suzanne dense 0,37). **Même au pire cas
> dense, Saint-Denis ≈ 4 h** — runnable sans optimisation préalable. **L'optimisation code n'est pas justifiée par
> la mesure.**

## 7. Synthèse

- **Re-cascade SÛRE** : 0 perte, 0 inflation silencieuse, complétude stable, conservation PPR exacte.
- **Bénéfice = qualité** (115 faux positifs assainis), **pas volume** (+1 opportunité).
- **Faible rendement d'opportunités** sur une commune **rurale ultra-contrainte PPR** (99 % fort) — attendu.
- **Perf acceptable** (~1 h Saint-Denis au taux canari, ~4 h au pire) → **pas besoin d'optimiser d'abord**.

## 8. Recommandation

**Le canari valide la mécanique (sûre, propre, perf OK) mais ne prédit pas le rendement *urbain*.** Les Trois-Bassins
est rural/volcanique ; Saint-Denis & Saint-André sont **urbains avec un gros backlog near-threshold** (Saint-Denis :
742 `à creuser` à 60-64) — leur rendement peut différer.

1. **❌ Optimiser avant Saint-Denis/Saint-André** — **non justifié** : la mesure montre une perf acceptable (~1 h,
   ~4 h au pire). Optimiser maintenant = prématuré.
2. **❌ Stop** — laisserait 5 communes hétérogènes (vieilles règles) et renoncerait à un assainissement **sûr**.
3. **✅ Poursuivre l'homogénéisation, SANS optimisation, par commune sous GO** — ordre recommandé :
   **Saint-André d'abord** (urbain, taille moyenne ~35 min–2,3 h) comme **2ᵉ canari « urbain »** pour mesurer le
   rendement urbain réel ; puis **Saint-Denis** ; puis les **3 non-gold** (La Plaine-des-Palmistes, Sainte-Rose —
   et Les Trois-Bassins déjà faite) pour cohérence, en sachant le rendement faible.

> **Recommandation = option 3** : poursuivre sans optimisation, Saint-André en prochain canari urbain. Chaque
> commune sous GO explicite + backup pré-run selon l'espace disque.

## 9. Conservation / intégrité

- **Mutation = re-cascade Les Trois-Bassins uniquement** (5 314 parcelles, re-cascade 27/06 10:22→10:30 UTC). DB
  globale : 24 communes / 431 663 parcelles inchangées, **17 gold inchangé**, **aucune autre commune touchée**.
- **Aucun backup post-canari créé** (attente GO). **Rollback disponible = baseline `post-batch3`** (contient Les
  Trois-Bassins à l'état 06-23). Aucun rollback appliqué.
- `main = origin/main = d22d6b8`, working tree clean (ce rapport est **non commité**).

---

### Provenance (lecture seule, hors la mutation re-cascade autorisée)
- Avant = dernière `parcel_evaluations` < `2026-06-27 10:21:58 UTC` ; après = éval canari. PPR avant = snapshot
  `cascade_results` lu **avant** le run (table remplacée à la re-cascade) ; PPR après = état courant.
- Attribution Étape A vs re-scoring : croisement statut avant/après × `cascade_results.layer_name='risques'`
  (severity `faible` = déflag marginal). Aucune autre commune, aucun code, aucun import, aucun passage gold.
