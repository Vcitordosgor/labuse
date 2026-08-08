# M-E — Robustesse du scoring v2 — synthèse

Branche `feat/m-e-robustesse` (worktree `~/Desktop/labuse-me`). CC ne merge pas : Vic valide et merge.
Méthode imposée par le mandat : **mesurer chaque point avant de corriger** ; rapporter les constats
qui ne se reproduisent pas plutôt que corriger dans le vide (leçon M-D). Périmètre strict : `scoring/*`.

## 1. P2-7 — Équivalence ICD SQL ↔ Python — **LIVRÉ (test) + constat nuancé**

**Le cadrage du mandat est partiellement inexact.** Il annonçait « l'ICD calculé à deux endroits :
SQL (batch) et Python (fiche) ». Mesuré : la fiche/API ne calcule PAS l'ICD — elle LIT la colonne
`icd`/`icd_detail` déjà écrite par le batch SQL (`parcel_p_score_v2`) et n'utilise que des helpers
d'affichage (`bande`, `libelle_bande`, `manquants`). `compute_from_row` (Python) n'est appelé que
dans les tests : c'est une **implémentation de référence**. Il n'y a donc qu'UN calcul en prod (SQL).

La **vraie** duplication est interne à `icd.py` : chaque groupe porte deux prédicats maintenus à la
main — `sql_test` (chaîne SQL) et la branche `_eval_group` (Python). Rien ne garantit qu'ils restent
d'accord.

- **Mesure grande échelle** (`reports/m-e-robustesse/icd_equivalence.py`, run servi `q_v8_calibre`,
  année 2026) : **0 / 431 663** parcelles en désaccord ; les 9 groupes coïncident, icd_python == icd_sql
  partout.
- **Livrable** = `tests/test_icd_equivalence.py` : verrouille l'équivalence sur des lignes
  représentatives couvrant les pièges (NULL vs `'inconnu'` vs `''` vs 0/négatif vs nominal), en jouant
  le VRAI SQL Postgres contre le Python. Passe.

→ Validation #1 satisfaite : le test passe, l'écart mesuré est nul.

## 2. P1-5 — Robustesse de lecture — **1 durcissement appliqué (en périmètre)**

Lecture de `scoring/p_v2/pipeline.py` : le pipeline est déjà bien gardé (sha256 refusé, fraîcheur
permis en échec bruyant P1-6, `assert p_raw notna` « NA interdit », tables optionnelles → colonne
neutre documentée). **Un** point contredisait la règle « signalé, pas comblé silencieusement » :

- Backfill ICD (pipeline.py) : `except Exception → n_icd = 0` **muet**. Un backfill cassé aurait servi
  un ICD absent/périmé sans trace. Sur le run servi le cas **ne se manifeste pas** (n_icd = 431 663,
  ICD complet) — fragilité latente. Durcissement minimal, hors happy-path, aucun chiffre servi touché :
  `warnings.warn(...)` + `icd_error` remonté dans le rapport de run (lu à la bascule). Le run reste en
  vie (ICD cloisonné, ne touche ni tier ni rang ni p_raw). **Pas de valeur par défaut silencieuse.**

## 3. P2-9, P2-13, P2-15 — **NON REPRODUCTIBLES en l'état**

Ces codes renvoient à la revue « domaine 1 » de M53. **Le document source n'est pas dans le repo**
(seul `BUGS.md` porte des P-codes, mais d'une numérotation DIFFÉRENTE : son P2-7 = PUT segments, son
P1-5 = NL dégradé — sans rapport avec l'ICD/robustesse de ce mandat). Sans la description d'origine, je
ne peux pas mapper P2-9/13/15 à du code avec certitude. **Rapporté comme tel, pas corrigé au hasard**
(consigne du mandat). La lecture de `scoring/*` n'a pas fait apparaître d'autre lecture fragile
substituant une valeur par défaut silencieuse au-delà du point 2.

## 4. Funnel renouvellement — **COHÉRENT (aucune incohérence) + note périmètre**

⚠ Le funnel renouvellement vit dans `src/labuse/renouvellement.py` — **hors périmètre `scoring/*`**.
Mesuré en LECTURE (build `commit=False` + rollback, run `q_v8_calibre`, as-of 2026) :

| étape | parcelles | filtrées à l'étape |
|---|---|---|
| 1_bati_exclues | 195 209 | — |
| 2_zone_u_au | 182 330 | −12 879 |
| 3_capacite | 71 899 | −110 431 |
| 4_hors_copro | 70 128 | −1 771 |
| 5_hors_foncier_public_final | 67 258 | −2 870 |

`n` inséré dans `parcel_renouvellement` = 67 258 = étape 5. **Entrée = (passées) + (filtrées) à chaque
étape** : les différences successives se réconcilient exactement, aucune parcelle perdue ni comptée deux
fois, monotonie stricte. C'est un entonnoir-FILTRE cohérent (déjà couvert par `test_renouvellement`).
→ Validation #4 satisfaite. **Aucune correction** : rien n'est incohérent, et le fichier est hors
périmètre (toute retouche = décision Vic).

À NE PAS confondre avec `scoring/dryrun.py::build_entonnoir` (motifs des écartées) : buckets
**cumulatifs par conception** (une parcelle cumule des motifs) — somme > total voulue, documenté,
non trompeur.

## 5. P2-25 — Poids du feedback — **NON REPRODUCTIBLE (effet nul) + borne confirmée**

- **Effet réel mesuré** : table `parcel_feedback` = **0 ligne**. Aucun feedback n'existe → effet nul sur
  quoi que ce soit de servi aujourd'hui.
- **Structure** : `scoring/feedback.py` borne l'ajustement à ±`max_adjustment` (20) et le clampe dans
  `score_bounds`. Surtout, le feedback ne touche QUE le `opportunity.score` de la cascade (via
  `apply_feedback`, appelé dans `cascade/pipeline.py`) — **jamais** le tier P gelé (`parcel_p_score_v2`,
  calculé sans aucune lecture du feedback). Un feedback ne peut donc pas déplacer un tier au-delà de la
  calibration : il ne déplace pas de tier du tout. → P2-25 satisfait, **aucune correction**.

## Hors périmètre respecté

P2-11 (8 copropriétés en réserve) : arbitrage Vic non tranché — **pas touché**. Modèle, coefficients,
calibration, golden, surfaces servies : **pas touchés**.

## Validation attendue

1. Test d'équivalence ICD : **passe** (écart réel 0/431 663). ✔
2. Aucun changement de tier sur le golden : `parcel_p_score_v2` **non ré-écrit** par M-E ; comparaison
   directe des 118 IDU golden = **0 écart** sur les 85 à tier renseigné. ✔
3. Constats non reproductibles **rapportés comme tels** (P2-9/13/15 introuvables ; feedback nul ;
   cadrage ICD nuancé). ✔
4. Funnel renouvellement : entrée = somme des sorties à chaque étape, étape 5 = n inséré. ✔

## Fichiers touchés (périmètre)

- `src/labuse/scoring/p_v2/pipeline.py` — durcissement backfill ICD (signalé, pas comblé).
- `tests/test_icd_equivalence.py` — nouveau test d'équivalence SQL↔Python.
- `reports/m-e-robustesse/` — scripts de mesure (icd_equivalence.py) + cette synthèse.

Tests : suite scoring/renouvellement/p_v2 = **52 passés** ; `test_icd_equivalence` inclus.
