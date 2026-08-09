# CARTOGRAPHIE — LABUSE

Document **factuel**, lecture seule. Décrit ce qui existe, sans jugement ni recommandation.
Généré le 2026-07-20 (dernier commit du repo : 2026-07-20). Périmètre : `/Users/openclaw/Desktop/labuse`.

> **Découpage.** Le détail par fichier (section 2 « arborescence commentée ») est déporté en annexes
> par domaine. Ce document porte les sections transverses (1, 3, 4, 5, 6, 7, 10, 11, 12) et la synthèse.
>
> | Annexe | Domaine |
> |---|---|
> | [CARTO_SCORING.md](CARTO_SCORING.md) | scoring P/C, cascade, segments, mutation, faisabilité |
> | [CARTO_INGESTION.md](CARTO_INGESTION.md) | ingestion (45 modules), connecteurs, `data/` |
> | [CARTO_API.md](CARTO_API.md) | API FastAPI (30 fichiers, 174 routes), socle IA, flash |
> | [CARTO_FRONT.md](CARTO_FRONT.md) | frontend React/TS, scripts QA Playwright |
> | [CARTO_CORE.md](CARTO_CORE.md) | CLI (78 commandes), `models.py`, config, helpers transverses |
> | [CARTO_INFRA.md](CARTO_INFRA.md) | config/, tests/, scripts/, deploy/, docker, docs |

---

## 1. Vue d'ensemble

**LABUSE** — plateforme de prospection foncière pour La Réunion (974) : ingère des données publiques,
score la « probabilité de mutation » et l'« accessibilité » des parcelles, et sert une interface carte
+ fiche + copilote IA + CRM + modules d'aide au montage promoteur.

### Stack
- **Backend** : Python 3.11/3.12, **FastAPI** + **uvicorn**, **SQLAlchemy 2** + **GeoAlchemy2**,
  **psycopg 3**. CLI **typer**. Validation **pydantic 2** + **jsonschema**. Géo : **shapely**, **pyproj**,
  **pyshp**. PDF : **weasyprint** + **jinja2** + **pypdf**. Paiement : **stripe**. Imagerie : **opencv**,
  **numpy**. ML (optionnel, hors `labuse api`) : **torch**, **scikit-learn** (cascade de juges ortho).
- **Base** : **PostgreSQL + PostGIS** (rôle `openclaw`, base `labuse`), **220 tables**, **6 vues métier**
  (+ 4 vues système PostGIS).
- **Frontend** : **React 18** + **TypeScript** + **Vite** + **Tailwind** + **MapLibre GL** +
  **@tanstack/react-query** + **zustand**. Build Vite → `frontend/dist`, servi par FastAPI sous `/socle/`.
- **Tests** : **pytest** (backend, 107 fichiers / 865 tests), **Playwright** (89 scripts `.mjs` QA/E2E/captures, sur 101 `.mjs` au total).
- **Conteneurisation** : Dockerfile + docker-compose (dont variantes pilot / caddy).

### Taille (hors node_modules/.venv/.git/dist/caches)
| Langage | Fichiers | Lignes |
|---|---|---|
| Python | 321 | 59 466 |
| TypeScript (`.ts`) | 11 | 1 519 |
| React (`.tsx`) | 33 | 8 821 |
| JS (`.js`) | 5 | 3 138 |
| QA Playwright (`.mjs`) | 101 | 10 690 |
| SQL | 17 | 962 |
| Markdown (docs) | 274 | 31 308 |
| YAML (config) | 48 | ~63 000 |

Assets : **24 964 `.jpg`** + **942 `.png`** (tuiles/vignettes ortho & captures), 91 `.csv`, 31 `.pdf`.

### Structure top-level
| Répertoire | Rôle |
|---|---|
| `src/labuse/` | Le code applicatif (backend + CLI). Sous-paquets : `api`, `scoring`, `ingestion`, `cascade`, `connectors`, `faisabilite`, `segments`, `flash`, `ml`, `ai` + helpers racine. |
| `frontend/` | Application React/TS (Vite). `src/`, `dist/` (build), `qa/` (Playwright). |
| `config/` | 23 fichiers (22 YAML + CSV) + `calibrage/` (24 manifestes) : matrice scoring, poids mutation/opportunité, cascade, segments, PLU, EPCI… |
| `tests/` | Suite pytest (backend). |
| `qa/` | Scripts Playwright E2E/QA (`.mjs`) + `golden_check.py`. |
| `scripts/` | Scripts utilitaires d'ingestion/ops. |
| `data/` | Données brutes/ingérées (tuiles ortho, CSV, exports…). |
| `deploy/` | Dockerfiles, compose, Caddy, runbooks de déploiement. |
| `docs/` | Documentation (+ `docs/cartographie/` = ce livrable). |
| `reports/` | Rapports de livraison (post-validation, waves…). |
| `commercial/`, `outputs/`, `audit_shots/` | Supports commerciaux, sorties générées, captures d'audit. |
| Racine | ~90 `.md` (RAPPORT_*, NOTES_*, MANDAT_*, AUDIT*), `.env*`, `pyproject.toml`, `requirements*.txt`, `docker-compose*.yml`. |

---

## 2. Arborescence commentée

Le détail par fichier (rôle, lignes, classes/fonctions + signatures) est **dans les annexes** (voir table
en tête). Vue d'ensemble des sous-paquets `src/labuse/` :

| Sous-paquet | Fichiers py | Lignes | Rôle | Annexe |
|---|---|---|---|---|
| `api/` | 30 | 12 133 | Couche HTTP FastAPI (174 routes), fiche, modules, projets, exports | CARTO_API |
| `ingestion/` | 45 | 8 605 | Ingesteurs des sources publiques → tables | CARTO_INGESTION |
| (racine) | 27 | 6 589 | CLI, `models.py`, config, helpers métier | CARTO_CORE |
| `faisabilite/` | 10 | 2 309 | Bilan promoteur, SDP résiduelle, viabilisation, règles PLU | CARTO_SCORING |
| `scoring/` | 23 | ~4 000 | Score P (p_model/p_v2), score_v, opportunité, complétude | CARTO_SCORING |
| `connectors/` | 13 | 1 545 | Clients des API externes (BODACC, INPI, GPU, Géorisques…) | CARTO_INGESTION |
| `cascade/` | 11 | 2 438 | Cascade de règles (étage 0 exclusions dures) + couches | CARTO_SCORING |
| `segments/` | 7 | 1 420 | Moteur de segments/vues (presets Solaire/Ortho/ANC) | CARTO_SCORING |
| `ai/` | 6 | 918 | Socle IA unique (clé, modèles, cache, log, validation) | CARTO_API |
| `flash/` | 4 | 726 | Rapport parcelle à l'unité (PDF + Stripe) | CARTO_API |
| `ml/` | 4 | 524 | Cascade de juges ortho (probe DINOv2 + régression) | CARTO_INGESTION |

---

## 3. Points d'entrée

### 3.1 CLI (`labuse …`, typer — 78 commandes)
Point d'entrée `src/labuse/cli.py` (2 171 lignes). Familles (liste exhaustive en CARTO_CORE) :
- **DB / ops** : `init-db`, `seed-sources`, `seed-demo`, `rebuild-demo`, `warm-demo`, `demo-healthcheck`,
  `doctor`, `prepare-pilot`, `backup-db`, `restore-db`, `discover`, `sources`, `test-source`, `watch`, `api`.
- **Ingestion** : `ingest-real`, `ingest-island`, `ingest-permits`, `geocode-permits`,
  `ingest-personnes-morales`, `ingest-inpi-rne`, `ingest-inpi-gigogne`, `ingest-georisques`,
  `ingest-cartofriches`, `ingest-dpe`, `ingest-mvt`, `ingest-qpv`, `ingest-amenites`, `ingest-abf`,
  `ingest-sup`, `ingest-bruit-route`, `ingest-cinquante-pas`, `ingest-rnic`, `rnic-complements`,
  `ingest-catnat`, `ingest-ban`, `dvf-marche`, `score-v-fetch`, `warm-vue-mer`, `compute-residuel`.
- **Scoring** : `evaluate`, `dryrun-evaluate`, `dryrun-report`, `dryrun-matrice`, `matrice-simulate`,
  `matrice-apply`, `build-mvt`, `score-v2`, `monitor-forward`, `viabilisation`, `detect-events`,
  `score-v-compute`, `declassement`(via evaluate).
- **Segments** : `segments-seed`, `segments-counts`, `segments-residuel`.
- **Solaire** : `solaire-pvgis`, `solaire-flags`, `solaire-conso`, `solaire-tertiaire`, `solaire-parkings`,
  `solaire-pv-registry`, `solaire-grid-capacity`, `solaire-cache-purge`.
- **Ortho / ANC / végétation** : `ortho-pente`, `ortho-tiles`, `ortho-detect`, `ortho-materialise`,
  `ortho-detect-pv`, `ortho-refresh`, `ortho-juge-probe`, `ortho-juge-vlm`, `anc`, `vegetation-irc`,
  `vegetation`, `vegetation-validation`.
- **Autres** : `abuse-scan`, `nl-eval`.

### 3.2 API HTTP (FastAPI — 174 routes)
Lancée par `labuse api` (défaut port 8000 ; servie ici sur **8010**). L'app monte le front buildé sous
`/socle/` (`StaticFiles`, `frontend/dist`) et applique une compression gzip. Routes par router (détail
exhaustif méthode+chemin+rôle en CARTO_API) :

| Fichier | Préfixe | Routes | Domaine |
|---|---|---|---|
| `api/app.py` | `/` (app) | 66 | Cœur : fiche, recherche q_v2, geojson, tuiles, pipeline CRM, sources… |
| `api/modules.py` | `/modules` | 17 | Modules d'aide (M22 programme, faisabilité, viabilisation…) |
| `api/projets.py` | `/projets` | 16 | Copilote-projet : fiche cadrage, dérivation, parcours de tri, PDF |
| `api/events.py` | `/events` | 13 | Radar événementiel (BODACC…) |
| `api/partners.py` | `/partners` | 10 | Pack apporteur d'affaires |
| `api/segments.py` | `/segments` | 9 | Moteur de segments/vues |
| `api/moteurs.py` | `/moteurs` | 7 | Matching+, assemblage |
| `api/ia.py` | `/ia` | 6 | Copilote IA (recherche NL, synthèse, entretien cadrage) |
| `api/solaire.py`, `score_v2.py`, `ortho.py` | resp. | 5 each | Solaire, verdict v2, vignettes ortho |
| `api/protection.py`, `courrier.py` | resp. | 4 each | Protections (PPR/ABF…), courrier postal API |
| `api/tiles.py` | `/tiles` | 3 | Tuiles carto |
| `api/dossier.py`, `pre_dossier.py`, `fiche_ask.py` | resp. | 2/1/1 | Dossiers, /ask fiche |

**Tâches planifiées** : aucune tâche cron câblée dans le repo (le champ `derniere_execution_at` des
projets et les commentaires « prépa cron » indiquent un radar futur non branché). Voir Observations.

### 3.3 Scripts batch
- `scripts/` : utilitaires d'ingestion/ops (détail en CARTO_INFRA).
- `src/labuse/ingestion/run_all.py` : orchestration d'ingestion.
- `frontend/qa/*.mjs` (78) + `qa/*.mjs` (11) = **89 scripts Playwright** (E2E, QA, captures) tournant
  contre `http://127.0.0.1:8010/socle/`. `qa/golden_check.py` : contrôle de non-régression scoring.

---

## 4. Flux de données

Chaîne complète (source → tables → enrichissements → scoring P puis C → surfaces). Détail par fichier
en CARTO_INGESTION et CARTO_SCORING.

```
[1] SOURCES PUBLIQUES (connecteurs + ingesteurs)
    Cadastre (parcelles), BAN (adresses), DVF (mutations/prix), DPE (ADEME), BODACC (procédures),
    INPI/RNE (dirigeants PM), Géorisques (PPR/ICPE/cavités/mvt), GPU (zonage PLU/SUP), Mérimée (ABF),
    Cartofriches, QPV, RNIC (copro), SITADEL (permis), PVGIS/APER (solaire), ortho IGN (piscines/PV),
    LiDAR HD (pente/végétation), Cerema (conso ENAF)…
        │  connectors/*.py (clients HTTP)  +  ingestion/*.py (transforme + écrit)
        ▼
[2] TABLES SOCLE
    parcels (431 k), adresses (341 k), spatial_layers (1,3 M ; kind=ppr/icpe/abf/qpv/friche/mvt…),
    dvf_mutations*, dpe_records, bodacc_procedures, pm_dirigeants, parcelle_personne_morale,
    sitadel_permits, parcel_solar, parcel_vegetation, parcel_anc, parcel_viabilisation…
        ▼
[3] ENRICHISSEMENTS / FEATURES
    p_model_* (dataset, static, geo, filo, bati, dvf, copro, ext_*) — features par parcelle ;
    parcel_residuel(_bati) (SDP résiduelle) ; parcel_terrain (pente) ; parcel_amenites (OSM) ;
    parcel_zone_plu ; pm_proprietaires_millesimes (churn PM) ; adresse_parcelles.
        ▼
[4] SCORE P  (probabilité de mutation)
    scoring/p_model (features→WOE→modèle→scores)  →  scoring/p_v2/pipeline.run_score_v2
        →  parcel_p_score_v2 (1,3 M) : p_raw, mult_base (×N vs moyenne), percentile, rang, tier
           (brulante/chaude/reserve_fonciere/a_creuser/ecartee), icd (complétude cloisonnée).
    En parallèle : scoring/score_v (signaux VENDEUR : BODACC, âge dirigeant…) → parcel_v_score.
        ▼
[5] CASCADE + MATRICE  (accessibilité / exclusions)
    cascade/context.prime + cascade/layers/phase1.evaluate → cascade_results (9 M) /
    dryrun_cascade_results (77 M) : étage 0 = exclusions dures (status exclue/faux_positif_probable).
    scoring/dryrun (matrice Q×A) → dryrun_parcel_evaluations (2,4 M) : q_score, a_score,
    matrice_statut (chaude/a_surveiller/a_creuser), completeness_score, opportunity_score.
    Run de référence servi : run_label = q_v6_m8 (Q_A_RUN_LABEL, scoring/score_v_constants).
        ▼
[6] MATÉRIALISATION CARTE
    build-mvt → mvt_parcels (431 k) : la couche servie à la carte (verdict + tier figés par run).
        ▼
[7] SURFACES SERVIES (api/)
    A  — Fiche + /ask (fiche_ask, assistant) : question sourcée sur LA parcelle.
    B1 — /ia/search : recherche NL → filtres validés (nl_semantics).
    B2 — /ia/aggregate : questions agrégées SQL-sourcées (nl_aggregate).
    C  — Exports (export.py, pdf_premium, pdf_projet, dossier, partners) + modules (M22, faisabilité,
         solaire, segments/vues) + copilote-projet (projets.py : cadrage → parcours de tri → CRM).
```

**Doctrine transverse (récurrente dans le code)** : l'IA ne calcule ni ne modifie aucun score ; les
signaux « étage 1/2 » sont ingérés mais **pas encore branchés** au scoring (voir § 11 TODO).

---

## 5. Base de données

PostgreSQL + PostGIS, rôle `openclaw`, base `labuse`. **220 tables**, **6 vues métier**.

### 5.1 Tables cœur (colonnes clés)
| Table | Rôle | Colonnes clés |
|---|---|---|
| `parcels` | Parcelles cadastrales (431 k) | `idu`, `commune`, `geom`/`geom_2975`, `surface_m2`, `centroid`, `bbox` |
| `dryrun_parcel_evaluations` | Éval matrice Q×A servie (2,4 M) | `run_label`, `parcel_id`, `q_score`, `a_score`, `matrice_statut`, `completeness_score`, `opportunity_score`, `status` |
| `parcel_p_score_v2` | Score P v2 (1,3 M) | `run_id`, `parcelle_id`, `p_raw`, `mult_base`, `percentile`, `rang`, `tier`, `icd`, `top5_contributions` |
| `cascade_results` / `dryrun_cascade_results` | Résultats cascade (9 M / **77 M, 13 GB**) | `parcel_id`, `layer_name`, `result`, `severity`, `weight_applied`, `detail` |
| `spatial_layers` | Couches géo génériques (1,3 M) | `kind`, `subtype`, `geom`, `attrs` (jsonb), `commune` |
| `parcel_v_score` | Signaux vendeur (431 k) | `parcelle_id`, `v_score`, `v_band`, `owner_type`, `owner_siren`, `signals` (jsonb) |
| `projets` | Copilote-projet | `nom`, `fiche` (jsonb), `filtres` (jsonb), `programme` (jsonb), `statut`, `derniere_execution_at` |
| `projet_parcelles` | Statut parcelle×projet (tri) | `projet_id`, `parcel_id`, `statut` (proposee/retenue/ecartee/a_analyser), `rang` ; UNIQUE(projet_id,parcel_id) |
| `pipeline_entries` | CRM | `parcel_id`, `status`, `priority`, `prospection` (jsonb), `projet_id` ; UNIQUE(parcel_id) |
| `score_snapshots` / `score_snapshot_parcelles` | Gel de runs (1,7 M) | `label`, `run_label`, `brulante_threshold` |

### 5.2 Plus grosses tables (par taille disque)
`dryrun_cascade_results` (77 M lignes, **13 GB**) · `spatial_layers` (1,3 M, 2,7 GB) ·
`parcel_p_score_v2` (1,3 M, 2,1 GB) · `cascade_results` (9,2 M, 1,8 GB) · `p_model_ext_dataset`
(4,3 M, 1,5 GB) · `adresses` (341 k, 951 MB) · `p_model_dataset` (2,2 M, 769 MB) ·
`dryrun_parcel_evaluations` (2,4 M, 624 MB) · `parcels` (431 k, 457 MB). Familles volumineuses :
`p_model_*` (features), `parcel_*` (enrichissements 1:1 parcelle), snapshots `m6_*` (backups PLU/mvt).

### 5.3 Vues métier (6)
- `v_parcelles_brulantes` — jointure parcels × dryrun_eval × v_score (le verdict « brûlante »).
- `v_foncier_sous_pression` — PM × BODACC (procédures collectives → pression).
- `v_foncier_propension_vendre` / `v_pm_propension_vendre` — âge dirigeant / churn PM → propension.
- `v_passoire_thermique` — DPE F/G rattachés parcelle.
- `v_parcel_dvf_last` — dernière mutation DVF par parcelle.

(4 vues système PostGIS : `geometry_columns`, `geography_columns`, `raster_columns`, `raster_overviews`.)
Le schéma ORM = **34 classes `__tablename__`** dans `models.py` (1 349 l) ; **19 fonctions `ensure_*`**
créent en outre ~9 tables/vues en **SQL brut** (hors ORM : `parcelle_personne_morale`, alertes,
signalements…). Détail : voir CARTO_CORE.

---

## 6. Dépendances externes

### 6.1 Backend (`requirements.txt`)
`SQLAlchemy>=2.0`, `GeoAlchemy2>=0.14`, `psycopg[binary]>=3.1`, `pydantic>=2.5`, `pydantic-settings>=2.1`,
`PyYAML>=6.0`, `fastapi>=0.110`, `uvicorn[standard]>=0.27`, `httpx>=0.26`, `shapely>=2.0`, `pyproj>=3.6`,
`pyshp>=2.3`, `typer>=0.9`, `jsonschema>=4.21`, `opencv-python-headless>=4.9`, `numpy>=1.26`,
`openpyxl>=3.1`, `pytest>=8.0`, `weasyprint>=61`, `jinja2>=3.1`, `stripe>=8`, `pypdf>=5`.
**ML séparé** (`requirements-ml.txt`, ~2 Go, hors `labuse api`) : `torch>=2.2`, `scikit-learn>=1.4`.

### 6.2 Frontend (`package.json`)
Deps : `react@^18.3.1`, `react-dom@^18.3.1`, `@tanstack/react-query@^5.59`, `maplibre-gl@^4.7.1`,
`zustand@^5.0`. Dev : `vite@^5.4.9`, `typescript@^5.6.3`, `tailwindcss@^3.4.14`, `playwright@^1.61`,
`@vitejs/plugin-react`, `postcss`, `autoprefixer`.

### 6.3 Services/API externes appelés
(Domaines identifiés par grep — détail « fichier appelant → URL » en CARTO_INGESTION et CARTO_API.)
- **Anthropic** (copilote IA) — clé `ANTHROPIC_API_KEY`, `ai/core.py`.
- **Stripe** (module flash) — clé `STRIPE_SECRET_KEY`, `flash/`.
- **BAN** (adresses), **DVF/DGFiP**, **ADEME** (DPE), **BODACC**, **INPI/RNE** (auth `INPI_API_*`),
  **Géorisques**, **GPU/IGN Géoplateforme** (zonage/SUP), **Mérimée**, **Cerema** (Cartofriches/CONSOENAF),
  **PVGIS**, **EDF SEI/ORE** (Data Fair), **OSM/Overpass** (aménités), **Merci Facteur** (courrier).

---

## 7. Dépendances internes (carte des imports)

Imports entre sous-paquets `src/labuse/` (granularité paquet) :

```
(root)     → ai, api, cascade, connectors, faisabilite, ingestion, ml, scoring, segments
api        → ai, cascade, connectors, faisabilite, flash, ingestion, scoring, segments
scoring    → api, cascade, connectors
cascade    → ai, faisabilite, scoring
ingestion  → cascade, connectors, segments
segments   → connectors, faisabilite, ingestion, scoring
faisabilite→ (feuille, peu de deps internes)
ai         → segments
flash      → api, scoring
ml         → ingestion
```

**Paires bidirectionnelles (cycles au niveau paquet)** — fait brut :
- `cascade ↔ scoring`
- `scoring ↔ api`
- `ingestion ↔ segments`
- `flash ↔ api`

Ces cycles sont majoritairement résolus par des **imports différés** (`from .app import …` /
`from ..modules import …` **à l'intérieur des fonctions**, pattern récurrent : `api/projets.py`,
`scoring/*`, `cascade/*`). Constat, pas verdict.

---

## 8. Tests

Suite **pytest** dans `tests/` : **107 fichiers `test_*.py`, 865 fonctions de test**. Marqueurs
`pytest.mark.db` et `network`. Commande : `pytest`. Contournement PROJ documenté
(`PROJ_DATA=…/share/proj`). E2E/QA **Playwright** : **89 scripts `.mjs`** (78 dans `frontend/qa/`,
11 dans `qa/`), autonomes contre `127.0.0.1:8010/socle/`. Non-régression scoring : `qa/golden_check.py`.
**Fait brut** : **85 des ~180 modules `src/labuse` ne sont importés par AUCUN test** en direct
(couverture indirecte via fixtures/endpoints non exclue). Détail : **CARTO_INFRA**.

---

## 9. Configuration

- **Config métier** : **23 fichiers dans `config/`** (22 YAML + `bilan_calibration_vic.csv`) —
  matrice scoring, poids mutation/opportunité, cascade, complétude, segments, PLU par commune, EPCI,
  PLH, courrier… — **+ 24 manifestes dans `config/calibrage/`**. Détail fichier→consommateur : **CARTO_INFRA**.
- **Variables d'environnement** (noms uniquement, valeurs jamais dans ces docs) : `LABUSE_DATABASE_URL`
  (défaut code : `postgresql+psycopg://labuse:labuse@localhost:5432/labuse`), `ANTHROPIC_API_KEY`,
  `STRIPE_SECRET_KEY`, `INPI_API_*`, `LABUSE_DEV_MODE`, `PROJ_DATA`. Fichiers : `.env` (racine, non
  versionné), `.env.example`, `.env.pilot.example`. Emplacement des secrets : `.env` racine.
- **Dev/prod** : dev = Vite racine + `labuse api` local ; prod = build Vite `/socle/` servi par FastAPI,
  Docker + Caddy (voir `deploy/`, `docker-compose.pilot.yml`, `docker-compose.caddy.yml`).

---

## 10. Histoire du code

Repo actif du **2026-06-07** au **2026-07-20** — **877 commits** sur ~6 semaines. Strates M6→M11
visibles dans les noms de rapports/mandats (RAPPORT_*, MANDAT_FABLE_*). Dernier commit par sous-paquet :

| Sous-paquet | Dernier commit | Commits |
|---|---|---|
| `src/labuse/api` | 2026-07-20 | 244 |
| `src/labuse/ingestion` | 2026-07-14 | 87 |
| `src/labuse/cascade` | 2026-07-14 | 41 |
| `src/labuse/scoring` | 2026-07-15 | 37 |
| `src/labuse/faisabilite` | 2026-07-14 | 33 |
| `src/labuse/connectors` | 2026-07-11 | 24 |
| `src/labuse/segments` | 2026-07-11 | 12 |
| `src/labuse/ai` | 2026-07-15 | 7 |
| `src/labuse/flash` | 2026-07-15 | 6 |
| `src/labuse/ml` | 2026-07-11 | 3 |

`api/` est la strate la plus mouvante (244 commits, actif jusqu'au dernier jour). `ml/`, `flash/`,
`segments/` sont les plus stables. Détail par répertoire dans chaque annexe.

---

## 11. Métriques brutes

### 11.1 Top 20 fichiers les plus longs (`src/`)
```
2983  api/app.py            793  cascade/layers/phase1.py   499  api/export.py
2171  cli.py                722  api/ia.py                  493  api/protection.py
1349  models.py             694  api/projets.py             484  ingestion/vegetation.py
1033  api/modules.py        655  api/enrichment.py          474  flash/data.py
1032  ingestion/layers_ingest.py  604  scoring/score_v.py   465  scoring/p_model/sql.py
                            564  cascade/context.py         525  segments/registry.py
                            520  faisabilite/bilan.py       443  api/moteurs.py
                                                            440  api/partners.py
```

### 11.2 Top 20 fonctions les plus longues (lignes)
```
313  api/pdf_premium.py:96      render_fiche_pdf()      146  scoring/p_v2/pipeline.py:164  run_score_v2()
247  faisabilite/engine.py:125  estimate_capacity()     141  scoring/p_model/sql.py:166    build_static()
214  cascade/context.py:71      prime()                 138  scoring/p_model/ext_sql.py:150 build_ext_dataset()
210  faisabilite/bilan.py:248   compute_bilan()         130  api/app.py:1093               _q_v2_geojson()
181  scoring/score_v.py:396     compute_all()           127  cascade/layers/phase1.py:210  evaluate()
174  api/app.py:1440            _q_v2_fiche()           119  ingestion/demo_saint_paul.py:87 seed_demo()
170  api/app.py:2070            _build_fiche()          119  api/export.py:20              fiche_markdown()
148  scoring/p_model/sql.py:309 build_dataset()         113  api/fiche_ask.py:52           _ask_context()
147  segments/engine.py:89      build()                 110  api/export.py:141             fiche_html()
                                                        109  api/pdf_projet.py:45          render_projet_pdf()
```

### 11.3 TODO / FIXME / HACK / XXX
**47** occurrences dans `src/labuse` (+ front). **Quasi-totalité = marqueurs de doctrine
`# TODO étage 1/2/bilan`** : un signal est ingéré mais **volontairement non branché au scoring**
(`models.py`, `cli.py`, `ingestion/{bodacc,inpi_rne,abf_merimee,georisques_layers,cartofriches,amenites,qpv,seed_sources}.py`,
`scoring/{declassement,score_v_constants}.py`). Exceptions notables non-« étage » :
- `ingestion/vegetation.py:23` — `TODO v1.1 : pondération directionnelle` (végétation omnidirectionnelle).
- `scoring/score_v_constants.py:72-76` — `# TODO v2` sur les poids BODACC (LJ/RJ/sauvegarde non tranchés).
Aucun `FIXME`/`HACK`/`XXX` classique repéré (les marqueurs sont des jalons doctrinaux, pas des alertes).

### 11.4 Modules `src/labuse` apparemment jamais importés (approx.)
Scan statique (regex sur `from … import` / `import …`) — **inclut les entrées CLI et les modules
chargés dynamiquement**, donc à interpréter avec prudence. Le brut : `cli.py` (point d'entrée),
`cascade/layers/{phase1,phase2,etage1,etage2}.py`, `scoring/p_model/{evaluate,shadow}.py`,
`ingestion/{dvf_histo,permit_delais_m10,pm_millesimes,pv_detection}.py`, `ml/juge_flair.py`, `geo.py`,
`prospection.py`. **Après vérification des annexes** : `cascade/layers/phase1.py` est en réalité **le
cœur** de la cascade (18 couches d'exclusion) — faux positif du regex ; les commandes CLI
(`dvf_histo`, `permit_delais_m10`, `pm_millesimes`, `pv_detection`) sont invoquées via `cli.py`, pas
importées ; **`scoring/p_model/shadow.py` est confirmé orphelin** (utilisé par des scripts seulement,
selon l'annexe SCORING). Les annexes affinent par domaine.

### 11.5 Candidats à duplication (constat, pas verdict)
- Trois modules `nl_*` côté API (`nl_aggregate.py`, `nl_semantics.py`) + `ia.py` — traitement NL réparti.
- Deux ingesteurs de permis : `ingestion/permits.py` et `ingestion/permits_sdes.py`.
- Familles `solaire_*` (7 modules ingestion) et `ortho_*` (5 ingestion + `api/ortho.py`).
- Deux modules de génération PDF : `api/pdf_premium.py` et `api/pdf_projet.py`.
- `faisabilite/db.py` et `api/*` partagent la construction de « fiche_payload »/`_build_fiche`.
- Fonctions homonymes redéfinies dans plusieurs modules scoring/cascade : `_osm_label`, `_er_split`,
  `_trace` (relevé par l'annexe SCORING).
- Deux tables résiduel proches : `parcel_residuel` et `parcel_residuel_bati`.
- Snapshots `m6_*` en base (`m6_snapshot_mvt_post2a/2b`, `m6_a02_backup_plu_dup`) = copies de travail.

---

## 12. Observations factuelles

- **`api/app.py` = 2 983 lignes, 66 routes** : le plus gros fichier et le routeur principal (fiche,
  recherche q_v2, geojson, tuiles, CRM, sources) concentré en un module.
- **`cli.py` = 2 171 lignes, 78 commandes** : second plus gros fichier ; couvre ingestion, scoring, ops.
- **Cycles d'imports au niveau paquet** (cascade↔scoring, scoring↔api, ingestion↔segments, flash↔api),
  résolus par imports différés dans les fonctions.
- **Doctrine « étage 0/1/2 » omniprésente** : l'étage 0 (cascade) = exclusions dures qui comptent ;
  les étages 1/2 = signaux ingérés mais non branchés (47 marqueurs `# TODO étage`).
- **Run servi figé** : `q_v6_m8` (`Q_A_RUN_LABEL`) — les surfaces lisent ce run, pas un recalcul live.
- **Volumétrie cascade** : `dryrun_cascade_results` seule pèse 13 GB / 77 M lignes (dominant la base).
- **220 tables pour ~60 k lignes de Python** : forte densité relationnelle ; beaucoup de tables 1:1
  parcelle (`parcel_*`, `p_model_*`) à 431 658 lignes (= nombre de parcelles).
- **Assets** : ~25 000 images (tuiles/vignettes ortho) versionnées ou présentes sous `data/`.
- **Aucune tâche planifiée câblée** : le « radar cron » est préparé (champs, commentaires) mais non actif.
- **274 fichiers `.md`** (dont ~90 à la racine) : documentation abondante, strates M5→M11.

---

## Fin de mission

### Fichiers produits
- `docs/cartographie/CARTOGRAPHIE.md` (ce document — sections transverses + synthèse).
- `docs/cartographie/CARTO_SCORING.md` — scoring P/C, cascade, segments, mutation, faisabilité.
- `docs/cartographie/CARTO_INGESTION.md` — ingestion, connecteurs, `data/`.
- `docs/cartographie/CARTO_API.md` — API FastAPI, socle IA, flash.
- `docs/cartographie/CARTO_FRONT.md` — frontend React/TS + QA Playwright.
- `docs/cartographie/CARTO_CORE.md` — CLI, `models.py`, config, helpers transverses.
- `docs/cartographie/CARTO_INFRA.md` — config/, tests/, scripts/, deploy/, docker, docs.

### 5 zones où la description est la moins certaine
1. **Chaîne exacte P → C → matrice** (§4) : l'ordre précis et les tables intermédiaires entre
   `p_model`, `p_v2/pipeline`, la cascade et `dryrun_evaluate` sont reconstitués par lecture partielle —
   à confirmer via CARTO_SCORING (agent dédié).
2. **Modules « jamais importés » (§11.4)** : scan regex approximatif ; les modules chargés
   dynamiquement (couches cascade) et les commandes CLI y apparaissent à tort comme orphelins.
3. **APIs externes exactes (§6.3)** : domaines identifiés par grep ; l'appariement précis
   « endpoint externe ↔ fichier ↔ table » est affiné dans les annexes, pas exhaustivement vérifié ici.
4. **Volumétrie « lignes » des tables** : `reltuples` (estimation de l'optimiseur Postgres), pas un
   `COUNT(*)` exact.
5. **`config/` → consommateur** : le rattachement de chaque YAML au module qui le lit est délégué à
   CARTO_INFRA (agent) et non revérifié centralement.
```
