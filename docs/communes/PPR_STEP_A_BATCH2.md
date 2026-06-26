# Généralisation Étape A PPR — mini-batch 2 (Saint-Louis · Saint-Joseph · Saint-Benoît) — ⏸️ **en attente de validation**

> **Mini-batch 2 de généralisation de l'Étape A PPR** (règle déjà mergée : périmètre PM1 marginal < 10 % →
> flag `faible` informatif au lieu de `fort` bloquant). **Re-cascade SEULE** des 3 communes gold
> (`run_all.evaluate_commune`, **sans ré-import, sans changement de code/config/scoring/seuil 65**).
> Résultat **quasi net-neutre sur les opportunités** (1 593 → 1 596, **+3**) : l'Étape A ajoute **+26**
> opportunités (déflag marginal), le `declassement` en assainit **−25** (faux positifs déjà bâtis / micro /
> emplacement réservé). **Qualité des leads ↑, volume stable.**
> **Rapport de travail — NON commité, NON mergé, aucun backup stable créé. Stop pour validation.**

## 1. Objectif

- **Généraliser l'Étape A** à 3 communes gold qui la précédaient (PPR faible = 0, `rules 2b45db742f40`) :
  **Saint-Louis (97414)**, **Saint-Joseph (97412)**, **Saint-Benoît (97410)**.
- **Re-cascade uniquement** : `evaluate_commune` séquentiel — aucun reload de couches, aucun import, aucun
  changement code/config/seuil 65/scoring, aucune Étape B.

## 2. Backup pré-batch (unique, couvre les 3 communes)

| Champ | Valeur |
|---|---|
| Chemin | `/var/backups/labuse/labuse-pre-stepa-batch2-saint-louis-saint-joseph-saint-benoit-20260626-140509.dump` |
| SHA-256 | `78ccbb82a6e1da841f83ea6b20dee278cba70c81627412ccf2d0fc9b401f808a` |
| Vérification | sidecar `.sha256` · `sha256sum -c` **OK** · 175 entrées TOC · 6/6 tables critiques |

> 🟢 Baseline stable courante inchangée : `labuse-post-stepa-batch1-17gold-24communes-20260626-130808.dump`.

## 3. Méthode + incident de performance (transparence)

Re-cascade séquentielle **Saint-Louis → Saint-Joseph → Saint-Benoît**, transaction indépendante par commune.

- **Saint-Louis** : passée vite (~0,076 s/parcelle), commitée Étape A.
- **Saint-Joseph** : **~5–10× plus lente** (CPU-bound côté PostgreSQL — `ST_Intersection` géométrique sur une
  commune dense). Diagnostic **read-only** : plan **optimal** (index GiST utilisé), stats/index/bloat sains →
  **pas une régression**, coût **intrinsèque** à cette commune dense. Un **`ANALYZE` de maintenance** (parcels,
  spatial_layers, cascade_results, parcel_evaluations) a été appliqué (**stats planificateur uniquement, zéro
  impact verdicts**). Sur décision : **Saint-Joseph re-cascadée EN ENTIER** (idempotente) puis **Saint-Benoît**,
  jusqu'à un passage **100 % propre**. Wall-time total du batch ~plusieurs heures (lent mais correct).
- **Chantier d'optimisation cascade** (distances DVF indexées en 2975, etc.) **différé** à une mission dédiée.

| Commune | Parcelles évaluées | Durée |
|---|---:|---:|
| Saint-Louis | 29 241 | ~2 223 s |
| Saint-Joseph | 28 959 | ~8 477 s (commune dense) |
| Saint-Benoît | 21 671 | ~8 819 s |

## 4. Résultats par commune

### 4.1 Saint-Louis (29 241 parcelles) — **net positif**

| Verdict | Avant | Après | Δ |
|---|---:|---:|---:|
| **Opportunité** | 474 | **489** | **+15** |
| À creuser | 4 799 | 4 156 | −643 |
| Écartée | 1 307 | 1 355 | +48 |
| Faux positif probable | 22 661 | 23 241 | +580 |
| **PPR fort** | 8 214 | 7 163 | −1 051 |
| **PPR faible (Étape A)** | 0 | **2 131** | **+2 131** |

- **Gains : +16** = **14 via flag PPR marginal** (Étape A) + 2 via re-scoring montant.
- **Retrait : −1** (via `declassement`). **0 perte via le flag marginal.**
- **Net +15 (= 16 − 1)** · taux d'opportunité 1,62 % → **1,67 %**.

### 4.2 Saint-Joseph (28 959 parcelles) — **léger assainissement net**

| Verdict | Avant | Après | Δ |
|---|---:|---:|---:|
| **Opportunité** | 530 | **514** | **−16** |
| À creuser | 7 653 | 7 251 | −402 |
| Écartée | 1 032 | 1 051 | +19 |
| Faux positif probable | 19 744 | 20 143 | +399 |
| **PPR fort** | 9 948 | 8 712 | −1 236 |
| **PPR faible (Étape A)** | 0 | **2 536** | **+2 536** |

- **Gains : +5** (tous via flag PPR marginal — Étape A).
- **Retrait : −21** = **18 `declassement`** (déjà bâti / micro) + **1 `prescription_plu`** (emplacement réservé)
  + 2 re-scoring sous le seuil 65. **0 perte via le flag marginal.**
- **Net −16 (= 5 − 21)** · taux d'opportunité 1,83 % → **1,78 %**.

### 4.3 Saint-Benoît (21 671 parcelles) — **net positif**

| Verdict | Avant | Après | Δ |
|---|---:|---:|---:|
| **Opportunité** | 589 | **593** | **+4** |
| À creuser | 4 611 | 4 433 | −178 |
| Écartée | 1 035 | 1 037 | +2 |
| Faux positif probable | 15 436 | 15 608 | +172 |
| **PPR fort** | 7 148 | 5 808 | −1 340 |
| **PPR faible (Étape A)** | 0 | **2 829** | **+2 829** |

- **Gains : +7** (tous via flag PPR marginal — Étape A).
- **Retrait : −3** = 2 `declassement` + 1 re-scoring. **0 perte via le flag marginal.**
- **Net +4 (= 7 − 3)** · taux d'opportunité 2,72 % → **2,74 %**.

## 5. Synthèse globale (3 communes)

| Indicateur | Valeur |
|---|---:|
| Parcelles re-cascadées | 79 871 (3 communes), 100 % évaluées |
| **Opportunités avant → après** | **1 593 → 1 596** |
| **Gains totaux** | **+28** |
| — via flag Étape A (PPR marginal < 10 %) | +26 (14 + 5 + 7) |
| — via re-scoring montant | +2 (Saint-Louis) |
| **Retraits totaux** | **−25** |
| — via `declassement` (déjà bâti / micro) | −21 |
| — via `prescription_plu` (emplacement réservé) | −1 |
| — via re-scoring descendant (borderline sous 65) | −3 |
| **Net opportunités** | **+3  (= 28 − 25 = 1 596 − 1 593)** |
| **Perte imputable à l'Étape A** (flag marginal) | **0** |
| PPR faible créé (flag informatif Étape A) | 0 → 7 496 |
| Taux d'opportunité global | 1,99 % → 2,00 % |

> **Contrôle de cohérence (read-only).** `net = gains − retraits` vérifié par commune et au total ;
> `gained`/`lost` disjoints. **28 − 25 = +3 = 1 596 − 1 593.** **0 perte via le flag marginal** sur les 3 communes.
> **22 / 25 retraits** passent par un blocage hard explicite (déjà bâti / micro / emplacement réservé) ;
> 3 via re-scoring borderline.

- **Batch quasi net-neutre** : contrairement au batch 1 (−136), l'assainissement `declassement` est ici **faible**
  (ces communes avaient une cascade plus récente, donc moins de dérive accumulée). L'Étape A (+26) **équilibre**
  presque exactement le retrait de faux positifs (−25) → **+3 net, qualité ↑ à volume stable**.
- **7 496 parcelles** nouvellement annotées **PPR faible** (informatif, non bloquant) ; **PPR fort baisse** partout.

## 6. Conservation / intégrité

- **DB globale inchangée : 431 663 parcelles / 24 communes** · **gold 17 inchangé** (aucun passage gold).
- **Seules les 3 communes du batch** ont reçu de nouvelles évaluations (Saint-Louis 14:09–14:44, Saint-Joseph
  14:46–19:51, Saint-Benoît 20:00–22:04) ; **21 autres communes intactes**, aucun autre INSEE touché.
- **Aucun changement de code / config / tests / scripts** : `git status` propre, `HEAD = origin/main = 233a9c7`.
- Aucun import, aucune couche rechargée, aucune Étape B, aucun rollback, aucun changement de seuil/scoring.

## 7. Notes opérationnelles

- **`ANALYZE` de maintenance** exécuté pendant le diagnostic perf (stats planificateur seules) — **n'altère aucun
  verdict/score**.
- **Saint-Joseph** porte des lignes `parcel_evaluations` « stale » supplémentaires (run partiel ~10 000 + run
  complet 28 959) — **verdict canonique = dernière éval**, impact fonctionnel nul (comportement documenté).
- **Lenteur Saint-Joseph/Saint-Benoît** : CPU-bound géométrique, intrinsèque aux communes denses, **pas une
  régression**. Pré-requis du **chantier d'optimisation cascade** (mission séparée, sur GO).

## 8. Recommandation

- **Mini-batch 2 réussi et propre** : 3 communes gold désormais en Étape A, qualité améliorée, volume stable.
  Gold count **17**, état restaurable = baseline batch 1 + ce passage (non encore figé en backup stable).
- **Avant le mini-batch 3** : ouvrir le **chantier d'optimisation cascade** — les communes restantes denses
  (ex. **Saint-Denis** 38 138, **Saint-André** PPR 92 %) seraient **très lentes** sans optimisation.
- **Communes gold restantes hors Étape A (8)** : Saint-Denis · Saint-André · Sainte-Marie · Petite-Île ·
  Sainte-Suzanne · Le Port · Les Avirons · Bras-Panon.
- **Décision attendue** : valider l'état re-cascadé (pas de rollback), puis — sur GO séparé — commit docs-only,
  merge, et backup stable post-batch.

---

### Provenance (lecture seule, hors les 3 mutations re-cascade autorisées)
- Mutations **autorisées** : re-cascade Saint-Louis / Saint-Joseph / Saint-Benoît (`evaluate_commune`), backup
  pré-batch validé, `ANALYZE` de maintenance.
- Avant/après : snapshot Phase 1 (avant) + état courant (après) ; transitions reconstruites via versions
  `parcel_evaluations` (avant = dernière éval < 13:30, après = dernière éval), attribution via `cascade_results`.
- Aucun import, aucune couche modifiée, aucune autre commune touchée, aucun rollback, aucun passage gold,
  aucun changement code/config/scoring/tests.
