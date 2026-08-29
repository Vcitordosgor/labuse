# GOLDEN-REGEN · LOT 0 — DIAGNOSTIC (avant régénération)

## Sur quel run le golden est-il gravé, et que sert l'app ?

- **Golden gravé** : `reports/m6-audit/golden/golden-parcelles.json` → `meta.run_v2_servi = q_v10_m129`
  (119 parcelles, dont des ancres J3).
- **App servie** : `config/served_run.txt` = **`q_v11_m137`** (= `Q_A_RUN_LABEL`, source de vérité unique).
- Les DEUX runs existent en base (`p_score_v2_runs`). **Mismatch : le golden est gravé sur q_v10_m129,
  l'app sert q_v11_m137.** La bascule q_v10→q_v11 s'est faite SANS régénérer le golden.

## Les 120 passent-ils parce que les valeurs coïncident, ou parce qu'ils ne comparent rien ?

**Ni l'un ni l'autre : lancé sur le run SERVI (défaut = `config/served_run.txt`), le golden est ROUGE —
`Bilan: 120 FAIL / 119`.** Les écarts, cas par cas :
- **119 × `api.score_v2.run_id: attendu='q_v10_m129' obtenu='q_v11_m137'`** — le run gravé n'est plus le
  run servi (sur CHAQUE parcelle).
- **6 × libellé zonage** : `« U » (urbaine / à urbaniser — constructible)` → `« U » (urbaine —
  constructible)` — raffinement de libellé (M128-2-J : U = urbaine, distincte de AU) — **évolution voulue**.
- **1 × `tiers_effectifs`** : les effectifs des tiers ont dérivé entre q_v10 et q_v11 (brulante 82→111,
  chaude 1525→1367, a_creuser 136763→136841, réserve 8738→8789, écartée 145882→145881) — **delta de run**.

Ce n'est PAS des fixtures vides ni des assertions neutralisées : la référence porte de VRAIES valeurs sur
les deux faces (db/api) et `compare_entry` les compare champ par champ. C'est une **référence PÉRIMÉE sur
un run que l'app ne sert plus**.

## Discrimination : si on casse une valeur de scoring, combien rougissent ?

Mesuré empiriquement (parcelle golden `97401000AB0001`, run servi q_v11_m137) :
- **avant** : 1 écart (le seul `run_id` q_v10≠q_v11).
- après avoir cassé le tier en base (`ecartee` → `chaude`) : **10 écarts** — `db.score_v2.tier`,
  `api.score_v2.tier`, `api.fiche.score_v2.tier` (les TROIS faces), + rang/mult/… cascadés, + le
  `tiers_effectifs` global déplacé. Restauré.

→ **Le mécanisme EST discriminant** : une régression de scoring sur une parcelle golden rougit sur ses
trois surfaces. Le golden n'est pas aveugle *dans sa comparaison* — il est gravé sur le **mauvais run**.

## Alors, où est l'aveuglement ?

`qa/golden_check.py` n'est PAS dans la suite pytest (le gate de merge). Une garde EXISTE pourtant —
`bascule_gardes.check_golden_regenere(run_servi, GOLDEN_PATH)` lève `GoldenPerimeError` si
`golden.meta.run_v2_servi ≠ run_servi` — MAIS `test_bascule_gardes.py` ne la teste qu'avec un golden
BIDON (`parcelles: {}`, run codé en dur `q_v8_calibre`) : **aucun test ne la lance sur le VRAI golden +
le VRAI run servi.** Résultat : la bascule vers q_v11_m137 a laissé le golden gravé sur q_v10_m129 et
AUCUN test n'a rougi. Le filet est décroché du gate — « vert » qui ne vérifie rien.

## Plan

- **LOT 1** : régénérer le golden sur q_v11_m137 (`qa/golden_regen.py`), lister chaque valeur d'ancre qui
  bouge, vérifier qu'aucun écart n'est une régression (les diffs attendus = run_id + libellé zonage +
  effectifs de tiers = delta q_v10→q_v11 assumé, run servi décidé par `served_run.txt`).
- **LOT 2** : un test pytest qui appelle `check_golden_regenere(Q_A_RUN_LABEL)` sur le VRAI golden — il
  ÉCHOUE tant que le golden n'est pas gravé sur le run servi. C'est ce qui manquait.
