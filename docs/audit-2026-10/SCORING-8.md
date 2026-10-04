# SCORING-8 — remettre le scoring sur les données du jour, puis graver

Branche `fix/scoring-8` depuis `origin/main` `09c50a83` · worktree `~/Desktop/labuse-scoring8` ·
base Postgres `labuse` · venv `~/Desktop/labuse/.venv`. Aucun run île, aucune bascule, aucun
`golden promote`, aucun merge. Opus, 1 session.

Commits (un par lot) :
- `d0463d67` Lot A — jointures de caches dédoublonnées
- `6f7ec7a5` Lot A bis — boot sans verrou + C26 (SDP inconnue ≠ 0)
- `e63de0f5` Lot B — mesure dérive cascade + remise au jour préparée
- `9d067236` Lot C — harnais de re-calage/gravure (prêt, bloqué sur q_v16 servi)

## Étape 0 — état constaté

| point | valeur |
|---|---|
| branche / base | `fix/scoring-8` sur `origin/main` `09c50a83`, arbre propre, `.env` présent |
| résiduel servi (`parcel_residuel`) | VUE du run servi, 431 663 lignes, `computed_at` 2026-09-25 (seq 10, `residuel_runs.is_served`) |
| run scoring servi | `q_v11_m137` (`config/served_run.txt` + `served_manifest.json`) |
| étage 0 de q_v15 (`q_v13_sources1`) | cascade du 07/09, 431 663 parcelles évaluées : **150 260 exclue**, 263 676 a_creuser, 17 727 opportunité |

---

## Lot A — jointures de caches dédoublonnées (`score_labuse.py`, `_ENTREES_SQL`)

### Fait
`_ENTREES_SQL` garantit désormais **une ligne par parcelle** pour chaque cache, par une règle
EXPLICITE et INDÉPENDANTE DE L'ORDRE — plus jamais « la dernière au hasard ». Chaque jointure est
une sous-requête `LATERAL` qui choisit la ligne la plus **contraignante** :

| cache | règle | commentaire |
|---|---|---|
| `parcel_residuel` | ligne COMPLÈTE la plus récente (`computed_at DESC`) | cache multi-champ cohérent → jamais un mélange de champs de lignes différentes |
| `batiment_hauteur_lidar` | `MAX(faitage_m)` | le bâtiment le plus HAUT → cran R+2 déclenché quel que soit l'ordre |
| `parcel_terrain` | `MAX(pente_moy_deg)` | pente la plus forte = la plus contraignante |
| `parcel_au_statut` | classe AU différée d'abord (`_AU_DIFFEREE`), puis alpha | capacité ×0,5 l'emporte ; départage déterministe |
| cascade `acces` | `ORDER BY (result='PASS') DESC` | verdict le plus défavorable, au lieu d'un `LIMIT 1` au hasard |

### Mesuré
- **Doublons en base aujourd'hui : 0** partout. Les trois tables nommées ont une **clé primaire**
  sur la colonne de jointure (`batiment_hauteur_lidar.idu`, `parcel_terrain.idu`,
  `parcel_au_statut.parcel_id`) ; `parcel_residuel` est une **vue** du run servi (une ligne/parcelle
  par construction) ; `dryrun_cascade_results` a 0 ligne `acces` multiple. La prémisse « plusieurs
  lignes par parcelle » ne se réalise pas sur la base du jour — mais la requête ne dépend plus d'un
  invariant tenu ailleurs : elle se garantit seule (robuste au prochain rebuild / ingestion partielle).
- `batiment_hauteur_lidar.faitage_m` est déjà le **P99 des cellules LiDAR de toute la parcelle**
  (`hauteur_lidar_dalles.py`, `ON CONFLICT (idu)`) : « 3 bâtiments dont un ≥ 9 m » se résout au P99
  dès l'ingestion ; le `MAX` du join est le filet.
- **Dry-run 30 témoins + Saint-Paul = 51 155 parcelles** (`scoring8_dryrun.py`, cascade
  `q_v13_sources1`) : **0 score, 0 bande, 0 NC bougent**. Changement behavior-preserving sur la base
  du jour (confirmé old-code vs new-code identiques).

### Test
`tests/test_scoring8_dedup.py` (7 tests) : chaque règle de dédoublonnage testée en PERMUTANT l'ordre
des lignes candidates → le gagnant est déterministe ; R+2 déclenché dès qu'un bâtiment dépasse le
seuil, quel que soit l'ordre.

---

## Lot A bis

### (1) Verrou ALTER au démarrage (`models.py`)
Même correctif que `ensure_geom_2975` (commit `70278401`), **généralisé**. Un DDL idempotent
(`ADD/DROP COLUMN IF [NOT] EXISTS`, `ALTER … TYPE` agrandissant, `CREATE INDEX IF NOT EXISTS`) prend
quand même un verrou **ACCESS EXCLUSIVE** (ou SHARE pour un index) sur la table au moment où il
s'exécute, **même quand il n'a rien à faire** ; si une transaction (run cascade, build) tient la
table, le boot se met en file derrière elle et gèle les lectures suivantes. On teste donc
`information_schema` / `pg_class` AVANT (aucun verrou de table) et on n'émet le DDL QUE s'il manque.

Fonctions gardées (toutes dans le chemin de boot `_ensure_schema_steps`) :
`ensure_parcel_origine` (cible du mandat, `parcels`), `ensure_icd_columns` (dont
`CREATE INDEX … ON parcels` — **décisif**, + 3 ALTER/index sur `parcel_p_score_v2`),
`ensure_sitadel_depot`, `ensure_parcel_eval_status_dropped`, `ensure_constructibilite_cache`
(2 `ALTER COLUMN TYPE` sur `parcel_p_score_v2` / `score_snapshot_parcelles`).
Helpers `_col_presente` / `_index_present` / `_varchar_len`.

**Test** (`tests/test_scoring8_boot_sans_verrou.py`) : une transaction tient `parcels` en ACCESS
SHARE (SELECT non commité) ; les `ensure_*` tournent dans un thread et **terminent en < 10 s** (chemin
gardé = aucun DDL émis = aucun blocage). Si un garde saute, le DDL bloquerait et le test échouerait.

### (2) C26 (arbitrage Vic) — SDP inconnue ≠ 0 (`score_labuse.py`)
Une SDP résiduelle **inconnue** (`sdp_residuelle_m2 IS NULL`, non calculée) ne doit JAMAIS être lue
comme 0 dans l'éligibilité du classement → `_cause_nc` renvoie désormais `NC_SDP`
(« capacité résiduelle non calculée ») → bande **NC « Analyse incomplète »**, jamais
« 0 / Non retenue ». Un **vrai zéro** (`sdp = 0` produit par le moteur : terrain exigu, zone
inconstructible, bâti saturé…) reste la bande « 0 ». Filet **cause-indépendant**.

**Mesuré sur l'île** : 4 244 parcelles à SDP inconnue (`NULL`) — **toutes `hors_plu`**, donc DÉJÀ NC
par la cause (`NC_ZONE`) aujourd'hui → **0 bande bascule maintenant**. Nombre réellement « sauvé » de
la bande 0 = **0** (toute SDP NULL porte déjà une cause NC). La règle garantit le cas à q_v16, où une
exception PLU non modélisée ou un trou de donnée peut produire une SDP NULL SANS cause NC.
Vérifié : sur la base du jour, `sdp=0` = valeur produite (279 916 parcelles, causes connues),
`sdp=NULL` = non calculée (4 244, hors_plu) — distinction nette NULL ≠ 0.

**Test** (`tests/test_scoring8_c26.py`, 4 tests) : NULL → NC `NC_SDP` même sans cause NC ; `sdp=0`
→ bande « 0 / Non retenue » ; `hors_plu` garde le motif « zone non résolue ».

---

## Lot B — cascade du 07/09 : mesure + remise au jour préparée

### B.1 — ce qui a changé depuis le 07/09
- **Code cascade** : 11 commits depuis le 07/09 (SOURCES-1 nouvelles couches, FICHE-COUCHES handlers,
  PLU-CALIBRAGE-4 bascule du moteur, CHASSE-FIX-1).
- **Données `spatial_layers`** : ré-ingestion massive **09-13 / 09-14 / 09-26**, toutes postérieures à
  q_v13_sources1 : `sup`, `ppr_etat`, `georisque_alea`, `icpe`, `sol_pollue`, `mvt`, `zone_humide`,
  `tri_zone`, `endiguement`, `trait_de_cote`, `potentiel_foncier`, + couches NEUVES
  `mesures_compensatoires`, `scot`, `poste_transformation`, `pylone`, `enr_exclue_hors_toiture`.
- `spatial_layers_sub` (prime de la cascade, 1 548 388 pièces) est **à jour** (contient les couches
  du 09-26) → le rejeu LIVE évalue bien les données du jour.

### B.2 — mesure (`scoring8_cascade_probe.py`)
Échantillon **3 004 parcelles** stratifié commune × verdict actuel (graine fixe `s8b`,
reproductible), rejeu de la cascade LIVE (code + données + `spatial_layers_sub` du jour) sous un
label jetable, comparé parcelle à parcelle à `q_v13_sources1`.

**Transitions de statut** : 2 970 / 3 004 **inchangés (98,9 %)**.

| avant → après | n | |
|---|---|---|
| a_creuser → a_creuser | 1 823 | |
| exclue → exclue | 1 044 | |
| opportunité → opportunité | 103 | |
| opportunité → a_creuser | 23 | reclassement interne |
| a_creuser → opportunité | 11 | reclassement interne |
| **exclue → non exclue** | **0** | — |
| **non exclue → exclue** | **0** | — |

**Accès** (facteur mineur du Score LABUSE) : 2 529 POSITIVE→POSITIVE + 475 PASS→PASS = **0 bascule
PASS↔POSITIVE**.

**Verdicts cascade changés par couche** (sur les 3 004) : les couches à `3004/3004` sont **NEUVES**
(absentes au 07/09, désormais évaluées) — `cimetiere, vefa_neuf, zone_activite, tri_zone,
endiguement, znieff, bassin_versant, bruit_carte` — **aucune ne flip une exclusion**. Churn de flags
sans franchir l'exclusion : `risques` 2064/25457, `bati` 363, `zonage_plu_gpu` 344, `friche` 275,
`prescription_plu` 262, `declassement` 209, `residuel_socle` 104, `sol_pollue` 49, `ens` 7, `icpe` 2,
`peb` 2, `sitadel` 1.

**Extrapolation île** (× 143,7) : **~0 parcelle change d'exclusion** ; ~4 886 (1,1 %) reclassements
a_creuser↔opportunité À L'INTÉRIEUR des non-exclues.

**Conclusion B** : remettre la cascade au jour est de l'**hygiène de fraîcheur** (SUP/ER/EBC repris,
ORACLE-FIX-1, 50 pas, couches informatives neuves) à **faible risque** — l'étage 0 (exclusions) est
stable depuis le 07/09.

### B.3 — commande de remise au jour (geste Vic)
`scripts/audit/scoring/run_cascade_2026_10.py` rejoue la cascade **île SEULE** (pas de scoring, pas de
fit) sous le label neuf `cascade_2026_10`, écrit dans `dryrun_parcel_evaluations` +
`dryrun_cascade_results` → **étage 0 valide** (la garde de complétude `resoudre_cascade_run` exige une
ligne par parcelle sous le label). Reprend la logique EXACTE de la phase cascade de `flux-run`
(reconstruction `spatial_layers_sub` + 24 communes), sans le scoring. Reprenable.

- **Estimation** : **431 663 parcelles**, durée **≈ 3 h 26 – 4 h 13** (référence historique cascade île).
- **Rejeu partiel : NON viable.** La garde de complétude exige une ligne pour CHAQUE parcelle de l'île
  sous le label — le faible drift mesuré (0 exclusion) ne réduit pas le périmètre : couverture
  **totale** obligatoire.

### B.4 — `run_qv16.py` (non exécuté)
`scripts/audit/scoring/run_qv16.py`, calqué sur `run_qv15.py` : `LABUSE_ETAGE0_RUN=cascade_2026_10`,
`run_id=q_v16`, **modèle inchangé `recette="q_v15"`** (q_v16 = modèle q_v15 + étage 0 du jour ;
`q_v16` n'est pas une recette connue — m36 | q_v12 | q_v14 | q_v15). `etage0_run=cascade_2026_10`
gravé dans `params` → le run passe la garde de complétude. Rien de servi ne bouge.

---

## Lot C — re-caler et graver les bandes (BLOQUÉ sur q_v16 servi)

**Non exécutable dans cette session : q_v16 n'existe pas** (0 ligne `p_score_v2_runs` / `score_labuse`).
Prérequis = gestes Vic (B.3 + B.4 + `residuel-serve` de q_v16). Harnais prêt :
`scripts/audit/scoring/scoring8_lotC.py` (modes `temoins` | `ile`).

**Pré-lancé sur le résiduel servi COURANT (pré-q_v16)** comme baseline :
- Reproduit SCORING-7 **au score près** pour les parcelles stables (bonnes : 90/85/90/90/100/100/
  80/90/64/90 = `temoins_q_v15.json`) → **preuve que Lot A + C26 sont sans effet** (old-code vs
  new-code : CP0427 45=45, AB1117 15, AM0140 32, AC0109 0 — identiques).
- Surface la **dérive DONNÉE** du résiduel servi (seq 10, 25/09) depuis le snapshot SCORING-7 :
  `97411000CP0427` mauvaise = **45 (>25)**, `97402000AB1117` 35→15, `97401000AM0140` 50→32,
  `97415000AC0109` 15→0. L'invariant déclenche **« NE RIEN GRAVER »** (correct : q_v16 non servi +
  un témoin viole déjà le seuil sur la donnée du jour). → c'est précisément pourquoi les bandes
  doivent être re-calées sur q_v16 avant toute gravure.

Le yaml `config/score_labuse.yaml` reste **« VALEURS PROVISOIRES … à RE-CALER »** (inchangé).

---

## Séquence exacte des gestes de Vic (copiable)

Préfixe commun :
```sh
cd ~/Desktop/labuse-scoring8
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"
VENV=~/Desktop/labuse/.venv/bin/python
```

1. **Cascade île remise au jour** (B.3, ≈ 3 h 26 – 4 h 13, 431 663 parcelles) :
   ```sh
   $VENV scripts/audit/scoring/run_cascade_2026_10.py
   ```
2. **Scoring q_v16** (B.4, lit l'étage 0 `cascade_2026_10`, modèle q_v15 ; purger q_v16 d'abord s'il
   existait) :
   ```sh
   $VENV scripts/audit/scoring/run_qv16.py
   ```
3. **`residuel-serve` de q_v16** (geste Vic habituel) + le scoring Score LABUSE île de q_v16.
4. **Lot C — re-caler / vérifier** (≈ 15 min) :
   ```sh
   S8_CASCADE=cascade_2026_10 $VENV scripts/audit/scoring/scoring8_lotC.py temoins
   S8_CASCADE=cascade_2026_10 $VENV scripts/audit/scoring/scoring8_lotC.py ile
   ```
   - Si tous les invariants tiennent (bonnes ≥ 80 sauf AB0798, mauvaises ≤ 25, pas d'inversion,
     aucune NC à 0) → **graver** `config/score_labuse.yaml` : retirer « provisoire / à re-caler »,
     écrire « bandes validées le <date> sur q_v16 ».
   - Sinon : **ne rien graver**, expliquer la cause, proposer le seuil (le harnais nomme le témoin
     fautif).

## Harnais / tests livrés
- `scripts/audit/scoring/scoring8_dryrun.py` — snapshot/diff du Score LABUSE (Lot A).
- `scripts/audit/scoring/scoring8_cascade_probe.py` — mesure dérive cascade (Lot B).
- `scripts/audit/scoring/run_cascade_2026_10.py`, `run_qv16.py` — gestes Vic préparés (non exécutés).
- `scripts/audit/scoring/scoring8_lotC.py` — re-calage/vérification des bandes (Lot C).
- `tests/test_scoring8_dedup.py` (7), `test_scoring8_boot_sans_verrou.py` (2),
  `test_scoring8_c26.py` (4) — **13 tests verts**.

## pytest
Départ (origin/main, avant SCORING-8) : **15 échecs / 3 573 passés / 71 skipped** — tous
pré-existants/environnementaux (crédit API LLM, `LABUSE_RATE_LIMIT_OFF` non posé, `deps_declared`,
verrous base réelle, `test_plafond_densite`). Fin : voir §pytest final ci-dessous (≤ départ attendu,
+ 13 tests SCORING-8).
