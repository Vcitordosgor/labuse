# Cartographie — Domaine INGESTION & CONNECTEURS

Document factuel (lecture seule). Périmètre : `src/labuse/ingestion/**`
(45 fichiers `.py`), `src/labuse/connectors/**` (12 modules + `__init__`),
`data/`, et les fichiers `config/*.yaml` pertinents.

Généré le 2026-07-20.

---

## 1. Intro — rôle du domaine

Le domaine INGESTION rapatrie des sources externes (open data État,
géoplateforme IGN, portails régionaux, ortho-imagerie, fichiers DGFiP/ADEME)
et les écrit dans Postgres/PostGIS. Les CONNECTEURS sont la couche d'accès
réseau (un objet par source, dérivé de `connectors.base.Connector`) ; les
ingesteurs orchestrent l'appel, le parse et l'écriture SQL.

Deux natures de cibles Postgres :

- **Couches géométriques** : la grande majorité atterrit dans la table
  générique `spatial_layers` (colonnes `kind`/`subtype`), consommée par la
  cascade. `layers_ingest.py` est le hub de ces couches structurantes.
- **Tables métier dédiées** : `parcels`, `dvf_mutations`,
  `dvf_mutations_histo`, `sitadel_permits`, `dpe_records`,
  `bodacc_procedures`, `rnic_coproprietes`, `adresses` / `adresse_parcelles`,
  `parcel_solar` / `solar_grid` / `pv_registry` / `grid_capacity`,
  `parcel_anc`, `parcel_vegetation`, `parcel_amenites`, `parcel_equipements`,
  `ortho_tiles` / `ortho_detections`, `parcel_signals`, etc.

Deux tables d'infrastructure transverses : `data_sources` (métadonnées de
source, `last_sync_at` posé à l'ingestion — voir `seed_sources.py`) et
`ingestion_runs` (état/reprise par commune — voir `run_all.py`).

Sources externes → tables (vue synthétique) :

| Famille de source | Table(s) cible(s) principale(s) |
|---|---|
| IGN Géoplateforme WFS/WMS (GPU, BD TOPO, OCS GE, LiDAR HD, RPG, ortho) | `spatial_layers`, `parcel_vegetation`, `ortho_tiles` |
| apicarto.ign.fr (cadastre, GPU zone_urba/prescriptions) | `parcels`, `spatial_layers` |
| Géorisques (georisques.gouv.fr) | `spatial_layers` (sol_pollue, cavite, mvt, icpe, alea) |
| DEAL Réunion Lizmap (PPR, aléas) | `spatial_layers` |
| DVF (files.data.gouv.fr / geo-dvf) | `dvf_mutations`, `dvf_mutations_histo`, `dvf_secteur_medianes` |
| SITADEL — SDES/Dido (vivant) + ODS Région (mort) | `sitadel_permits`, `m10_permit_delais` |
| BAN (adresse.data.gouv.fr) | `adresses`, `adresse_parcelles` |
| DGFiP « parcelles PM » | `parcelle_personne_morale`, `pm_proprietaires_millesimes` |
| BODACC / INPI-RNE / recherche-entreprises | `bodacc_procedures`, `pm_dirigeants`, `owner_enrichment` |
| ADEME DPE (data.ademe.fr) | `dpe_records` |
| RNIC copropriétés | `rnic_coproprietes` |
| PVGIS (JRC EU) + EDF SEI/ODRE + APER + registre PV | `solar_grid`, `parcel_solar`, `grid_capacity`, `pv_registry`, `parkings_aper` |
| Ortho tuiles IGN → détection piscines/PV | `ortho_tiles`, `ortho_detections`, `parcel_equipements` |
| INSEE RP2022 (EGOUL) + Office de l'eau | `anc_maille_taux`, `parcel_anc` |
| Cartofriches (Cerema) | `spatial_layers` (kind=friche) |
| QPV (data.gouv) | `spatial_layers` (kind=qpv) |
| Mérimée (data.culture.gouv) | `spatial_layers` (kind=abf) |
| Overpass/OSM (aménités) | `spatial_layers`, `parcel_amenites` |

---

## 2. Sources externes (connecteur / ingesteur → source → table)

Domaines relevés par `grep http` (occurrences décroissantes) :
`data.regionreunion.com`, `data.geopf.fr`, `apicarto.ign.fr`,
`georisques.gouv.fr`, `geoservices.ign.fr`, `opendata-reunion.edf.fr`,
`deal974.lizmap.com`, `insee.fr`, `recherche-entreprises.api.gouv.fr`,
`data.gouv.fr` / `files.data.gouv.fr` / `static.data.gouv.fr`,
`overpass-api.de` (+ `overpass.kumi.systems`),
`data.statistiques.developpement-durable.gouv.fr`, `cartagene.cerema.fr`,
`apidf-preprod.cerema.fr`, `datafoncier.cerema.fr`, `cadastre.data.gouv.fr`,
`re.jrc.ec.europa.eu` (PVGIS), `peigeo.re` (AGORAH), `odre.opendatasoft.com`,
`geolittoral.developpement-durable.gouv.fr`, `data.economie.gouv.fr`,
`data.culture.gouv.fr` (Mérimée), `data.ademe.fr` (DPE),
`bodacc-datadila.opendatasoft.com`, `adresse.data.gouv.fr` /
`api-adresse.data.gouv.fr`, `registre-national-entreprises.inpi.fr`,
`diffusion-lidarhd.ign.fr`, `inpn.mnhn.fr`, `eaureunion.fr`.

| Source (domaine) | Fichier appelant | Table(s) écrite(s) |
|---|---|---|
| Cadastre Etalab (`cadastre.data.gouv.fr`, `apicarto.ign.fr`) | `connectors/cadastre.py`, `ingestion/cadastre_bulk.py` | `parcels` |
| GPU zone_urba / prescriptions (`apicarto.ign.fr`) | `connectors/gpu.py`, `ingestion/layers_ingest.py` | `spatial_layers` |
| BD TOPO / OCS GE / RPG / ravines / bâti (`data.geopf.fr` WFS) | `connectors/wfs.py`, `ingestion/layers_ingest.py` | `spatial_layers` |
| PPR / aléas DEAL (`deal974.lizmap.com`) | `connectors/wfs.py`, `ingestion/layers_ingest.py` | `spatial_layers` |
| SAR / AGORAH PLU (`peigeo.re`) | `ingestion/agorah_plu.py`, `layers_ingest.py` | `spatial_layers` |
| Géorisques (`georisques.gouv.fr`) | `connectors/georisques.py`, `ingestion/georisques_layers.py` | `spatial_layers` (sol_pollue/cavite/mvt/icpe) |
| Cartofriches (`apidf-preprod.cerema.fr`) | `connectors/cartofriches.py`, `ingestion/cartofriches.py` | `spatial_layers` (friche) |
| QPV (`static.data.gouv.fr`) | `connectors/qpv.py`, `ingestion/qpv.py` | `spatial_layers` (qpv) |
| Mérimée MH (`data.culture.gouv.fr`) | `connectors/merimee.py`, `ingestion/abf_merimee.py` | `spatial_layers` (abf) |
| Overpass/OSM (`overpass-api.de`) | `ingestion/amenites.py` | `spatial_layers`, `parcel_amenites` |
| DVF géolocalisé (`files.data.gouv.fr` geo-dvf) | `ingestion/layers_ingest.py`, `dvf_marche.py` | `dvf_mutations`, `dvf_secteur_medianes` |
| DVF historique fichiers plats | `ingestion/dvf_histo.py` | `dvf_mutations_histo` |
| SITADEL SDES/Dido (`data.statistiques.developpement-durable.gouv.fr`) | `ingestion/permits_sdes.py` | `sitadel_permits`, `ingestion_runs` |
| SITADEL ODS Région (mort 2023-09) (`data.regionreunion.com`) | `ingestion/permits.py` | `sitadel_permits` (legacy) |
| Délais permis M10 | `ingestion/permit_delais_m10.py` | `m10_permit_delais` |
| BAN (`adresse.data.gouv.fr`) | `ingestion/ban_adresses.py` | `adresses`, `adresse_parcelles`, `rnic_coproprietes` (rattach.) |
| DGFiP parcelles PM (`data.economie.gouv.fr` / fichiers) | `ingestion/personnes_morales.py`, `pm_millesimes.py` | `parcelle_personne_morale`, `pm_proprietaires_millesimes` |
| BODACC (`bodacc-datadila.opendatasoft.com`) | `connectors/bodacc.py`, `ingestion/bodacc.py`, `score_v_fetch.py` | `bodacc_procedures`, `bodacc_annonces_owner` |
| INPI RNE (`registre-national-entreprises.inpi.fr`) | `connectors/inpi_rne.py`, `ingestion/inpi_rne.py` | `pm_dirigeants`, `pm_dirigeant_gigogne` |
| recherche-entreprises (`recherche-entreprises.api.gouv.fr`) | `connectors/recherche_entreprises.py`, `score_v_fetch.py` | `owner_enrichment` |
| DPE ADEME (`data.ademe.fr`) | `connectors/dpe.py`, `ingestion/dpe.py` | `dpe_records` |
| RNIC copropriétés | `ingestion/rnic.py` | `rnic_coproprietes` |
| PVGIS (`re.jrc.ec.europa.eu`) | `ingestion/solaire_pvgis.py` | `solar_grid`, `parcel_solar` |
| EDF SEI / ODRE (`opendata-reunion.edf.fr`, `odre.opendatasoft.com`) | `ingestion/solaire_grid_capacity.py`, `solaire_conso.py` | `grid_capacity`, `conso_baseline_commune`, `parcel_solar` |
| Registre PV / APER (`data.gouv.fr`) | `ingestion/solaire_pv_registry.py`, `parkings_aper.py` | `pv_registry`, `parkings_aper`, `parcel_solar`, `parcel_signals` |
| LiDAR HD MNH + ortho IRC (`data.geopf.fr`, `diffusion-lidarhd.ign.fr`) | `ingestion/vegetation.py`, `ortho_tiles.py` | `ortho_tiles`, `vegetation_zonal_acc`, `parcel_vegetation` |
| Ortho tuiles → piscines/PV (`data.geopf.fr` WMS) | `ingestion/ortho_tiles.py`, `ortho_piscines.py`, `ortho_pv.py`, `ortho_equipements.py` | `ortho_tiles`, `ortho_detections`, `parcel_equipements` |
| Pente (RGE ALTI) | `ingestion/ortho_pente.py`, `layers_ingest.py` | `spatial_layers` (pente) |
| INSEE RP2022 EGOUL + Office de l'eau (`insee.fr`, `eaureunion.fr`) | `ingestion/anc.py` | `anc_maille_taux`, `parcel_anc`, `parcel_signals` |
| Bruit routier / SUP GPU / 50 pas géométriques | `ingestion/bruit_route.py`, `sup_gpu.py`, `cinquante_pas.py` | `spatial_layers` |

Note secrets : `INPI_API_*` sont lus en variables d'environnement (jamais en
dur — cf. `seed_sources.py` ligne 188). Aucun secret n'est stocké dans les
fichiers du domaine.

---

## 3. Arborescence commentée

### 3.1 `src/labuse/connectors/` (couche accès réseau)

| Fichier | `wc -l` | Rôle |
|---|---|---|
| `base.py` | 74 | `Connector` (classe mère, `test_connection`), `GenericGetConnector`, `ConnectionTestResult`. |
| `__init__.py` | 92 | Registre : `get_connector(source_name)` retourne l'instance du connecteur. |
| `wfs.py` | 93 | `WfsConnector` générique piloté par `config/wfs_layers.yaml` : `fetch_layer(endpoint_key, typename, bbox)`, `get_capabilities_url`. |
| `cadastre.py` | 116 | `CadastreConnector.fetch_by_section/fetch_by_geom`; `parse_parcelles`, `ingest_parcels` → `parcels`. |
| `gpu.py` | 50 | `GpuConnector.zone_urba/prescriptions`; `parse_zones`. |
| `georisques.py` | 126 | `GeorisquesConnector` : sites_pollues, cavites, ICPE, mvt, risques, catnat, azi, by_latlon. |
| `dpe.py` | 100 | `DpeConnector.fetch_commune/fetch_orphelins_974`; `in_reunion` (filtre géo). |
| `bodacc.py` | 234 | `BodaccConnector.fetch_score_v_by_sirens/fetch_collective_by_sirens`; parseurs annonces + extraction SIREN. |
| `inpi_rne.py` | 348 | `InpiRneConnector` (auth SSO, quota `QuotaExceededError`, `fetch_company/fetch_companies`); `parse_company`, `compute_age`, `propension_band`. |
| `recherche_entreprises.py` | 137 | `RechercheEntreprisesConnector.fetch_by_siren(s)/search_by_name`; `normalize_denomination`, `parse_result`. |
| `cartofriches.py` | 80 | `CartofrichesConnector.geofriches/detail`. |
| `merimee.py` | 57 | `MerimeeConnector.fetch_reunion`; extraction coordonnées. |
| `qpv.py` | 38 | `QpvConnector.fetch_dep(dep='974')`. |

### 3.2 `src/labuse/ingestion/` — hubs (fichiers longs / structurants)

**`layers_ingest.py` (1032 l.)** — hub des couches structurantes → `spatial_layers`.
Une fonction `ingest_*` par couche, chacune rangeant son résultat dans le
`kind`/`subtype` exact consommé par la cascade phase 1. Géométries stockées en
4326 (`ST_GeomFromGeoJSON` + `ST_MakeValid`). Résultats partiels isolés par
SAVEPOINT — une couche en échec n'empêche pas les autres. Fonctions :
`ingest_gpu_zones`, `ingest_gpu_prescriptions`, `ingest_ppr_sup`,
`ingest_ppr_zone`, `ingest_georisque_alea`, `ingest_parc_national`,
`ingest_potentiel_foncier`, `ingest_sar`, `ingest_abf`, `ingest_bdtopo`,
`ingest_ravines`, `ingest_batiments`, `ingest_ocsge`, `ingest_pente`,
`ingest_dvf` (+ `fetch_geo_dvf`, `load_dvf_geo`, `_geo_dvf_aggregate`),
`ingest_foret_publique`, `ingest_rpg_agricole`, `ingest_espaces_proteges`,
`ingest_trait_de_cote`, `ingest_osm_faux_positifs`, et l'orchestrateur
`ingest_layers(session, insee, commune, ...)`.

**`vegetation.py` (484 l.)** — Wave ANC & Végétation, Lot B : canopée par NDVI
(BD ORTHO IRC) × hauteur (MNH LiDAR HD). Réutilise la grille `ortho_tiles`
(EPSG:2975). IRC streamé par WMS (cache `irc_acquise_at`), MNH streamé en
GeoTIFF float32 jamais stocké. Fonctions : `process_tiles`, `_rasterize`,
`preparer_validation`, + écritures `vegetation_zonal_acc`, `parcel_vegetation`,
`parcel_signals`, `ortho_detections`. `CREATE TABLE vegetation_zonal_acc`,
`parcel_vegetation`.

**`personnes_morales.py` (120 l.)** — propriétaires personnes morales (1.A),
fichier DGFiP « parcelles des personnes morales » (Licence Ouverte v2,
millésime annuel, CSV `;` par département, `PM_25_NB_974.csv`). Reconstruit
l'IDU 14 caractères, classe via `proprietaire_type.classify_dgfip`, upsert
idempotent → `parcelle_personne_morale`. Parcelle absente = particulier, aucune
donnée perso (contrainte légale). `ingest` (via `INSERT INTO
parcelle_personne_morale`).

**`permits.py` (225 l.)** — SITADEL voie ODS Région, **morte depuis 2023-09**
(données arrêtées au 31/01/2023), conservée en LEGACY documenté, non appelée.
Ses helpers (`_idu`, `_nature`, `_statut`, `nearby_permits`,
`geocode_permits_via_cadastre`) restent partagés avec la voie SDES. Fonctions
publiques : `ingest_permits`, `geocode_permits_via_cadastre`, `nearby_permits`
→ `sitadel_permits`, signal `new_permit_nearby`.

**`permits_sdes.py` (295 l.)** — SITADEL voie **VIVANTE** SDES/Dido (Sitadel3,
MAJ mensuelle, historique 2013+). Export CSV filtré serveur par datafile (4
datafiles : PC/DP logements, PC/DP non résidentiels, PA, PD).
`ensure_indexes`, `ingest_sdes`, `geocode_missing`, `refresh_since`, `run` →
`sitadel_permits`, `ingestion_runs`.

**`run_all.py` (127 l.)** — orchestrateur ingestion+évaluation MULTI-COMMUNES
974, en série et REPRENABLE via `ingestion_runs.status`. `run_status`,
`purge_commune`, `ingest_commune`, `evaluate_commune`. Bbox des couches = bbox
de la commune. Appelé depuis `communes.py`, `cli.py`, `segments/catnat.py`.

**`seed_sources.py` (390 l.)** — déclaration des métadonnées `data_sources`
(nom, URL, `technical_notes`, statut « live »). Source de vérité des sources
recensées (BODACC, INPI, Géorisques, Cartofriches, Mérimée, QPV, DPE, bruit,
SUP, 50 pas...).

### 3.3 `src/labuse/ingestion/` — autres fichiers

| Fichier | `wc -l` | Rôle |
|---|---|---|
| `__init__.py` | 1 | Package marker. |
| `pv_detection.py` | 32 | `detect_rooftop_pv(ortho_tile)` — détection PV toiture (stub / entrée). |
| `solaire_grid_capacity.py` | 47 | Capacité réseau EDF/ODRE → `grid_capacity`. |
| `cinquante_pas.py` | 62 | Bande des 50 pas géométriques (LIMITE_HA, corridor ±90 m) → `spatial_layers` (cinquante_pas). |
| `cadastre_bulk.py` | 67 | Téléchargement cadastre Etalab par commune : `download_parcelles`, `parse_etalab`, `filter_bbox`. |
| `bruit_route.py` | 68 | Secteurs bruit routier (buffer par catégorie) → `spatial_layers`. |
| `qpv.py` | 69 | QPV 974 (zip GeoJSON national) → `spatial_layers` (qpv). Sert le bilan promoteur, pas le score. |
| `sup_gpu.py` | 82 | Servitudes d'utilité publique GPU (assiette par bbox) → `spatial_layers` (sup). |
| `abf_merimee.py` | 84 | Abords MH Mérimée (tampon 500 m) → `spatial_layers` (abf). `ingest`, `parcelles_intersectees`, `bilan`. Flag qualité étage 1. |
| `habitat_solaire_schema.py` | 106 | `ensure_schema` : `CREATE TABLE` solar_grid, parcel_solar, parkings_aper, pv_registry, grid_capacity, solar_api_cache. |
| `ortho_pente.py` | 109 | Pente parcelle (RGE ALTI) : `compute`, `sanity_check`, `run`. |
| `signals.py` | 113 | Veille : `run_watch` → `parcel_signals`, `watch_snapshots`. |
| `solaire_tertiaire.py` | 114 | Obligations solaire tertiaire (parkings, toitures). |
| `dvf_marche.py` | 121 | `ensure_dvf_views`, `compute_medianes_secteur` → `dvf_secteur_medianes`. |
| `cartofriches.py` | 127 | Friches Cerema : `parse_friche`, `ingest_commune`, `parcelles_croisees`, `sample_report` → `spatial_layers` (friche). |
| `bodacc.py` | 129 | Procédures collectives BODACC : `distinct_sirens`, `ingest_bodacc`, `parcelles_sous_pression`, `sample_report` → `bodacc_procedures`. |
| `solaire_pv_registry.py` | 130 | Registre PV : `ingest`, `commune_forte_densite`, `repowering` → `pv_registry`, `parcel_solar`. |
| `amenites.py` | 131 | POI/aménités Overpass : `ingest_poi_commune`, `ingest_poi_affichage`, `compute_amenites_commune` → `spatial_layers`, `parcel_amenites`. |
| `permit_delais_m10.py` | 145 | Délais dépôt→autorisation : `build_delais` → `m10_permit_delais`. |
| `parkings_aper.py` | 151 | Parkings APER (obligation solaire) : `build_parkings`, `rattacher`, `signaux_deadline`, `run` → `parkings_aper`, `parcel_signals`. |
| `ortho_tiles.py` | 154 | Grille tuiles ortho + acquisition WMS : `build_grid`, `acquire`, `tile_path`, `cache_dir`, `purge_cache` → `ortho_tiles`. |
| `solaire_flags.py` | 160 | Drapeaux solaires (topo/ombrage, etc.) → `parcel_solar`. |
| `pm_millesimes.py` | 164 | Millésimes DGFiP PM (2021-2024) : `url_millesime`, `fetch_974_csv`, `ingest_millesime` → `pm_proprietaires_millesimes`. |
| `solaire_conso.py` | 166 | Conso baseline commune (EDF) : `compute_conso` → `conso_baseline_commune`, `parcel_solar`. |
| `rnic.py` | 182 | RNIC copropriétés : `ingest_rnic`, `rattacher_proche`, `purge_rgpd`, `complements` → `rnic_coproprietes`. |
| `agorah_plu.py` | 194 | PLU AGORAH (fallback GPU non propre) : `agorah_partition`, `should_use_agorah_fallback`, `fetch_agorah_zones`, `ingest_agorah_plu_zones`, `agorah_plu_preflight`. |
| `score_v_fetch.py` | 196 | Enrichissement propriétaires (recherche-entreprises + BODACC) : `eligible_sirens`, `fetch_owner_enrichment`, `denominations_sans_siren`, `fetch_denom_lookups`, `matched_owner_sirens`, `fetch_bodacc_annonces` → `owner_enrichment`, `bodacc_annonces_owner`. |
| `ortho_equipements.py` | 199 | Matérialisation piscines/PV : `materialiser_piscines`, `signal_piscines`, `precision_validee`, `materialiser_pv`, `branchements_solaire`, `run` → `parcel_equipements`, `parcel_signals`. |
| `dvf_histo.py` | 207 | DVF historique multi-millésimes : `ensure_table`, `parse_fichier`, `ingest_millesime` → `dvf_mutations_histo`. |
| `demo_saint_paul.py` | 215 | Seed démo synthétique (Saint-Paul 97415) : `reset_demo`, `seed_demo` → `spatial_layers`, `parcels`, `dvf_mutations`, `sitadel_permits`, `parcel_source_results`. |
| `georisques_layers.py` | 238 | Couches Géorisques : parseurs sol_pollue/cavite/mvt/icpe, `ingest_commune`, `ingest_mvt_commune`, `parcelles_croisees`, `sample_report` → `spatial_layers`. |
| `ortho_pv.py` | 243 | Détection PV sur tuiles : `_detect_pv` → `ortho_detections`, `ortho_tiles`. |
| `solaire_pvgis.py` | 245 | Baseline PVGIS (grille ~400 m, PVcalc SARAH3, IDW, flags) : `build_grid` → fetch → interpolate → flags → `solar_grid`, `parcel_solar`. |
| `inpi_rne.py` | 253 | Dirigeants PM (INPI RNE) : `eligible_sirens`, `ingest_inpi_rne`, `sample_report`, `resolve_gigogne` → `pm_dirigeants`, `pm_dirigeant_gigogne`. |
| `dpe.py` | 255 | DPE ADEME : `parse_record`, `ingest_commune`, `ingest_orphelins`, `sample_report` → `dpe_records`. Re-géocodage BAN. |
| `ortho_piscines.py` | 289 | Détection piscines : `detect_tiles`, `post_traitement` → `ortho_detections`, `ortho_tiles`. |
| `ban_adresses.py` | 298 | BAN : `download_ban_csv`, `ingest_ban` (COPY staging), `couverture_bati_residentiel`, `rattacher_copros_par_adresse` → `adresses`, `adresse_parcelles`, `rnic_coproprietes`. |
| `anc.py` | 386 | ANC probabiliste : `ingest_insee_egoul`, `ingest_iris_contours`, `ingest_zonages_gpu`, `compute_proba`, `calage_office_eau`, `signal_mutation`, `couverture` → `anc_maille_taux`, `parcel_anc`, `parcel_signals`. |

---

## 4. Métriques

### 4.1 Top fichiers longs (`wc -l`)

1. `ingestion/layers_ingest.py` — 1032
2. `ingestion/vegetation.py` — 484
3. `ingestion/seed_sources.py` — 390
4. `ingestion/anc.py` — 386
5. `connectors/inpi_rne.py` — 348
6. `ingestion/ban_adresses.py` — 298
7. `ingestion/permits_sdes.py` — 295
8. `ingestion/ortho_piscines.py` — 289
9. `ingestion/dpe.py` — 255
10. `ingestion/inpi_rne.py` — 253

Total domaine : ingestion ≈ 8 605 lignes (45 fichiers), connectors ≈ 1 545
lignes (13 fichiers).

### 4.2 Top fonctions longues (approximation par comptage de lignes entre `def`)

| Fonction | Fichier:ligne | ~lignes |
|---|---|---|
| `add_layer` (closure) | `demo_saint_paul.py:100` | 108 |
| `post_traitement` | `ortho_piscines.py:187` | 103 |
| `ingest_rnic` | `rnic.py:71` | 68 |
| `process_tiles` | `vegetation.py:244` | 67 |
| `sample_report` | `inpi_rne.py:102` | 64 |
| `_geo_dvf_aggregate` | `layers_ingest.py:690` | 63 |
| `ingest_insee_egoul` | `anc.py:89` | 62 |
| `compute_conso` | `solaire_conso.py:93` | 61 |
| `nearby_permits` | `permits.py:165` | 61 |
| `_detect_pv` | `ortho_pv.py:99` | 61 |

### 4.3 Marqueurs TODO/FIXME/HACK/XXX

Aucun `FIXME`/`HACK`/`XXX` isolé. Les occurrences `TODO` sont majoritairement
des **marqueurs de doctrine « # TODO étage 1/2 »** (couche présente mais non
branchée au scoring) dans des docstrings/`technical_notes`, pas de la dette de
code au sens strict :

- `abf_merimee.py:6`, `abf_merimee.py:38` — « # TODO étage 1 », ne touche pas au score.
- `amenites.py:8` — poids au calibrage, « # TODO étage 1 ».
- `bodacc.py:8`, `bodacc.py:82` — branchement conditionné à la Vague A, « # TODO étage 2 ».
- `qpv.py:4`, `qpv.py:40` — « # TODO bilan » (non branché au score).
- `inpi_rne.py:8` — « # TODO étage 2 ».
- `georisques_layers.py:10`, `:158` — « # TODO étage 1 », n'alimente pas le score.
- `cartofriches.py:8` — « # TODO étage 1/2 », n'alimente pas le score.
- `vegetation.py:23` — « TODO v1.1 : pondération directionnelle nord/est/ouest » (le seul TODO d'évolution technique réel).
- `seed_sources.py` (lignes 54, 60, 66, 72, 182, 188, 218, 224, 230, 253) — marqueurs de doctrine dans les `technical_notes`.
- `score_v_fetch.py` — les `todo` sont des noms de **variables locales** (listes de SIREN à requêter), pas des marqueurs.

### 4.4 Fichiers du domaine jamais importés ailleurs

Modules ingestion sans `import` détecté hors de leur propre fichier :
`agorah_plu`, `bodacc`, `dvf_histo`, `habitat_solaire_schema`, `permits_sdes`,
`pm_millesimes`, `pv_detection`.

Nuances constatées : `bodacc` est bien référencé par nom dans `cli.py` et
`api/ia.py` (invocation par nom, pas `import ingestion.bodacc`). Les autres
(`permits_sdes`, `dvf_histo`, `pm_millesimes`, `habitat_solaire_schema`,
`agorah_plu`) exposent une fonction `run`/`ensure_*`/`ingest_*` sans référence
détectée dans `cli.py`, `api/`, `communes.py` — invocation probable manuelle /
script one-shot. `pv_detection.py` (stub 32 l.) n'est référencé nulle part.
Aucun `[project.scripts]` du `pyproject.toml` ne pointe explicitement vers ces
modules (section scripts présente mais non peuplée pour ces noms).

---

## 5. Histoire (git)

| Domaine | Dernier commit | Nb de commits |
|---|---|---|
| `src/labuse/ingestion/` | 2026-07-14 16:55:01 +0200 | 87 |
| `src/labuse/connectors/` | 2026-07-11 23:05:52 +0200 | 24 |

Les ingesteurs sont plus actifs et plus récents que les connecteurs (couche
d'accès stabilisée plus tôt).

---

## 6. Observations factuelles

- **Deux ingesteurs de permits** : `permits.py` (voie ODS Région, marquée
  « † mort depuis 2023-09 », conservée en legacy) et `permits_sdes.py` (voie
  SDES/Dido vivante). Les deux écrivent `sitadel_permits` ; le géocodage
  (`geocode_permits_via_cadastre`, `nearby_permits`) est partagé.
- **Famille solaire éclatée en 8 fichiers** : `solaire_conso`, `solaire_flags`,
  `solaire_grid_capacity`, `solaire_pv_registry`, `solaire_pvgis`,
  `solaire_tertiaire` + le schéma `habitat_solaire_schema` + `pv_detection`.
  Plusieurs convergent vers `parcel_solar`.
- **Trois chaînes ortho** distinctes partageant `ortho_tiles`/`ortho_detections` :
  piscines (`ortho_piscines`), PV (`ortho_pv`), végétation (`vegetation`,
  qui réutilise la grille tuiles). `ortho_equipements` matérialise les deux
  détections en `parcel_equipements`.
- **`spatial_layers` est la table pivot** : au moins 13 ingesteurs y écrivent
  via `kind`/`subtype` (GPU, PPR, géorisques, ABF, friche, QPV, bruit, SUP, 50
  pas, aménités, pente...). `layers_ingest.py` en concentre l'essentiel.
- **`ortho_tiles` importé par 5 modules** — le plus « partagé » du domaine.
- **Deux ingesteurs DVF** : `dvf_histo.py` (millésimes plats →
  `dvf_mutations_histo`) et `layers_ingest.ingest_dvf` / `dvf_marche.py`
  (geo-dvf → `dvf_mutations`, `dvf_secteur_medianes`).
- **Trois modules d'enrichissement PM/propriétaires** : `bodacc`, `inpi_rne`,
  `score_v_fetch` (recherche-entreprises) ; plus les fichiers propriété DGFiP
  `personnes_morales` / `pm_millesimes`.
- **Chaîne PM par nom** : `bodacc` est appelé par nom (cli/api) mais sans
  `import` de module — le détecteur d'imports le classe « non importé » à tort.
- **Deux endpoints Overpass** configurés (`overpass-api.de` +
  `overpass.kumi.systems`) — miroir de repli.
- **`demo_saint_paul.py`** est le seul ingesteur qui écrit des données
  synthétiques (seed démo, INSEE 97415), touchant 5 tables métier.
- **Config = source des seuils** : les mandats (ortho, ANC/végétation, solaire,
  WFS) externalisent tous leurs seuils/endpoints dans `config/*.yaml`
  (discipline « jamais en dur »). `wfs_layers.yaml` déclare 3 endpoints de base
  (geoplateforme, deal_reunion Lizmap, peigeo AGORAH) et distingue
  `reliability: verifie | a_confirmer`.

### Configs du domaine (rôle)

| Fichier | Rôle |
|---|---|
| `config/wfs_layers.yaml` | Déclaration des couches WMS/WFS pour le connecteur générique (endpoint, typename, spatial_kind, reliability). |
| `config/anc_vegetation.yaml` | Seuils du mandat ANC & Végétation (INSEE RP2022 EGOUL, URLs zip/dictionnaire, seuils NDVI/hauteur). |
| `config/detection_ortho.yaml` | Seuils du pipeline détection ortho (pente terrassement 15°, tuiles, colorimétrie V0). |
| `config/habitat_solaire.yaml` | Coefficients métier solaire (PVGIS peakpower/loss/angle/aspect=180 nord, seuils réglementaires). |
| `config/epci_974.yaml` | Rattachement commune→EPCI (BANATIC/DGCL 2025) pour le bloc PLH. |
| `config/gestionnaires_via.yaml` | Mapping gestionnaires eau/assainissement/élec par commune (contact administratif, aucune donnée sensible). |
| `config/rtaa_dom.yaml` | Rappel réglementaire RTAA DOM (construction neuve, seuils altitude 400/600 m, vérifié Légifrance). |

---

## 7. Zones les moins certaines (relevé factuel)

- **Fichiers « jamais importés »** (`permits_sdes`, `dvf_histo`,
  `pm_millesimes`, `habitat_solaire_schema`, `agorah_plu`, `pv_detection`) :
  le mode d'invocation exact (script manuel vs entrée CLI non peuplée) n'a pas
  été tracé jusqu'à un appelant unique.
- **Correspondance domaine↔table par grep** : les URLs et les
  `INSERT INTO`/`CREATE TABLE` ont été relevés séparément ; l'association
  source→table du tableau §2 s'appuie sur les docstrings et la co-localisation,
  non sur un traçage runtime.
- **`peigeo.re` / AGORAH SAR** : endpoint marqué « confirmer endpoint OWS »
  dans `wfs_layers.yaml` — statut « a_confirmer » non levé dans le code lu.
