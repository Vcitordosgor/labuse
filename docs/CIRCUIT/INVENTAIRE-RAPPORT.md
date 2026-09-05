# CIRCUIT-0 — Rapport d'inventaire de la plomberie

| en-tête | valeur | preuve |
|---|---|---|
| commit de départ | `b222d00f` (main), mandat commité en `d04b4960` | `git log --oneline -1` |
| run servi | `q_v11_m137` | `config/served_run.txt` ligne 1 (constante unique, lue par `runs.current()` — `src/labuse/runs.py:49-61`) |
| base utilisée | locale, `postgresql:///labuse` (user openclaw), 242 tables | `psql -l` ; `SELECT count(*) FROM information_schema.tables WHERE table_schema='public'` → 242 |
| date | 05/09/2026 | — |

## Le tableau des compteurs (sortie de `scripts/inventaire/compte_rapport.py`, jamais tapé à la main)

| compteur | valeur |
|---|---|
| réservoirs : total / job sur clic / cron mensuel / dépôt manuel / en direct / absents | 79 / 3 / 4 / 5 / 4 / 11 (one_shot 52 ; « dérivés » requalifiés en pompes, Q1.2) |
| réservoirs surveillés / non / sans cadence / avec URL producteur | 45 / 34 / 71 / 75 |
| moteurs / versionnés par run / live | 21 / 7 / 14 |
| runs en base / servi / morts / tables de run en retard encore lues | 8 (p_score_v2_runs) / 1 (q_v11_m137) / 6 (q_v8×5 + q_v10) + 1 candidat (q_v12) / 2 (division_or_candidates q_v10 ; dvf_prix_sortie_neuf lu par score_e) |
| jobs / qui touchent l'eau / avec trace en base cohérente | 32 (19 wrapper + 13 legacy) / 20 / 21 |
| robinets : total, par catégorie | 122 — admin 9 · copilote 10 · couche 16 · crm 2 · fiche 28 · fond 10 · notification 5 · outil 28 · page_client 5 · pdf 6 · projets 2 · veille 1 |
| chiffres : lignes / ids distincts / moteur / sql_propre / front / passe_plat / constante / avec tampon | 139 / 88 / 64 / 54 / 2 / 16 / 3 / 58 |
| fuites candidates / mesurées / avec écart ≠ 0 | 33 / 49 / 46 |
| chiffres en eau ancienne aujourd'hui | 6 familles |
| lignes DOUTE (tous CSV) | 81 |

Détail DOUTE par fichier : reservoirs 19 · moteurs 1 · jobs 32 · robinets 2 · chiffres 1 · eau_ancienne 1 · agents_fiches 25.

---

## Lot 1 — Les réservoirs

Livrable : `docs/CIRCUIT/inventaire/reservoirs.csv` (79 lignes : 77 sources de `data_sources` + 2 voulues-absentes ECLN et LOVAC), généré par `scripts/inventaire/extrait_reservoirs.py` (SELECT seuls + surcouche prouvée).

### La source de vérité, et pourquoi Vic voit trois chiffres différents

- **La liste des sources = la table `data_sources`** (77 lignes au 05/09/2026). Elle est ensemencée et mise à jour par upsert idempotent depuis le catalogue statique `src/labuse/ingestion/seed_sources.py` (77 entrées, `ON CONFLICT (name) DO UPDATE`) — c'est le seul canal d'ajout. La sentinelle vit dans `source_veille` (49 lignes, FK vers `data_sources`, `src/labuse/models.py`), les métadonnées de fraîcheur dans les colonnes `source_millesime`/`source_horizon_at`/`source_cadence` remplies par `src/labuse/ingestion/fraicheur.py:299-331`.
- **La vitrine canonique** filtre par `WHERE_AFFICHEES` (`src/labuse/sources_catalog.py:36-41` : statut `connecte`∪`manuel`, exclut `DOUBLON`/`RETIRÉ`/`DORMANT`/`affichage_desactive`) → **66 sources affichées** (SQL exécuté le 05/09 : 66). Les endpoints `/sources` (client, `src/labuse/api/app.py:919-924`) et `/admin/sources` (`src/labuse/api/dashboard.py:891-894`, prédicat Python `est_affichee`) la respectent.
- **Le « 77 dont 49 » vu par Vic vient de l'écran Flux** : `src/labuse/flux.py:198` compte `SELECT count(*) FROM data_sources` **sans** `WHERE_AFFICHEES` (→ 77) et `flux.py:199-201` compte les lignes `source_veille` actives à vraie sonde (→ 49). Écart de 11 avec la vitrine : ids 2, 65, 67 (DOUBLON), 49, 50 (RETIRÉ), 11, 12, 14 (hubs), 80, 89, 95 (a_faire). Chaque ligne du CSV hors vitrine porte la mention dans sa colonne `preuve`.
- **Écart secondaire** : `dashboard.py:893` appelle `est_affichee(name, technical_notes, status)` **sans passer `affichage_desactive`** — une source désactivée au dashboard resterait listée à l'écran Catalogue admin (aujourd'hui sans effet : 0 ligne à `affichage_desactive=true`, `SELECT` du 05/09).
- **Sentinelle vs vitrine** : 49 lignes `source_veille` = 45 vraies sondes (`api`/`page`/`entete`/`temoin`) + 4 rappels manuels (`SELECT` du 05/09) ; parmi les 66 affichées, 41 portent une vraie sonde. Le « 49 sous veille » de l'écran Flux mélange donc sondes et compte brut.
- **Les moteurs ne lisent pas `data_sources`** pour calculer (la cascade lit `spatial_layers` et les tables de données) ; seuls l'orchestration et l'affichage la lisent (`flux.py:198,251`, `radar.py:165`, `cascade/context.py:525` pour le rattachement `parcel_source_results`, `bascule_gardes.py:174,542`). Page Sources, sentinelle et moteurs parlent de la même table, mais **pas du même sous-ensemble ni du même compte**.

### Q1.1 — Les quatre crons mensuels

| cron | quoi exactement | preuve |
|---|---|---|
| `ingest-sitadel` (le 10, 04:30 Réunion) | **incrémental par date** : delta depuis max(date)−3 mois de recouvrement, upsert `permit_id`, jamais de saut de communes ; trace `ingestion_runs` (statuts running/ok/error) ; **enchaîne veille foncière + run candidat** (`rapport_candidat`, bascule manuelle) | `src/labuse/ingestion/permits_sdes.py:177-236,302-324` ; `src/labuse/jobs_impl.py:360-370` |
| `ingest-dpe` (le 12, 04:00) | **saute toute commune déjà peuplée** (sans `--force`) : `SELECT count(*) FROM dpe_records WHERE code_insee=:c` → skip ; upsert `numero_dpe` sinon. **La trace ment par omission** : `_touch_source()` écrit `data_sources.last_sync_at` même quand 0 commune a été traitée (`dpe.py:243`, aucun `if` autour) → `/healthz/crons` peut dire « ok » sans qu'aucune donnée n'ait bougé | `src/labuse/cli.py` (`ingest_dpe_cmd`, boucle de saut) ; `src/labuse/ingestion/dpe.py:217-245,306-308` |
| `ingest-sirene` (le 7, 04:00) | **rafraîchissement complet** : `DELETE FROM sirene_etablissements` puis réinsertion (jointure DuckDB géo INSEE × Stock, filtre 974 actifs) | `src/labuse/ingestion/sirene_etablissements.py:143,127-128,171-173` |
| `sync-gpu` (le 15, 04:00) | **complet par commune** : purge `spatial_layers kind='sup'` de la commune puis réinsertion, idempotent, une commune en échec n'arrête pas les autres ; enchaîne `evaluer_toutes()` (veille) | `src/labuse/ingestion/sup_gpu.py:55-56,67-68` ; `src/labuse/jobs_impl.py:385-389` |

La trace en base : seul Sitadel écrit `ingestion_runs` ; les autres n'ont que `data_sources.last_sync_at`. `ingestion_runs.data_source_id` est **NULL sur les 48 lignes** (`SELECT` du 05/09) — la table ne ventile pas par source.

### Q1.2 — Dérivées : réservoir ou pompe ?

13 modules d'ingestion transforment des données **déjà en base** au lieu d'un amont producteur : `dispositifs.py` (QPV+textes→zonages fiscaux), `division_or.py`, `ortho_pente.py`, `ortho_piscines.py`, `ortho_pv.py` (mort, purgé), `pv_detection.py`, `score_e.py`, `score_v_fetch.py`, `signals.py`, `solaire.py` (PVGIS+bâti), `surface_d.py`, `vefa_neuf.py` (DVF→couche), `vegetation.py`. **Tranché : ce sont des pompes**, pas des réservoirs — leurs amonts sont les réservoirs (BD ORTHO, DVF, textes) et leurs sorties des tables de résultats. Deux cas hybrides restent au catalogue comme réservoirs parce que le producteur y est réel : `pvgis` (l'API de calcul est l'amont du builder solaire) et `cosia` (couverture IA de l'IGN, produite hors LABUSE). Les détections piscine/végétation figurent au Lot 2 comme moteurs, avec `bd_ortho` en entrée.

### Q1.3 — Plusieurs millésimes en base

- **DGFiP parcelles PM** : panel 2019→2025 dans `pm_proprietaires_millesimes` (situation au 1ᵉʳ janvier), le servi (`parcelle_personne_morale`, millésime 2025) n'est jamais écrasé — timeline versionné∪servi (`src/labuse/proprietaire_historique.py`, mandat RATTRAPAGE-KF-2).
- **DVF** : géo-DVF 2021-2025 + archives 2014-2020 (millésime en base `data_sources.source_millesime` id 5) ; les moteurs lisent des fenêtres temporelles (36 mois glissants pour VEFA, `vefa_neuf.py:4`), pas un millésime pointé.
- **Scoring** : 9 runs coexistent dans `parcel_p_score_v2` (q_v2_demo, q_v8×5, q_v10, q_v11, q_v12 — `SELECT run_id, count(*)` du 05/09) ; l'app choisit par la constante unique `config/served_run.txt` (Lot 2).

### Q1.4 — « Injecter cette version »

Front `frontend/src/components/admin/Sources.tsx:195-205` → `POST /admin/sources/{id}/veille/injecter` (`dashboard.py:1186-1225`) → `_lancer_ingestion(nom)` (`dashboard.py:1126-1149`) qui lit `config/sources_ingestion.yaml:7-23`. **Réellement branché pour 5 sources seulement** : SITADEL, BODACC, DVF, DPE, BAN. Toute autre source n'affiche pas le bouton. Trace : `source_veille.injection_lancee_at` + `injection_vu` (`dashboard.py:1209-1211`), job détaché (`subprocess.Popen`, log `/tmp/labuse-relance-<label>.log`).

### Q1.5 — De 64 à 77 depuis le 01/09/2026

Les deux chiffres ne mesurent pas la même chose : 64 (SENTINELLE-2, 01/09) ≈ la **vitrine** d'alors ; 77 (Vic, 05/09) = le **compte brut** de l'écran Flux. Évolutions réelles depuis le 01/09 (`data_sources.created_at`) :

| id | source | créée le | mandat d'origine | preuve |
|---|---|---|---|---|
| 89 | BDNB | 03/09 | SCORING-3 L3 (commit `1be67c8c`, dans main) — constat : 974 absent de l'amont | `git log` ; technical_notes id 89 |
| 93 | EDF Réunion — lignes HTA | 05/09 | RETOURS-13 Lot 1 (commit `44443736`) — **branche `fix/retours-12` NON mergée** ; la ligne existe en base locale, pas dans le seed de main | `git branch --contains 44443736` → `fix/retours-12` seule ; grep seed_sources.py (main) : absent |
| 94 | TCSP — voies bus (OSM) | 05/09 | RETOURS-13 Lot 1 (idem, non mergé) | idem |
| 95 | Réunion Express (CNDP) | 05/09 | RETOURS-13 Lot 1 (idem), status `a_faire` | idem |

Créées fin août (avant le comptage du 01/09) : 84 Radar (28/08), 86 SIRENE établissements (28/08), 87 MOBPRO (28/08), 88 Trafic RN (29/08) — mandat ZONE-DONNÉES/RADAR. Aucun renommage ni découpage détecté sur la période (`updated_at` scanné). **La base locale est en avance sur main pour 3 sources (93-95)** — à retrouver après merge de `fix/retours-12`.

### Compteurs (sortie de `scripts/inventaire/extrait_reservoirs.py`, comptés sur le CSV livré)

| compteur | valeur |
|---|---|
| lignes totales | 79 (77 en base + 2 absentes ECLN/LOVAC) |
| par mode | absente 11 · cron_mensuel 4 · depot_manuel 5 · en_direct 4 · job_sur_clic 3 · one_shot 52 |
| surveillées (vraie sonde) / non | 45 / 34 |
| sans cadence déclarée | 71 |
| absentes | 11 |
| avec URL producteur connue | 75 |
| lignes portant DOUTE | 19 |

**Hors énumération du mandat** : la valeur `en_direct` a dû être ajoutée (source interrogée à la requête, aucun réservoir en base : API Carto GPU, RPG proxy, recherche-entreprises ×2). L'énum du futur registre devra la prévoir.

### Point d'étape Lot 1

- Compteurs : ci-dessus, produits par le script.
- Lignes `DOUTE` : 19 (essentiellement `tables_servies`/`job_ingestion` de couches ingérées par `layers_ingest.py` sans CLI dédiée : RGE ALTI, RPG, DEAL WMS, INPN espaces, SPANC, SRU, parkings APER, Filosofi, LiDAR MNH, RGE ALTI 5 m + licences « à confirmer »).
- A bloqué : `ingestion_runs` non ventilée par source (data_source_id NULL) → `date_injection` = `data_sources.last_sync_at`, vide pour les one_shot anciens ; l'état JSON du wrapper de jobs n'existe pas en local (`.local/state` absent) → « derniers statuts » des jobs traités au Lot 3 comme DOUTE local.

---

## Lot 2 — La pompe : moteurs et runs

Livrable : `docs/CIRCUIT/inventaire/moteurs.csv` (21 moteurs), généré par `scripts/inventaire/extrait_moteurs.py`. Compteurs (sortie du script) : **21 moteurs, 7 versionnés par run, 14 live, 1 DOUTE** (entrées de `loyers.py`).

### Q2.1 — Le run servi : la constante unique est-elle le SEUL pointeur ?

**Non — quatre pointeurs coexistent**, trois alignés, un en retard :

| pointeur | valeur au 05/09 | qui l'écrit | qui le lit | aligné ? |
|---|---|---|---|---|
| `config/served_run.txt` (constante unique) | `q_v11_m137` | `golden_ops.promote()` (`golden_ops.py:120-134`) | `runs.current()` relu à la requête, cache 3 s (`src/labuse/runs.py:49-61`) — API, tuiles, gardes | référence |
| `config/run_precedent.txt` | suit la bascule | `bascule_flux.basculer()` (`bascule_flux.py:221-223`) | `runs.precedent()` (`runs.py:64-78`) — cible du retour arrière | oui |
| `mvt_meta key='run_label'` | `q_v11_m137` | build-mvt | tuiles (invalidation cache `api/tiles.py`) | **oui** (SELECT 05/09) |
| `residuel_runs.is_served` (run_seq) | run_seq 2 « m135-run2-ile » | `residuel_runs.set_served()` (`residuel_runs.py:96-103`) | vue `parcel_residuel` | **pointeur séparé assumé** (nomenclature propre, garde anti-écriture `residuel_runs.py:87-93`) |
| `division_or_candidates.run_label` | `q_v10_m129` | CLI division-or | fiche + filtre **sans filtre de run** (`app.py:1573,2692-2696`) | **NON — en retard d'un run**, toléré comme « workflow de revue par commune » (`bascule_gardes.py:663-665`) |

Tables servies run-scopées alignées sur `q_v11_m137` (SELECT du 05/09) : `score_e` (285 781), `parcel_flags` (2 208 373), `parcel_renouvellement` (67 260).

### Q2.2 — Les runs en base

`p_score_v2_runs` (SELECT du 05/09) :

| run | date | contenu | statut |
|---|---|---|---|
| q_v8_calibre_pre_pond / _pre_regle / _pre_m28 / _pre_m39 | 04-05/08 | 431 663 scores chacun | morts (lignée de calibrage) |
| q_v8_calibre | 07/08 | 431 663 | mort (ancien servi) |
| q_v10_m129 | 19/08 | 431 663 | mort — **mais `division_or_candidates` y est resté** |
| q_v11_m137 | 27/08 | 431 663 | **SERVI** |
| q_v12 | 03/09 | 431 663 | candidat (basculé puis retour arrière le 04/09, `run_bascule_journal`) |

- `parcel_p_score_v2` garde **9 runs × ~431 663 lignes** (dont `q_v2_demo`, 8 lignes) ; la purge existe (`labuse purge-runs-morts --apply`, `cli.py:698-739`, garde la lignée `CHAINE_GESTES` + servi + précédent + démo + exceptions) mais n'a pas été passée.
- `dryrun_parcel_evaluations` : 6 run_labels dont 2 mini-runs de recette `q_v12_20260903_*` (2 000 lignes).
- **Tables de run encore lues alors que non servies** : `division_or_candidates` (q_v10_m129, lu par la fiche `app.py:2696`, le filtre `app.py:1573`, `division_review.py:38`, `verdict_servi.py:40`). Tables legacy `*_pre_v8`, `parcel_residuel_base_legacy`, `parcel_au_statut_pre_m32`, `m6_snapshot_*` : présentes en base, aucun lecteur trouvé côté API (grep) — mortes non lues, jamais supprimées (règle 7).

### Q2.3 — « Calculer » aujourd'hui

- **`labuse flux-run --label L --recette (m36|q_v12)`** (`cli.py:604-667`) — le geste complet : cascade + scoring → `dryrun_*` + `parcel_p_score_v2` sous le label candidat. Lancé détaché par la page admin (`POST /admin/flux/run/lancer`, `dashboard.py:1309-1362`, un seul run actif à la fois, progression `run_progress` JSON).
- **Candidat automatique après Sitadel** : réel — `jobs_impl.py:360-370` enchaîne ingestion → veille foncière → `golden_ops.rapport_candidat()` (mail de comparaison, dry-run aware). La bascule reste manuelle.
- Recalculs partiels : `labuse score-v2` (scoring seul), `labuse dryrun-evaluate` (cascade seule), résiduel par `residuel_runs` (geste séparé), `build-mvt` (tables servies + tuiles). Durées : non documentées dans le code → DOUTE (le mandat demandait mesurée ou estimée ; aucun job n'a été lancé, règle « lecture seule »).

### Q2.4 — « Basculer » et « Revenir en arrière »

`POST /admin/flux/bascule` (`dashboard.py:1401-1445`) → `bascule_flux.basculer()` :
1. refuse un run incomplet (`_run_complet`, `bascule_flux.py:85`) ; 2. `golden_ops.promote()` réécrit `served_run.txt` (validation d'existence en base) ; 3. réécrit `run_precedent.txt` ; 4. `runs.invalidate()` (effet immédiat sans redémarrage) ; 5. purge les caches A6 (`purger_caches_run`, `bascule_flux.py:30-61`) ; 6. garde de cohérence immédiate (`coherence_flux.verifier`) ; 7. **journalise** dans `run_bascule_journal` (ts, ancien, nouveau, par, sens, caches_purges, coherence) + notification système (`event_log`, dedup `bascule:<run>:<minute>`) ; 8. lance détaché `build-mvt` pour reconstruire les tables run-scopées (pas en ligne : deadlock constaté, commentaire `dashboard.py:1428-1432`).
**Atomicité** : la promotion du pointeur est un write de fichier unique ; mais les tables servies (`parcel_flags`…) **montent en différé** — pendant la reconstruction, la garde est à 5/6 (assumé, commenté). **Revenir** : même endpoint avec `run = précédent` → `sens='arriere'` (`bascule_flux.py:227`) ; exécuté en vrai le 04/09 (`run_bascule_journal` : q_v12 → q_v11_m137 arriere).

### Q2.5 — Page Données › Mise à jour (DONNEES-2)

**Implémentée et mergée** (`frontend/src/components/admin/MiseAJour.tsx` + `Flux.tsx` + `Donnees.tsx`, présents sur main ; tests `MiseAJour.test.tsx`, `Flux.circuit.test.tsx`).

| étape | endpoint | commande | sync ? | event_log |
|---|---|---|---|---|
| Injecter | `POST /admin/sources/{id}/veille/injecter` (`dashboard.py:1186-1225`) | `config/sources_ingestion.yaml` (5 sources) via `subprocess.Popen` | asynchrone détachée, log `/tmp/labuse-relance-<label>.log` | oui — notification admin (`dashboard.py:1213-1222`) ; trace `source_veille.injection_lancee_at/injection_vu` |
| Calculer | `POST /admin/flux/run/lancer` (`dashboard.py:1309-1362`) | `labuse flux-run --label … --recette …` détaché | asynchrone (pid + progression `run_progress`) | oui — notification dedup `flux-run:<label>` |
| Basculer | `POST /admin/flux/bascule` (`dashboard.py:1401-1445`) | `bascule_flux.basculer()` en ligne + `build-mvt` détaché | bascule synchrone, reconstruction asynchrone | oui — `run_bascule_journal` (qui/quand/de/vers/sens) + notification |

### Q2.6 — Chiffres liés au run vs lus en direct (définition d'« eau ancienne » par famille)

- **Ne changent qu'à la bascule** (run-scopés) : tiers/score P (`parcel_p_score_v2`), verdicts cascade (`dryrun_*`), drapeaux (`parcel_flags`), renouvellement, score E, résiduel (pointeur propre), divisibilité (en retard), tuiles carte (mvt). Leur « eau ancienne » = réservoir réinjecté sans recalcul+bascule.
- **Changent dès l'injection** (live) : prix de secteur et bilan (DVF), étude de zone (SIRENE/Filosofi/DVF/trafic), marché Radar et cycle, DPE affiché, contexte fiche (risques, mairies), destinations PLU, taxe, timeline PM, solaire (millésime gelé — change au re-build, pas à l'injection). Leur « eau ancienne » = cache non purgé (ex. `zone_isochrone_cache`, `fiche-commune-cache`) ou millésime gelé.

### Point d'étape Lot 2

- Compteurs : 21 moteurs (7 versionnés / 14 live), produits par le script.
- Lignes `DOUTE` : 1 (entrées de `loyers.py`) + durées de calcul non documentées (Q2.3).
- A bloqué : rien — mais la mesure des durées exigerait de lancer un run (interdit).

---

## Lot 3 — Les horloges

Livrables : `docs/CIRCUIT/inventaire/jobs.csv` (32 lignes : 19 jobs du wrapper + 13 lignes de crons hors wrapper) et `docs/CIRCUIT/inventaire/source_veille.csv` (49 lignes), générés par `scripts/inventaire/extrait_jobs.py`. Compteurs (script) : **20 touchent l'eau / 12 non ; 3 traces en base incohérentes ou partielles**.

### Le constat qui change la lecture : DEUX jeux de crons coexistent dans le dépôt

- **Le wrapper** (`scripts/jobs/run-job.sh` → `labuse jobs exec <nom>`) : registre de **19 jobs** (`src/labuse/jobs.py:263-318`), **16 posés** dans `deploy/cron.d-labuse` (écrit en UTC, heure Réunion en commentaire). 3 enregistrés mais **non posés** : `copilote-purge`, `ingest-bdnb`, `sante-endpoints`.
- **Les anciens crons** `deploy/cron.d/*` (11 fichiers, 13 lignes actives, heures RÉUNION — converties avant pose, `docs/audit-2026-08/VPS/JOURNAL.md:139-140`) : bodacc QUOTIDIEN, dpe HEBDO mardi, dvf HEBDO mercredi, sitadel QUOTIDIEN delta, ban mensuel le 5, abuse-scan, notifications (évaluer-suivis/veilles + digest), radar-sources lundi, sessions, backup/maintenance shell.
- **Lequel des deux jeux est posé sur le VPS aujourd'hui : DOUTE** (indécidable en local ; le JOURNAL VPS du go-live documente la pose des 13 anciens, `JOURNAL.md:140`, le mandat CRON-1/2 a versionné le wrapper ensuite). Le mandat attendait « 13 jobs du wrapper » : le compte réel est 19 enregistrés / 16 posés côté wrapper, + 13 lignes legacy.
- Conséquence directe : les « contradictions healthz » s'expliquent — `/healthz/crons` (`src/labuse/api/ops.py:23-41`) attend **bodacc à 2 j** et **dpe à 10 j (note « hebdo »)**, c'est-à-dire les cadences des ANCIENS crons, pas celles du wrapper (dpe mensuel le 12, bodacc absent du wrapper).

### Q3.1 — `source_veille`

Schéma complet : 22 colonnes (`\d source_veille` du 05/09 — id, source_id, url_version, methode, selecteur, cadence_heures, dernier_passage_at, dernier_vu, dernier_statut, dernier_message, dernier_entete, actif, created_at, updated_at, dernier_notifie_vu, echecs_consecutifs, injection_lancee_at, injection_vu, cadence_attendue_jours, convention_echeance, mail_alerte, url_temoin_2). Dump : `inventaire/source_veille.csv` (49 lignes — méthodes : api 34, temoin 5, entete 5, rappel 4, page 1).

### Q3.2 — Notifications de la sentinelle

Détection (`sentinelle.py:314-330`) : une sonde `nouvelle_version` dont `dernier_vu ≠ dernier_notifie_vu` entre au digest du passage. **Cloche** : UN digest quotidien admin (`_emettre_digest`, `sentinelle.py:675-710`, kind `systeme`, lien `/sources`), dédup par signature des source_ids. **Mail** : seulement si la notif est neuve ET qu'une source annoncée porte `mail_alerte=true` (`_alerter_mail`, `sentinelle.py:713-731`). **Dédup permanente** : `dernier_notifie_vu` (un millésime déjà annoncé ne re-sonne jamais, `sentinelle.py:319-320`). Le morning brief n'est pas alimenté par la sentinelle (retrait des chiffres de surface au brief : mandat RECETTE-2 D).

### Q3.3 — SENTINELLE-3 : exécuté et mergé

Preuves dans le code de main : `sentinelle.py:496-498` (« second passage 2026-09-01, appels réels »), rappels manuels Y4 (`sentinelle.py:529-540`), et `source_veille.created_at` = **46 lignes créées le 01/09** (le passage a re-semé la table), +1 le 03/09 (BDNB, api), +2 le 05/09 (EDF HTA, Réunion Express — entete). Le passage 35→49 = +6 sources récupérées par sondes réelles (DEAL PPR/WMS, Région ODS, Géorisques cavités/mvt/ssp — `sentinelle.py:497-498`), +4 rappels manuels Y4 (Radar, SPANC, Fichiers fonciers, Office de l'eau — `sentinelle.py:535-540`), + créations postérieures (BDNB, EDF HTA, Réunion Express) ; le détail méthode par méthode est dans `source_veille.csv` (colonne methode). La ventilation exacte de chacune des 14 depuis SENTINELLE-2 : DOUTE partiel (les `created_at` d'avant le re-semis du 01/09 ont été écrasés).

### Q3.4 — Candidat automatique après Sitadel : OUI

`src/labuse/jobs_impl.py:360-370` — fin d'ingestion réussie → `veilles.evaluer_toutes()` puis `golden_ops.rapport_candidat(dry_run=…)` (comparaison candidat vs servi, mail). Ne touche jamais le run servi ; la bascule reste `labuse golden promote` / bouton admin.

### Q3.5 — Contradictions connues : toujours là

1. **DPE** : `_touch_source()` écrit `last_sync_at` même à 0 commune traitée (`dpe.py:243`) → `/healthz/crons` peut afficher « ok » sans donnée nouvelle. Toujours présent.
2. **DPE hebdo vs mensuel** : healthz note « hebdo » (`ops.py:39-40`) = cadence de l'ancien cron (`deploy/cron.d/dpe`, mardi) ; le wrapper le pose mensuel le 12. Toujours présent.
3. **BODACC** : attendu à 2 j par healthz, absent du wrapper — seul l'ancien cron quotidien le couvre. Toujours présent.
4. **Radar** : healthz lit `etat_radar` (`ops.py:111-122`) tandis que l'ancien cron `radar-sources` (lundi) écrit son propre log — cohérence dépendante du jeu de crons posé (DOUTE VPS).

### Point d'étape Lot 3

- Compteurs : 32 lignes jobs (19+13), 20 touchent l'eau, 3 traces incohérentes/partielles ; source_veille 49 lignes.
- Lignes `DOUTE` : 15 (les 19 `dernier_statut` wrapper sont un seul et même DOUTE local — état JSON absent ; 13 poses VPS legacy indécidables ; 1 table de trace abuse-scan ; ventilation fine 35→49).
- A bloqué : l'état JSON du wrapper et le crontab réellement posé ne sont lisibles que sur le VPS — hors périmètre local, aucune connexion tentée (lecture seule).

---

## Lot 4 — Les robinets

Livrable : `docs/CIRCUIT/inventaire/robinets.csv` (**122 robinets**), généré par `scripts/inventaire/extrait_robinets.py`. La colonne `nb_chiffres` est recalculée depuis `chiffres.csv` au Lot 5 (0 à ce stade — le script est relancé après).

### Compteurs par catégorie (sortie du script)

| catégorie | n | | catégorie | n |
|---|---|---|---|---|
| fond | 10 | | veille | 1 |
| couche | 16 | | projets | 2 |
| outil | 28 | | crm | 2 |
| fiche | 28 | | notification | 5 |
| copilote | 10 | | pdf | 6 |
| page_client | 5 | | admin | 9 |
| **total** | | | | **122** |

### Écarts au périmètre attendu du mandat (constatés, avec preuve)

- **« Les 5 fonds de carte »** : il y en a **10** — 8 fonds raster IGN (Plan IGN v2 + « Actuelle · Ortho Express 2025 » + 6 millésimes historiques 1950→2023, registre unique `frontend/src/components/map/basemaps.ts:33-45`) et 2 modes canvas (Sombre/Clair, `MapView.tsx:28-29`).
- **« Le Copilote : ses 6 outils SQL »** : le registre v2 en compte **10** (`src/labuse/copilote_v2/outils.py` : compter_parcelles:130, parcelles_par_entreprise:279, fiche_parcelle:333, stats_commune:350, delais_instruction:370, marche:395, recherche_web:474, compter_piscines:529, compter_permis:550, destination_zone:573).
- **Fiche commune : 15 cartes** — confirmé exactement (libellés `ContextePanel.tsx:327-569`, endpoint `/communes/{c}/contexte`, producteur `api/fiche_commune.py:build`).
- Deux robinets restent `DOUTE` sur leur composant front exact : la section Solaire de la fiche parcelle et la « fiche soleil » (photo du toit + rosace, RETOURS-12 O7) — le back (`parcel_solar`, `toiture_lidar`) est identifié, le fichier front pas encore pointé ligne à ligne.

### Ce que le tour des robinets confirme sur la plomberie

- Le producteur dominant des fiches parcelle est **un point unique** : `_q_v2_fiche()` (`src/labuse/api/app.py:3283`), servi par `/parcels/{idu}` (`app.py:4250`) — 8 des 10 sections de la fiche y puisent ; « Autour de cette parcelle » y ajoute `/parcels/{idu}/zone` (`app.py:4265`, moteur `zone.py`).
- La fiche commune est servie par `fiche_commune.py:build()` avec cache nocturne (`fiche-commune-cache`, 03:00) — ses chiffres partagés avec le comparateur passent par `comparable()` (`fiche_commune.py:16-58`), point à mesurer au Lot 5 (fuite RNU).
- Les mails Radar (Brevo ID 12/13) reçoivent leurs chiffres en **paramètres nommés** (`NB_BIENS`, `CARTES` HTML construit serveur — `pige/digests.py:278-313`) : aucun calcul dans le template.
- L'écran admin « Données › Circuit » est le robinet qui affiche le **77 brut** (`flux.py:198`, cf. Lot 1).

### Point d'étape Lot 4

- Compteurs : 122 robinets, ventilation ci-dessus, produits par le script.
- Lignes `DOUTE` : 2 (composants front Solaire fiche / fiche soleil).
- A bloqué : rien. `nb_chiffres` sera rempli au Lot 5 (dépendance assumée du mandat).

---

## Lot 5 — Les chiffres

Livrables : `chiffres.csv` (139 couples robinet×chiffre, 88 `chiffre_id` distincts — généré par `scripts/inventaire/extrait_chiffres.py`), `fuites_candidates.csv` (33, dérivées par groupby), `fuites_mesurees.csv` (49 lignes, 46 avec écart ≠ 0) et `eau_ancienne.csv` (6 lignes) — mesures par `scripts/inventaire/mesure_fuites.py` (SELECT seuls). `robinets.csv` a été régénéré avec `nb_chiffres` rempli.

**Couverture assumée** : 139 couples couvrent les chiffres porteurs de 55 robinets ; 67 robinets restent à 0 ligne (fonds de carte sans nombre, couches de simple présence, sous-entrées redondantes, écrans admin secondaires). Le mandat attendait « plusieurs centaines de lignes » : l'estimation du reste à déclarer est au Lot 8.

### Compteurs (sortie des scripts)

| compteur | valeur |
|---|---|
| lignes chiffres.csv / chiffre_id distincts | 139 / 88 |
| par calcul | moteur 64 · sql_propre 54 · passe_plat 16 · constante 3 · front 2 |
| avec tampon ≠ rien | 58 |
| fuites candidates / mesurées / avec écart ≠ 0 | 33 / 49 / 46 |
| chiffres en eau ancienne | 6 familles |
| DOUTE (chiffres.csv) | 1 |

### Q5.1-5.2 — La fuite mandatée : « part RNU » de Saint-Paul

Aucune métrique littérale « part RNU » n'existe dans le code (grep exhaustif — seule Saint-Philippe est RNU, `config/rnu_communes.yaml`). Les valeurs vues par Vic correspondent aux **parts de zonage** servies par DEUX dénominateurs :

- chemin A — **part de SURFACE** : `_foncier_commune` (`app.py:1908-1955`), carte « Zonage » de la fiche commune ; le commentaire OUTILS-6 C1 y déclare l'intention (« les parts de parcelles ne représentent pas le territoire ») ;
- chemin B — **comptes de PARCELLES** par famille : `/zones-plu` (`app.py:2436`).

Mesuré sur Saint-Paul (les deux valeurs, cause `denominateur`) : **zone A = 35,8 % (surface) vs 17,8 % (parcelles)** ; **zone N = 47,2 % vs 6,8 %**. Le « 18 % vs 6 % » de Vic = les parts par parcelles de A et N (17,8 / 6,8). L'écran exact où chaque valeur lui est apparue reste `DOUTE` ; le chemin fidèle à l'intention est la **surface**. Mesure étendue aux 24 communes dans `fuites_mesurees.csv` (48 lignes A/N). S'y ajoutent : `n_sources` (66 vitrine vs 77 brut — cause `perimetre`, chemin fidèle WHERE_AFFICHEES) et `prix_neuf_vefa` (fuite historique 5 003 vs 4 730 €/m², corrigée pour comparateur/fiche/carte par RETOURS-11F M1, **mais le précalcul divergent `dvf_prix_sortie_neuf` est encore lu par score_e** — cause `table`).

### Q5.3 — Eau ancienne (mesurée, `eau_ancienne.csv`)

1. **DPE** (premier suspect confirmé) : base locale max(date_etablissement)=21/07, amont vu 02/09 ; mécanisme structurel — le cron saute les communes peuplées ET tamponne `last_sync_at` (volume prod ≠ local : DOUTE sur l'ampleur, pas sur le mécanisme).
2. **Divisibilité** : `division_or_candidates` sur q_v10_m129, lu sans filtre de run (1 run de retard, toléré).
3. **Solaire** : gel assumé et étiqueté (millésime en base).
4. **Fiche commune** : cache nocturne ≤ 24 h, tamponné (« compteurs précalculés le … »).
5. **Isochrones** : `zone_isochrone_cache` sans TTL (138 entrées) — géométrie figée à la 1re demande.
6. **score_e** : lit le précalcul neuf divergent (cf. ci-dessus).

### Q5.4 — Calculs côté navigateur (agent dédié, liste complète en annexe de l'agent)

**95 sites** examinés : **9 `calcul_metier`** (le nombre affiché n'existe pas côté serveur — dont `ContextePanel.tsx:526` « autres logés gratuitement » = 100−locataires−propriétaires, `constructibilite.tsx:137` charge foncière bornée, `ProspectionSolaire.tsx:325-326` kWc et MWh/an dérivés au front, `MarcheSecteurBlock.tsx:16` % propriétaires, `blocB.tsx:358` % ZAN, `ProjetsPanel.tsx:53` % décidées, `Licences.tsx:26` heures restantes), **17 dérivations légères** (max/min de fourchettes, différences, durées), **69 formatage seul**. « Zéro recalcul au front » n'est PAS tenu hors des 15 outils vérifiés. Deux lignes de `chiffres.csv` portent `calcul=front` (charge foncière calculette, n_vigilances) ; les kWc/MWh solaire s'y ajoutent comme candidats au registre.

### Q5.5 — Chiffres du Copilote

Les 9 outils SQL passent chacun par le **point de calcul unique** du robinet équivalent (facette canonique du filtre pour compter_parcelles — égalité verrouillée par test ; `patrimoine()`, `velocite()` avec réserve Sitadel citée mot à mot, `build_marche_commune()`, `_q_v2_fiche()` lu du run servi, `plu.destinations` même moteur que la fiche). `recherche_web` sort du verrou par construction (texte ≤ 2 phrases, marqué web, jamais Sourcé). **DOUTE** : aucune garde formelle n'empêche la surface `copilote-general` (réponse libre) d'énoncer un nombre hors outils — à trancher pour le registre.

### Q5.6 — Chiffres des PDF et des mails

- **Flash / Dossier parcelle** : `flash/data.py:collect_report_data` consomme les moteurs (verdict run servi, sector_price, moteur zone via `_zone` — aucune recopie, F2) ; TEMPLATE_VERSION 1.4.
- **Banquier** : `briques_pdf.py` + 11 étapes faisabilité ; la synthèse IA est contrainte `strict_numbers` (`banquier.py:87`).
- **Pré-dossier PC / Lettre de zonage** : passe-plat du zonage GPU servi + références datées.
- **Argumentaire** : faits chiffrés sourcés (correctif m143 `out.get('regime')` au passif).
- **Brevo 12/13** : chiffres en paramètres nommés (`NB_BIENS`, `CARTES` HTML serveur, chaque valeur échappée) — zéro calcul dans le template (contrainte Brevo sans `{% for %}`).

### Point d'étape Lot 5

- Compteurs ci-dessus (scripts). Ligne mandatée Saint-Paul : présente avec les deux valeurs et la cause.
- `DOUTE` : 1 dans chiffres.csv (entrées loyers) ; écran exact du constat Vic ; ampleur prod de l'eau ancienne DPE ; garde copilote-general.
- A bloqué : la mesure « deux chemins exécutés » n'était possible en local que pour zonage et n_sources (les autres candidates du groupby convergent en réalité vers la même fonction — notées candidates, pas mesurées comme fuites).

---

## Lot 6 — Le graphe

Livrables : `docs/CIRCUIT/inventaire/circuit.json` construit PAR SCRIPT depuis les CSV des lots 1/2/4/5 (`scripts/inventaire/construit_circuit.py`) et validé par `scripts/inventaire/valide_circuit.py` : **OK — 80 réservoirs (79 + pseudo `labuse_interne` pour les tables internes event_log/comptes/projets), 21 moteurs, 88 chiffres, 122 robinets ; 124 arêtes réservoir→chiffre + 139 chiffre→robinet ; 4 fuites ; compteurs = tailles des CSV.**

### Q6.1 — Impact par réservoir (« combien de produits récupèrent cette source »)

Top de la table (sortie du script, tri par robinets touchés) :

| réservoir | chiffres | robinets touchés |
|---|---|---|
| dvf | 13 | **19** (fiches parcelle/commune, comparateur, baromètre, Copilote, PDF Flash/banquier/argumentaire, couches VEFA/verdict…) |
| cadastre_api_carto | 12 | 14 |
| sitadel | 10 | 14 |
| gpu_plu_api_carto | 13 | 13 |
| cosia | 7 | 12 |
| bd_topo | 5 | 11 |
| filosofi_carreaux | 4 | 8 |
| radar_pige | 8 | 7 (dont les deux mails Brevo) |
| dgfip_parcelles_pm | 3 | 5 |
| sudocuh | 4 | 4 |

Queue de table : 16 réservoirs ne touchent qu'1 à 3 robinets (trafic_rn, qpv_2024, plh_epci, gtfs_pan, rge_alti…). La liste complète, robinets nommés, est dans la sortie du script (et rejouable : `python3 scripts/inventaire/construit_circuit.py`). Lecture directe pour CIRCUIT-1 : **une injection DVF touche 19 robinets ; une injection GPU/PLU en touche 13, dont la fuite de dénominateur du zonage.**

### Point d'étape Lot 6

- Validation : PASS (script, aucun id orphelin, chaque chiffre a ≥ 1 réservoir et ≥ 1 robinet).
- `DOUTE` : 0 nouveau.
- A bloqué : rien.

---

## Lot 7 — Agents et traçage (faisabilité, rien construit)

Livrable : `docs/CIRCUIT/inventaire/agents_fiches.csv` (**34 réservoirs non surveillés** — le mandat en attendait 28 ; l'écart vient des lignes absentes/hors-vitrine comptées ici — dont 24 avec `page_rendue_en_js=DOUTE`, aucun appel réseau n'étant autorisé), généré par `scripts/inventaire/extrait_agents_fiches.py` depuis `reservoirs.csv`.

### Q7.1 — Pile IA

- **Modèles** : `src/labuse/ai_models.py` — routeur par tâche (`MODEL_FACTUAL`/`MODEL_VISION` = `claude-haiku-4-5-20251001`, `MODEL_REASONING` = `claude-sonnet-4-6`, ai_models.py:22-25), garde `RETIRED_MODELS`+`check_model()` (échec BRUYANT, ai_models.py:29-49), registre `SURFACES` de **22 usages** avec override env par surface (`ai_models.py:60-96`) — le tableau admin EST la vérité servie.
- **SDK figé** : `anthropic==0.116.0` (`pyproject.toml:60`, garde `tests/test_anthropic_pin.py`).
- **Où l'API est appelée** : Copilote v2 (routage/sélection/formulation/missions), recherche NL, synthèse fiche/banquier (`strict_numbers`), traducteur PLU, parseur programmes promoteur, **extraction pige** (`pige/extraction.py:98`, kind `vision_pige`), accroche du jour — tous via `ai/core.complete()` (façade unique, ledger `ia_log`).
- **`ia_budget`** : **PAS sur main** — `ai/core.py:108` le dit : la porte budget/compte vit sur la branche `fix/ia-modele-budget` non mergée. Sur main : ledger `ia_log` + quotas Copilote (`quota.py`, réglages admin).
- **LLM en job de fond** : le pattern existe — `pige/extraction.py` est appelé hors requête (traitement des dépôts Radar, cron `radar-cycle`) via la même façade ; aucun worker dédié, un `subprocess`/cron suffit aujourd'hui.
- **Playwright / navigateur sur le VPS** : absent des requirements et du deploy (grep) ; le chromium local (`chromium_headless_shell-1217`) est un outil de dev pour captures. Un agent « page JS » devrait l'installer.
- **Sortie réseau du VPS** : `deploy/scripts/ufw_setup.sh:25-27` — `default deny incoming, default allow outgoing` : **rien ne bloque un agent sortant**.

### Q7.3 — Traçage : par où passe un chiffre avant l'écran

- **Front** : un point de passage **quasi unique** existe — `frontend/src/lib/format.ts` (8 formateurs : fmtInt, fmtDec, fmtEur, fmtM2, fmtEurCompact, fmtPct, fmtDate, fmtDateNum ; **~225 appels** dans components/). Exceptions recensées : redéfinitions locales dans `ContextePanel.tsx`, `MarcheSecteurBlock.tsx`, `RadarMarche.tsx` (~58 usages inline) et des `toLocaleString` épars côté admin.
- **Hors front, 4 chemins de rendu distincts** : templates Jinja2 du Flash (WeasyPrint, `flash/templates/rapport.html`), builders fpdf2 (`api/briques_pdf.py`, courrier, zone), HTML mail construit serveur (`pige/digests.py:carte_html`, `events.py:cartes_html`), pages serveur `coffre_ui`.
- **Verdict** : PAS de point unique global. Pour équiper chaque nombre d'une étiquette de provenance : ~225 sites front via `format.ts` (1 chantier), + ~60-80 sites inline front, + 4 familles serveur (Jinja/fpdf2/mail/coffre) — estimation honnête : **~300-350 sites d'appel**, dont l'essentiel se factorise en étendant `format.ts` et un helper serveur unique.

### Q7.4 — Journal des gestes

- **Basculer / Revenir** : journalisés au complet — `run_bascule_journal` (ts, ancien, nouveau, **par** (email admin), sens avant/arrière, caches purgés, verdict cohérence — `bascule_flux.py:71,227` ; `dashboard.py:1414` passe `par=compte_email`) + notification `event_log`. **OUI (qui, quand, quoi).**
- **Calculer** : notification système dédupliquée `flux-run:<label>` (event_log) + état `run_progress` (pid, phases) — **pas d'identité « qui »** dans le journal.
- **Injecter** : trace `source_veille.injection_lancee_at/injection_vu` + notification admin + log fichier `/tmp/labuse-relance-<label>.log` — **pas d'identité « qui »** non plus. Les crons, eux, ne journalisent PAS event_log (commentaire `dashboard.py:863` : leur vraie trace est `ingestion_runs`/`last_sync_at`).

### Point d'étape Lot 7

- Compteurs : 34 fiches agents (24 js=DOUTE), produits par le script.
- `DOUTE` : 24 `page_rendue_en_js` (interdiction d'appel réseau) + formats de millésime inconnus au code.
- A bloqué : rien — la question « JS ou pas » exige un passage réseau, reporté aux agents eux-mêmes.

---

## Lot 8 — Synthèse

### Les 10 constats qui pèsent le plus (impact client)

1. **La fuite de dénominateur du zonage** : la fiche commune sert des parts de SURFACE (`app.py:1908-1955`, l'intention documentée), un second chemin sert des comptes de PARCELLES (`app.py:2436`). Saint-Paul : A 35,8 % vs 17,8 %, N 47,2 % vs 6,8 % — un client qui voit les deux ne peut pas les réconcilier. Mesuré sur les 24 communes.
2. **« 77 sources dont 49 sous veille » est un chiffre faux à l'écran Circuit** : `flux.py:198` compte le brut (77) là où la vitrine canonique en sert 66 ; les 49 mélangent sondes et lignes brutes (45 vraies sondes, 41 sur les affichées). Trois écrans, trois nombres.
3. **score_e mange de l'eau ancienne** : il lit le précalcul `dvf_prix_sortie_neuf`, mesuré divergent du moteur live (4 730 vs 5 003 €/m² à Saint-Paul) que RETOURS-11F M1 a corrigé partout AILLEURS. La marge promoteur servie est calée sur un neuf faux.
4. **La trace DPE ment par omission** : le cron saute les communes peuplées ET tamponne `last_sync_at` (`dpe.py:243`) — healthz peut dire « ok » sans donnée neuve ; l'amont a 6 semaines d'avance sur la base locale.
5. **Deux jeux de crons coexistent dans le dépôt** (19 wrapper/16 posés vs 13 lignes legacy `deploy/cron.d/*`) avec des cadences contradictoires (bodacc quotidien legacy vs absent du wrapper ; dpe hebdo legacy vs mensuel wrapper) — et healthz attend les cadences LEGACY. Ce qui tourne réellement sur le VPS : indécidable en local.
6. **La divisibilité est servie sur un run mort** : `division_or_candidates` = q_v10_m129, lu sans filtre de run par la fiche (`app.py:2696`), 2 runs derrière le servi (toléré comme workflow — mais rien ne l'affiche au client).
7. **« Zéro recalcul au front » n'est pas tenu hors outils** : 9 calculs métier au navigateur (charge foncière bornée, % propriétaires, % autres logés, kWc/MWh solaire, % ZAN…) — des nombres que le serveur ne produit nulle part.
8. **Le run résiduel vit sur un pointeur SÉPARÉ** (`residuel_runs.is_served`, nomenclature propre m135-run2-ile) : la « constante unique » ne gouverne pas tout ; une bascule scoring ne bascule pas le résiduel.
9. **L'injection n'est branchée que pour 5 sources sur 79** (`config/sources_ingestion.yaml`) : partout ailleurs, « Injecter cette version » n'existe pas — le geste du circuit est incomplet par construction.
10. **La base locale devance main** : les sources 93-95 (EDF HTA, TCSP, Réunion Express) existent en base mais leur code est sur `fix/retours-12` non mergée — l'inventaire du code et celui de la base ne coïncident pas tant que le merge n'est pas fait.

### Les fuites mesurées

`inventaire/fuites_mesurees.csv` — 49 lignes, 46 avec écart ≠ 0 : parts de zonage A et N × 24 communes (cause `denominateur`, chemin fidèle = surface), `n_sources` 66 vs 77 (cause `perimetre`, chemin fidèle = WHERE_AFFICHEES), `prix_neuf_vefa` 5 003 vs 4 730 €/m² (cause `table`, chemin fidèle = moteur live ; le précalc n'est plus lu que par score_e).

### La liste des DOUTE (81) et ce qui permettrait de trancher

- **jobs.csv (32)** : 19 « dernier_statut » wrapper (l'état JSON n'existe que sur le VPS) + 13 poses legacy → un `ls /etc/cron.d/ && cat /opt/labuse/state/jobs/*.json` sur le VPS tranche tout.
- **agents_fiches.csv (25)** : 24 « page_rendue_en_js » + formats de millésime → un passage réseau par les agents eux-mêmes (interdit ici).
- **reservoirs.csv (19)** : tables/jobs de couches sans CLI dédiée (RGE ALTI, RPG, DEAL WMS, INPN, SPANC, SRU, parkings, Filosofi, LiDAR) + licences « à confirmer » → 1 h de lecture ciblée de `layers_ingest.py`/scripts, et l'audit licences M6 §1.11 à terminer.
- **Divers (5)** : entrées de `loyers.py` ; composants front Solaire/fiche soleil ; ampleur PROD de l'eau ancienne DPE ; garde anti-invention de `copilote-general` ; écran exact du « 18 %/6 % » de Vic.

### Questions pour Vic

1. Sur quels écrans précis as-tu lu « 18 % » et « 6 % » pour Saint-Paul ? (Les deux chemins existent et sont mesurés ; il reste à épingler l'écran de chaque valeur.)
2. Quel jeu de crons est posé sur le VPS aujourd'hui — wrapper, legacy, ou les deux ? (Un `ls /etc/cron.d/` suffit.)
3. La part de zonage doit-elle être servie en surface partout (l'intention du code) — et le chemin « comptes de parcelles » réservé aux filtres ?
4. score_e doit-il basculer sur le moteur neuf live (comme comparateur/fiche/carte) au prochain run ?
5. Le pointeur résiduel séparé est-il un choix durable ou doit-il rejoindre la constante unique à CIRCUIT-1 ?
6. Faut-il étendre `config/sources_ingestion.yaml` au-delà des 5 sources branchées, et à quelles sources en premier ?

### Taille du registre à écrire (estimation honnête)

- **Chiffres à déclarer** : 88 ids recensés couvrant 55 robinets ; les 67 robinets restants (sous-entrées d'outils, couches, admin) portent une longue traîne estimée à **150-250 chiffres supplémentaires** → un registre complet ≈ **250-350 chiffres**.
- **Robinets à rebrancher** (servir le moteur au lieu d'un chemin propre) : 2 chemins de zonage à unifier, 1 écran Flux (n_sources), score_e (neuf précalc), 9 calculs métier front à rapatrier côté serveur, 2 lecteurs de division_or à scoper au run → **~15 rebranchements**, plus l'équipement d'étiquette de provenance (~300-350 sites de formatage, factorisables via `lib/format.ts` + un helper serveur).

### Clôture

- **Commits** : mandat `d04b4960` · lot 1 `ef1709ea` · lot 2 `40ebdf6b` · lot 3 `19e92a72` · lot 4 `c037cc8f` · lot 5 `b0dd001d` · lot 6 `7367c6ac` · lot 7 `6b7a95e3` · lot 8 = commit courant (final).
- **Lignes DOUTE** : 81 (détail en tête de rapport).
- **Temps passé par lot** (horodatage des commits, exploration parallélisée par agents) : L1 ~14 min · L2 ~3 · L3 ~3 · L4 ~6 · L5 ~10 · L6 ~1 · L7 ~2 · L8 ~6.
- **Ce qui n'a pas pu être fait, et pourquoi** : durées de « Calculer » (interdit de lancer un job) ; état JSON des jobs et crontab réellement posés (VPS seulement) ; `page_rendue_en_js` des amonts (aucun appel HTTP producteur) ; mesure des fuites candidates convergeant vers une même fonction (pas de deuxième chemin à exécuter) ; ampleur PROD de l'eau ancienne DPE (base locale n=17) ; exhaustivité des chiffres de la longue traîne (139 couples livrés, reste estimé ci-dessus).
