# INVENTAIRE SPIN-OFF « VUES + SOLAIRE » — la carte au trésor

Branche d'archive : `spinoff/vues-solaire` · tag : `avant-spinoff-vues-solaire` (état complet de main
AVANT tout retrait). **Cette branche n'est jamais mergée ni supprimée.** Objectif : dans six mois, ce
document suffit à reconstruire les deux features dans un produit extérieur (Plein Sud / Soley).

## 0 · Les données (INTOUCHÉES en base — elles dorment, prêtes)

| Table | Lignes | Taille | Contenu |
|---|---|---|---|
| `parcel_solar` | 431 663 | 194 MB | pivot solaire par parcelle : prod_spec PVGIS, score percentile île, 5 flags, conso/facture estimées |
| `parcel_vue_mer` | 150 643 | 13 MB | vue mer par parcelle (oui/partielle/non, distance côte, obstruction %) — jobs err=0 toutes communes |
| `solar_grid` | 15 680 | 3,8 MB | grille ~400 m de points PVGIS (PVcalc v5_3, SARAH3 + horizon) |
| `parkings_aper` | 901 | 2,4 MB | parkings assujettis APER (tranches, échéances 2026/2028, signal) |
| `pv_registry` | 686 | 0,9 MB | registre PV national ODRÉ/EDF SEI (974, repowering 2006-2013) |
| `solar_api_cache` | 0 | — | cache Google Solar API (TTL 30 j, vide) |
| `backup_*_vuemer_*` | 13 tables | — | backups communaux vue mer (2026-07-01/03) |
| + `mv_toitures_tertiaires` | vue matérialisée | — | toitures tertiaires > 500 m² × PM × PVGIS |

Signaux déjà émis dans `parcel_signals` : `aper_deadline` (1 466) — données conservées ; la GÉNÉRATION
future de ces signaux part avec le code.

## 1 · Backend — API

- **`src/labuse/api/solaire.py`** (191 l., EXCLUSIF) — routeur `/solaire` : `fiche/{idu}`, `parkings`
  (CSV), `tertiaire`, `statut` (gating Google Solar), `mesure/{idu}` (stub 501, Lot 8 conditionnel),
  purge cache. Dict SOURCES (attributions PVGIS/EDF SEI/ODRÉ/APER/amiante).
- **`src/labuse/api/enrichment.py`** — `vue_mer(db, parcel_id)` (l.201-264 : profil 1D RGE ALTI +
  trait de côte, raccourci front-de-mer < 120 m, ratio d'obstruction, 3 états) + `_memo_vue_mer`
  (l.267). **ATTENTION PARTAGÉ** : `_alti_sample_points`/`_alti_query` (l.74-127) servent AUSSI
  `exposition()` (orientation cardinale, hors spin-off) → **restent** ; seul `vue_mer()` part.
- **`src/labuse/api/app.py`** — intégrations : param `vue_mer` de filtre (l.572, 627-628, 685, 739,
  968), SELECT/JOIN `parcel_vue_mer` (l.1153, 1180, 1217), montage du routeur solaire (l.3006, 3035).

## 2 · Backend — modules d'ingestion (EXCLUSIFS, 862 l.)

`src/labuse/ingestion/` : `habitat_solaire_schema.py` (DDL des 6 tables, l.21-100) ·
`solaire_pvgis.py` (Lot 1 : grille ST_SquareGrid, fetch async PVcalc 10 req/s, IDW 4-NN, percentile,
flag ombrage) · `solaire_conso.py` (Lot 2 : conso commune × ratio surface, clim littoral +20 %, ECS
+1500, piscine +2000) · `solaire_flags.py` (Lot 5 : amiante DPE<1997, azimut élongation 1,4, proba
proprio-occupant, pv_detecte, repowering) · `solaire_pv_registry.py` (Lot 4 : ODRÉ/EDF SEI Data Fair) ·
`solaire_tertiaire.py` (Lot 6 : MV + export CSV) · `solaire_grid_capacity.py` (Lot 7 : capacités postes
sources) · `parkings_aper.py` (Lot 3). **`ortho_pv.py` : à trancher au retrait** — la détection PV ortho
sert le flag solaire ET le re-flag végétation (wave ANC) → vérifier avant de retirer.

## 3 · CLI (8 commandes + 1)

`cli.py` : `solaire-pvgis`, `solaire-flags`, `solaire-conso`, `solaire-tertiaire`, `solaire-parkings`,
`solaire-pv-registry`, `solaire-grid-capacity`, `solaire-cache-purge` (l.1847-1957) + `warm-vue-mer`
(l.936, pré-chauffe côtière).

## 4 · Frontend

- `fiche/Fiche.tsx` : `SolaireTab` (l.594-…), onglet TABS `solaire` (l.899), rendu conditionnel.
- `map/MapView.tsx` : couches `parcels-vuemer`/`ile-vuemer` (filtres `vue_mer='oui'`, l.86, 277, 331,
  530-534).
- `panel/ResultsSection.tsx` : badge vue mer « ◠ » cyan (l.76). `panel/LeftPanel.tsx` : filtre vue mer.
- `lib/api.ts` : `getSolaireFiche`, `modSolaireParkings`, `modSolaireTertiaire`. `lib/filters.ts` :
  `vueMer` (matchScope l.73, chip l.107, removeToken l.120). `store/useApp.ts` : état filtre.
- `outils/registry.ts` : modules **M23 parkings-aper** (phare) et **M24 toitures-tertiaires** ;
  `outils/ModulePanel.tsx` : leurs panneaux.

## 5 · Config

- **`config/habitat_solaire.yaml`** (73 l.) — TOUS les coefficients (pvgis: peakpower 1 kWc, loss 14 %,
  angle 15°, aspect 180° [nord, hémisphère sud] ; conso ; aper: 1 000 m² Réunion décret 2025-802,
  échéances 2026-07-01/2028-07-01 ; pv_registry ; flags ; tertiaire).
- `config.py` : `pvgis_version="v5_3"`, `pvgis_grid_step_m=400`, `pvgis_rps=10.0`, `solar_api_key`,
  `solar_api_cache_ttl_jours=30`, loader `habitat_solaire()` (l.101-108, 195).
- `config/segment_presets.yaml` : presets `pv-residentiel` (l.294-308) et `chauffe-eau-solaire`
  (l.310-325) ; `electricite-facture` référence `facture_elec_estimee_eur` (l.337-340).
- `segments/registry.py` : FilterDefs `score_solaire`, `pv_detecte`, `flag_amiante`,
  `flag_topo_ombrage`, `repowering`, conso/facture (l.177-210), tri `score_solaire_desc` (l.350),
  colonnes d'export (l.388).

## 6 · Faisabilité (intégration fine)

`faisabilite/bilan.py` l.298-313 : `bonus_vue_mer_pct` (défaut 0 %, gate `contexte_eco.vue_mer=='oui'`,
step « Bonus vue mer (2.B) ») ; `bilan_params.py` l.25 : définition du paramètre calibrable.

## 7 · Tests (partent dans l'archive au retrait)

`tests/test_habitat_solaire.py` (191 l., 7 tests : schéma, amiante, azimut, proba proprio, conso,
APER, percentile/ombrage) · `tests/test_vue_mer.py` (66 l., 3 tests : front de mer, profil/relief,
bonus bilan) · références dans `test_segments.py` (filtres gated) et `test_nl_semantics.py` (règle NL
« solaire|photovolta|panneau » → intent potentiel solaire).

## 8 · Partagé vs exclusif (la ligne de coupe)

| Élément | Verdict |
|---|---|
| `_alti_sample_points`/`_alti_query` (RGE ALTI) | **PARTAGÉ — reste** (sert `exposition()`) |
| couche `trait_de_cote` (spatial_layers) | **PARTAGÉ — reste** (50 pas, littoral, cascade) |
| `exposition()` (orientation cardinale) | **reste** (hors spin-off) |
| `ortho_pv.py` (détection PV ortho) | **à vérifier au retrait** (sert aussi re-flag végétation) |
| signaux `aper_deadline` déjà en base | **restent** (données) ; génération future part |
| tout le reste des §1-7 | **EXCLUSIF — part au spin-off** |

## 9 · Checklist de reconstruction (6 mois plus tard)

1. Restaurer depuis CETTE branche (`git checkout spinoff/vues-solaire -- <chemins>`) : les 8 modules
   d'ingestion + `solaire.py` + `vue_mer()`/`_memo_vue_mer` d'enrichment + composants front §4 +
   configs §5 + tests §7.
2. Recréer les tables via `habitat_solaire_schema.py` + `models.py` (parcel_vue_mer l.1051-1054) — ou
   repartir des tables qui DORMENT en base (dump/restore, volumes §0).
3. Vérifier la dispo des APIs externes : PVGIS PVcalc v5_3 (10 req/s), RGE ALTI, ODRÉ/EDF SEI Data
   Fair (pattern /data-fair/api/v1), Google Solar (Lot 8 conditionnel, jamais activé).
4. Limites connues à ne pas re-découvrir : PVGIS/SARAH3 n'a PAS le gradient côtier Ouest/Est de La
   Réunion (mémoire pvgis-sarah3) ; APER = décret 2025-802 (seuil Réunion 1 000 m²) ; registre PV
   < 36 kVA agrégé commune (jamais géolocalisé individuel).
