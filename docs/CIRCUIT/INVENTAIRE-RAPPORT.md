# CIRCUIT-0 — Rapport d'inventaire de la plomberie

| en-tête | valeur | preuve |
|---|---|---|
| commit de départ | `b222d00f` (main), mandat commité en `d04b4960` | `git log --oneline -1` |
| run servi | `q_v11_m137` | `config/served_run.txt` ligne 1 (constante unique, lue par `runs.current()` — `src/labuse/runs.py:49-61`) |
| base utilisée | locale, `postgresql:///labuse` (user openclaw), 242 tables | `psql -l` ; `SELECT count(*) FROM information_schema.tables WHERE table_schema='public'` → 242 |
| date | 05/09/2026 | — |

Le tableau final des compteurs (Lot 8) est produit par `scripts/inventaire/compte_rapport.py` à partir des CSV livrés.

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
