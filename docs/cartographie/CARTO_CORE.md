# CARTO_CORE — Cœur / Plomberie de LA BUSE

> Cartographie factuelle (lecture seule) du domaine CŒUR de `src/labuse/` :
> point d'entrée CLI, modèles ORM, configuration, helpers transverses.
> Périmètre = les `.py` à la RACINE de `src/labuse/` (27 fichiers). Les sous-paquets
> `api/`, `scoring/`, `ingestion/`, `faisabilite/`, `cascade/`, `segments/`, `ai/`,
> `flash/` sont HORS périmètre.

---

## 1. Rôle de cette couche

Cette couche est la **plomberie transverse** de l'application. Elle regroupe :

- **Le point d'entrée opérateur** : `cli.py`, une application Typer de **78 commandes**
  (`@app.command`) — ingestion des données, scoring/dry-run, waves ortho/solaire,
  exploitation (backup, doctor, api…). C'est l'interface unique en ligne de commande.
- **Le modèle de données ORM** : `models.py`, **34 classes SQLAlchemy** + **19 fonctions
  DDL `ensure_*`** qui créent en SQL brut les vues et 9 tables complémentaires. Stockage
  géométrique en EPSG:4326, mesures via `ST_Transform(geom, 2975)`.
- **La configuration** : `config.py` (settings Pydantic, préfixe `LABUSE_`, chargement
  YAML des règles/poids), `db.py` (engine/session PostGIS), `enums.py` (vocabulaires
  contrôlés), `constants.py`, `numeric.py`.
- **Les helpers métier transverses** (19 fichiers) consommés surtout par `api/` : audit à
  la demande, assemblage foncier, bâti, communes, courrier, démo, géométrie, loyers,
  mutation, marché (obsimmo), occupation, plans/quotas, PLH, règlement PLU, type de
  propriétaire, prospection, shortlist promoteur, alertes, état de la base.

Invariant récurrent dans le code : les commandes d'ingestion « NE touchent PAS au score »
(marqueurs `# TODO étage 1/2`) ; les règles et poids vivent en YAML (`config/*.yaml`), jamais
en dur.

---

## 2. `cli.py` — les 78 commandes (2171 lignes)

Point d'entrée Typer. Dernière modification : **2026-07-15 11:30:17 +0200**.
Liste exhaustive, groupée par thème.

### Socle / schéma
| Commande | Rôle |
|---|---|
| `init-db` | Crée l'extension PostGIS et toutes les tables. |
| `seed-sources` | Injecte le catalogue des sources de données. |
| `bilan-calibrate` | Injecte les valeurs de bilan (par secteur, upsert CSV). |
| `seed-demo` | Seed d'une base de démo. |

### Ingestion (données réelles & couches)
| Commande | Rôle |
|---|---|
| `ingest-real` | Ingestion RÉELLE : cadastre bulk Etalab + couches structurantes live. |
| `ingest-island` | Ingestion + évaluation des 24 communes, en série et reprenable. |
| `ingest-permits` | Autorisations d'urbanisme SITADEL (API Région Réunion ODS). |
| `geocode-permits` | Géolocalise les permis SITADEL non géocodés (API Carto, par section). |
| `ingest-personnes-morales` | Propriétaires personnes morales (fichier DGFiP, Licence Ouverte). |
| `ingest-inpi-rne` | Dirigeants RNE des PM foncières (signal âge dirigeant). |
| `ingest-inpi-gigogne` | Résout l'âge dirigeant des SIREN sans dirigeant physique direct (depth-1). |
| `ingest-georisques` | Couches Géorisques (sites pollués, cavités, ICPE…) → spatial_layers. |
| `ingest-cartofriches` | Friches Cartofriches (Cerema) → spatial_layers kind='friche'. |
| `ingest-dpe` | DPE ADEME (logements existants) → dpe_records (rattachement local). |
| `ingest-mvt` | Mouvements de terrain Géorisques → spatial_layers kind='mvt'. |
| `ingest-qpv` | QPV 2024 (ANCT) → spatial_layers kind='qpv' (bilan promoteur). |
| `ingest-amenites` | Aménités OSM (école/santé/commerce/tcsp) → spatial_layers + distances. |
| `ingest-abf` | Abords ABF (base Mérimée, tampon ~500 m) → spatial_layers kind='abf'. |
| `ingest-sup` | Assiettes SUP (GPU/API Carto) → spatial_layers kind='sup'. |
| `ingest-bruit-route` | Classement sonore (Cerema) → spatial_layers kind='bruit_route'. |
| `ingest-cinquante-pas` | Limite haute des 50 pas géométriques (DEAL) → kind='cinquante_pas'. |
| `ingest-rnic` | Copropriétés RNIC 974 → rnic_coproprietes. |
| `rnic-complements` | Compléments RNIC sans CSV + purge RGPD des syndics. |
| `ingest-catnat` | Arrêtés CATNAT GASPAR (Géorisques) → catnat_arretes. |
| `ingest-ban` | BAN 974 → table `adresses` rattachée aux parcelles. |

### Scoring & évaluation
| Commande | Rôle |
|---|---|
| `evaluate` | Fait tourner la cascade + le scoring et persiste les évaluations. |
| `dryrun-evaluate` | DRY-RUN étages 1+2 dans les tables PARALLÈLES `dryrun_*`. |
| `dryrun-report` | Livrable d'un run dry-run : distributions, top, contrôle traçabilité. |
| `matrice-simulate` | SIMULATION à blanc de conventions de matrice (aucune écriture). |
| `matrice-apply` | Applique la convention versionnée (config/scoring_matrice.yaml). |
| `build-mvt` | (Re)construit `mvt_parcels` servie en tuiles vectorielles. |
| `dryrun-matrice` | Post-pass matrice Q×A (étape 3) sur un run dry-run existant. |
| `score-v2` | Scoring v2 production (artifact M3.6 gelé, sha256 vérifié). |
| `score-v-fetch` | Récupère les données externes du Score V (resumable, cache). |
| `score-v-compute` | Calcule le Score V (Vendabilité) → parcel_v_score. |
| `detect-events` | Diffe deux runs → événements (bascules, BODACC, permis proches). |
| `monitor-forward` | Monitoring forward mensuel : hits du top gelé vs nouvelles mutations. |
| `viabilisation` | Construit parcel_viabilisation (indicateur de viabilisation). |
| `compute-residuel` | Calcule/cache le potentiel résiduel (filtre sous-densité). |
| `dvf-marche` | Recalcule les médianes €/m² par secteur × type de bien. |

### Segments
| Commande | Rôle |
|---|---|
| `segments-seed` | Tables du moteur de segments + seed des presets manquants. |
| `segments-counts` | Compteurs live de parcelles par preset (cache 24 h). |
| `segments-residuel` | Droits résiduels sur parcelles bâties → parcel_residuel_bati. |

### Habitat Solaire (wave habitat-solaire)
| Commande | Rôle |
|---|---|
| `solaire-pvgis` | Baseline PVGIS (grille ~400 m, E_y par point, SARAH3). |
| `solaire-flags` | Flags de qualification (amiante DPE pré-1997…). |
| `solaire-conso` | Baseline EDF SEI (conso résidentielle par commune). |
| `solaire-tertiaire` | Vue matérialisée toitures tertiaires > 500 m². |
| `solaire-parkings` | Parkings assujettis loi APER (OSM). |
| `solaire-pv-registry` | Registre national des installations (extrait 974). |
| `solaire-grid-capacity` | Capacités d'accueil réseau EDF SEI (best effort). |
| `solaire-cache-purge` | Purge STRICTE du cache Google Solar API (ToS 30 j). |

### Ortho / piscines & PV (wave-ortho)
| Commande | Rôle |
|---|---|
| `ortho-pente` | Pente de la partie non bâtie des parcelles bâties (checkpoint). |
| `ortho-tiles` | Grille 512 m (bâti ∪ parkings) + acquisition BD ORTHO 20 cm. |
| `ortho-detect` | Détection piscines V0 (HSV calibré) sur les tuiles. |
| `ortho-materialise` | Matérialise parcel_equipements depuis les détections + signal piscine. |
| `ortho-detect-pv` | Détection PV V0 sur emprises bâties + parkings. |
| `ortho-refresh` | Re-survol BD ORTHO 974 (~3-4 ans). |
| `ortho-juge-probe` | Cascade de juges étage 1 : probe linéaire (DINOv2 + logreg). |
| `ortho-juge-vlm` | Cascade de juges étage 2 : juge VLM (Haiku 4.5, prompt binaire). |

### ANC & Végétation (wave-anc-vegetation)
| Commande | Rôle |
|---|---|
| `anc` | Couche probabiliste ANC (INSEE EGOUL RP2022). |
| `vegetation-irc` | Acquisition BD ORTHO IRC sur la grille ortho. |
| `vegetation` | NDVI (IRC) × MNH LiDAR HD streamé par tuile. |
| `vegetation-validation` | Session de validation : 20 vignettes « végétation haute en limite ». |

### Adresses / anti-abus / NL (wave-adresses)
| Commande | Rôle |
|---|---|
| `abuse-scan` | Score quotidien des patterns de scraping → abuse_scores. |
| `nl-eval` | Évalue la recherche NL sur le jeu de test d'acceptation. |
| `warm-vue-mer` | Pré-chauffe le cache VUE MER (parcelles littorales). |

### Démo / exploitation / diagnostic
| Commande | Rôle |
|---|---|
| `rebuild-demo` | Reconstruit une base de démo cohérente et idempotente. |
| `demo-healthcheck` | Vérifie que la base est prête pour une démo (exit ≠ 0 si couche manquante). |
| `warm-demo` | Pré-chauffe le cache d'enrichissement + vérifie verdicts & exports. |
| `doctor` | Diagnostic complet : DB → schéma → données → démo. |
| `prepare-pilot` | Une commande pour préparer un pilote/démo (schéma → rebuild → …). |
| `discover` | Vue Découverte (offre B) : cascade sur la commune → survivantes classées. |
| `sources` | Page Sources de données : statut de chaque connecteur. |
| `test-source` | Bouton « tester la connexion » : tente l'appel réel. |
| `watch` | Veille (offre C) : snapshot/delta → signaux + ré-évaluation. |
| `backup-db` | Sauvegarde complète (pg_dump format custom compressé). |
| `restore-db` | Restaure une sauvegarde (pg_restore --clean : ÉCRASE l'existant). |
| `api` | Lance l'API FastAPI (uvicorn). |

> Compte : `grep -c '@app.command(' cli.py` = **78**.

---

## 3. `models.py` — modèles ORM (1349 lignes)

Dernière modification : **2026-07-15 22:53:01 +0200**. `SRID = 4326` (stockage),
`SRID_M = 2975` (RGR92 UTM 40S, mesures). `_enum()` = colonne VARCHAR+CHECK stockant la
VALEUR de l'enum. `TimestampMixin` fournit `created_at`/`updated_at`.

### 3.1 Cadastre & socle d'évaluation
| Classe → table | Colonnes clés | Contraintes / index |
|---|---|---|
| `Parcel` → `parcels` | idu(14), commune, section, numero, geom(4326), geom_2975, surface_m2, centroid, bbox, origine | idu unique+index ; commune index ; geom GIST |
| `DataSource` → `data_sources` | name(unique), category, provider, access_type, status(enum), reliability_level(enum), rate_limit, legal/technical_notes | name unique |
| `ParcelSourceResult` → `parcel_source_results` | parcel_id(FK), data_source_id(FK), status(enum), raw_payload(JSONB), confidence_level(enum) | Index (parcel_id, data_source_id) |
| `CascadeResult` → `cascade_results` | parcel_id(FK), layer_name, result(enum), severity(enum), weight_applied(signé), detail(motif humain), data_source_id(FK) | Index parcel_id — « la traçabilité EST le produit » |
| `ParcelEvaluation` → `parcel_evaluations` | parcel_id(FK), completeness_score, opportunity_score, status(enum), ai_payload(JSONB), model_version, rules_version | CHECK 0-100 (×2) ; Index (parcel_id, evaluated_at) |
| `IngestionRun` → `ingestion_runs` | commune, data_source_id(FK), started/finished_at, parcels_count, status | — |

### 3.2 Dry-run scoring (tables PARALLÈLES, jamais lues par l'app)
| Classe → table | Colonnes clés | Contraintes / index |
|---|---|---|
| `DryrunParcelEvaluation` → `dryrun_parcel_evaluations` | run_label, parcel_id(FK), completeness/opportunity_score, opportunity_base, status, q_score, a_score, a_completude, matrice_statut | UniqueConstraint(run_label, parcel_id) |
| `DryrunCascadeResult` → `dryrun_cascade_results` | run_label, parcel_id(FK), layer_name, result, severity, weight_applied, source_table, source_id, evenement | Index (run_label, parcel_id) + index PARTIEL where evenement='rouge' |

### 3.3 Scoring V / P v2 & snapshots
| Classe → table | Colonnes clés | Contraintes / index |
|---|---|---|
| `ParcelVeilleSuccession` → `parcel_veille_succession` | parcelle_id(14, PK), siren, dirigeant_age, sci_dormante | radar patrimonial, hors Score V |
| `ScoreSnapshot` → `score_snapshots` | label(unique), run_label, brulante_threshold, notes | label jamais écrasé |
| `ScoreSnapshotParcelle` → `score_snapshot_parcelles` | snapshot_id(FK), parcelle_id, statut, v_score, v_band, brulante, veille_succession | index snapshot_id, parcelle_id |
| `ParcelVScore` → `parcel_v_score` | parcelle_id(PK), v_score(0-100/NULL), v_band, v_coverage, v_confidence, owner_type/siren/denomination, signals(JSONB) | Index v_band, owner_siren |
| `PScoreV2Run` → `p_score_v2_runs` | run_id(PK), model_version, model_sha256, params(JSONB), n_parcelles, snapshot_label | run_id unique, refus si existant |
| `ParcelPScoreV2` → `parcel_p_score_v2` | run_id, parcelle_id, p_raw, mult_base, percentile, rang, contrib_z/d, top5_contributions, copro, tier, icd, icd_detail | UniqueConstraint(run_id, parcelle_id) ; index (run_id, rang), (run_id, tier). ICD cloisonné du score P |

### 3.4 Panel PM / matching propriétaires (Score V)
| Classe → table | Colonnes clés | Contraintes / index |
|---|---|---|
| `PmProprietaireMillesime` → `pm_proprietaires_millesimes` | millesime, idu(14), groupe, forme_juridique, denomination, siren | UniqueConstraint(millesime, idu) ; panel point-in-time 2021-2024 |
| `PmDirigeant` → `pm_dirigeants` | siren, representant_id, type_personne, nom, prenoms, date_naissance('YYYY-MM'), role, gerant_siren, diffusible | UniqueConstraint(siren, representant_id) ; index siren. RGPD |
| `PmDirigeantGigogne` → `pm_dirigeant_gigogne` | siren(cible), gerant_siren, representant_id, nom, prenoms, date_naissance | UniqueConstraint(siren, gerant_siren, representant_id) ; depth-1 |
| `OwnerEnrichment` → `owner_enrichment` | siren(PK), denomination, source, payload(JSONB) | cache resumable par SIREN |
| `OwnerDenomLookup` → `owner_denom_lookup` | denomination_norm(PK), status, siren, candidats(JSONB) | cache matching par dénomination |
| `BodaccAnnonceOwner` → `bodacc_annonces_owner` | id(PK «ODS:siren»), siren, famille, nature, date_annonce, payload | Index siren ; toutes familles |
| `MatchingReviewQueue` → `matching_review_queue` | parcelle_id, denomination, candidats(JSONB) | file de revue humaine |

### 3.5 Signaux externes (BODACC, DPE, permis, DVF, aménités)
| Classe → table | Colonnes clés | Contraintes / index |
|---|---|---|
| `BodaccProcedure` → `bodacc_procedures` | annonce_id, siren, type_procedure, famille_jugement, date_annonce, tribunal | UniqueConstraint(annonce_id) ; index siren |
| `DpeRecord` → `dpe_records` | numero_dpe, etiquette_dpe/ges, type_batiment, surface_habitable, parcelle_idu, rattachement | UniqueConstraint(numero_dpe) ; index code_insee, parcelle_idu |
| `SitadelPermit` → `sitadel_permits` | permit_id, type(PC/PA/PD/DP), date, idu_codes(JSONB 1..3), geom(POINT) | Index commune |
| `DvfMutation` → `dvf_mutations` | mutation_id, date_mutation, valeur_fonciere, type_local, surface_*, geom(POINT) | Index commune ; requête par rayon |
| `DvfMutationParcelle` → `dvf_mutations_parcelle` | id(BigInt), id_mutation, id_parcelle(14), valeur_fonciere, millesime | Index id_parcelle, date ; millésimes 2021-2025 |
| `ParcelAmenite` → `parcel_amenites` | parcel_id(FK), dist_ecole/sante/commerce/tcsp_m | UniqueConstraint(parcel_id) |

### 3.6 Couches spatiales & veille
| Classe → table | Colonnes clés | Contraintes / index |
|---|---|---|
| `SpatialLayer` → `spatial_layers` | kind, subtype, name, geom(4326), geom_2975, attrs(JSONB), commune | Index kind ; (kind, subtype). Cascade phase 1 |
| `ParcelSignal` → `parcel_signals` | parcel_id(FK), signal_type(enum), payload(JSONB), detected_at, notified_at | offre C |
| `ParcelFeedback` → `parcel_feedback` | parcel_id(FK), user_id, verdict(enum), comment | — |
| `WatchSnapshot` → `watch_snapshots` | parcel_id(FK, unique), gpu_zone, dvf_last, permit_last | veille : photo comparée pour deltas |
| `SourceCheck` → `source_checks` | data_source_id(FK), verified_at, note | index data_source_id ; vide tant que non audité |

### 3.7 Pipeline & projets (prospection)
| Classe → table | Colonnes clés | Contraintes / index |
|---|---|---|
| `PipelineEntry` → `pipeline_entries` | parcel_id(FK), status, priority, notes, reminder_date, prospection(JSONB), projet_id(FK) | UniqueConstraint(parcel_id) |
| `Projet` → `projets` | nom, fiche(JSONB), filtres(JSONB), programme(JSONB), statut, derniere_execution_at | copilote-projet |
| `ProjetParcelle` → `projet_parcelles` | projet_id(FK), parcel_id(FK), statut(proposee/retenue/ecartee/a_analyser), rang, proposee_at | UniqueConstraint(projet_id, parcel_id) ; parcours Tinder |

### 3.8 Tables & vues créées en SQL brut par les fonctions `ensure_*`
`create_all()` appelle 19 fonctions `ensure_*` idempotentes. Tables `CREATE TABLE IF NOT
EXISTS` : `signalements` (QA humaine, M9), `parcel_enrichment`, `parcel_vue_mer`,
`bilan_params`, `parcelle_personne_morale` (situation 2025, prod), `saved_filters`,
`watch_zones`, `alertes`, `parcel_residuel`. Ces fonctions créent aussi les vues :
`v_foncier_sous_pression` (bodacc), `v_pm_propension_vendre`, `v_passoire_thermique`,
la vue Score V, la vue dvf-marché, plus les colonnes ICD (`ensure_icd_columns`) et la
maintenance `geom_2975` par trigger (`ensure_geom_2975`).

---

## 4. `config.py` — settings & variables d'environnement (221 lignes)

`Settings(BaseSettings)`, préfixe **`LABUSE_`**, `.env` chargé depuis la racine du dépôt.
Modifié : **2026-07-11 23:27:55 +0200**. Variables (NOMS uniquement, aucun secret) :

**Base & déploiement**
- `LABUSE_DATABASE_URL` — URL PostgreSQL/PostGIS.
- `LABUSE_ENV` — local | pilot | production.
- `LABUSE_AUTH_PASSWORD` — mot de passe pilote (clair ou `sha256:…`) ; absent hors local → routes métier 503 (fail-closed).
- `LABUSE_SECRET_KEY` — signature des cookies de session.
- `LABUSE_SESSION_HOURS`, `LABUSE_PUBLIC_URL`, `LABUSE_CONFIG_DIR`, `LABUSE_HTTP_TIMEOUT_S`.
- `LABUSE_PILOT_COMMUNE_INSEE`, `LABUSE_PILOT_COMMUNE_NAME`.

**Agent IA**
- `LABUSE_AI_PROVIDER` (défaut `stub`), `LABUSE_AI_MODEL` (défaut `claude-sonnet-4-6`).

**Protection / quotas (anti-scraping, plans)**
- `LABUSE_QUOTA_FICHES_JOUR`, `LABUSE_RATE_LIMIT_RPM`, `LABUSE_DEV_MODE`, `LABUSE_TRUSTED_PROXIES`, `LABUSE_RATE_BURST_GEL`, `LABUSE_ABUSE_ALERT_SEUIL`, `LABUSE_NL_QUOTA_JOUR`, `LABUSE_DOSSIER_QUOTA_MOIS`, `LABUSE_PLAN_DEFAUT`, `LABUSE_RAISON_SOCIALE`, `LABUSE_ETIQUETTES_FORMAT`.

**Courrier postal (Merci Facteur)**
- `LABUSE_COURRIER_PROVIDER`, **`LABUSE_MERCIFACTEUR_API_KEY`**, **`LABUSE_MERCIFACTEUR_API_SECRET`**, `LABUSE_COURRIER_COUT_LETTRE_EUR`, `LABUSE_COURRIER_MARGE`, `LABUSE_COURRIER_MAX_JOUR`.

**Habitat Solaire / PVGIS / Google Solar**
- `LABUSE_TARIF_ELEC_EUR_KWH`, `LABUSE_PVGIS_VERSION`, `LABUSE_PVGIS_GRID_STEP_M`, `LABUSE_PVGIS_RPS`, **`LABUSE_SOLAR_API_KEY`**, `LABUSE_SOLAR_API_CACHE_TTL_JOURS`, `LABUSE_SOLAR_API_QUOTA_CLIENT_JOUR`, `LABUSE_SOLAR_API_MAX_GLOBAL_JOUR`.

**Module Flash / Stripe / SMTP**
- `LABUSE_FLASH_PRICE_EUR`, `LABUSE_FLASH_STORAGE_DIR`, `LABUSE_FLASH_TOKEN_DAYS`.
- **`LABUSE_STRIPE_SECRET_KEY`**, **`LABUSE_STRIPE_WEBHOOK_SECRET`**, `LABUSE_STRIPE_PRICE_ID`.
- `LABUSE_SMTP_HOST`, `LABUSE_SMTP_PORT`, `LABUSE_SMTP_USER`, **`LABUSE_SMTP_PASSWORD`**, `LABUSE_SMTP_FROM`, `LABUSE_SMTP_STARTTLS`, `LABUSE_ADMIN_EMAIL`.

**Loaders YAML** (config/*.yaml, avec `@lru_cache`) : `cascade_rules`, `completeness_weights`,
`opportunity_weights`, `wfs_layers`, `pipeline`, `shortlist`, `plh_tco`, `habitat_solaire`.
`rules_version()` = empreinte SHA1 courte des 3 configs de règles. `reset_config_cache()`
purge tout (tests).

> Note hors périmètre : `LABUSE_ANTHROPIC_API_KEY` / `ANTHROPIC_API_KEY` (clé du copilote)
> est chargée via `.env` mais consommée dans `ai/` (hors CŒUR).

---

## 5. Autres helpers de la racine (arborescence commentée)

Chemins absolus sous `/Users/openclaw/Desktop/labuse/src/labuse/`.

### Socle technique
- **`db.py`** (60 l) — Engine/session PostGIS. `make_engine()`, `engine()`, `session_factory()`, `session_scope()` (contextmanager commit/rollback), `ensure_postgis()`.
- **`enums.py`** (103 l) — Vocabulaires contrôlés (contrats sérialisés en base) : `CascadeVerdict`, `Severity`, `EvaluationStatus`, `SourceResultStatus`, `DataSourceStatus`, `ReliabilityLevel`, `ConfidenceLevel`, `FeedbackVerdict`, `SignalType`. Tous `StrEnum`.
- **`constants.py`** (5 l) — `USER_AGENT` (requis par certaines API, ex. Overpass).
- **`numeric.py`** (7 l) — `clamp(x, lo, hi)`.
- **`geo.py`** (72 l) — Helpers PostGIS/Shapely : `to_metric()`, `area_m2()`, `distance_m()`, `buffer_m()`, `intersection_area_ratio()`, `geom_area_m2(geom_4326)`.

### Référentiels & marché (chargés depuis YAML/JSON de config)
- **`communes.py`** (121 l) — Roster/fiabilité des communes : `load_communes()`, `meta()`, `commune_known()`, `get()`, `is_reliable()`, `reliability()`, `status_list()`.
- **`loyers.py`** (96 l) — Loyers de référence : `load()`, `source()`, `get_loyers(insee, commune)`, `fiche_block()`.
- **`obsimmo.py`** (259 l) — Signal marché immobilier (obsimmo) : `load()`, `get_market()`, `get_market_by_parent_commune()`, `get_regional_market()`, `local_disponible()`, `market_signal()`, `fiche_block()`, `validate()`.
- **`occupation.py`** (78 l) — Occupation résidentielle/vacance : `load()`, `source()`, `get_occupation()`, `fiche_block()`.
- **`plh.py`** (45 l) — Orientations habitat PLH : `orientations(commune, logements_estimes)`.

### Analyse parcelle
- **`bati.py`** (132 l) — Bâti et emprise : `classify(ratio, count, max_m2, surface_m2)`, `layer_available()`, `stats_batch(parcel_ids)`, `fiche_block(parcel_id, surface_m2)`.
- **`assemblage.py`** (113 l) — Détection d'assemblage foncier (même propriétaire) : `parcel_assemblage(parcel_id)`, `find_assemblages(commune, limit)`.
- **`mutation.py`** (354 l — aussi vu côté scoring) — Score de mutabilité/transformation : `MutationFeatures` (dataclass), `compute_mutation_score(f)`, `features_for_parcels(session, ids)`, `mutation_for_parcels(session, ids)`, `top_for_commune(...)`, `clear_top_cache()`.
- **`plu_reglement.py`** (104 l) — Deep-link vers le règlement PLU (page) : `resolve_reglement(commune, zone_code, …)`, `reglement_block(zones, commune)`.
- **`proprietaire_type.py`** (158 l) — Classification du type de propriétaire (privacy) : `classify_owner_type(payload)`, `classify_dgfip(groupe, forme, denomination)`, `needs_spf(owner)`, `spf_letter(parcel, …)`.

### Prospection / CRM / courrier
- **`prospection.py`** (87 l) — Prospection manuelle (Niveau 1, RGPD) : `default_prospection()`, `merge_prospection(current, patch)`, `statut_label()`, `has_manual_contact()`, `disclaimer()`.
- **`shortlist.py`** (191 l) — Shortlist promoteur (pondérée config) : `priority_score(row, cfg)`, `rank_candidates(rows, pool)`, `assemblage_bonus()`, `marche_bonus()`, `badges(sujet)`, `assemble_sujet(rang, row, fiche)`.
- **`alertes.py`** (148 l) — Zones de veille & alertes (offre C) : `create_watch_zone()`, `list_watch_zones()`, `delete_watch_zone()`, `compute_alertes(session, commune, permit_radius_m)`, `list_alertes()`, `acknowledge()`.
- **`courrier.py`** (133 l) — Courrier postal (Merci Facteur/stub) : `ensure_tables(engine)`, `provider_actif()`, `tarif()`, `envois_du_jour(db, sujet)`, `envoyer(db, sujet, destinataires, …)`.
- **`plans.py`** (49 l) — Gating par plan (stub) : `plan_courant()`, `acces(feature)`, `refus(feature)`.

### Audit, démo, état
- **`audit.py`** (200 l) — Audit à la demande (pull d'une parcelle hors référentiel) : `AuditResult`, `audit_by_reference(section, numero, …)`, `audit_by_address(q)`, `audit_by_polygon(geometry, max_parcels)`.
- **`demo.py`** (201 l) — Orchestration démo : `demo_overview(session, commune)`, `seed_demo_pipeline(session, commune)`, `healthcheck(session, commune)`.
- **`state.py`** (125 l) — État de préparation : `schema_status()`, `data_status(session, commune)`, `readiness()`, `demo_status()`.

---

## 6. Métriques

### Top fonctions les plus longues (racine src/labuse)
| Lignes | Fichier:ligne | Fonction |
|---|---|---|
| 84 | models.py:943 | `ensure_geom_2975` (DDL trigger) |
| 78 | cli.py:203 | `ingest_island_cmd` |
| 74 | mutation.py:180 | `features_for_parcels` |
| 74 | demo.py:128 | `healthcheck` |
| 68 | mutation.py:287 | `top_for_commune` |
| 66 | cli.py:625 | `ingest_inpi_gigogne_cmd` |
| 65 | models.py:1122 | `ensure_pm_propension_view` |
| 61 | obsimmo.py:146 | `market_signal` |
| 61 | cli.py:1157 | `doctor_cmd` |
| 57 | mutation.py:105 | `compute_mutation_score` |

### Top fichiers (lignes)
`cli.py` 2171 · `models.py` 1349 · `mutation.py` 354 · `obsimmo.py` 259 · `config.py` 221 ·
`demo.py` 201 · `audit.py` 200 · `shortlist.py` 191.

### Marqueurs TODO/FIXME/HACK/XXX
Aucun `FIXME`/`HACK`/`XXX`. Uniquement des `# TODO` (jalons de scoring différé, « ne touche
pas au score ») :
- `cli.py:583`, `cli.py:635`, `cli.py:702`, `cli.py:760`, `cli.py:834`, `cli.py:862`, `cli.py:879`, `cli.py:924`
- `models.py:460`, `models.py:494`, `models.py:525`, `models.py:591`, `models.py:1100`, `models.py:1135`, `models.py:1203`

### Helpers jamais importés
**Aucun.** Les 19 helpers de la racine sont tous référencés au moins une fois (surtout par
`api/`). Comptes de références hors self (grep) : `bati` 17, `communes` 16, `plans` 15,
`demo` 15, `alertes` 14, `state` 13, `prospection` 12, `geo` 11, `courrier` 8, `mutation` 8,
`audit` 7, `proprietaire_type` 4, `assemblage` 3, `shortlist` 3, `loyers`/`obsimmo`/
`occupation`/`plh`/`plu_reglement` 1 chacun. (Ces derniers à 1 sont importés par `api/app.py`
ou par un module de `api/`, pas orphelins.)

---

## 7. Histoire (git)

| Cible | `git log -1 --format=%ci` |
|---|---|
| `src/labuse/cli.py` | 2026-07-15 11:30:17 +0200 |
| `src/labuse/models.py` | 2026-07-15 22:53:01 +0200 |
| `src/labuse/config.py` | 2026-07-11 23:27:55 +0200 |
| `src/labuse/` (arbre) | 2026-07-20 14:40:07 +0200 |

---

## 8. Observations factuelles

- Le CLI est monolithique : **78 commandes** dans un seul `cli.py` (2171 l), sans
  sous-groupes Typer — l'organisation thématique existe uniquement par ordre/commentaires.
- La quasi-totalité des commandes d'ingestion portent le marqueur explicite
  « NE touche PAS au score » / `# TODO étage 1/2` : le scoring est délibérément cloisonné
  de l'ingestion des données.
- `models.py` mélange deux styles : **34 classes ORM déclaratives** + **19 fonctions
  `ensure_*`** créant tables/vues/colonnes en **SQL brut**. 9 tables (dont
  `parcelle_personne_morale` en prod, `signalements`, `alertes`, `watch_zones`) et
  plusieurs vues n'ont donc **pas de classe SQLAlchemy** et n'apparaissent pas dans la
  liste `__tablename__`.
- Le géo-modèle est double-projeté : `geom` (4326) + `geom_2975` pré-calculé et
  auto-maintenu par trigger (`ensure_geom_2975`) pour la performance des intersections.
- Plusieurs tables sont conçues comme **parallèles / non lues par l'app** (dry-run) ou
  **cache resumable** (`owner_enrichment`, `owner_denom_lookup`) : le versionnement et la
  non-écrasement (run_id unique, snapshots jamais réécrits) sont des invariants récurrents.
- Contrainte **RGPD** encodée dans le schéma : données de personnes physiques conservées
  seulement si `diffusible`, date de naissance au **mois** (`'YYYY-MM'`), signaux internes.
- Les enums sont stockés comme **VARCHAR + CHECK** (valeur, pas nom), documentés comme
  « contrats » non renommables sans migration.
- Aucun secret n'est en dur : toutes les clés (Merci Facteur, Google Solar, Stripe, SMTP,
  Anthropic) passent par des variables `LABUSE_*` avec repli « stub » honnête si absentes.
- Zéro `FIXME`/`HACK`/`XXX` ; les seuls TODO sont des jalons d'intégration au scoring.
