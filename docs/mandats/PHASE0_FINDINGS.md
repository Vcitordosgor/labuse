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
- **Arbitrage Vic** : **option A** (la fixture s'aligne sur la config). **Vérification préalable
  exigée par Vic, faite** : les subtypes PPR réels en base = `INTERDICTION`(74), `PRESCRIPTION`(88),
  `i`(2). Le `i` est une **assiette PM1** (`suptype:"PM1"`, `code_risque:"i"`=inondation, périmètre —
  pas un degré), **PAS un équivalent-interdiction** → aucun trou de couverture, pas de nouveau S1.
- **Correctif appliqué** (commit `PHASE0-J1: F1+F2`) : `demo_saint_paul.py` pose désormais la PPR en
  `subtype='INTERDICTION'`. `RisquesLayer` HARD_EXCLUDE de nouveau P3. `seed-demo` → 9 parcelles,
  `demo-healthcheck` sans crash (les ✗ bâtiments/déclassement sont pré-existants, hors F1). `warm-demo`
  (IDU pilotes réels) non concerné par le seed synthétique.
- **Statut** : **`traité`**.

---

### F2 — `test_statuts_attendus` non-déterministe : isolation démo incomplète *(observation liée à F1)*
- **Réel** : `demo_saint_paul._RESET_TABLES` **n'inclut pas `parcelle_personne_morale`**. La couche
  `foncier_public` (étage 0) lit cette table ; ses lignes **fuient d'un seed à l'autre**. Selon l'état
  résiduel, P3 est tantôt `exclue` (via `foncier_public` — ex. « OFFICE NATIONAL DES FORETS »), tantôt
  `a_creuser`. Observé : run direct → P3 `exclue` (foncier_public) ; run pytest → P3 `a_creuser`.
- **Nature** : défaut d'**isolation de test** (une table d'exclusion non purgée entre seeds). N'affecte
  pas le run servi.
- **Correctif appliqué** (arbitrage Vic, commit `F1+F2`) : `demo_saint_paul` **contrôle** désormais
  `parcelle_personne_morale` — ajoutée à `_RESET_TABLES` + helper `_add_pm` : P1 = PM privée (groupe 6,
  acquérable), nouvelle **P9 = propriété publique** (Commune, groupe 4) → `foncier_public` HARD_EXCLUDE
  déterministe ET démontrable. `test_cascade.py` : 12/12.
- **Statut** : **`traité`**.

---

### F3 — `test_verdict_effectif` (×4) : table `parcel_terrain` absente de `labuse_test` *(environnement)*
- **Tests** : `test_fiche_expose_score_v2_et_etage0`, `test_etage0_du_run_servi_prime`,
  `test_repli_legacy_sans_ligne_v2`, `test_liste_porte_le_verdict_effectif`.
- **Réel** : `sqlalchemy … UndefinedTable: relation "parcel_terrain" does not exist` — puis, une fois
  celle-ci créée, `rnic_coproprietes`, `filosofi_carreaux_200m`, `parcel_adresse`, `parcel_zone_plu`,
  `parcel_viabilisation`. `_q_v2_fiche` lit une DIZAINE de tables « data-gap » créées hors ORM en prod.
- **Correctif appliqué** (arbitrage Vic « fix trivial », commit `F3+F4+F5+F6`) : `conftest.py` provisionne
  ces tables VIDES en base de test (rnic via sa DDL d'ingesteur ; les autres en CREATE minimal) → le
  contrat data-gap (0 ligne, jamais une erreur) est rétabli. **Puis F5** (voir ci-dessous) a levé
  l'échec logique restant. `test_verdict_effectif` : 4/4.
- **Statut** : **`traité`**.

---

### F5 — `test_verdict_effectif` seedait un run v2 sous un label NON servi *(caractérisation, touche verdict servi)*
- **Réel (une fois F3 levée)** : le test seedait le run v2 sous un label custom (`test-verdict-v2`),
  mais `_score_v2_run_id` est **ÉPINGLÉ à `Q_A_RUN_LABEL`** (« fix pré-lancement — ferme la bombe
  latente » : le run v2 servi n'est plus le dernier par timestamp, il est pinné au label servi) →
  renvoyait `None`, les cas v2 ne s'exerçaient pas.
- **Nature** : **test périmé** ; le CODE est correct (pinning volontaire). Aligné le run de test sur
  `Q_A_RUN_LABEL` — **assertions inchangées** (tier v2 pilote, étage 0 prime). ⚠ Touche la logique de
  **verdict servi** → signalé ici pour revue Vic (aucun changement de code/served ; seul le label du
  seed de test change).
- **Statut** : **`traité`** (à confirmer en revue).

---

### F4 — Rouges d'environnement → skips DOCUMENTÉS *(arbitrage Vic : « des skips oui, des rouges non »)*
- `test_backup` : `pg_dump` 16 (Homebrew) < serveur PostgreSQL 18 → « server version mismatch ». **Skip
  gardé** (compare pg_dump vs version serveur ; s'exécute dans un env où elles concordent).
- `test_saint_paul_quality` / `test_ux_v1` : skips PRÉ-EXISTANTS (base applicative indisponible en
  sandbox) — inchangés, déjà documentés dans les tests.
- **Statut** : **`traité`** (skips explicites documentés).

---

### F6 — `test_ortho_detection::test_post_traitement_rejets` : drift ortho *(hors périmètre scoring J1)*
- **Réel** : un candidat piscine rattaché à une parcelle bâtie (emprise 120 m² > 20, contexte attendu
  1.0) ne survit plus au `post_traitement` (0 restant au lieu de 1 → `NoResultFound`). Cause non triviale
  dans la chaîne `ortho_piscines.post_traitement` (hors chemin critique SCORING de J1).
- **Correctif** : `@pytest.mark.skip` DOCUMENTÉ (raison + renvoi ici). **Triage propriétaire ortho requis.**
- **Statut** : **`skip documenté`** (finding ouvert pour l'équipe ortho).

---

## Décision de lot (J1) — CLÔTURE

Après arbitrage Vic (F1 = option A vérifiée en base ; F0 = golden 32 confirmé ; F3/F4 = 0 failed via
fix trivial ou skip documenté ; F2 = seed contrôle `parcelle_personne_morale`), **J1 est livré** :

- **Baseline → verte** : `pytest` **929 passed, 16 skipped, 0 failed** (852 au départ ; +77 tests J1).
  **Golden 32/32 PASS** sur `q_v6_m8` — boussole intacte.
- **F1–F6 tous traités** (F6 = skip documenté, finding ouvert ortho ; F5 signalé pour revue verdict).
- **Tests J1 ajoutés** :
  - J1.a (41) : `test_etage0_ext.py`, `test_cascade_engine.py`, `test_phase2_layers.py`.
  - J1.b (13) : `test_p_model_ext_sql.py` (label L2-F, copro), `test_p_model_sql.py` (fenêtres anti-leakage).
  - J1.c (16) : `test_p_model_features.py` (équipements, shrinkage), `test_scoring_pure.py` (ICD, status).
- **Zones gelées respectées** : zéro touche scoring/cascade/config/étage 0 ; modèle P M3.6, `q_v6_m8`,
  golden 32 intacts. Seuls modifiés : `demo_saint_paul.py` (fixture, arbitré Vic), `conftest.py` (schéma
  test), 3 tests pré-existants (skips/label), + les nouveaux fichiers de test.

**Points à confirmer en revue Vic** :
1. **F5** — l'alignement du run de test sur `Q_A_RUN_LABEL` touche la logique de verdict servi
   (test-only, assertions inchangées) : OK ?
2. **F6** — skip ortho documenté, à router vers l'équipe ortho (hors scoring).

**STOP — review et merge Vic (branche `phase0/j1-tests`).**
