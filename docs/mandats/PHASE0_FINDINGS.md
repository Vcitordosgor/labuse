# PHASE 0 « LE JUGE » — FINDINGS

Journal des findings (caractérisation). Règle : on **documente le réel**, on ne corrige pas hors
périmètre ; tout finding touchant une **exclusion** ou un **score servi** = **S1 → STOP → Vic**.

Statuts possibles : `S1-EN ATTENTE DE VIC` · `reporté` · `traité`.

---

## LOT J1 — Baseline (branche `phase0/j1-tests`)

### Baseline mesurée (2026-07-20, `main` @ `070a6ac`, aucune modif de code)
- **`git status`** : propre (la cartographie a été parquée sur la branche `docs/cartographie`).
- **`pytest` complet** (`.venv`, `LABUSE_DATABASE_URL=openclaw`, `PROJ_DATA` posé) :
  **852 passed · 9 failed · 14 skipped** (1 warning). Compte de référence du lot.
- **Golden** (`qa/golden_check.py` contre l'API `:8010` servant `q_v6_m8`) :
  **32/32 PASS, 0 FAIL, 0 incohérence base↔API**. ✅ *Le run servi — la boussole — est intact.*
  (NB : le golden actuel compte **32** parcelles, pas 30 — cf. finding F0.)

Les 9 échecs sont **pré-existants** (branche neuve, zéro modif de code) et se répartissent ci-dessous.

---

### F0 — Golden = 32 parcelles, le mandat en annonce 30 *(observation, non bloquant)*
- **Réel** : `qa/golden_check.py` et `COMMANDES.md` documentent **32** parcelles témoins ; le mandat
  Phase 0 parle de « golden 30 ». Écart de comptage, pas de contenu.
- **Statut** : `reporté` — à confirmer avec Vic (le noyau à étendre en J3 part de 32, pas 30).

---

### F1 — Tests cascade « exclusions » en échec : fixture démo périmée vs config *(EXCLUSION → S1)*
- **Tests concernés** (`tests/test_cascade.py`, marqueur `db`, jeu démo Saint-Paul) :
  `test_exclusions_sont_dures`, `test_statuts_attendus`, `test_promotion_phase2_ne_tourne_pas_sur_exclues`.
- **Symptôme** : la parcelle démo P3 (censée « exclue par PPR zone rouge ») n'est **plus exclue par la
  couche `risques`** : `_verdict(demo[3], "risques", HARD_EXCLUDE)` renvoie `None` ; la couche émet un
  `SOFT_FLAG` « Périmètre PPR — servitude réglementaire approuvée ».
- **Cause exacte (diagnostiquée, non corrigée)** :
  - Le jeu démo (`ingestion/demo_saint_paul.py`) pose la couche PPR avec **`subtype="rouge"`**
    (`add_layer("ppr", "rouge", …)`).
  - `config/cascade_rules.yaml` (couche `risques`) attend désormais **`ppr_red_subtypes: ['INTERDICTION']`**.
  - `RisquesLayer.evaluate` (`cascade/layers/phase1.py:460`) ne HARD_EXCLUDE que si le sous-type de
    l'intersection ∈ `ppr_red_subtypes`. `"rouge"` ∉ `{'INTERDICTION'}` → chute dans la branche
    « périmètre PPR / servitude PM1 » = **SOFT_FLAG prudent** (comportement PPR-v2 **documenté dans le
    code** : « on connaît le périmètre réglementaire, pas le zonage rouge/bleue interne → flag fort
    prudent, jamais une exclusion automatique »).
- **Nature** : **drift fixture ↔ config**, PAS une régression du run servi. La *logique* d'exclusion est
  intacte (un vrai sous-type `'INTERDICTION'` HARD_EXCLUDE toujours) ; c'est la **donnée de test** qui
  utilise l'ancien libellé `"rouge"`. Le run servi q_v6_m8 est vérifié intact (**golden 32/32**).
- **Pourquoi S1 / STOP** : le finding **touche la couche d'exclusion**. Le mandat interdit de modifier
  une attendue de test d'exclusion sans validation explicite de Vic (zone gelée, règle 3) et impose le
  STOP (règle 1). **Je ne touche donc NI le jeu démo NI la config NI le test.**
- **Correctif possible (à décider par Vic, hors de ma main)** : soit aligner le jeu démo sur
  `subtype='INTERDICTION'` (changement fixture-only), soit réintroduire `'rouge'` dans
  `ppr_red_subtypes`. Trancher côté doctrine PPR-v2.
- **Statut** : **`S1-EN ATTENTE DE VIC`**.

---

### F2 — `test_statuts_attendus` non-déterministe : isolation démo incomplète *(observation liée à F1)*
- **Réel** : `demo_saint_paul._RESET_TABLES` **n'inclut pas `parcelle_personne_morale`**. La couche
  `foncier_public` (étage 0) lit cette table ; ses lignes **fuient d'un seed à l'autre**. Selon l'état
  résiduel, P3 est tantôt `exclue` (via `foncier_public` — ex. « OFFICE NATIONAL DES FORETS »), tantôt
  `a_creuser`. Observé : run direct → P3 `exclue` (foncier_public) ; run pytest → P3 `a_creuser`.
- **Nature** : défaut d'**isolation de test** (une table d'exclusion non purgée entre seeds). N'affecte
  pas le run servi. Renforce F1 (le résultat P3 dépend d'un état non réinitialisé).
- **Statut** : **`reporté`** (dépend de la décision F1 ; ne rien changer sans Vic — touche `foncier_public`).

---

### F3 — `test_verdict_effectif` (×4) : table `parcel_terrain` absente de `labuse_test` *(environnement)*
- **Tests** : `test_fiche_expose_score_v2_et_etage0`, `test_etage0_du_run_servi_prime`,
  `test_repli_legacy_sans_ligne_v2`, `test_liste_porte_le_verdict_effectif`.
- **Réel** : `sqlalchemy … UndefinedTable: relation "parcel_terrain" does not exist`. La table n'est pas
  créée par `models.create_all` (probablement produite par un `ensure_*` en SQL brut non appelé par
  `conftest`). Échec d'**environnement de test**, pas de logique.
- **Statut** : **`reporté`** — hors périmètre J1 (schéma test). À signaler ; ne pas « réparer » ici.

---

### F4 — Échecs d'environnement divers *(environnement)*
- `test_saint_paul_quality` (9 skips) : « base applicative indisponible » — nécessite la base *app*.
- `test_backup::test_backup_puis_restore_sur_base_temporaire` : nécessite droits admin PG / base temporaire.
- `test_ortho_detection::test_post_traitement_rejets` : `sqlalchemy` (table/at absente en `labuse_test`).
- **Statut** : **`reporté`** — dépendances d'environnement, hors périmètre du chemin critique J1.

---

## Décision de lot (J1)

Le **gate boussole est vert** (golden 32/32, run servi intact) et `git` est propre. **Mais** la baseline
`pytest` n'est pas verte, et **F1 touche la couche d'exclusion** (fixture démo périmée vs
`ppr_red_subtypes`). Conformément au mandat (baseline « sinon STOP » + règle 1 « STOP si le finding
touche une exclusion » + zone gelée règle 3 « ne jamais modifier une attendue sans Vic »), **je m'arrête
avant d'écrire les tests J1** et je remonte à Vic :

- **Aucune** modification de code, de config, de jeu démo ou de test existant n'a été faite.
- Les tests J1 à écrire portent en partie sur les **couches d'exclusion** (`test_etage0_ext.py`,
  complétion de `test_cascade.py`, `test_phase2_layers.py`) : les caractériser suppose de savoir si le
  comportement d'exclusion démo est **volontaire (PPR-v2)** ou **à corriger** — c'est la décision de Vic.

**Question à Vic (déblocage J1)** :
1. F1 — aligner le jeu démo sur `subtype='INTERDICTION'` (fixture-only), OU rétablir `'rouge'` dans
   `ppr_red_subtypes` ? (Cela conditionne les attendues d'exclusion que J1 doit encoder.)
2. F0 — golden = 32 confirmé comme noyau pour J3 ?
3. F3/F4 — j'encode le comportement ACTUEL et laisse ces tests d'environnement en l'état (findings), OK ?

Dès l'arbitrage F1, je reprends J1.a→c (les tests d'exclusion à ctx stubé — `test_etage0_ext.py` — sont
d'ailleurs **indépendants** de la fixture démo et pourront être écrits sans risque).
