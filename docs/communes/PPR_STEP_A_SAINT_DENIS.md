# Homogénéisation Étape A PPR — Saint-Denis (dernière gold *stale*) — ⏸️ **en attente de validation**

> **Dernière commune gold *stale*** du chantier d'homogénéisation : re-cascade **SEULE** de **Saint-Denis (97411)**
> (`labuse evaluate --commune`, **sans ré-import, sans changement de code/config/scoring/seuil 65, sans --ai**),
> repassée des vieilles règles `2b45db742f40` (06-21) au code courant `fb6a5478b2bf` (avec Étape A). **Baseline
> rollback = backup stable post-canaris** (aucun backup pré-run dédié). **Aucune autre commune touchée.**
> **Rapport de travail — NON commité, aucun backup post-Saint-Denis créé. Stop pour validation.**

## 1. Méthode & exécution

- Commune : **Saint-Denis** uniquement (97411, 38 138 parcelles). Aucun autre INSEE.
- `labuse evaluate --commune "Saint-Denis"` → cascade + scoring par lots de 2 000. **RC=0.**
- Avant/après par cutoff `evaluated_at` = `2026-06-27 11:53:55 UTC` (`parcel_evaluations` append-only ; PPR « avant »
  = snapshot `cascade_results` lu avant le run, table remplacée à la re-cascade).
- Aucun import, aucune couche rechargée, aucune Étape B, aucun passage gold, aucun rollback, aucun changement de code.

| Mesure | Valeur |
|---|---:|
| Durée totale | **1 932 s (32 min)** |
| **Temps / parcelle** | **0,051 s** (la plus rapide — beaucoup de parcelles « PASS » simples) |
| Parcelles évaluées | 38 138 (100 %) |

## 2. Résultats — verdicts avant → après

| Verdict | Avant (06-21) | Après | Δ |
|---|---:|---:|---:|
| 🎯 **opportunité** | 84 | **70** | **−14** |
| à creuser | 11 643 | 8 129 | **−3 514** |
| exclue | 2 165 | 2 335 | +170 |
| faux positif probable | 24 246 | 27 604 | **+3 358** |
| **complétude moyenne** | **82,7** | **82,6** | **≈0** |

**Transitions** : `a_creuser → fpp` **3 515** · `fpp → exclue` 170 · **`opportunité → fpp` 14** · `opportunité →
a_creuser` 1 · `a_creuser → opportunité` 1 · `fpp → a_creuser` 1.

> **⚠️ Première commune à net NÉGATIF.** L'ancienne cascade (06-21, vieilles règles) **SUR-flaguait** : le code
> courant **assainit massivement** — **3 515 `à creuser` → faux positif probable**. Effet **qualité fort**, volume
> d'opportunités **en baisse**.

## 3. PPR fort / faible (effet Étape A marginal)

| | Avant | Après | Δ |
|---|---:|---:|---:|
| PPR **fort** | 27 619 | 26 379 | **−1 240** |
| PPR **faible** (flag marginal) | **0** | **1 240** | **+1 240** |

72 % de PPR fort avant (27 619 / 38 138 ; + 10 519 PASS sans PPR). L'Étape A a **déflagué 1 240 parcelles**
(`26 379 + 1 240 = 27 619`, conservation exacte). **Mais des 1 240 déflaguées, 0 devient opportunité** (842 fpp /
346 à creuser / 52 exclue) — toutes bloquées par d'autres facteurs ou score < 65.

## 4. Attribution du Δ net (−14) & pertes

| Source | Opportunités |
|---|---:|
| Gain via **Étape A** (déflag marginal) | **0** |
| Gain **re-scoring pur** | **+1** |
| **Retraits / pertes d'opportunité** | **−15** |
| **Net** | **−14** |

- **+1 gain** = parcelle **171973** : score **64 → 65**, **PASS** (aucun PPR) → **re-scoring pur** (1er gain
  non-Étape A des 3 canaris).
- **−15 pertes** (opportunité → fpp ×14, → à creuser ×1) : **0 déflaguée** (`faible`) parmi elles. Cause =
  **assainissement / re-scoring descendant** (déjà bâti, micro, faux positif), **PAS le flag marginal**.
- **0 perte imputable au flag marginal** : le déflag ne fait que *lever* un blocage PPR — il ne peut jamais retirer
  une opportunité. Vérifié (0/15 pertes déflaguées).

## 5. ⭐⭐⭐ Comparaison à 4 — synthèse du chantier d'homogénéisation

| | Le Port (batch3) | Les Trois-Bassins (c1) | Saint-André (c2) | **Saint-Denis (c3)** |
|---|---:|---:|---:|---:|
| Profil | urbain/port | rural/volcan | urbain | **urbain (capitale)** |
| Parcelles | 10 195 | 5 314 | 22 600 | **38 138** |
| Temps / parcelle | 0,035 s | 0,092 s | 0,093 s | **0,051 s** |
| **Net opportunités** | **+162** | **+1** | **+2** | **−14** |
| dont Étape A (marginal) | +5 | +1 | +2 | **0** |
| dont re-scoring pur | +157 | 0 | 0 | **+1** |
| **Pertes / retraits** | 0 | 0 | 0 | **−15** |
| **Complétude Δ** | **+10** | 0 | 0 | **≈0** |
| Assainissement `a_creuser→fpp` | — | 115 | 0 | **3 515** |
| PPR déflaguées (fort→faible) | ~101 | 183 | 765 | **1 240** |
| **Pertes imputables au flag marginal** | 0 | 0 | 0 | **0** |

> **Enseignements (4 communes re-cascadées) :**
> 1. **Complétude plate partout** (sauf Le Port) → le **+157 de Le Port était un événement LOCAL** (couche de
>    données ré-apparue), **définitivement confirmé** sur 3 canaris.
> 2. **Le flag marginal Étape A ne « crée » quasiment pas d'opportunités** sur les communes ultra-contraintes
>    (Saint-Denis : 1 240 déflaguées → **0** opportunité) : les parcelles débloquées restent sous le seuil ou
>    bloquées ailleurs.
> 3. **Saint-Denis prouve l'effet inverse d'un gisement** : l'ancien code **sur-flaguait** ; re-cascader **retire
>    14 opportunités** et **assainit 3 515 faux positifs**. **La re-cascade des *stale* = cohérence/QUALITÉ, et peut
>    RÉDUIRE le volume**, jamais une découverte.
> 4. **0 perte imputable au flag marginal** sur les 4 communes (le déflag ne retire jamais d'opportunité).

## 6. Conclusion — **homogénéisation GOLD TERMINÉE** ✅

- **17 / 17 communes gold** sont désormais sur le code courant `fb6a5478b2bf`. **0 commune gold *stale*.**
- **Reste *stale* : 2 communes NON-gold** — **La Plaine-des-Palmistes** (6 450 parc.) et **Sainte-Rose** (6 287),
  soit **12 737 parcelles** sur vieilles règles. Rendement attendu **quasi nul** (rural/volcanique), **cohérence
  uniquement**, basse priorité.
- Opportunités globales : **9 116 → 9 102** (net **−14**, assainissement Saint-Denis). Portefeuille **plus propre**.

## 7. Conservation / intégrité

- **Mutation = re-cascade Saint-Denis uniquement** (38 138 parcelles, 27/06 11:54→12:26 UTC). DB globale : 24
  communes / 431 663 parcelles inchangées, **17 gold inchangé** (aucun passage gold), **aucune autre commune touchée**.
- **Aucun backup post-Saint-Denis créé** (attente GO). **Rollback = baseline `post-canaris`** (contient Saint-Denis
  à l'état 06-21). Aucun rollback appliqué.
- `main = origin/main = c24b15b` ; ce rapport est **non commité**.

---

### Provenance (lecture seule, hors la mutation re-cascade autorisée)
- Avant = dernière `parcel_evaluations` < `2026-06-27 11:53:55 UTC` ; après = éval re-cascade. PPR avant = snapshot
  `cascade_results` lu avant le run ; après = état courant. Attribution via `cascade_results.layer_name='risques'`
  (severity `faible` = déflag marginal). Aucune autre commune, aucun code, aucun import, aucun passage gold.
