# SOURCES-AUDIT-2 — la partie sources, sans aucun doute

**Branche** `audit/sources-2` · worktree `/Users/openclaw/Desktop/labuse-sources` · lecture seule (aucune écriture `src/` ni base) · 2026-09-27.
**Base** `postgresql://openclaw@localhost:5432/labuse` (dev, même schéma que `main`). App non lancée — tout est prouvé par le code + la base.
**Méthode** : le catalogue `data_sources` → le pont `circuit_etats.NOM_VERS_SLUG` → les réservoirs `registre/tables.RESERVOIR_TABLES` → les tables/`spatial_layers.kind` en base (comptes EXACTS `count(*)`, jamais l'estimateur `pg_stat`), croisés avec le registre servi `registre/donnees.DONNEES` et le tracé code des consommateurs (fiche parcelle/commune, outils, filtres, couches, exports, Copilote, Radar/Veille).

---

## Les cinq chiffres

| Chiffre | Valeur | Définition retenue (preuve) |
|---|---:|---|
| **Sources actives** | **123** | `data_sources` total **128** − 5 `retiree`. (Le mandat citait « 125 actives » : le catalogue est passé de 125 à 128 ; 5 retirées → 123.) `SELECT status,count(*) FROM data_sources GROUP BY status` |
| **Sources affichées** | **98** | `WHERE_AFFICHEES` (sources_catalog.py:36) = 96 `connecte` + 2 `manuel`. Vérifié : `SELECT count(*) … WHERE lower(status) IN ('connecte','manuel','live') AND technical_notes NOT LIKE 'DOUBLON/RETIRÉ/DORMANT%' AND affichage_desactive=false` → **98**. |
| **Sources fantômes** | **0** | Aucune table porteuse de donnée-source lue par l'app n'échappe au catalogue (détail §A). Les 35 tables orphelines sont des sauvegardes/scratch/exploitation ; les 70 `kind` de `spatial_layers` tracent tous vers une ligne `data_sources`. |
| **Sources mortes** | **5** | Les 5 lignes `retiree` : lignes conservées mais **jamais lues** par l'app (détail §A). La seule « surprise » est **Office de l'eau** (table de 6 lignes conservée, 0 lecteur, mais un commentaire canonique la dit encore servie — voir E3). |
| **Cases « devrait l'être »** | **3** | `enr_exclue_hors_toiture` (APER), `mesures_compensatoires` (GéoMCE), `scot` — présentes sur la carte / en fiche commune mais absentes de la **fiche parcelle** alors qu'elles touchent la parcelle (détail A1-A3). |

Livrable : **`MATRICE.csv`** (98 sources affichées × 9 endroits) + ce rapport. **98/98 affichées sont servies au moins quelque part** (aucune affichée morte).

---

## A · Le compte juste

### Les 30 non-affichées : raison, et si elle tient

30 lignes hors vitrine = **5 `retiree` + 6 `alias` + 4 `hub` + 14 `partenariat_requis` + 1 `interne`.**

| Statut | N | Raison | Tient ? |
|---|---:|---|---|
| `alias` | 6 | DOUBLON de catalogue (canal du même réservoir), `alias_de` renseigné : 2→1 (Cadastre Etalab→API Carto), 65→6 (RGE ALTI 5 m→RGE ALTI), 67→63 (GPU assainissement info-surf→GPU assainissement), 9→15 (Potentiel foncier Région→data.regionreunion), 21→86 (SIRENE→SIRENE établissements), 119→5 (DVF Réunion Région→DVF). | **Oui** (6/6). |
| `hub` | 4 | Portails (Région ODS, PEIGEO, DEAL WMS/WFS, Géoplateforme) : servent N couches via d'AUTRES lignes, aucune donnée propre. | **Oui** — nuance : **PEIGEO** noté « hôte injoignable » (portail mort mais étiqueté hub). |
| `interne` | 1 | Cadastre d'époque (96) — référentiel interne (`cadastre_historique`, 6 526 lignes) pour « Remonter le temps ». | **Oui.** |
| `retiree` | 5 | Voir « mortes » ci-dessous. | 4/5 nettes ; 1 contradiction doc (Office de l'eau, E3). |
| `partenariat_requis` | 14 | Chantiers « en attente de demande / convention » (Fichiers fonciers, DV3F, LOVAC, ZAE, ZAC, OPAH, ORT infra, ENS Dépt, OLL micro, assainissement SIG EPCI, ZPPA, SAR officiel, Réunion Express, carte hypsométrique) : aucune table/donnée attendue à ce stade. | **Oui pour 12/14** — 2 exceptions contradictoires : **ENS du Département** (E4) et **SAR** (voir note). |

**Note SAR (118, `partenariat_requis`)** : la couche SIG officielle du SAR n'est pas diffusée (raison exacte), MAIS 2 453 polygones `kind=sar` sont en base et servis (fiche cascade + carte), issus du **proxy AGORAH** (sources 9/15, alias/connectée). La ligne 118 reste donc « en attente » à juste titre (c'est l'officiel qui manque), mais le mandat doit savoir que **du SAR EST servi**, sous une autre source.

### Sources fantômes — 0

- **Tables orphelines** (schéma − `RESERVOIR_TABLES` − `TABLES_FABRIQUEES` − `TABLES_EXPLOITATION` − PostGIS) = **35**, TOUTES des sauvegardes/scratch/opérationnelles à 0 ligne (`*_backup*`, `*_pre_*`, `*_avant`, `m6_snapshot_*`, `repli_*`, `qa_*`…). Deux seules sont lues par l'app — `agent_runs` (copilote_v2/historique.py, 0 ligne) et `pige_watermark` (pige/digests.py) — et sont **opérationnelles**, pas des données-source. → aucun fantôme.
- **`spatial_layers` (70 `kind`)** : chaque `kind` trace vers une ligne `data_sources`. Les 3 non listés dans les `couches` d'un réservoir (`pylone`, `poste_transformation` → **BD TOPO IGN** ; `ppr_etat` → **DEAL PPR**) sont bien attribués ailleurs (donnees.py:1014-1024, reservoirs=`bd_topo`) : incohérence de déclaration interne (A6), pas un fantôme.

### Sources mortes — les 5 `retiree`

| id | Source | Table / 974 | Lue ? | Raison | Verdict |
|---|---|---|---|---|---|
| 49 | EDF SEI — open data | pas de table | non | amont HTTP 410 Gone (jeu retiré par EDF) | mort, raison tient |
| 50 | Registre installations (ODRÉ) | pas de table | non | jamais branché | mort, raison tient |
| 87 | MOBPRO (INSEE) | `mobpro_commune` **0 ligne** | non | retiré | mort, raison tient |
| 89 | BDNB (CSTB) | 0 ligne 974 | non | « métropole seule — 974 absent » | mort, raison tient (`sans ligne 974`) |
| 68 | **Office de l'eau** | `anc_office_eau_commune` **6 lignes** | **non** (tables.py:238 « plus aucun lecteur du code ») | remplacé par INSEE RP2022 EGOUL | **mort — MAIS documentation contradictoire, voir E3** |

---

## Les écarts, par gravité

### Gravité 1 — donnée fausse ou contradictoire

**E1 — DVF servi depuis 4 tables par des chemins de calcul indépendants (risque de chiffres divergents).**
DVF est lu depuis `dvf_mutations` (marché « point de calcul unique », marche_service.py), `dvf_mutations_parcelle` (Étude de zone `zone.py:435`, ANC `ingestion/anc.py:387`, courrier `courrier_compose.py:100`), `dvf_secteur_medianes` (médianes secteur fiche), `v_parcel_dvf_last` (dernière mutation fiche). La médiane €/m² de l'Étude de zone est **recalculée** dans `zone.py:435-445` — le garde-fou EXISTE (dédup `DISTINCT id_mutation,id_parcelle` + ventes ≥ 20 m² bâti + borne `BETWEEN 1000 AND 12000`, commentaire `zone.py:427-434` documentant l'ancien « 100 888 €/m² » corrigé par ETUDE-ZONE-1 A2). **Pas de bug live**, mais **deux calculs de médiane indépendants, sur deux tables, sans garde partagé** : si le filtre YAML du marché (`marche_service._filtre_comparables`/`dvf_profils.yaml`) et les bornes en dur de `zone.py` dérivent, les deux €/m² divergent sans alarme. `region_dvf` (119, alias) = 0 ligne servie.

**E2 — `sol_pollue` : trois sources (SSP/SIS/CASIAS) sur un seul `kind`, filtrage par `subtype` non forcé.**
`georisques_ssp`, `georisques_sis`, `georisques_casias` sont trois lignes `data_sources` déclarées comme réservoirs « logiques » sur le MÊME `kind='sol_pollue'` (531 lignes, subtypes `casias`=458 / `instruction`=63 / `sis`=10 — `tables.py:133-140`). La couche carte filtre par subtype (`couches_tuyau.py`, sis vs casias), mais rien n'IMPOSE le filtre : un lecteur du `kind` sans clause `subtype` mélange les trois concepts. La couverture registre peut attribuer 531 à chacune des trois → triple comptage possible. `sols_parcelle` (fiche) déclare `georisques_sis`+`georisques_casias` ensemble (donnees.py). **Concept partagé, cloison portée par des commentaires, pas par une contrainte.**

**E3 — Office de l'eau (68) : deux vérités opposées dans le code.**
`sources_catalog.py:6-8` affirme encore : « Office de l'eau … est **SERVIE à la fiche** depuis M95 (anc_office_eau_commune) ; une source servie s'affiche ». `registre/tables.py:234-238` (SOURCES-3, daté 2026-09-13) dit l'inverse : « **RETIRÉ** … l'ANC à l'échelle commune est porté par l'INSEE RP2022 EGOUL (`anc_maille_taux`) … **plus aucun lecteur du code** ». Le grep confirme tables.py : 0 lecteur fiche de `anc_office_eau_commune`. → la source est bien morte, mais un commentaire canonique du fichier qui DÉFINIT l'affichage la dit encore servie. Contradiction à trancher.

**E4 — ENS du Département (139, `partenariat_requis` « en attente ») alors que la donnée est déjà en base et servie.**
La ligne 139 déclare « en attente de la demande (non diffusés en open data) ». Or 178 polygones `spatial_layers kind=ens subtype=ens_departement` sont ingérés via la source 113 (**Espaces protégés complémentaires — DEAL Lizmap**, « ENS Dépt 178 »), servis par `enp_couche` (carte) et la couche cascade `ens` (fiche parcelle). → la ligne affirme une donnée non obtenue qui l'EST, via un autre producteur (DEAL).

### Gravité 2 — donnée absente d'un endroit où elle a un sens

**A1 — `enr_exclue_hors_toiture` (APER, source 152) absente de la fiche parcelle.** Servie en couche carte (`enr_exclue_hors_toiture_couche`, niveau commune) mais aucune lecture dans la fiche parcelle, alors que ~103 k parcelles sont intersectées (contrainte APER ombrières/PV — sens direct en fiche). → **devrait l'être** (fiche parcelle). *(La plus notable des 3.)*

**A2 — `mesures_compensatoires` (GéoMCE, source 150) absente de la fiche parcelle.** Couche carte (niveau commune) ; ~700 parcelles intersectées, non signalées en fiche. → **devrait l'être** (fiche parcelle).

**A3 — `scot` (source 151) absente de la fiche parcelle.** Servie en fiche commune + carte, pas en fiche parcelle (toute parcelle est dans un périmètre SCOT). → **devrait l'être** (fiche parcelle).

**A4 — `ppr_etat` ingéré, jamais servi.** 24 lignes `spatial_layers kind=ppr_etat` (état/date d'approbation des PPR/PAC, source DEAL PPR) ingérées (`deal_carmen.ingest_ppr_etat`) ; **aucun lecteur hors ingestion**. Donnée dormante (pas une ligne `data_sources` propre — sous DEAL PPR, qui est servi par ailleurs).

**A5 — 3 sources connectées absentes du registre `donnees.py` bien que servies en fiche.** `forets_onf_bdtopo` (ONF), `erosion_cotiere_geolittoral` (trait de côte), `bd_carto_ocs` (OCS proxy) : servies en fiche parcelle par des couches cascade (`phase1.py:133/841/967`) et **attribuées au client à l'exécution** (`dryrun_cascade_results.data_source_id` renseigné pour 100 % des lignes de ces `layer_name` — vérifié en base). Mais la doctrine de `donnees.py` (« tout ce qui s'affiche et vient d'une source est déclaré ICI ») n'en porte AUCUNE déclaration. → couverture du registre incomplète (**impact client nul** : l'attribution runtime existe). Gravité faible.

**A6 — Incohérence entre les deux cartes source→couche.** `RESERVOIR_TABLES['bd_topo'].couches` omet `pylone` et `poste_transformation`, et `['deal_ppr'].couches` omet `ppr_etat`, alors que `donnees.py` les rattache correctement (`reservoirs=('bd_topo',)`, donnees.py:1014-1024). Deux cartes internes qui ne disent pas la même chose. Gravité faible.

### Gravité 3 — propreté côté client

**P1 — 22 sources affichées ont `source_millesime` NULL → cellule millésime VIDE côté client.** `millesime_source.composer()` (millesime_source.py:95-96) renvoie `None` quand aucun millésime amont n'est publié → la source s'imprime « Nom — producteur », sans millésime. Légitime pour les flux continus (Géorisques, OSM, INPI RNE — `RAISON_SANS_MILLESIME`), **discutable** pour BAN, ABF, BODACC, DPE, SUP, Cartofriches, SRU, NPNRU, INSEE RP Logement, PLH, BD ORTHO IRC : un millésime réel existe (dans `technical_notes` ou `RESERVOIR_TABLES.millesime`) mais n'est pas surfacé. Complétude d'affichage.

**P2 — Deux magasins de millésime.** `data_sources.source_millesime` (client, via `composer`, app.py:1049) vs `RESERVOIR_TABLES[slug].millesime` (page Circuit/Données admin, ex. Sudocuh « état au 31/12/2024 » tables.py). Divergence possible entre les deux, mais **le client ne voit que `source_millesime`** → pas de contradiction visible client (par conception).

**P3 — Attribution/licence exigée non affichée sur la page Sources.** `legal_notes` corrects et présents pour toutes les sources qui l'exigent (IGN, INSEE, OSM/ODbL, DGFiP/Etalab, BRGM), dérivés par `_source_licence()` (app.py:1102). MAIS la licence est **retirée de la vitrine cliente** (`SourcesPage.tsx:11-12`, PAGE-SOURCES-1 lot 2) : le client voit source + producteur, pas la mention de licence (elle reste en fiche via `legal_notes`). Pour OSM/ODbL et DVF (restriction L.112A), l'attribution est exigée par la licence ; à noter qu'elle n'est pas sur la page Sources.

**P4 — Sentinelle : 6 sources affichées sans ligne `source_veille`.** 104 lignes `source_veille` (toutes actives) ; 6 sources `connecte/manuel` ne sont pas surveillées (état normal, mais absence de veille amont).

**P5 — Jargon client : RAS.** Aucun jargon interne dans les NOMS affichés (`data_sources.name` propres) ni dans les champs rendus. Les termes internes (DOUBLON, PROXY, MESURÉ MAXIMUM, `spatial_layers`, `kind=`, `q_v15`) restent confinés à `technical_notes`, non affiché. Les badges nature (« proxy », « curée manuellement », « servi par proxys », `_source_nature()` app.py:1139) sont lisibles. ✓

---

## B · La matrice d'arrosage

`MATRICE.csv` — une ligne par source affichée (98), une colonne par endroit : `fiche_parcelle · fiche_commune · carte_couches · filtres · outils · export_dossier · export_flash · copilote · radar_veille`. Valeurs : `servie` / `devrait` / `sans_objet`.

Construction : dérivée du registre servi `DONNEES` (niveau parcelle/commune, type couche), des couches raster WMTS (`ortho_proxy.py`), de l'attribution cascade runtime (`dryrun_cascade_results.data_source_id`), et du tracé code des consommateurs (agents de tracé, file:line vérifiés). Les exports Dossier/Flash **miroir** de la fiche (`exports/miroir.py`) → mêmes cellules que la fiche parcelle.

**Résultat clé : 98/98 sources affichées sont servies au moins à un endroit** (0 affichée orpheline). **3 cases `devrait`** : `enr_exclue_hors_toiture`, `mesures_compensatoires`, `scot` (fiche parcelle, cf. A1-A3).

**Contrôle 3 témoins réels** (via `spatial_layers ST_Intersects` sur parcelles réelles) : Saint-Denis urbain, Saint-Paul littoral, Cilaos Hauts — chaque source intersectant la parcelle apparaît en fiche via la cascade attribuée (`data_source_id`), **sauf** `enr_exclue_hors_toiture` (Cilaos/Saint-Paul, intersecté, non affiché) → confirme A1.

---

## C · Les outils

**19 outils au menu** (`frontend/src/components/outils/registry.ts:46-150`, ordre du Rail), dont ~3 masqués/alias (calculette-fonciere, mon-secteur, veille-promoteurs) et 2 dormants (promesses→permis, barometre→communes). Implémentations back : `src/labuse/api/modules.py` (patrimoine :274, permis :532, prospection-solaire :847, blocs :1142, successions :1051), `app.py` (taxe :2807), `faisabilite/`, `comparateur.py`, `zone.py` (étude de zone), `pige/` (radar).

**Sources lues par outil** : détaillées dans `MATRICE.csv` (colonne `outils`). Filtres : `filtres/sources.py` (registre `FILTRES_RICHES`, une table par filtre — DVF `dvf_mutations`:62, GPU :106, cadastre `parcels`:117, SITADEL :132, DGFiP PM :158, DPE :177, Géorisques MVT :194) — aucune divergence dans les définitions de filtre. Couches carte : `registre/robinets.py` + `api/couches_tuyau.py`.

**Données lues à deux endroits depuis deux tables différentes (risque de divergence)** — repris des écarts : **E1 DVF** (4 tables, 2 chemins de médiane), **E2 sol_pollue** (3 sources 1 kind), OCS `ocs_ge` proxy (cascade phase1:967) vs OCS GE natif `parcel_ocsge`/`artificialisation` (le proxy porte sa réserve « grain grossier », les deux coexistent), Loyers `oll_loyers` vs repli `loyers_dhup` (JSON embarqué — repli assumé), Taxe `taxe_amenagement_taux` (commune) + `taxe_amenagement_secteur` (parcelle) jointes au même endpoint (app.py:2807). Le cas E1 est le plus exposé (deux calculs, pas un repli).

---

## D · Le dashboard (page Sources / page Données)

- **Page Sources (client)** : `GET /sources` (app.py:941 `list_sources`) → 98 sources ; champs = `name`, `provider`, `couverture_note`, `source_millesime` (via `composer`), `cadence_mention` (← `etats_sources`), statut de fraîcheur (`fraicheur`), badge nature (`_source_nature`). Frontend `SourcesPage.tsx`.
- **Page Données (admin/Circuit)** : `/admin/circuit` — lit `RESERVOIR_TABLES.millesime` + état circuit. Une source n'est sur la vitrine cliente QUE si affichée (98) ; les 30 non-affichées restent visibles côté admin.
- **Millésime affiché = réel ?** Client = `source_millesime` nettoyé (composer). 22 affichées → cellule vide (P1). Deux magasins possibles (P2).
- **Cadence déclarée** : `source_cadence` / `etats_sources.cadence`. **CRON d'ingestion : seuls 5 jobs planifiés** (`ingest-bodacc`, `ingest-sitadel`, `ingest-dpe`, `ingest-sirene`, `sync-gpu` — jobs.py). Toutes les autres sources sont ingérées **manuellement (CLI `labuse …-build`) + sonde sentinelle** (`sonde-sources`, `agents-sources`) : la « cadence déclarée » (trimestriel/mensuel…) n'est PAS garantie par un job pour la majorité (par conception — injection supervisée par Vic, jamais automatique).
- **Sentinelle** : 104 `source_veille` actives ; 6 affichées non surveillées (P4).
- **Dernière ingestion réelle** : `data_sources.last_sync_at` (méta interne, jamais servie au client). Fraîches globalement (majorité 2026-09-14 → 2026-09-26).

---

## E · Propreté côté client

Voir P1-P5. En résumé : **noms propres, zéro jargon affiché** (P5) ; licence retirée de la vitrine (P3) ; 22 millésimes vides (P1) ; deux magasins de millésime non contradictoires côté client (P2).

---

## Annexe — reproductibilité

- Comptes catalogue : `SELECT status,count(*) FROM data_sources GROUP BY status;`
- Affichées : `WHERE_AFFICHEES` (sources_catalog.py:36).
- Comptes exacts réservoirs : `/tmp/count.sql` (UNION `count(*)` des 92 tables de `RESERVOIR_TABLES`) ; `kind` : `SELECT kind,count(*) FROM spatial_layers GROUP BY kind;`
- Attribution cascade : `SELECT layer_name, count(*) FILTER (WHERE data_source_id IS NOT NULL), count(*) FROM dryrun_cascade_results WHERE layer_name IN ('foret_publique','trait_de_cote','ocs_ge','sar','safer') GROUP BY layer_name;` → 100 % attribués.
- Matrice : `MATRICE.csv` (généré depuis `registre.donnees.DONNEES` + overlays tracés, script `/tmp/genmatrix.py`).
