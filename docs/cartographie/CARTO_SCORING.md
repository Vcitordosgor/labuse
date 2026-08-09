# Cartographie — domaine SCORING & FAISABILITÉ

Document descriptif et factuel (lecture seule). Il cartographie le code du scoring
et de la faisabilité de `src/labuse/` : rôle de chaque fichier, pipelines, tables
de sortie, dépendances externes, métriques. Aucun jugement, aucune recommandation.

Périmètre couvert : **51 fichiers Python** (`scoring/**` = 21, `cascade/**` = 12,
`segments/**` = 8, `faisabilite/**` = 10, `mutation.py`) + 7 fichiers de config YAML.
Dernier commit du domaine : `2026-07-15 11:30:17 +0200`.

---

## 1. Rôle du domaine et relations entre les scores

Le domaine calcule plusieurs signaux INDÉPENDANTS sur chaque parcelle du parc
réunionnais (référentiel `parcels` / `mvt_parcels`, ~431 663 parcelles). Chacun a
son grain, son moteur, sa table de sortie et son wording.

| Signal | Question posée | Moteur (fichiers) | Table(s) de sortie | Run servi |
|---|---|---|---|---|
| **Cascade (étage 0/1/2)** | Contraintes dures / signaux qualité / accessibilité | `cascade/**` | `cascade_results`, `dryrun_cascade_results` ; `parcel_evaluations`, `dryrun_parcel_evaluations` | `q_v6_m8` |
| **Opportunité (0-100)** | « À prospecter maintenant ? » (dérivé cascade) | `scoring/opportunity.py`, `status.py`, `feedback.py` | `parcel_evaluations.opportunity_score` / `.status` | (live) |
| **Complétude (0-100)** | « Combien SAIT-on ? » | `scoring/completeness.py` | `parcel_evaluations.completeness_score` | (live) |
| **Matrice Q×A** | Statut (chaude/à surveiller/à creuser/écartée) | `scoring/dryrun.py` (+ `config/scoring_matrice.yaml`) | `dryrun_parcel_evaluations.matrice_statut`, `q_score`, `a_score` | `q_v6_m8` |
| **Score P (proba mutation)** | Probabilité calibrée de vente L2 à 12 mois | `scoring/p_model/**`, `scoring/p_v2/**` | `parcel_p_score_v2` (p_raw, tier, rang, percentile, top5, icd) | run `m36-l2f-2026-<date>` |
| **Score V (vendabilité)** | Signaux PUBLICS de raison de vendre | `scoring/score_v.py`, `score_v_constants.py` | `parcel_v_score`, `parcel_veille_succession`, `matching_review_queue` | (barème v1.3) |
| **Score Mutation V1** | Potentiel de TRANSFORMATION (radar) | `mutation.py` (+ `config/mutation_weights.yaml`) | aucune (lecture seule, cache mémoire TTL) | (live) |
| **ICD** | Complétude pondérée des données du score P | `scoring/icd.py` | `parcel_p_score_v2.icd` / `.icd_detail` (colonnes annexes) | même run que P |
| **Faisabilité / bilan** | Capacité constructible + bilan promoteur | `faisabilite/**` | payloads JSON de fiche ; `parcel_residuel`, `parcel_viabilisation`, `bilan_params` | (à la demande) |
| **Segments** | Filtrage/prospection multi-critères (30 métiers) | `segments/**` (+ `config/segments*.yaml`) | `segment_presets`, `segment_preset_counts`, exports CSV/PDF | lit `q_v6_m8` |

### Qui produit quoi — points de rattachement

- **`Q_A_RUN_LABEL = "q_v6_m8"`** (dans `scoring/score_v_constants.py`) est la SOURCE
  UNIQUE du run servi de la matrice Q×A. Elle est ré-importée par `p_v2/pipeline.py`
  (étage 0 lu sur ce run, override possible via `LABUSE_ETAGE0_RUN`), `dryrun.py`
  (`apply_convention`, `build_entonnoir` défaut), `segments/registry.py`
  (`CASCADE_RUN`). L'historique des bascules (`q_v2` → … → `q_v6_m8`) est documenté
  en commentaire dans `score_v_constants.py`.
- **Cloisonnements déclarés** dans les docstrings : le score P (`p_v2`/`p_model`) est
  gelé (sha256 au manifeste) et n'est modifié ni par l'ICD, ni par V, ni par la
  matrice. Le score V « ne touche ni la cascade, ni Q/A, ni la matrice ». `mutation.py`
  et `faisabilite/**` se déclarent « lecture seule », sans effet sur cascade/scoring.
- **La cascade alimente** l'opportunité, la complétude, la matrice Q×A et (indirectement,
  via `cascade_results`) le score Mutation. Le score P est calculé à part sur son propre
  dataset SQL (`p_model_ext_dataset`), avec seulement l'ÉTAGE 0 de la cascade réinjecté
  (parcelles écartées → tier `ecartee`).

---

## 2. Arborescence commentée

Signature notée `nom(args) -> retour`. Nombre de lignes via `wc -l`.

### `src/labuse/scoring/`

- **`__init__.py`** (9 l.) — ré-exporte le paquet.
- **`score_v.py`** (604 l.) — **[cœur]** Moteur du Score V (vendabilité), Stage 3
  additif. Précalculs SET-BASED (une requête par source de signal), assemblage Python
  par parcelle, écriture COPY dans `parcel_v_score`. Matching propriétaire (SIREN direct
  1.0 → dénomination normalisée 0.8 → ambigu = review queue), typage (public/bailleur →
  V NULL + badge ; copro ; pm). Familles A (détresse BODACC), B (cycle de vie — sortie
  de V en v1.3), C (détachement géo), D (dormance, somme plafonnée), E (DPE). Tenure
  conditionnelle DVF_TENURE_OBS5.
  Fonctions : `compute_all(session, limit, log) -> dict` (batch complet) ;
  `resolve_owner(link, lookups) -> dict` ; `classify_owner(link, siren, fiche) -> str` ;
  `famille_a/b/c(...) -> list[dict]` ; `_retain(cands, factor_families) -> tuple[list, int]`
  (MAX A/B/C/E vs SOMME plafonnée D) ; `veille_succession_eligible(owner_type, confiance,
  age, sci_dormante) -> bool` ; `snapshot_scores(session, label, notes, brulante_threshold,
  run_label) -> int` ; nombreux `_load_*` (owner links, bodacc, friches, dvf, dpe…).
- **`score_v_constants.py`** (179 l.) — **[cœur config]** Barème V1 verrouillé.
  `V_BRULANTE_THRESHOLD = 17`, `BRULANTE_GUARDRAIL = (30, 120)`, **`Q_A_RUN_LABEL = "q_v6_m8"`**,
  `V_BANDS`, `FAMILY_CAPS`, `SUM_FAMILIES`, dict `SIGNALS` (code → (famille, points, label)),
  familles qualifiantes de tenure, listes bailleurs sociaux (SIREN), groupes DGFiP →
  owner_type, préfixes NAF immo, fenêtres temporelles. Nombreux `# TODO v2` sur les points
  BODACC.
- **`p_v2/pipeline.py`** (335 l.) — **[cœur]** Pipeline `labuse score-v2` : vérif sha256
  de l'artifact gelé (REFUS si mismatch) → rebuild features as-of → recalage d'intercept
  (année la plus récente labellisée, coefs intacts) → scoring → rangs/percentiles HORS
  copro (ties seedés 974) → étage 0 lu sur `Q_A_RUN_LABEL` → tiers v2 avec hystérésis →
  calibrage N_e (~1150) et seuil brûlante → écriture `parcel_p_score_v2` → snapshot M1 →
  backfill ICD.
  Fonctions : `run_score_v2(session, *, run_id, rebuild, annee, snapshot) -> dict` ;
  `verify_artifact() -> tuple[PModel, str]` ; `rebuild_features(session)` ;
  `load_events(session) -> DataFrame` ; `top5_lisibles(model, contrib, df) -> list` ;
  `previous_run(session) -> tuple[str|None, Series|None]` ; `_snapshot_v2(...)`.
- **`p_v2/statuts.py`** (131 l.) — **[cœur]** Tiers v2 PURS (sans DB) : `brulante` /
  `chaude` / `a_creuser` / `reserve_fonciere` / `ecartee`. `TierParams` (dataclass) ;
  `plancher_c(df, params) -> Series` (SDP résiduelle > 0 OU surface ≥ 600 m² en U/AU) ;
  `assign_tiers(df, params, prev_tier) -> Series` (hystérésis anti-churn + bypass événement
  daté) ; `calibre_brulante(chaude_df, params, ...) -> TierParams` (garde-fou 30-120) ;
  `calibre_n_entree(rangs_c_ok, cible=1150) -> int`.
- **`p_v2/libelles_client.py`** (181 l.) — Table de correspondance VERSIONNÉE feature/bin →
  phrase française client (bloc « Pourquoi ce score »). `phrase_client(feature, bin_, libelle)
  -> str` ; `enrichir_contributions(top5) -> list|None`. Dicts `_CATEGORIELS`, `_INTERACTIONS`,
  `_NUMERIQUES` (seuils bas/haut par feature). `VERSION = "2026-07-12.1"`.
- **`p_v2/monitoring.py`** (107 l.) — Monitoring forward mensuel (`labuse monitor-forward`) :
  suit le top gelé (snapshot `m5-*`) contre mutations L2-F et permis post-gel, sonde faux
  négatifs, churn observé. `run_monitor(session, snapshot_label) -> dict` (écrit `reports/monitoring/*.md/csv`).
- **`p_v2/__init__.py`** (23 l.) — Constantes du paquet : `MODEL_ARTIFACT` (joblib gelé),
  `MODEL_FREEZE` (manifeste sha256), `MODEL_VERSION = "m36-l2f-2026"`, `SEED = 974`.
- **`p_model/model.py`** (148 l.) — **[cœur]** Classe `PModel` (dataclass) : logistique
  régularisée sur WoE → log-hazard additif par bloc (Z/D). `fit(df, y, C, min_count) -> PModel` ;
  `margin(df) -> ndarray` ; `predict_proba(df) -> ndarray` (isotonique si calibrée) ;
  `contributions(df) -> DataFrame` (coef × WoE + agrégats contrib_Z/contrib_D) ;
  `calibrate(df_val, y_val) -> PModel` (isotonique) ; `recale_intercept(df, y) -> PModel`
  (dichotomie sur le décalage additif) ; `save/load` ; `model_card_rows() -> DataFrame`.
- **`p_model/features.py`** (210 l.) — Registre des features (source unique). `FeatureSpec`
  (dataclass : name, bloc, kind, monotone, source, fenêtre, disponibilité). Liste `FEATURES`
  (bloc Z = zone/marché ; bloc D = dormance parcelle). `derive(df) -> DataFrame` (shrinkage
  rotations gamma-Poisson, composite équipements exp(-d/800 m), dormance) ;
  `_shrink_rotation(grp, kind) -> Series` ; `load_dataset(engine, years) -> DataFrame` ;
  `generate_dictionary() -> str`.
- **`p_model/woe.py`** (225 l.) — Binning WoE (≤10 bins, effectif min, monotonie contrainte,
  bin « manquant » explicite). `BinnedFeature` (dataclass : transform/bin_index/bin_label) ;
  `WoeEncoder` (fit/transform/iv_table) ; `fit_numeric(...) -> BinnedFeature` ;
  `fit_categorical(...) -> BinnedFeature` ; `_woe_iv(n1, n0) -> tuple[ndarray, float]`.
- **`p_model/sql.py`** (465 l.) — **[cœur SQL]** Dataset personne-période as-of (anti-leakage)
  du modèle M3. Crée `p_model_frame`, `p_model_mut_l2`, `p_model_mut_all`, `p_model_permits`,
  `p_model_bati`, `p_model_static`, `p_model_dataset`. `YEARS`, `L2_NATURES`, `DVF_START`.
  `build_frame/build_mutations/build_permits/build_bati/build_static/build_dataset(session)` ;
  `build_all(session, years)`.
- **`p_model/ext_sql.py`** (287 l.) — **[cœur SQL]** Extension M3.6 : flag copro (RNIC ∪ DVF
  appartements) et label L2-F (exclusion ventes d'unités de copro, immeuble entier conservé).
  Dataset étendu 2014-2025. `build_copro_flags(session, dvf_table)` ; `build_ext_union` ;
  `build_ext_mutations` ; `build_ext_dataset(session, years)` ; `l2f_mutation_flags(dvf_table) -> str`.
  `IMMEUBLE_ENTIER_MIN_APP = 4`, `EXT_YEARS`, `EXT_DVF_START`.
- **`p_model/evaluate.py`** (126 l.) — Protocole d'évaluation strict (RR@k, IC bootstrap,
  lift, calibration ECE, churn, contrôles négatifs), tirages seedés 974. `rr_at_k` ;
  `bootstrap_rr` ; `lift_table` ; `ventilation` ; `ece` ; `churn_topk` ; `permutation_control`.
- **`p_model/shadow.py`** (90 l.) — GBM shadow pour miner les interactions (jamais en prod).
  `shadow_report` ; `top_features` ; `mine_interactions(...) -> tuple[list, DataFrame]`.
- **`p_model/__init__.py`** (21 l.) — `P_MODEL_VERSION = "m3-phase1"`, `SEED = 974`.
- **`opportunity.py`** (77 l.) — Score d'opportunité (0-100) dérivé de la cascade :
  HARD_EXCLUDE → 0 ; sinon clamp(50 − Σpénalités + Σbonus + ai_adjustment, 1, 100).
  `OpportunityResult` (dataclass) ; `compute_opportunity(verdicts, ai_adjustment, cfg) -> OpportunityResult`.
  Gère `weight_override` (couches à barème propre, ex. residuel_socle).
- **`completeness.py`** (49 l.) — Score de complétude (0-100) : une famille couverte dès
  qu'une couche a rendu ≠ UNKNOWN ; `cadastre` couvert si parcelle ingérée. `CompletenessResult` ;
  `compute_completeness(verdicts, parcel_ingested, cfg) -> CompletenessResult`.
- **`status.py`** (30 l.) — Décision de STATUT (règles dures) : HARD_EXCLUDE → exclue/faux_positif ;
  complétude < 50 → plafonné `a_creuser` ; opp ≥ seuil sans flag fort → `opportunite`.
  `decide_status(opp, completeness_score, cfg) -> EvaluationStatus`.
- **`feedback.py`** (49 l.) — Réinjection du feedback terrain agrégé par zone (§10).
  `feedback_adjustment(fp, gl, ni, cfg) -> int` (borné) ; `apply_feedback(opp,
  completeness_score, fp, gl, ni, cfg) -> tuple[statut, verdict|None]`.
- **`declassement.py`** (156 l.) — Volet NON-franc du garde-fou faux positifs (flags QUALITÉ,
  étage 1). Les bloquants FRANCS ont migré vers l'étage 0 (cascade). Seuils NON-francs
  (`SURFACE_MIN_M2 = 250`, `PENTE_FORTE_PCT = 40`, `OSM_FLAG_COVERAGE = 0.30`, `ACCES_MAX_M = 6`).
  `apply_declassement(status, signals) -> tuple[ES, str|None]` (ne rétrograde qu'en `à creuser`) ;
  `compute_declass_signals(session, parcel_ids) -> dict[int, dict]` (signaux batch SQL :
  surface, pente, OSM, bâti, accès). Plusieurs `# TODO étage 1`.
- **`icd.py`** (171 l.) — Indice de confiance données (ICD ∈ [0,100]) : complétude pondérée
  des 9 groupes du dataset P, cloisonné du score P (colonnes annexes). `IcdGroup` (dataclass) ;
  `ICD_GROUPS` (poids sommant à 100, invariant assert) ; `bande/libelle_bande/manquants` ;
  `compute_from_row(row) -> tuple[int, dict]` ; `backfill_run(session, run_id, annee) -> int`
  (UPDATE SQL construit dynamiquement depuis ICD_GROUPS).
- **`dryrun.py`** (324 l.) — **[cœur matrice]** Lecture des tables `dryrun_*` + post-pass
  matrice Q×A. `compute_matrice(session, run_label, commune) -> dict` (Q = base + Σ étages 0/1 ;
  A = base + Σ étage 2 ; DOUBLE VERROU chaude : A ≥ seuil ET A-hors-zone ≥ seuil ET
  A-complétude ≥ min ; bascule `evenement='rouge'` → chaude) ; `matrice_report` ; `report`
  (livrable + contrôle traçabilité base+Σ) ; `simulate_matrice(session, run_label, candidates)
  -> list` (à blanc, table temp) ; `apply_convention(session, run_label) -> dict` (rejoue ×24
  communes + CANARI `97415000AC0253` doit rester chaude) ; `build_entonnoir(session, run_label)
  -> int` (décomposition des écartées par motif).

### `src/labuse/cascade/`

- **`__init__.py`** (8 l.) — Import déclenche l'enregistrement des couches ; ré-exporte
  `REGISTRY`, `run_cascade`, `evaluate_parcels`.
- **`base.py`** (78 l.) — Abstractions : `Verdict` (dataclass : layer_name, result, detail,
  severity, bonus_key, magnitude, exclude_kind, extra) ; helpers `hard_exclude/soft_flag/
  positive/passed/unknown` ; classe `Layer` (méthode `evaluate`) ; `REGISTRY` + décorateur
  `register`.
- **`context.py`** (564 l.) — **[cœur]** `EvalContext` : accès PostGIS partagé, tout en
  EPSG:2975. `prime(parcel_ids)` précalcule EN BATCH (une requête par famille : intersections
  via ST_Subdivide(256), centroïde eau, distance ravine, DVF par rayon, SITADEL, Fichiers
  fonciers, feedback zone, POI ponctuels étage 1, aménités, vues BODACC/propension/passoire
  étage 2). Getters : `intersections/min_distance_m/centroid_in/dvf_stats/sitadel_near/
  kind_present/table_has_commune/latest_source_result/feedback_counts` + helpers étage 0
  étendu (`owner_pm`, `oriented_envelope_dims`, `emprise_routiere_signals`, `residuel_sdp`).
  `ParcelRef`, `Intersection` (dataclasses).
- **`engine.py`** (56 l.) — Orchestrateur : `run_cascade(parcels, ctx, phases) -> dict[int,
  list[Verdict]]` (phase 1 sur toutes, promotion des survivantes sans HARD_EXCLUDE en phase 2) ;
  `is_promoted(verdicts) -> bool` ; `_layers_for_phase(rules, phase)`.
- **`pipeline.py`** (244 l.) — **[cœur]** `evaluate_parcels(parcel_ids, session, *, persist,
  ai_provider, dryrun_label) -> list[EvaluationOutcome]` : prime → declass signals → cascade →
  complétude → opportunité → statut → IA (narratif only, ai_adjustment=0) → feedback zone →
  déclassement non-franc → persistance (`_persist` live vs `_persist_dryrun`). `EvaluationOutcome`
  (dataclass) ; `_apply_ai(...)`.
- **`layers/__init__.py`** (2 l.) — Importe etage0_ext, etage1, etage2, phase1, phase2 (effet
  de bord : enregistre les couches).
- **`layers/phase1.py`** (794 l.) — **[cœur]** Couches PHASE 1 (géométriques, PostGIS, toutes
  parcelles). 18 couches `@register` : `EauLayer`, `ParcNationalLayer`, `ForetPubliqueLayer`,
  `SarLayer` (informative, zéro pouvoir d'exclusion), `ZonagePluGpuLayer` (exclusion A/N sensible
  au recouvrement, zones éco habitat interdit via `plu_rules.resolve_zone`), `PrescriptionPluLayer`
  (ER, EBC, mixité, OAP… avec RESCUE/VETO par libellé), `SaferLayer`, `RisquesLayer` (PPR + aléas,
  multi-verdicts), `RavineLayer`, `TraitDeCoteLayer`, `PenteLayer` (étage 0 franc + flag),
  `AbfLayer`, `EnsLayer`, `OcsGeLayer`, `OsmFauxPositifLayer` (étage 0 franc), `AccesLayer`,
  `SurfaceLayer` (étage 0 franc micro-parcelle + courbe saturante), `BatiLayer` (occupation
  bâtie franche, lit `ctx.declass_signals`). Chaque `evaluate(parcel, ctx, params) -> Verdict|list`.
- **`layers/etage0_ext.py`** (169 l.) — Extensions étage 0 (mandat cascade île). 4 couches
  `@register` : `FoncierPublicLayer` (DGFiP groupes publics → HARD_EXCLUDE), `EmpriseLineaireLayer`
  (délaissé voirie : largeur < 8 m ET allongement > 8×), `EmpriseRoutiereLayer` (emprise routière
  cadastrée, garde-fou signal privé), `ResiduelSocleLayer` (barème SDP -25…+30 via
  `extra["weight_override"]`). Constantes de seuils (`SOCLE_TIERS`, `ROUTIERE_*`, `LINEAIRE_*`).
- **`layers/etage1.py`** (263 l.) — Couches ÉTAGE 1 (dry-run, QUALITÉ). `FricheLayer`,
  `_NearestFlagLayer` (base), `SolPollueLayer` (SIS + CASIAS), `SupLayer` (servitudes d'utilité
  publique, anti-double-compte), `CinquantePasLayer`, `BruitRouteLayer`, `CaviteLayer`, `MvtLayer`,
  `IcpeLayer`, `AmenitesLayer`. Chaque verdict porte `extra{source_table, source_id}` (cliquable).
- **`layers/etage2.py`** (94 l.) — Couches ÉTAGE 2 (dry-run, ACCESSIBILITÉ). `AgeDirigeantLayer`
  (INPI, âge absent → UNKNOWN), `BodaccLayer` (procédures collectives, `evenement='rouge'` →
  bascule chaude), `DpePassoireLayer` (F/G, flag 0 point).
- **`layers/phase2.py`** (166 l.) — Couches PHASE 2 (coûteuses, sur parcelles promues).
  `DvfLayer` (contexte marché par rayon), `SitadelLayer` (§7bis, RATTACHÉ par IDU vs SIGNAL
  DE ZONE — marqueur lu par `dryrun.compute_matrice`), `PotentielFoncierLayer`,
  `ProprietaireLayer` (moral/indivision, Fichiers fonciers).

### `src/labuse/segments/`

- **`__init__.py`** (11 l.) — Docstring du moteur (un query builder + presets métiers).
- **`registry.py`** (525 l.) — **[cœur]** Registry DÉCLARATIF des filtres (le SQL vit
  UNIQUEMENT côté serveur ; le client n'envoie que des clés validées + valeurs bindées).
  `FilterDef`/`SortDef` (dataclasses) ; dicts `FILTERS`, `JOINS`, `SORTS`, `EXPORT_COLS`,
  `_EXPORT_REQUIRES`. Détection de disponibilité (`compute_availability(session, *,
  simulate_missing, use_cache) -> dict`, cache TTL 600 s), filtres grisés « disponible
  prochainement » quand la source manque. `CASCADE_RUN = Q_A_RUN_LABEL`.
- **`engine.py`** (255 l.) — Évaluateur : `build(session, filtres, tri, *, colonnes_export,
  avail, simulate_missing) -> Query` (compile chaque filtre en condition SQL paramétrée, gère
  groupes OU, tri à repli, colonnes d'export). `Query` (dataclass) ; `FiltreInvalide` ;
  `run_count/run_items/run_export_rows`. `MAX_LIMIT=500`, `MAX_EXPORT=10_000`.
- **`presets.py`** (207 l.) — Presets métiers (seed versionné, n'écrase jamais un preset
  édité). DDL `segment_presets`/`segment_preset_counts`. `validate_preset`, `seed_presets`,
  `list_presets`, `get_preset`, `preset_disponibilite`, `counts`, `refresh_counts`, `upsert_preset`.
- **`residuel_bati.py`** (179 l.) — Lot 2 : droits résiduels sur parcelles BÂTIES (recycle
  `plu_rules.resolve_zone`). Table `parcel_residuel_bati` (clé idu, DISTINCTE de `parcel_residuel`).
  `_regles(zone, commune) -> dict` ; `compute_commune(session, commune, batch) -> dict`.
- **`catnat.py`** (136 l.) — Signal CATNAT (arrêtés GASPAR Géorisques). Table `catnat_arretes`.
  `ingest_catnat(session, ...) -> dict` ; `catnat_config() -> dict` ; `communes_recentes(session) -> dict`.
- **`publipostage.py`** (107 l.) — Export publipostage « à l'occupant » (RGPD : jamais de nom
  de personne physique). ZIP = CSV + planches d'étiquettes PDF. `lignes_publipostage`,
  `csv_bytes`, `etiquettes_pdf`, `zip_publipostage`.

### `src/labuse/faisabilite/`

- **`__init__.py`** (19 l.) — Ré-exporte `Faisabilite`, `Hypotheses`, `estimate_capacity`,
  `ZoneRules`, `resolve_zone`, `BANDEAU`.
- **`engine.py`** (371 l.) — **[cœur]** Moteur de pré-faisabilité (capacité constructible).
  `Hypotheses` (dataclass : coefs, coûts construction 2300/2800 €/m², marge/frais, seuils
  mixité Art. 2, placeholders) ; `Contraintes` (dataclass) ; `Step`, `Faisabilite` (dataclasses) ;
  `estimate_capacity(rules, surface_m2, contraintes, hyp, emprise_geo) -> Faisabilite`
  (emprise reculs → % → pleine terre → niveaux hé → footprint → SDP → habitable → logements →
  plafond densité → stationnement 2 scénarios → modulation réunionnaise pente/PPR/littoral/SAR).
- **`plu_rules.py`** (213 l.) — Chargement des règles PLU (YAML calibrés par commune) et
  résolution de zone. `ZoneRules` (dataclass) ; `resolve_zone(code, commune) -> ZoneRules|None`
  (mode `strict` Saint-Paul vs `progressif` autres, renvoi AU→U, AU*st, estimation générique) ;
  `load_rules(commune)` ; `_zone_generique(code) -> ZoneRules` ; `_has_usable_height(r) -> bool`.
- **`db.py`** (427 l.) — **[cœur]** Intégration base (lecture seule) : résout le contexte
  parcelle et lance le moteur. `parcel_context(session, parcel_id) -> ParcelContext|None` ;
  `parcel_faisabilite(session, parcel_id) -> tuple[ParcelContext, Faisabilite]|None` (emprise
  sur géométrie réelle ST_Buffer, clippée à la portion U/AU, amputée des ER, hauteur prospect
  L≥H) ; `fiche_payload(session, parcel_id) -> dict|None` (assemble faisabilité + résiduel +
  bilan + volume3d + prescriptions_eco, chaque bloc défensif) ; `volume3d_payload(...)` ;
  `_facade_largeur`, `_prospect_hauteur`, `_ring_local`.
- **`bilan.py`** (520 l.) — **[cœur]** Bilan promoteur (partie 1) : prix de sortie DVF fiabilisé
  (type prioritaire, rayon adaptatif, aberrants Tukey, récence, indice fiable/fragile/insuffisant),
  CA = surface × prix, charge foncière à rebours. `Bilan` (dataclass) ; `sector_price(db,
  parcel_id, hyp) -> dict` ; `compute_bilan(shab_vendable_m2, surface_terrain_m2, prix, hyp,
  contexte_eco, bilan_params) -> Bilan` (cœur pur ; pondération mixité sociale, bonus vue mer,
  majoration VRD pente/pluvial) ; `compute_calculette(...) -> dict` (charge foncière supportable,
  hypothèses saisies) ; `_trim_aberrants`, `_fiabilite`, `_comparables`, `_clause_mixite`.
- **`bilan_params.py`** (162 l.) — Registre des paramètres du bilan + résolution par SECTEUR
  (défaut ← global '*' ← secteur). `PARAMS` (liste), `CRITIQUES`. `resolve(session, secteur) ->
  dict[str, dict]` ; `values` ; `uncalibrated_critical` ; `estimated_to_refine` ; `save` ;
  `read_calibration_csv` ; `apply_calibration(session, rows, dry_run) -> dict`.
- **`bilan_calibration.py`** (63 l.) — Socle de démarrage sourcé du bilan (valeurs de départ
  crédibles, sourcee/estimee). `CALIBRATION` (param → (valeur, provenance)) ; `SECTEUR_PRIX_NEUF`
  (prix neuf ventilé par bassin PLU) ; `seed(executor, secteur)`.
- **`residuel.py`** (134 l.) — Potentiel résiduel (Lot B) : croise bâti existant (BD TOPO) ×
  capacité max (faisabilité). `compute_residuel(session, parcel_id, faisa) -> dict` ;
  `compute_residuel_batch(session, parcel_ids) -> int` (cache `parcel_residuel`) ;
  `_niveaux_existants`, `_libelle`.
- **`viabilisation.py`** (252 l.) — M-VIA : indicateur de VIABILISATION par faisceau de preuves
  (aucun tracé de réseau — donnée sensible). Poids calibrés `W_PERMIS=40/W_FACADE=25/W_BATI=15/
  W_ZONE=20`. `compute_score(sig) -> int` ; `band(score) -> tuple` ; `contributions(sig) -> list` ;
  `cout_raccordement(sig, code_band) -> dict` (qualitatif) ; `build_indicateur(...)` ;
  `resolve_gestionnaires(commune) -> dict|None`.
- **`viabilisation_build.py`** (148 l.) — Construction batch de `parcel_viabilisation` (score SQL
  miroir EXACT de `viabilisation.compute_score`). DDL, `_SCORE_SQL`, `_INSERT_COMMUNE`.
  `build_viabilisation(session, communes) -> dict` ; `ilot_s3renr_note(session) -> dict|None`.

### `src/labuse/mutation.py`

- **`mutation.py`** (354 l.) — Score Mutation V1 (Radar Mutation) — potentiel de TRANSFORMATION,
  distinct du verdict d'opportunité. LECTURE SEULE, moteur pur. Poids/seuils depuis
  `config/mutation_weights.yaml` (défauts codés en fallback). `MutationFeatures` (dataclass) ;
  `compute_mutation_score(f) -> dict` (sous-exploitation, intensité latente presque-seuil,
  zonage, potentiel régional, marché, foncier acquérable, malus contrainte forte ; règle d'or
  confiance < 50) ; `features_for_parcels(session, parcel_ids) -> dict` (petit lot ≤ 2000) ;
  `mutation_for_parcels` ; `top_for_commune(session, commune, ...) -> list` (pré-sélection SQL
  proxy + score autoritatif ; cache mémoire TTL 300 s).

---

## 3. Pipelines pas-à-pas

### Score P (probabilité de mutation)

`labuse score-v2` → `p_v2/pipeline.run_score_v2` :

1. `verify_artifact()` — charge l'artifact joblib gelé, REFUSE si sha256 ≠ manifeste
   (`reports/m36-foncier/FREEZE-scoring2026.json`).
2. `rebuild_features(session)` — `ext_sql.build_ext_union` (UNION `dvf_mutations_histo`
   2014-2020 + `dvf_mutations_parcelle` 2021+) → `build_ext_mutations` (L2 dédupliqué +
   flag L2-F) → `build_ext_dataset` (dataset parcelle × année, features as-of) →
   `build_copro_flags`. En amont, `p_model/sql.build_all` matérialise `p_model_frame`,
   `p_model_static`, `p_model_permits`, `p_model_bati` (réutilisés par `ext_sql`).
3. Lecture `p_model_ext_dataset` (année courante) → `features.derive` (shrinkage,
   composite équipements).
4. `model.recale_intercept` sur la dernière année labellisée (coefs intacts).
5. `model.predict_proba` + `model.contributions` (contrib_Z / contrib_D).
6. Merge copro (`p_model_ext_copro`) ; rangs/percentiles HORS copro, ties seedés 974.
7. Étage 0 lu sur `Q_A_RUN_LABEL` (ou `LABUSE_ETAGE0_RUN`) depuis
   `dryrun_parcel_evaluations` (status exclue/faux_positif_probable) → `ecartee_etage0`.
8. Événements datés (`load_events` sur `parcel_v_score.signals`) → `event_age_mois`.
9. `statuts.assign_tiers` (hystérésis vs run précédent) ; calibrage
   `calibre_n_entree(cible=1150)` puis `calibre_brulante` (garde-fou 30-120) ; second
   `assign_tiers`.
10. `top5_lisibles` (contributions lisibles) → écriture **`parcel_p_score_v2`**
    (p_raw, mult_base, percentile, rang, contrib_z/d, top5_contributions JSONB, copro,
    tier, event_date, model_version).
11. Snapshot M1 (`score_snapshots` + `score_snapshot_parcelles`, label `m5-<date>`) ;
    ligne `p_score_v2_runs` ; `icd.backfill_run` (colonnes annexes icd/icd_detail).

Fichiers impliqués : `p_v2/pipeline.py`, `p_v2/statuts.py`, `p_model/{model,features,
woe,ext_sql,sql}.py`, `scoring/icd.py`, `scoring/score_v.py` (mécanisme snapshot).

### Score C / complétude (+ opportunité, statut — chaîne cascade live)

`cascade/pipeline.evaluate_parcels(parcel_ids, session)` :

1. `EvalContext(session).prime(parcel_ids)` — précalcul batch PostGIS.
2. `declassement.compute_declass_signals` → injecté dans `ctx.declass_signals`.
3. `engine.run_cascade(parcels, ctx)` — phase 1 (toutes) → promotion → phase 2.
4. Par parcelle : `completeness.compute_completeness(verdicts)` →
   **`parcel_evaluations.completeness_score`** (familles couvertes si ≠ UNKNOWN) ;
   `opportunity.compute_opportunity(verdicts)` → **`opportunity_score`** ;
   `status.decide_status(opp, completeness)` → **`status`**.
5. IA (narratif only), `feedback.apply_feedback` (zone), `declassement.apply_declassement`
   (non-franc → au plus `à creuser`).
6. `_persist` (live : `cascade_results` + `parcel_evaluations` versionnée) ou
   `_persist_dryrun` (`dryrun_cascade_results` + `dryrun_parcel_evaluations`).

Le statut MATRICE (chaude/à surveiller/…) est un post-pass SÉPARÉ sur le run dry-run :
`dryrun.compute_matrice(session, run_label, commune)` lit `dryrun_cascade_results` et écrit
`q_score`/`a_score`/`a_completude`/`matrice_statut` dans `dryrun_parcel_evaluations`.
`apply_convention` rejoue les 24 communes et vérifie le CANARI.

Fichiers impliqués : `cascade/{pipeline,engine,context,base}.py`, `cascade/layers/*.py`,
`scoring/{completeness,opportunity,status,feedback,declassement,dryrun}.py`.

---

## 4. APIs / services externes appelés depuis ces fichiers

`grep -rn "http"` sur le périmètre ne révèle **aucun appel réseau sortant** : les seules
occurrences sont des URLs de traçabilité (attributs `url` de signaux, non requêtées),
toutes dans `scoring/score_v.py` :

- `https://cartofriches.cerema.fr/cartofriches/` (constante `CARTOFRICHES_URL`) ;
- `https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}` ;
- `https://data.inpi.fr/entreprises/{siren}` (×2).

Les données externes (BODACC, RNE/INPI, recherche-entreprises, DVF, Sitadel, Géorisques,
GASPAR…) sont consommées via des TABLES déjà ingérées (accès SQL en lecture) ou via des
connecteurs situés HORS de ce périmètre (`segments/catnat.py` importe `connectors.georisques`
et `ingestion.run_all`, mais l'appel HTTP vit dans le connecteur). Aucun `requests`/`httpx`
dans le domaine scoring/faisabilité lui-même.

---

## 5. Métriques du domaine

### Fichiers les plus longs (`wc -l`, top 12)

| Lignes | Fichier |
|---|---|
| 794 | `cascade/layers/phase1.py` |
| 604 | `scoring/score_v.py` |
| 564 | `cascade/context.py` |
| 525 | `segments/registry.py` |
| 520 | `faisabilite/bilan.py` |
| 465 | `scoring/p_model/sql.py` |
| 427 | `faisabilite/db.py` |
| 371 | `faisabilite/engine.py` |
| 354 | `mutation.py` |
| 335 | `scoring/p_v2/pipeline.py` |
| 324 | `scoring/dryrun.py` |
| 287 | `scoring/p_model/ext_sql.py` |

Total du périmètre : **10 518 lignes**.

### Fonctions les plus longues (estimation à la lecture)

- `bilan.compute_bilan` (~210 l.) — la plus longue fonction unique du domaine.
- `engine.estimate_capacity` (`faisabilite/engine.py`, ~245 l. avec les steps).
- `score_v.compute_all` (`scoring/score_v.py`, ~180 l.).
- `db.parcel_faisabilite` + `db.fiche_payload` (~75 l. et ~100 l.).
- `p_v2.pipeline.run_score_v2` (~145 l.).
- `EvalContext.prime` (`cascade/context.py`, ~215 l., majoritairement du SQL).
- `mutation.top_for_commune` (~70 l., dont un gros bloc SQL).

### Marqueurs TODO/FIXME/HACK/XXX

Aucun FIXME/HACK/XXX. **10 TODO** :

- `scoring/score_v_constants.py:72` — `BODACC_LJ` : « TODO v2 : non tranché Phase 0 »
- `scoring/score_v_constants.py:73` — `BODACC_LJ_CLOT` : « TODO v2 »
- `scoring/score_v_constants.py:74` — `BODACC_RJ` : « TODO v2 »
- `scoring/score_v_constants.py:76` — `BODACC_SAUVEGARDE` : « TODO v2 (idem LJ/RJ) »
- `scoring/declassement.py:20` — « TODO étage 1 : migrer les seuils en YAML »
- `scoring/declassement.py:50` — « TODO étage 1 : surface réduite bande 100-250 m² »
- `scoring/declassement.py:55` — « TODO étage 1 : pente forte bande 40-60 % »
- `scoring/declassement.py:60` — « TODO étage 1 : recouvrement partiel OSM 30-50 % »
- `scoring/declassement.py:66` — « TODO étage 1 — Accès (audit O1) »
- `scoring/declassement.py:76` — « TODO étage 1 — Correctif R1 déjà bâti »

### Fichiers du périmètre non importés par d'autres modules `src/labuse`

- **`scoring/p_model/shadow.py`** — importé UNIQUEMENT par des scripts d'entraînement
  (`scripts/m3-p-model/train.py`, `scripts/m36-foncier/lot2_walk_forward.py`), jamais par
  un module `src/labuse` ni par les tests. Orphelin au sens « périmètre servi ».
- `scoring/p_v2/monitoring.py`, `faisabilite/viabilisation_build.py`,
  `faisabilite/bilan_calibration.py` sont importés PONCTUELLEMENT hors périmètre
  (`cli.py`, `api/app.py`, `models.py`) — non orphelins.

Tous les autres fichiers (opportunity, completeness, status, feedback, declassement, icd,
dryrun, statuts, viabilisation, residuel_bati, catnat, publipostage, etc.) sont référencés
depuis `src/labuse` (pipeline, api, cli) ou les tests.

### Configs (rôle, sans valeurs de secret)

- **`config/scoring_matrice.yaml`** (49 l.) — Convention de matrice Q×A VERSIONNÉE
  (`convention.version=2`, seuils `q_chaude`/`a_chaude`/`a_completude_min`/`q_ecartee`,
  `base=50`, listes `a_layers`/`a_zone_layers`). La barre des chaudes est un réglage éditable.
- **`config/mutation_weights.yaml`** (28 l.) — Poids/seuils du Score Mutation V1 (miroir des
  défauts codés dans `mutation.py`) : poids par axe, malus, seuils niveaux, `confiance_floor=50`,
  bornes surface.
- **`config/opportunity_weights.yaml`** (63 l.) — Score d'opportunité : `base_score=50`,
  `penalty_per_flag`, `severity_multipliers` (info=0…fort=3), `bonuses` par bonus_key,
  `status_rules`, section `feedback` (rayon zone, bonus/décotes).
- **`config/cascade_rules.yaml`** (473 l.) — Séquence ordonnée des couches (phase, enabled,
  params : kinds spatiaux, seuils, sévérités, préfixes zonage, typepsc prescriptions…). Source
  unique de position/activation des couches.
- **`config/completeness_weights.yaml`** (45 l.) — Poids par famille de complétude (somme 100),
  `family_layers`, bandes forte/moyenne/faible.
- **`config/segments.yaml`** (9 l.) — Paramètres serveur du signal CATNAT (fenêtre, périls ILIKE).
- **`config/segment_presets.yaml`** (381 l.) — Bibliothèque de presets métiers (slug, catégorie,
  filtres, colonnes_export, tri, argumentaire). Seed versionné, seuils dans le YAML.

---

## 6. Histoire

`git log -1 --format=%ci` (dernier commit) et nombre de commits par sous-répertoire :

| Sous-répertoire | Dernier commit | Nb commits |
|---|---|---|
| `src/labuse/scoring/**` | 2026-07-15 11:30:17 +0200 | 37 |
| `src/labuse/cascade/**` | 2026-07-14 22:07:24 +0200 | 41 |
| `src/labuse/faisabilite/**` | 2026-07-14 14:11:14 +0200 | 33 |
| `src/labuse/segments/**` | 2026-07-11 22:21:52 +0200 | 12 |
| `src/labuse/mutation.py` | 2026-06-28 11:51:34 +0000 | 4 |

`mutation.py` est le fichier le plus ancien et le moins touché ; `cascade/**` le plus commité.

---

## 7. Observations factuelles

- **`Q_A_RUN_LABEL = "q_v6_m8"`** est déclarée une fois (`score_v_constants.py`) et ré-importée
  par 3 modules du domaine (`p_v2/pipeline.py`, `dryrun.py`, `segments/registry.py`) + hors
  domaine. Le défaut `apply_convention`/`build_entonnoir` retombe dessus (commentaires « ANO-1 :
  jamais q_v2 gelé »).
- **Deux tables résiduelles distinctes homonymes** : `parcel_residuel` (clé `parcel_id`, SDP
  promoteur, `faisabilite/residuel.py`) et `parcel_residuel_bati` (clé `idu`, droits résiduels
  segments, `segments/residuel_bati.py`) — la docstring de `residuel_bati.py` insiste sur le
  « NE TOUCHE PAS à `parcel_residuel` ».
- **Fonction `_osm_label`/`_er_split` dupliquées** : `_osm_label` existe à l'identique dans
  `cascade/layers/phase1.py` et `scoring/declassement.py` ; la logique `_er_split`/`_ER_RE`
  (« ER 81 - … ») apparaît dans `phase1.py` et, sous forme `_ER_LIB`, dans `faisabilite/db.py`.
- **`_trace()` défini deux fois** (helpers cliquables) : dans `cascade/layers/etage1.py` et
  `cascade/layers/etage2.py`, signatures voisines.
- **`SEED = 974` déclaré à trois endroits** : `p_model/__init__.py`, `p_v2/__init__.py`,
  `mutation.py` (via config) — même valeur.
- **Deux définitions de « brûlante »** coexistent : la matrice Q×A (`score_v.snapshot_scores` :
  chaude ∧ `v_score ≥ V_BRULANTE_THRESHOLD=17`) et le tier P v2 (`statuts.assign_tiers` : chaude
  ∧ contrib_D ≥ seuil calibré ∧ événement/top-décile). Wording identique, moteurs différents.
- **`p_model/shadow.py`** n'est jamais importé par un module servi ni par les tests (seuls des
  scripts d'entraînement l'utilisent).
- **`SarLayer`** (`phase1.py`) est enregistrée et évaluée mais n'émet plus jamais de HARD_EXCLUDE
  ni de SOFT_FLAG (décision : proxy informatif, PASS uniquement).
- **`SIGNALS` famille B à 0 point** (`score_v_constants.py`) : cessation/dirigeant âgé/SCI
  dormante sont tracés (motif) mais ne comptent plus dans V (v1.3) ; le circuit du malus
  `MALUS_ACHAT_RECENT` est conservé mais neutralisé à 0.
- **`CANARI 97415000AC0253`** codé en dur dans `dryrun.apply_convention` : doit rester chaude
  par événement, sinon l'application est stoppée (exception).
- **Deux fenêtres DVF de départ** dans le domaine P : `sql.py` clampe à 2021 (`DVF_START`),
  `ext_sql.py` à 2014 (`EXT_DVF_START`) — le dataset ext ajoute les millésimes historiques.
- **`icd.POIDS_TOTAL` protégé par `assert == 100`** au chargement du module.
- **Nombreux blocs `try/except … noqa: BLE001`** entourent les extensions défensives (ICD
  backfill, bilan/résiduel/volume3d dans `db.fiche_payload`, catnat, availability) : conçus
  pour ne jamais faire échouer le calcul principal.
