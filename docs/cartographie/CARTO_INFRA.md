# CARTO_INFRA — Cartographie INFRA / CONFIG / TESTS / SCRIPTS

Document factuel (lecture seule). Domaine : configuration, tests, scripts, déploiement, variables d'environnement, documentation. Aucun jugement, aucun secret (emplacements uniquement).

Généré le 2026-07-20. Racine : `/Users/openclaw/Desktop/labuse`.

---

## 1. Configuration (`config/`)

23 fichiers à la racine de `config/` (22 `.yaml` + 1 `.csv`) + sous-dossier `calibrage/` (24 fichiers). Consommateur = module `src/labuse/` où le nom de fichier est référencé (grep).

| Fichier | Rôle | Consommé par (module src) |
|---|---|---|
| `anc_vegetation.yaml` | Paramètres du mandat ANC & Végétation (seuils, sources) | `ingestion/anc.py`, `ingestion/vegetation.py`, `ingestion/seed_sources.py` |
| `bilan_calibration_vic.csv` | Jeu de calibration du bilan de faisabilité (paramètres validés Vic) | `cli.py`, `faisabilite/bilan_params.py`, `faisabilite/bilan_calibration.py` |
| `cascade_rules.yaml` | Règles de la cascade de qualification (couches / étages / seuils) — pivot du moteur | `config.py`, `ingestion/layers_ingest.py`, `cascade/layers/etage1.py`, `faisabilite/plu_rules.py` |
| `communes_gold_standard.yaml` | Référentiel « gold standard » des communes (attendus de calibrage) | `communes.py`, `api/app.py` |
| `completeness_weights.yaml` | Pondérations du score de complétude de fiche | `config.py`, `scoring/completeness.py` |
| `detection_ortho.yaml` | Paramètres de détection ortho (pente, tuiles, piscines, PV) | `ingestion/ortho_pente.py`, `ingestion/ortho_tiles.py`, `ingestion/ortho_piscines.py` |
| `epci_974.yaml` | Table EPCI de La Réunion (rattachement communes → intercommunalité) | `api/app.py` |
| `gabarits_courrier.yaml` | Gabarits de courrier / publipostage | `api/segments.py`, `courrier.py` |
| `gestionnaires_via.yaml` | Gestionnaires de voirie / réseaux (viabilisation) | `faisabilite/viabilisation.py` |
| `habitat_solaire.yaml` | Paramètres du mandat Habitat Solaire (PVGIS, capacités, échéances) | `config.py`, `cli.py`, `ingestion/ortho_equipements.py` |
| `mutation_weights.yaml` | Pondérations du score de mutabilité | `mutation.py` |
| `opportunity_weights.yaml` | Pondérations du score d'opportunité | `config.py`, `scoring/feedback.py`, `cascade/layers/etage1.py` |
| `pipeline.yaml` | Définition du pipeline d'ingestion / étapes | `config.py`, `models.py`, `cli.py` |
| `plh_tco.yaml` | Objectifs PLH du TCO (logement) | `config.py`, `plh.py` |
| `plu_saint_denis.yaml` | PLU calibré Saint-Denis (zones, hauteurs, emprises sourcées) | chargé dynamiquement via `faisabilite/plu_rules.py` (`plu_<slug>.yaml`) |
| `plu_saint_paul.yaml` | PLU « gold » de référence (défaut + Saint-Paul) | `assemblage.py`, `cascade/layers/phase1.py`, `faisabilite/plu_rules.py` |
| `rtaa_dom.yaml` | Règles RTAA DOM (thermique / ventilation) | `api/modules.py`, `api/app.py` |
| `scoring_matrice.yaml` | Matrice de scoring (verdicts / tiers) | `cli.py`, `flash/data.py`, `scoring/dryrun.py` |
| `segment_presets.yaml` | Presets des vues / segments (Solaire, Ortho, ANC…) | `segments/registry.py`, `segments/presets.py`, `segments/engine.py` |
| `segments.yaml` | Déclaration des segments de base | `ingestion/solaire_flags.py`, `ai/nl_segments.py`, `api/segments.py` |
| `shortlist.yaml` | Paramètres de la shortlist (Obsimmo, filtres) | `config.py`, `obsimmo.py`, `shortlist.py` |
| `wfs_layers.yaml` | Catalogue des couches WFS externes | `config.py`, `connectors/wfs.py` |

### `config/calibrage/` (24 fichiers)

24 manifestes `zonage_<slug>.yaml` (un par commune, 24/24 communes de La Réunion) : zonage OPPOSABLE tel qu'ingéré aux sessions de calibrage (idurba, zones, libellés, attrs, géométries EWKB en sidecar `data/calibrage/*.jsonl.gz` gitignoré). Producteur / consommateur : `scripts/calibrage_zonage.py` (export / import / roundtrip vers `spatial_layers_temoin`). Plus gros : `zonage_saint_paul.yaml` (~212 Ko), `zonage_saint_leu.yaml` (~155 Ko).

---

## 2. Tests (`tests/`)

- **Commande d'exécution** : `pytest` (config `[tool.pytest.ini_options]` de `pyproject.toml` : `testpaths=["tests"]`, `pythonpath=["src"]`, `addopts="-ra"`).
- **Fichiers de test** : 107 fichiers `test_*.py` (tous à plat sous `tests/`).
- **Fonctions de test** : 865 (`grep -rc "def test_"`).
- **Marqueurs déclarés** : `db` (tests nécessitant une base PostGIS accessible) et `network` (accès réseau sortant). Définis dans `pyproject.toml`.
- **conftest** : `tests/conftest.py` — bascule app + tests vers une base dédiée `labuse_test` (ou `LABUSE_TEST_DATABASE_URL`) AVANT tout `get_settings()` ; skip (pas échec) si PostGIS injoignable ; fixtures `engine` (session), `db_session` (transaction rollback-ée), `_clear_mem_caches` (autouse). Force `LABUSE_CONFIG_DIR=config` et `LABUSE_ENRICH_LIVE=0`.

### Fichiers de test par zone (échantillon représentatif)

- **API / IA** : `test_api.py`, `test_api_q_v2.py`, `test_ai.py`, `test_ai_core.py`, `test_assistant.py`, `test_fiche_ask.py`, `test_ia`/`nl` : `test_nl_aggregate.py`, `test_nl_segments.py`, `test_nl_semantics.py`, `test_resume.py`, `test_voisinage.py`, `test_enrichment.py`, `test_protection.py`, `test_pre_dossier.py`, `test_dossier.py`.
- **Cascade / étages** : `test_cascade.py`, `test_etage0_filtre_dur.py`, `test_etage1.py`, `test_etage2.py`, `test_verdict_effectif.py`, `test_cadrage_niveaux.py`.
- **Scoring** : `test_scoring.py`, `test_dryrun.py`, `test_declassement.py`, `test_score_v.py`, `test_score_v13.py`, `test_decisions_1_3.py`, `test_matrice.py`, `test_p_model_dataset.py`, `test_p_model_woe.py`, `test_p_v2_api.py`, `test_p_v2_statuts.py`, `test_micro_opportunite.py`.
- **Faisabilité / surface** : `test_faisabilite.py`, `test_bilan.py`, `test_bilan_calibrate.py`, `test_residuel.py`, `test_viabilisation.py`, `test_surface_c.py`, `test_geo_surface.py`, `test_volume3d.py`, `test_geom_2975.py`.
- **Connecteurs / ingestion** : `test_connectors.py`, `test_bodacc.py`, `test_cartofriches.py`, `test_dpe.py`, `test_georisques_layers.py`, `test_inpi_rne.py`, `test_qpv.py`, `test_ban_adresses.py`, `test_permits.py`, `test_rnic.py`, `test_personnes_morales.py`, `test_pm_millesimes.py`, `test_abf_merimee.py`, `test_agorah_plu_connector.py`, `test_deal_risques.py`, `test_ppr.py`, `test_ppr_marginal_coverage.py`, `test_sar.py`.
- **Mandats spécialisés** : `test_habitat_solaire.py`, `test_anc.py`, `test_vegetation.py`, `test_ortho_detection.py`, `test_pente_exposition.py`, `test_flash_report.py`, `test_pdf_premium.py`, `test_courrier.py`, `test_publipostage.py`, `test_segments.py`.
- **Données / commune / qualité** : `test_communes_gold_standard.py`, `test_saint_paul_quality.py`, `test_calibration.py`, `test_lot2_import_script.py`, `test_lot_d.py`, `test_run_serving_coherence.py`, `test_remonter_le_temps.py`, `test_dvf_geo.py`, `test_dvf_histo.py`, `test_export_comparables.py`, `test_voirie_pagination.py`, `test_ravine.py`, `test_vue_mer.py`.
- **Transverse / socle** : `test_auth.py`, `test_backup.py`, `test_state.py`, `test_cli_resolve.py`, `test_audit.py`, `test_audit_ui_fixes.py`, `test_ux_v1.py`, `test_vocabulary.py`, `test_alertes.py`, `test_assemblage.py`, `test_bati.py`, `test_loyers.py`, `test_obsimmo.py`, `test_occupation.py`, `test_proprietaire_type.py`, `test_prospect.py`, `test_prospection.py`, `test_mutation.py`, `test_mutation_api.py`, `test_plh.py`, `test_demo.py`, `test_preset_parc_piscines.py`.

### Modules `src/labuse` sans test (par import direct)

Méthode : arbre `src/labuse/*.py` (180 modules, `__init__` exclus) comparé aux chemins `labuse.<...>` importés dans `tests/`. 94 modules importés directement, **85 modules non importés par aucun test**. NOTE FACTUELLE : certains sont couverts indirectement (ex. `labuse.geo` via `test_geo_surface.py`, `labuse.models` via les fixtures) ; la liste ci-dessous est l'absence d'import DIRECT, pas une preuve d'absence totale de couverture.

Liste (85) :
```
ai.agent, ai.prompt
alertes
api.auth, api.courrier, api.dossier, api.events, api.export_commun, api.moteurs,
api.ortho, api.partners, api.pdf_projet, api.projets, api.score_v2, api.solaire, api.tiles
assemblage
cascade.engine, cascade.layers (pkg), cascade.layers.etage0_ext, cascade.layers.phase2
communes
connectors.cartofriches, connectors.georisques, connectors.qpv, connectors.wfs
constants, courrier, demo
faisabilite.bilan_calibration, faisabilite.bilan_params, faisabilite.viabilisation,
faisabilite.viabilisation_build
flash.carte
geo
ingestion.agorah_plu, ingestion.bruit_route, ingestion.cadastre_bulk, ingestion.cinquante_pas,
ingestion.demo_saint_paul, ingestion.dvf_marche, ingestion.ortho_equipements, ingestion.ortho_pente,
ingestion.permit_delais_m10, ingestion.permits_sdes, ingestion.personnes_morales, ingestion.pv_detection,
ingestion.score_v_fetch, ingestion.seed_sources, ingestion.signals, ingestion.solaire_grid_capacity,
ingestion.solaire_pv_registry, ingestion.solaire_tertiaire, ingestion.sup_gpu, ingestion.vegetation
loyers
ml (pkg), ml.juge_flair, ml.juge_vlm, ml.probe
models, numeric, obsimmo, occupation, plans, plh, plu_reglement, prospection
scoring.completeness, scoring.feedback, scoring.icd, scoring.p_model.evaluate, scoring.p_model.ext_sql,
scoring.p_model.features, scoring.p_model.shadow, scoring.p_model.sql,
scoring.p_v2 (pkg), scoring.p_v2.libelles_client, scoring.p_v2.monitoring, scoring.status
segments.catnat, segments.engine, segments.residuel_bati
shortlist, state
```

Concentration factuelle des non-importés : `ingestion/` (~20), `api/` (~14), `scoring/` (sous-paquets `p_model` / `p_v2`, ~11), `ml/` (4/4, dépendances ML lourdes séparées).

---

## 3. Scripts & déploiement

### `scripts/` (racine, 20 fichiers)

| Script | Rôle (1 ligne) |
|---|---|
| `_commune_worker.py` | Worker interne appelé par `build_communes.py` (traitement d'une commune) |
| `backup_daily.sh` | Sauvegarde quotidienne (shell) |
| `build_communes.py` | Construit / assemble les artefacts par commune |
| `calibrage_zonage.py` | Export/import/roundtrip des manifestes `config/calibrage/zonage_*.yaml` ↔ DB |
| `demo_faisabilite.py` | Démonstration du moteur de faisabilité |
| `dev_db.sh` | Démarrage / gestion de la base de dev (shell) |
| `extend_cascade_ile.py` | Étend la cascade à l'ensemble de l'île |
| `gen_tops_ile.py` | Génère les « tops » (classements) à l'échelle île |
| `gpu_witness_test.py` | Test témoin de l'API Carto GPU (phase 1.A) |
| `import_commune_gold_standard.py` | Importe le référentiel gold standard des communes |
| `ingest_conso_enaf.py` | Ingestion CONSOENAF (conso ENAF Cerema, ZAN) |
| `ingest_insee_logement.py` | Ingestion INSEE RP logement (XLSX) |
| `ingest_npnru.py` | Ingestion NPNRU |
| `ingest_rpls.py` | Ingestion RPLS (parc social) |
| `ingest_sru.py` | Ingestion SRU (obligations logement social) |
| `lot2_import_saint_paul.py` | Import LOT 2 Saint-Paul |
| `post_run_ile.sh` | Post-traitement après un run île (shell) |
| `run_ile_q_v2.sh` | Lance un run île en q_v2 (shell) |

Sous-dossiers : `m3-p-model/` (5 : `build_dataset`, `train`, `eval_test`, `score_2026`, `rapport` — modèle P), `m36-foncier/` (5 : `lot0_verdict_strate`, `lot2_b0_censure`, `lot2_walk_forward`, `lot3_verdict_final`, `rapport_m36`), `m5-produit/` (2 : `brulantes_delta`, `churn_simulation`), `score-v/` (2 : `backtest`, `rapport_final`).

### `deploy/`

- `Caddyfile.example` — modèle Caddy (reverse-proxy TLS ; copie serveur `deploy/Caddyfile` gitignorée).
- `cron.d/` — 5 crontabs : `abuse` (scan quotidien 6h), `ban` (rafraîchissement BAN mensuel), `catnat` (ingest CatNat + segments-counts mensuel), `sitadel` (permits SDES mensuel), `solaire` (chaîne PV registry/grid/parkings/flags/conso/tertiaire/cache-purge mensuel). Toutes sourcent `/etc/labuse/labuse.env` et appellent le venv `/opt/labuse/venv`.
- `env/labuse.env.example` — gabarit env serveur (noms seulement, voir §4).
- `nginx/labuse.conf` — vhost Nginx.
- `postgresql/postgresql.vps2.conf` — config PostgreSQL du VPS.
- `scripts/` — `backup_postgres.sh`, `db_maintenance.sh`, `smoke_test.sh`.
- `systemd/labuse.service` — unité systemd (FastAPI/Uvicorn derrière Nginx ; pose documentée dans `docs/DEPLOYMENT_OVH_VPS.md §8`).

### Racine — Docker & packaging

- `Dockerfile`, `docker-compose.yml`, `docker-compose.caddy.yml`, `docker-compose.pilot.yml`, `.dockerignore`.
- `pyproject.toml` : build setuptools ; `requires-python >=3.11` ; entry point **`labuse = "labuse.cli:app"`** ; extras `ai=["anthropic>=0.40"]`, `dev=["pytest>=8.0","ruff>=0.5"]`.
  - **Ruff** : `line-length=120`, `src=["src","tests"]`, `select=["F","I","E","W"]`, `ignore=["E501"]`.
- `requirements.txt` (cœur : SQLAlchemy, GeoAlchemy2, psycopg, pydantic, fastapi, uvicorn, httpx, shapely, pyproj, pyshp, typer, jsonschema, opencv-headless, numpy, openpyxl, weasyprint, jinja2, stripe, pypdf ; torch/scikit-learn commentés).
- `requirements-ml.txt` (cascade juges ortho : `torch>=2.2`, `scikit-learn>=1.4` — ~2 Go, non requis par `labuse api`).

---

## 4. Variables d'environnement (noms + rôle — AUCUNE valeur)

### `.env.example` (racine)
| Variable | Rôle |
|---|---|
| `LABUSE_DATABASE_URL` | URL de connexion PostgreSQL/PostGIS |
| `LABUSE_ENV` | Environnement d'exécution (dev/pilot/prod) |
| `LABUSE_PILOT_COMMUNE_INSEE` | Code INSEE de la commune pilote |
| `LABUSE_PILOT_COMMUNE_NAME` | Nom de la commune pilote |
| `LABUSE_CONFIG_DIR` | Répertoire des fichiers de config YAML |
| `LABUSE_HTTP_TIMEOUT_S` | Timeout HTTP sortant (secondes) |

### `.env.pilot.example` (racine — déploiement pilote)
| Variable | Rôle |
|---|---|
| `LABUSE_DOMAIN` | Domaine servi |
| `POSTGRES_PASSWORD` | Mot de passe base (secret) |
| `LABUSE_ENV` | Environnement |
| `LABUSE_AUTH_PASSWORD` | Mot de passe d'authentification applicative (secret) |
| `LABUSE_SECRET_KEY` | Clé secrète de session (secret) |
| `LABUSE_SESSION_HOURS` | Durée de session |
| `LABUSE_PUBLIC_URL` | URL publique |

### `deploy/env/labuse.env.example` (gabarit serveur)
`LABUSE_DATABASE_URL`, `LABUSE_ENV`, `LABUSE_AUTH_PASSWORD`, `LABUSE_SECRET_KEY`, `LABUSE_PUBLIC_URL`, `ANTHROPIC_API_KEY` (clé API IA / assistant), `LABUSE_ASSISTANT_MODEL` (modèle IA), `LABUSE_PILOT_COMMUNE_INSEE`, `LABUSE_PILOT_COMMUNE_NAME`, `LABUSE_HTTP_TIMEOUT_S`.

### Autres flags référencés (conftest / doc)
`LABUSE_TEST_DATABASE_URL`, `LABUSE_APP_DATABASE_URL`, `LABUSE_ENRICH_LIVE`, `LABUSE_DEV_MODE` (crawls dev, cf. mémoire projet). Catégories : **DB** (`*_DATABASE_URL`, `POSTGRES_PASSWORD`), **clés API** (`ANTHROPIC_API_KEY`, + Stripe via lib — `STRIPE_SECRET_KEY` évoquée dans la doc Module Flash, non présente dans les gabarits), **flags** (`LABUSE_ENV`, `LABUSE_ENRICH_LIVE`, `LABUSE_DEV_MODE`, `LABUSE_HTTP_TIMEOUT_S`).

`.env` réel présent à la racine et gitignoré (`.gitignore` : `.env`, `deploy/env/*.env` sauf `*.env.example`, `config/settings.yaml`).

---

## 5. Documentation

- **Racine** : 82 fichiers `.md`.
- **`docs/`** : 85 fichiers `.md` (dont `docs/communes/` 49, `docs/product/` 10, `docs/ux/` 2, `docs/cartographie/` — ce document).

### Grandes familles (racine)
`RAPPORT_*` (34), `NOTES_*` (12), `MANDAT_FABLE_*` (7), `AUDIT*` (3+), `PILOT_*` (2), `DEMO_*` (2), plus singletons (`README.md`, `BUGS.md`, `COMMANDES.md`, `DEPLOY_RUNBOOK.md`, `DESIGN_SYSTEM.md`, `DIAGNOSTIC.md`, `BILAN_ILE.md`…).

### ~15 documents notables
| Fichier | Famille / objet |
|---|---|
| `README.md` | Présentation projet |
| `COMMANDES.md` | Commandes CLI / opérations |
| `DEPLOY_RUNBOOK.md` | Runbook de déploiement |
| `DESIGN_SYSTEM.md` | Système de design UI |
| `BUGS.md` | Backlog de bugs (audit UI) |
| `DIAGNOSTIC.md` | Diagnostic outils |
| `BILAN_ILE.md` | Bilan run à l'échelle île |
| `AUDIT_COMPLET.md` / `AUDIT_27_OUTILS.md` | Audits transverses |
| `MANDAT_FABLE_HABITAT_SOLAIRE.md` | Mandat Habitat Solaire |
| `MANDAT_FABLE_MODULE_FLASH.md` | Mandat Module Flash |
| `MANDAT_FABLE_WAVE_ANC_VEGETATION.md` | Mandat ANC & Végétation |
| `PILOT_DEPLOYMENT.md` / `PILOT_SECURITY_DEPLOYMENT.md` | Déploiement pilote + sécurité |
| `NOTES_SOCLE_V1.md` | Notes socle IA v1 |
| `NOTES_ETAGE_0.md` | Notes étage 0 de la cascade |
| `docs/DEPLOYMENT_OVH_VPS.md` | Déploiement VPS OVH (référencé par systemd) |

---

## 6. Métriques

- **TODO/FIXME** dans `config/` + `scripts/` + `tests/` : **5 occurrences, toutes dans `config/plu_saint_denis.yaml`** (hauteurs zones Up/Upi/Upr à lire dans un tableau image p.34 — extraction manuelle). 0 dans `scripts/`, 0 dans `tests/`.
- **Scripts orphelins** (nom non référencé dans `deploy/`, `scripts/*.sh`, `*.md`, `docs/`) : `calibrage_zonage.py`, `demo_faisabilite.py`, `extend_cascade_ile.py`, `ingest_conso_enaf.py`, `ingest_insee_logement.py`, `ingest_sru.py` (0 référence externe trouvée — invocation manuelle / CLI). Bien référencés : `lot2_import_saint_paul.py` (4), `import_commune_gold_standard.py` (2), `build_communes.py`/`gen_tops_ile.py`/`gpu_witness_test.py`/`ingest_rpls.py` (1).
- **Modules src sans import direct de test** : 85 / 180 (cf. §2, dont couverture indirecte non exclue).
- **Cache Python versionné** : `scripts/__pycache__/` et `scripts/score-v/__pycache__/` présents sur disque (artefacts régénérables).

---

## 7. Histoire (`git log -1 --format=%ci`)

| Répertoire | Dernier commit |
|---|---|
| `tests/` | 2026-07-20 14:04:55 +0200 |
| `scripts/` | 2026-07-16 06:27:29 +0200 |
| `config/` | 2026-07-14 22:07:24 +0200 |
| `docs/` | 2026-07-15 11:30:17 +0200 |
| `deploy/` | 2026-07-11 09:51:07 +0200 |

`deploy/` est la zone la plus ancienne (stabilisée après la mise en place du pack de déploiement pilote), `tests/` la plus récente.

---

## 8. Observations factuelles

1. **Base de test isolée par construction** : `conftest.py` force app+tests vers `labuse_test` avant tout `get_settings()` et skippe (jamais échoue) si PostGIS est absent → une part des 865 tests dépend d'une base et ne s'exécute pas hors PostGIS.
2. **Config à chargement dynamique** : `plu_saint_denis.yaml` n'apparaît dans aucun `grep` de nom en dur ; il est résolu par `faisabilite/plu_rules.py` via le pattern `plu_<slug>.yaml` (défaut = `plu_saint_paul.yaml`). Ajouter un PLU communal = déposer un YAML, sans modifier de code.
3. **`config/calibrage/`** : 24/24 communes présentes ; les géométries réelles vivent dans `data/calibrage/*.jsonl.gz` (gitignoré), seuls les manifestes sont versionnés — la reconstruction passe par `scripts/calibrage_zonage.py`.
4. **Séparation ML** : `requirements-ml.txt` (torch, scikit-learn) est décorrélé du cœur ; les 4 modules `ml/*` ne sont importés par aucun test (dépendance lourde non installée par défaut).
5. **Dette TODO concentrée** : les 5 seuls TODO du périmètre sont dans un unique fichier PLU (hauteurs en tableau image, extraction manuelle) — aucune dette TODO dans les scripts ni les tests.
6. **Concentration des modules sans test direct** : `ingestion/`, `api/` (endpoints tuiles/ortho/solaire/projets/auth) et sous-paquets scoring `p_model`/`p_v2`. Plusieurs sont testés indirectement (fixtures, endpoints agrégés) mais pas importés nommément.
7. **Secrets** : `.env` réel présent à la racine (gitignoré) ; seuls les gabarits `*.env.example` sont versionnés ; `STRIPE_SECRET_KEY` est mentionnée en doc (Module Flash) mais absente des gabarits d'environnement listés.
