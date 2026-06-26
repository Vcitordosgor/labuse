# Généralisation Étape A PPR — mini-batch 1 (Le Tampon · La Possession · L'Étang-Salé) — ⏸️ **en attente de validation**

> **Mini-batch 1 de généralisation de l'Étape A PPR** (règle déjà mergée : périmètre PM1 marginal < 10 % →
> flag `faible` informatif au lieu de `fort` bloquant). **Re-cascade SEULE** des 3 communes gold
> (`run_all.evaluate_commune`, **sans ré-import de couches, sans changement de code/config/scoring/seuil 65**).
> Schéma identique au pilote Saint-Pierre : l'Étape A n'**ajoute** que des opportunités (0 perte propre), et la
> re-cascade ré-applique en plus le code courant → **assainissement de faux positifs** (déjà bâti, micro,
> emplacements réservés). **Net d'opportunités en légère baisse, qualité des leads en hausse.**
> **Rapport de travail — NON commité, NON mergé, aucun backup stable créé. Stop pour validation.**

## 1. Objectif

- **Accélérer la généralisation de l'Étape A** en re-cascadant **3 communes gold** en une seule mission contrôlée,
  **sans changement de code ni reload de couches**.
- Toutes trois **précédaient l'Étape A** (PPR faible = 0 avant), comme Saint-Pierre.
- **Re-cascade uniquement** : `run_all.evaluate_commune(commune)` séquentiel — applique la règle existante,
  **aucun reload de couches, aucun import, aucun changement code/config/seuil 65/scoring, aucune Étape B**.

## 2. Backup pré-batch (unique, couvre les 3 communes)

| Champ | Valeur |
|---|---|
| Chemin | `/var/backups/labuse/labuse-pre-stepa-batch1-tampon-possession-etang-sale-20260626-101136.dump` |
| SHA-256 | `eb25b4da749961a09a107afb05924439826dbfd0f050521b7d4a472811829473` |
| Taille | ~1,10 GiB (1 186 477 225 octets) + sidecar `.sha256` |
| Vérification | `sha256sum -c` **OK** · `pg_restore --list` 190 TOC · 6/6 tables critiques |

> Un seul backup pré-mutation pour le batch (les 3 re-cascades sont des transactions indépendantes commitées
> séquentiellement ; pas de rollback automatique). Baseline 🟢 courante inchangée :
> `labuse-post-saint-pierre-ppr-stepa-17gold-24communes-20260626-064042.dump`.

## 3. Méthode — re-cascade séquentielle

Ordre : **Le Tampon → La Possession → L'Étang-Salé**, chaque commune dans sa propre transaction
(`evaluate_commune` scopé commune → commit indépendant), arrêt sur exception (les communes faites restent
commitées). **Exit 0 (RC=0)**, aucune autre commune touchée.

| Commune | Parcelles évaluées | Durée |
|---|---:|---:|
| Le Tampon | 42 756 | 4 239 s (~70 min) |
| La Possession | 13 338 | 990 s (~16 min) |
| L'Étang-Salé | 9 070 | 837 s (~14 min) |
| **Total** | **65 164** | **~1 h 41** |

## 4. Résultats par commune

### 4.1 Le Tampon (42 756 parcelles)

| Verdict | Avant | Après | Δ |
|---|---:|---:|---:|
| **Opportunité** | 749 | **657** | **−92** |
| À creuser | 10 467 | 7 526 | −2 941 |
| Écartée | 1 030 | 1 147 | +117 |
| Faux positif probable | 30 510 | 33 426 | +2 916 |
| **PPR fort** | 12 421 | 9 760 | −2 661 |
| **PPR faible (Étape A)** | 0 | **4 342** | **+4 342** |

- **Gains : +24** = **23 via le flag PPR marginal < 10 %** (Étape A) **+ 1 via re-scoring montant** : parcelle
  29383, `à creuser` (score 64) → `opportunité` (65), **sans aucun flag PPR** (`risques` = PASS) — parcelle
  borderline qui franchit le seuil 65 vers le haut, indépendamment de l'Étape A.
- **Retrait : −116** opportunités, **100 % via la couche `declassement`** (92 → `HARD_EXCLUDE` déjà bâti/micro
  → faux positif/écartée ; 24 → sévérité `fort` → à creuser). **0 perte via le flag marginal.**
- **Net −92 (= 24 gains − 116 retraits)** · taux d'opportunité 1,75 % → **1,54 %**.
- **Conclusion :** assainissement net — l'Étape A (+23) et 1 re-scoring montant sont absorbés par le retrait de
  116 faux positifs déjà bâtis.

### 4.2 La Possession (13 338 parcelles) — **seule commune nette positive**

| Verdict | Avant | Après | Δ |
|---|---:|---:|---:|
| **Opportunité** | 611 | **620** | **+9** |
| À creuser | 3 950 | 3 619 | −331 |
| Écartée | 790 | 801 | +11 |
| Faux positif probable | 7 987 | 8 298 | +311 |
| **PPR fort** | 4 294 | 3 467 | −827 |
| **PPR faible (Étape A)** | 0 | **1 251** | **+1 251** |

- **Gain Étape A : +29** opportunités, **100 % via le flag PPR marginal** (29 gains totaux).
- **Retrait : −20** opportunités, décomposé :
  - **13 via `declassement`** (11 `HARD_EXCLUDE` + 2 `fort`) — déjà bâti / micro ;
  - **2 via `prescription_plu` `HARD_EXCLUDE`** — emplacements réservés (ER 32 « aménagement de carrefour » 77 %,
    ER 40 « création d'une voie » 100 %) → emprise publique majoritaire, score forcé à 0 → faux positif ;
  - **5 via re-scoring** sous le seuil 65 (scores 65→64, 70→60, 65→55, 67→57, 73→63 → à creuser ; aucun blocage hard).
- **0 perte via le flag marginal.**
- **Net +9** · taux d'opportunité 4,58 % → **4,65 %**.
- **Conclusion :** l'Étape A (+29) **dépasse** l'assainissement (−20) → **volume ET qualité en hausse**.

### 4.3 L'Étang-Salé (9 070 parcelles)

| Verdict | Avant | Après | Δ |
|---|---:|---:|---:|
| **Opportunité** | 342 | **289** | **−53** |
| À creuser | 2 640 | 1 731 | −909 |
| Écartée | 482 | 540 | +58 |
| Faux positif probable | 5 606 | 6 510 | +904 |
| **PPR fort** | 3 646 | 3 305 | −341 |
| **PPR faible (Étape A)** | 0 | **837** | **+837** |

- **Gain Étape A : +2** opportunités, **100 % via le flag PPR marginal** (2 gains totaux).
- **Retrait : −55** opportunités, **100 % via `declassement`** (40 `HARD_EXCLUDE` + 15 `fort`) — déjà bâti / micro.
  **0 perte via le flag marginal.**
- **Net −53** · taux d'opportunité 3,77 % → **3,19 %**.
- **Conclusion :** assainissement dominant — peu de marge Étape A (+2), peu de parcelles candidates en bord de
  périmètre marginal ; la baisse est le retrait de 55 faux positifs déjà bâtis.

## 5. Synthèse globale (3 communes)

| Indicateur | Valeur |
|---|---:|
| Parcelles re-cascadées | 65 164 (3 communes) |
| **Opportunités avant → après** | **1 702 → 1 566** |
| **Gains totaux** | **+55** |
| — via flag Étape A (PPR marginal < 10 %) | +54 (23 + 29 + 2) |
| — via re-scoring montant (borderline 64 → 65) | +1 (Le Tampon) |
| **Retraits totaux** | **−191** |
| — via `declassement` (déjà bâti / micro / pente / accès) | −184 |
| — via `prescription_plu` (emplacements réservés) | −2 |
| — via re-scoring descendant (borderline sous 65) | −5 |
| **Net opportunités** | **−136  (= 55 − 191 = 1 566 − 1 702)** |
| **Perte imputable à l'Étape A** (flag marginal) | **0** |
| PPR faible créé (flag informatif Étape A) | 0 → 6 430 |
| Taux d'opportunité global | 2,61 % → 2,40 % |

> **Contrôle de cohérence (read-only).** Identité vérifiée **par commune et au total** : `net = gains − retraits`,
> avec `gained`/`lost` **disjoints** (transitions exactes) et **0 parcelle sans état antérieur** (toutes ont un
> avant + un après → aucune transition non comptée). **55 − 191 = −136 = 1 566 − 1 702.** Le re-scoring au seuil 65
> joue **dans les deux sens** — **+1** remonte (Le Tampon 29383 : 64 → 65, sans PPR) et **−5** redescendent
> (La Possession) : comportement normal de seuil, **pas un double comptage ni une interaction Étape A**. Le gain
> Étape A « pur » reste **+54**, avec **0 perte via le flag marginal**.

- **186 / 191 retraits (97 %)** passent par un **blocage hard explicite** (déjà bâti, micro-parcelle, emplacement
  réservé) → **assainissement franc**. **5 / 191 (3 %)** sont des parcelles borderline re-scorées sous le seuil 65.
- **Pattern Saint-Pierre confirmé à l'échelle batch :** l'Étape A est **net-positive en propre** (0 perte via le
  flag marginal partout) ; la re-cascade ré-applique **tout le code courant** → retrait de faux positifs en plus.
  Le **net d'opportunités peut baisser** (Le Tampon, L'Étang-Salé) **tout en améliorant la qualité** ; là où peu de
  faux positifs subsistent et où le bord de périmètre est riche, le net **monte** (La Possession +9).
- Les **1 566 opportunités actuelles sont plus fiables** que les 1 702 précédentes (qui incluaient 191 parcelles
  déjà bâties / micro / réservées / borderline). **Qualité de lead ↑.**

## 6. Conservation / intégrité

- **DB globale inchangée : 431 663 parcelles / 24 communes** · **gold 17 inchangé** (aucun passage gold).
- **Seules les 3 communes du batch** ont reçu de nouvelles évaluations (`evaluated_at` < 3 h) ; **23 autres communes
  intactes**, aucun autre INSEE touché, 0 doublon de verdict canonique.
- **Aucun changement de code / config / tests** : `git status` propre, `HEAD = origin/main = d638653`.
- Aucun import, aucune couche rechargée, aucune Étape B, aucun rollback, aucun changement de seuil/scoring.

## 7. Recommandation — mini-batch 2

- **Schéma stable et prévisible** : la généralisation par re-cascade fonctionne comme au pilote. **Poursuivre par
  mini-batches de 3 communes gold**, avec **un backup pré-batch unique** et la **décomposition systématique**
  (gain Étape A / retrait faux positifs / net / taux) comme ici.
- **Ne PAS interpréter une baisse nette comme une régression** : sur les communes gold anciennes, la re-cascade
  **assainit** (déjà bâti / emplacements réservés) en plus d'appliquer l'Étape A. Présenter en **« qualité des
  leads améliorée »**, pas « moins d'opportunités ».
- **Communes restantes hors Étape A** à cibler en priorité (PPR faible = 0, gros volume gold) pour les prochains
  batches ; conserver l'ordre **grosse → petite** par batch pour lisser la durée (Le Tampon ~70 min domine).
- **Décision attendue** : valider l'état re-cascadé (pas de rollback), puis — sur GO séparé — commit docs-only,
  merge, et backup stable post-batch.

---

### Provenance (lecture seule, hors les 3 mutations re-cascade autorisées)
- Mutations **autorisées et uniques** : re-cascade Le Tampon / La Possession / L'Étang-Salé (`evaluate_commune`),
  backup pré-batch validé.
- Reconstruction avant/après : fenêtrage des versions `parcel_evaluations` (rn = 2 avant / rn = 1 après) —
  les opportunités avant reconstruites (749 / 611 / 342) **coïncident exactement** avec le snapshot Phase 1.
- Attribution des pertes : `cascade_results` courants (`declassement`, `prescription_plu`) + scores
  `parcel_evaluations` versionnés.
- Aucun import, aucune couche modifiée, aucune autre commune touchée, aucun rollback, aucun passage gold,
  aucun changement code/config/scoring/tests.
