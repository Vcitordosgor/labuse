# MANDAT-SOURCES-MAJ-1 — Phase 3 : conclusion

Date 2026-10-10 · branche `fix/sources-maj-1` (worktree `labuse-sources`, PAS mergée, PAS poussée) ·
base locale uniquement · **rien sur le VPS, aucun run, aucune bascule**.
Commits : `db725be4` (Phase 1 inventaire), `60d41c93` (Phase 2 injections + cadastre), + ce rapport.

---

## 1. Sources injectées / restées en l'état / en échec

### Injectées (base locale, commande d'ingestion existante, sauvegarde + guard ±20 % + témoin)

| id | source | avant → après | millésime | impact run |
|---|---|---|---|---|
| 126 | Fibre Arcep | 330 051 → 330 310 immeubles (+0,08 %) | 2026_T1 → **2026_T2** | non |
| 74 | Transport GTFS + OSM | 14 041 → 14 039 lignes de couches | → **2026-10-10** | non (aménités indirect) |
| 16 | **SITADEL** | 50 545 → 50 809 (max 07-31 → **08-31**) | → **2026-08** | **OUI** |
| 100 | RNIC copropriétés | 2 220 → 2 220 (974 stable) | → re-sync 2026-10-10 | non |
| **96/1** | **Cadastre Etalab** (différentiel) | 431 663 → **434 582** parcelles | 2026-06 → **2026-09** | **OUI** |

### En échec (signalé, passé — « si un connecteur est cassé, le dire et passer »)

- **86 SIRENE établissements géoloc** : la livraison de septembre porte `insee=97454`, absent de `communes_referentiel` → `ForeignKeyViolation`, **transaction annulée** (0 ligne, millésime inchangé). Correctif hors mandat : tolérer/mapper l'INSEE orphelin (pas de refonte de connecteur ici).

### Restées en l'état (motif)

| id | source | motif | impact run |
|---|---|---|---|
| 28 | Érosion côtière | URL figée sur le fichier 2018 **+** refresh seulement via le chemin par-commune qui **re-score** | **OUI** → à faire AVEC q_v18 |
| 46 | Classement sonore | la couche ArcGIS `_V2` ≠ arrêtés 26/12/2024 (jeu data.gouv distinct → **changement de source**) | **OUI** → à faire AVEC q_v18 |
| 10 | RPG agricole | WFS LATEST = 2025 mais refresh seulement via le chemin par-commune qui **re-score** | **OUI** → à faire AVEC q_v18 |
| 102 | Conso NAF | aucune commande CLI + colonne `conso_2021_2025` à ajouter | non (travail extra, optionnel) |
| 41 | INSEE RP Logement 2023 | **réécriture du parseur** (format harmonisé) | non (travail extra, optionnel) |
| 73 | FRR ex-ZRR | arrêté 14/04/2025 existe mais **aucune commune 974 concernée** | sans objet |
| 35 | Cartofriches | API Cerema en **HTTP 503 depuis le 02/10** | réessayer |

Les **93 autres sources** du périmètre étaient déjà **à jour** ou **flux continu** (API/base vivante) — détail dans `INVENTAIRE.md`.

### Cadastre différentiel — détail (`CADASTRE-DIFF.md`)

- **+2 919 nouvelles** (géométrie brute `ST_MakeValid`, dérivés OK, scores NULL jusqu'au run).
- **1 501 géométries** réellement modifiées (7 864 ré-encodages `ST_Equals` laissés intacts).
- **0 contenance** changée (vérifié y compris à géométrie identique).
- **1 353 disparues** marquées `cadastre_disparue_le = 2026-09-01`, **jamais supprimées** (les FK CASCADE auraient détruit `pipeline_entries`/`projet_parcelles`/`alertes`/`module_division`). 46 référencées client.
- **Remplacement** `parcel_cadastre_remplacement` : **1 292/1 353** mappées (recouvrement ≥ 50 %), 61 vraiment disparues.
- Fiche de courtoisie back (« parcelle disparue — remplacée par […] ») en place ; **rendu front + exclusion carte/recherche/listes = avec q_v18**.

---

## 2. Faut-il un nouveau run (résiduel + scoring) ? — **OUI**

**Pourquoi.** Trois sources à impact run ont changé en base sans que les scores servis en tiennent compte :
1. **Cadastre** : 2 919 nouvelles parcelles **non scorées**, 1 501 géométries modifiées (intersections/SDP à recalculer), 1 353 disparues à **écarter du servi**.
2. **SITADEL** : permis jusqu'à août 2026 (le scoring lit `sitadel_permits`).
3. **28 érosion / 46 classement sonore / 10 RPG** (à ingérer d'abord) : entrent dans la cascade.

Tant que q_v18 n'a pas tourné : les nouvelles parcelles n'apparaissent pas, les disparues apparaissent encore, les scores ne reflètent ni le cadastre 2026-09 ni SITADEL 08-2026.

**Parcelles touchées.** Directement **~4 420** (2 919 nouvelles + 1 501 géométries) + 1 353 à écarter ; indirectement, un run recompute le résiduel + scoring sur **tout le parc servi (~434 k)** — c'est le fonctionnement normal d'un run.

**Durée estimée.** Run complet résiduel + scoring 974 ≈ **plusieurs heures** (ordre q_v16). À lancer en arrière-plan.

### Prérequis AVANT de lancer q_v18 (à faire par CC quand Vic le dira)

1. **Ingérer 28, 46, 10** (impact run) — pour 28/46 : pointer la source producteur courante (URL/jeu 2026 / arrêtés 26/12/2024) ; pour 10 : WFS LATEST déjà 2025. Via le chemin par-commune (le re-score fait partie du run).
2. **Exclusion des disparues au niveau du run** : ajouter `AND p.cadastre_disparue_le IS NULL` à la **sélection des parcelles du run** (un seul point → carte/recherche/filtres/listes propres). C'est l'endroit unique, pas endpoint par endpoint.
3. **Rendu front** du bandeau « parcelle disparue » (api.ts + composant fiche) — à vérifier dans l'app.
4. Repartir d'un **label de run** `q_v18` ; **ne pas** basculer `served_run.txt` sans feu vert.

---

## 3. Tables à envoyer en prod au prochain déploiement

> **En bloc, APRÈS q_v18 validé en local** (ne pas expédier le cadastre sans le run correspondant, sinon scores périmés en prod). Ordre : schéma d'abord, puis données, puis bascule.

**Schéma (DDL à jouer sur prod avant les données) :**
- `ALTER TABLE parcels ADD COLUMN IF NOT EXISTS cadastre_disparue_le date;`
- `CREATE TABLE parcel_cadastre_remplacement (…)` (cf. structure créée en local).

**Données (tables modifiées par ce mandat) :**
- `parcels` (cadastre 2026-09 : +2 919, 1 501 géométries, 1 353 marquées) — **gros**, + `geom_2975` (trigger prod OK).
- `parcel_cadastre_remplacement` (liens de remplacement).
- `adresse_parcelles` (rattachement des nouvelles).
- `sitadel_permits` (jusqu'à 08-2026).
- `spatial_layers` (couches transport, IngestionRun 62) — + `spatial_layers_sub`/cache tuiles overlay (auto-invalidés par le bump de run).
- `arcep_immeubles` (2026_T2).
- `rnic_coproprietes` (re-sync ; 974 inchangé — facultatif).
- `data_sources` (millésimes id 1, 16, 74, 96, 100, 126).

**Sortie du run q_v18 (produite par le run, à expédier avec) :**
- `score_labuse`, `parcel_residuel_*`, `cascade_results`, `dryrun_parcel_evaluations` (label q_v18), `parcel_couche_intersection` (reconstruit par le run), `mvt_parcels` + tuiles (`build-mvt`).

**Code (via git, déploiement normal) :**
- `ingestion/arcep_fibre.py` (MILLESIME T2), `api/app.py` (fiche disparue) — commit `60d41c93` ; + le code des prérequis (exclusion run, connecteurs 28/46, front) à committer avant déploiement.

**Geste de bascule** (`served_run.txt` → q_v18, purge caches) = décision Vic, hors ce mandat.

---

## 5. Exécution du run q_v18 — contraintes DÉCOUVERTES (à lire avant de lancer)

### 5.1 Exclusion des disparues — FAIT & testé

Les parcelles `cadastre_disparue_le` sont **marquées, pas supprimées** (la fiche de courtoisie doit rester accessible). Exclusion câblée au **point d'entrée unique** `_parcel_ids` (cli) → tout run/export les écarte (testé : île 434 582 → **433 229**, −1 353), + omnibox `/parcels/search` (testé) + tuiles `mvt_parcels`. Fiche de courtoisie back OK (testée). **Rendu front du bandeau = RESTE À FAIRE** (api.ts + composant fiche).

### 5.2 ⛔ Landmine 1 — `ingest-island` PURGE `parcels`

`run_all.purge_commune` fait `DELETE FROM parcels WHERE commune` à chaque commune ingérée (vérifié `run_all.py:64`). **Lancer `ingest-island` (même sans `--force`, dès qu'une commune n'est pas « ok ») détruirait les 1 353 marques disparues + les liens de remplacement + ré-ingérerait le cadastre à plat.** → **q_v18 NE DOIT PAS passer par `ingest-island`.**

### 5.3 ⚠ Landmine 2 — re-jouer la cascade sans purger `parcels`

Les sources à impact run 28/46/10 + les 2 919 nouvelles parcelles n'affectent les scores **que si la cascade est re-jouée** (`evaluate_commune`). Or le seul chemin CLI qui re-joue la cascade est `ingest-island` (→ landmine 1). Le run q_v16 a **contourné** en NE re-jouant PAS la cascade (étage 0 `q_v13_sources1` réutilisé, `run_qv16.py`). **Décision requise pour q_v18 :**
- **(a) Réutiliser la cascade** (comme q_v16) : simple et sûr, mais 28/46/10 **n'entrent pas** dans le score et les nouvelles parcelles n'ont pas de cascade (pas de résiduel). Convient si on ne veut QUE propager cadastre-géométrie + SITADEL via le résiduel/Signal.
- **(b) Re-jouer la cascade proprement** : nécessite un chemin « evaluate sans purge » (re-eval ciblée des communes/nouvelles parcelles) à écrire — **n'existe pas encore** en CLI. C'est le vrai préalable pour que 28/46/10 comptent.

### 5.4 Sources 28/46/10 — état réel

- **10 RPG** : le WFS `RPG.LATEST` sert déjà 2025 ; refresh **data-only** faisable (DELETE `kind='safer' subtype='rpg'` + boucle `ingest_rpg_agricole` par commune avec `_commune_bbox`/`_source_ids`, SANS toucher parcels). **Non exécuté** (dépend de 5.3 pour compter au score).
- **28 Érosion** : `EROSION_URL` figée sur le fichier **2018** ; l'URL du millésime **2026** n'est pas un simple échange d'année (patterns 2023/2024/2026 → 404) — **à récupérer sur** `geolittoral.developpement-durable.gouv.fr/...a1434.html` (scraping de la page). Puis data-only comme RPG. **Non fait** (découverte d'URL requise).
- **46 Classement sonore** : la couche ArcGIS Cartagène `_V2` servie ≠ arrêtés **26/12/2024** (jeu data.gouv distinct) → **changement de source + parseur**. `ingest-bruit-route` purge/réinsère `kind='bruit_route'` (OK, hors parcels) mais sur l'ancienne source. **Non fait** (source/parseur à adapter).

### 5.5 Séquence q_v18 proposée (SÛRE vis-à-vis du cadastre)

> Toutes les commandes : `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=/Users/openclaw/Desktop/labuse-sources/src /Users/openclaw/Desktop/labuse/.venv/bin/python -m labuse.cli …` (venv du dépôt principal + PYTHONPATH worktree + `LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@/labuse?host=/tmp`). **Jamais `ingest-island`.**

**Variante (a) — propagation cadastre-géométrie + SITADEL, cascade réutilisée (prête, aucun préalable code) :**
```
# 0. (optionnel) refresh RPG data-only si décidé — script à écrire (cf 5.4)
# 1. RÉSIDUEL ÎLE → nouveau run q_v18 (exclut déjà les disparues via _parcel_ids)
labuse compute-residuel --ile --new-run q_v18 --assiette-clippee
# 2. P-RUN (Signal p_v2) — mirror run_qv16.py : refresh cache résiduel + score-v2
#    recette q_v15, étage0 q_v13_sources1 ; adapter scripts/audit/scoring/run_qv16.py → run_qv18.py (RUN_ID='q_v18')
python scripts/audit/scoring/run_qv18.py           # (copie de run_qv16.py, label q_v18)
# 3. SCORING LABUSE
labuse score-labuse --run q_v18 --cascade-label q_v13_sources1 --signal-run q_v18
# 4. TUILES (exclut les disparues)
labuse build-mvt --label q_v18
```
**Variante (b)** = idem + un chemin « re-eval cascade sans purge » à écrire d'abord (pour que 28/46/10 + nouvelles parcelles comptent) → **préalable code non livré**.

> ⚠ `score-v2`/`run_qv18.py` **REFUSE un run_id déjà présent** : purger `q_v18` de `p_score_v2_runs`/`parcel_p_score_v2`/`score_labuse` avant (copier `purge_qv16.py` → `purge_qv18.py`).
> La bascule `served_run.txt` → q_v18 reste TON geste.

### 5.6 Reste à livrer (code, AVANT q_v18 selon la variante choisie)

1. **Front** : rendu du bandeau « parcelle disparue — remplacée par […] » (api.ts `getFiche` tolère `cadastre_disparue` + composant fiche).
2. **Variante (b)** : chemin « re-eval cascade sans purge » + refresh data-only 28/46/10 (10 prêt à coder, 28/46 = source à récupérer).
3. `run_qv18.py`/`purge_qv18.py` (copies paramétrées de run_qv16/purge_qv16).

---

## 4. Ménage / état laissé

- Sauvegardes : `~/labuse-backups/sources-maj-1/` (parcels-AVANT-CADASTRE 201 Mo, + 1 dump par table injectée).
- Tables de travail en base : `_cad_sm1_staging` (181 Mo), `_cad_sm1_nouvelles/geommodif/disparues` — **gardées** pour préparer q_v18 (exclusion + ingestion 28/10 ciblées), **droppables** après le run.
- Aucune API/navigateur lancé par CC ; worktree propre hors ce rapport ; `served_manifest.json` du dépôt principal (run_seq 13→14) **non touché** par ce mandat.
- Branche `fix/sources-maj-1` NON mergée, NON poussée.
