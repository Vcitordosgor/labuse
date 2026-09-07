# SCORING-4 — ré-entraînement `q_v14` (les deux améliorations combinées)

**Nature** : ré-entraînement + run candidat. **Aucune promotion, aucune bascule, aucun merge.**
Le run servi reste `q_v11_m137` (`config/served_run.txt`) jusqu'à décision de Vic.
Branche `feat/scoring-4`, worktree `~/Desktop/labuse-scoring4`. Modèle CC : Fable (rédigé ici par Opus 4.8).

---

## Étape 0 — les deux réserves tranchées AVANT tout calcul

`pwd` = `/Users/openclaw/Desktop/labuse-scoring4` · branche = `feat/scoring-4` · arbre **propre** (vérifié).

### Réserve 1 — le pipeline sait-il réutiliser la cascade d'un run existant sous un nouveau `run_id` ?

**OUI. Réserve levée, sans rejeu de cascade.**

- Le pipeline expose un override **non destructif** dédié exactement à ce besoin :
  `src/labuse/scoring/p_v2/pipeline.py:366-369` —
  > « M8a — override NON DESTRUCTIF pour scorer un run CANDIDAT sur SA propre cascade sans
  > toucher la constante servie : `LABUSE_ETAGE0_RUN` (défaut = `Q_A_RUN_LABEL`). Utilisé
  > uniquement en batch candidat, jamais en prod. »
  ```python
  etage0_run = os.environ.get("LABUSE_ETAGE0_RUN", runs.current())
  ```
- L'étage 0 est lu depuis la cascade **déjà persistée** du run cité, pas recalculé :
  `src/labuse/scoring/p_v2/pipeline.py:370-374` — `SELECT p.idu FROM dryrun_parcel_evaluations d …
  WHERE d.run_label = :run AND d.status IN ('exclue','faux_positif_probable')`.
- `run_score_v2(session, *, run_id=…)` accepte un `run_id` explicite libre et refuse un doublon :
  `src/labuse/scoring/p_v2/pipeline.py:239-269` (`q_v14` sera donc accepté).
- **Précédent d'usage** identique : `qa/ponderation/mesure_ablanc.py:32` pose
  `LABUSE_ETAGE0_RUN = "q_v8_calibre"` puis score deux candidats sur cette cascade partagée.
- **Preuve en base** (base locale `labuse`) que la cascade de `q_v13_sources1` est bien là et
  réutilisable telle quelle :
  - `p_score_v2_runs` : `q_v13_sources1` présent (431 663 parcelles, `computed_at` 2026-09-07) ;
  - `dryrun_parcel_evaluations WHERE run_label='q_v13_sources1'` → **150 260 exclusions**
    (= 145 882 du servi `q_v11_m137` **+ 4 378 neuves**) sur 431 663 lignes. Les 4 378 exclusions
    neuves de SOURCES-1 sont donc dans l'étage 0 réutilisé, exactement le point de départ voulu.

→ `q_v14` repartira de l'étage 0 de `q_v13_sources1` via `LABUSE_ETAGE0_RUN=q_v13_sources1`.
**Coût du rejeu évité** : un `flux-run` complet (cascade sur 24 communes / 431 663 parcelles) se
compte en **heures** (`docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-1.md`, décision n° 16 ; `src/labuse/cli.py:668`).
Seul le scoring (P, tiers/rangs, contributions) est rejoué.

### Réserve 2 — les 22 sources de SOURCES-1 ont-elles ajouté des colonnes au dataset d'apprentissage ?

**NON. Réserve levée. Le rebuild features NE double PAS le temps.**

- SOURCES-1 n'a touché **que la cascade**, jamais le modèle :
  `docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md:363-364` —
  > « Recette scoring **inchangée** (m36 servie) : le run ne change QUE la **cascade** (les
  > nouveaux motifs SOURCES-1), **pas le modèle P**. »
- Les variables candidates issues des 22 sources (RPG canne, division récente DFI, vacance/âge
  IRIS) ont été **notées pour le banc K0 seulement**, jamais branchées :
  `docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md:135` et `:257` — « Rien au modèle sans banc ».
- Le dataset d'apprentissage a des **colonnes figées en dur**, non dérivées des sources :
  `src/labuse/scoring/p_model/ext_sql.py:150-287` (`build_ext_dataset`, SELECT explicite) et
  `src/labuse/scoring/p_model/sql.py:318-334` (`build_static`) ; le registre de features est une
  liste statique `FEATURES` : `src/labuse/scoring/p_model/features.py:40-151`.
- Le mandat lui-même acte que les 22 sources n'entrent pas dans `q_v14`
  (`docs/audit-2026-09/MANDAT-SCORING-4.md:49`).

→ Le rebuild du dataset reste au coût **habituel** : il n'est agrandi que des **4 variables neuves
prouvées par SCORING-DONNÉES-1** (`nu_asof`, `pct_bati_secteur_asof`, PC-de-PM, ancienneté PLU,
ventes PM secteur à surveiller) — pas des 22 sources. Pas de doublement.

### Verdict Étape 0

**Aucune des deux réserves ne bloque.** J'exécute le mandat. `q_v14` portera EN MÊME TEMPS
les gains de MODÈLE de `q_v12` (K2/K3/K4bis/isotonique par segment, rejoués) et les gains de
DONNÉES de `q_v13_sources1` (cascade + 4 378 exclusions, réutilisées via `LABUSE_ETAGE0_RUN`),
plus les 4 variables as-of de SCORING-DONNÉES-1. Le contrôle du manifeste (features q_v12 ∧
données/cascade q_v13_sources1 toutes présentes) sera fait et rapporté.
