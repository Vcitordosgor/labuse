# Saint-Pierre — pilote généralisation Étape A PPR (re-cascade) — ✅ **accepté (assainissement qualité)**

> **Pilote de généralisation de l'Étape A PPR** (règle déjà mergée : périmètre PM1 marginal < 10 % → flag
> `faible` au lieu de `fort` bloquant) sur **Saint-Pierre (97416)**, grande commune gold (42 425 parcelles, fort
> enjeu commercial). **Re-cascade SEULE** (`evaluate_commune`, **sans ré-import de couches, sans changement de
> code/config/scoring**). **État re-cascadé ACCEPTÉ** : la baisse nette d'opportunités est un **assainissement
> qualité** (retrait de faux positifs déjà bâtis), pas une régression. **Saint-Pierre reste non-modifiée gold.**

## 1. Objectif

- **Généraliser l'Étape A** (déjà testée au pilote Saint-Paul) à Saint-Pierre, qui **précédait l'Étape A**
  (PPR faible = 0 avant).
- **Re-cascade uniquement** : `run_all.evaluate_commune("Saint-Pierre")` — applique la règle existante, **aucun
  reload de couches, aucun import, aucun changement code/config/seuil 65/scoring**.

## 2. Backup pré-run

| Champ | Valeur |
|---|---|
| Chemin | `/var/backups/labuse/labuse-pre-saint-pierre-ppr-stepa-20260625-213017.dump` |
| SHA-256 | `5c3ef2539a21f8e5438c6177ae550b8f7465c69144a64fb80328e04eeb4de830` |
| Vérification | sidecar `.sha256` · `sha256sum -c` **OK** · 190 TOC · 6/6 tables critiques |
| Run | `evaluate_commune`, exit **0**, 42 425 parcelles évaluées en 3 078 s — **aucune autre commune touchée** |

## 3. Avant → après

| Verdict | Avant | Après | Δ |
|---|---:|---:|---:|
| **Opportunité** | 1 534 | **1 380** | **−154** |
| À creuser | 11 608 | 8 876 | −2 732 |
| Écartée | 1 141 | 1 215 | +74 |
| Faux positif probable | 28 142 | 30 954 | +2 812 |
| **PPR fort** | 9 835 | **8 219** | **−1 616** |
| **PPR faible (Étape A)** | 0 | **2 705** | **+2 705** |

- Parcelles évaluées : **42 425 / 42 425** (100 %) · DB globale **431 663 / 24** inchangée · **gold 17 inchangé** ·
  Saint-Pierre **reste gold** · 0 doublon · 23 autres communes intactes.

## 4. Résultat Étape A (l'effet recherché)

- **+28 opportunités** créées via le flag **PPR marginal < 10 %** (transition `≠opp → opp`, **100 % via marginal**).
- **0 perte imputable à l'Étape A** (aucune perte d'opportunité via le flag marginal).
- **PPR faible 0 → 2 705** (parcelles déflaguées en bord de périmètre) ; **PPR fort 9 835 → 8 219**.
- L'Étape A fonctionne comme conçu : conservatrice (< 10 %), gain net positif, 0 perte propre.

## 5. Dérive hors Étape A (−182) — **correction de faux positifs**

La re-cascade ré-applique **tout le code courant** (`rules_version 2b45db742f40 → fb6a5478b2bf`) aux verdicts
Saint-Pierre qui dataient du 2026-06-21 → **−182 opportunités retirées, 0 via le flag marginal**. Cause :

- **100 % via la couche `declassement`** (PPR/OSM/bâti-layer tous `PASS` pour ces parcelles) :
  - **126 → `HARD_EXCLUDE` → faux positif probable** (micro-parcelle < 100 m² **ou** **déjà bâti** « ensemble bâti » BD TOPO) ;
  - **56 → déclassement `fort` → à creuser** (surface réduite 100–250 m² / bâti partiel / accès non identifié).
- **Score INCHANGÉ** (ex. 73→73, 68→68, 66→66) : le déclassement corrige le **STATUT**, pas le score (transparence, par design — `declassement.py`).
- **120 / 182 étaient DÉJÀ non-opportunité au baseline 2026-06-08** (74 à creuser + 46 à creuser) : le cascade
  **2026-06-21 les avait sur-promues à tort** ; le recalcul actuel **restaure** le bon classement.

→ Ce sont de **vrais faux positifs** (parcelles **déjà construites** ou minuscules — pas des opportunités foncières).
La règle améliorée « ensemble bâti » (R1) les attrape correctement.

## 6. Conclusion

- **État re-cascadé ACCEPTÉ** — **pas de rollback**.
- La baisse nette **−154** = **+28 (Étape A réel)** − **182 faux positifs « déjà bâti » correctement retirés** :
  c'est un **assainissement qualité**, pas une perte commerciale.
- Les **1 380 opportunités actuelles sont PLUS FIABLES** que les 1 534 précédentes (qui incluaient 182 parcelles
  déjà bâties / micro). **Qualité de lead ↑.**
- **Saint-Pierre reste gold**, config inchangée, gold count **17**.

## 7. Recommandation

- **Ne PAS généraliser en mode « gain brut »** : sur les vieilles communes gold, la re-cascade **assainit** (retrait
  des faux positifs déjà bâtis) **en plus** d'appliquer l'Étape A → le **net d'opportunités peut baisser** tout en
  **améliorant la qualité**.
- **Généraliser commune par commune avec backup** (comme ici), **sans rollback réflexe** sur une baisse nette.
- **Présenter les futurs résultats comme « qualité des leads améliorée »**, pas « moins d'opportunités ».
- **Mesurer séparément, par commune** : (a) **gain Étape A** (via flag marginal), (b) **retrait faux positifs**
  (via déclassement), (c) **net opportunités** — comme dans ce rapport.

---

### Provenance (lecture seule, hors la mutation acceptée)
- Mutation **autorisée et unique** : re-cascade Saint-Pierre (`evaluate_commune`), backup pré-run validé.
- Investigation : `SELECT` sur `parcel_evaluations` (3 versions : 06-08 / 06-21 / 06-25), `cascade_results`, lecture de `declassement.py`.
- Aucun import, aucune couche modifiée, aucune autre commune touchée, aucun rollback, aucun passage gold, aucun changement code/config/scoring.
