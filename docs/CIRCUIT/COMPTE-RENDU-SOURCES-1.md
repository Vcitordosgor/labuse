# COMPTE-RENDU SOURCES-1 — vingt-deux sources par la porte du Circuit

Branche `feat/sources-1` depuis `origin/main` (`ea6fd161`, FICHE-1 mergé). Un chapitre par lot.
Reprise : « continue SOURCES-1 depuis docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md » — repartir au premier lot non clos.

## Étape 0 — départ (clos)

- `feat/sources-1` créée depuis `origin/main` (la branche locale `main` est extraite dans un autre worktree ; `origin/main` était à jour, FICHE-1 mergé).
- Mandat + `SOURCES-CANDIDATES.md` + `RAPPORT-SOURCES-974.md` posés dans `docs/CIRCUIT/` et committés (`4f5fa9ee`, poussé).
- `.env` déjà présent dans le worktree (rien copié).
- **Suites de départ** (06/09/2026, base locale `labuse`, env conda `labusedb`, `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` pour weasyprint) :
  - front : `tsc` 0 erreur · vitest **187/187**.
  - back : pytest **2710 passed, 4 failed, 52 skipped**. Les 4 échecs sont PRÉ-EXISTANTS sur ce main (état de base locale : FK `ia_log`→compte, etc.) : `test_courrier_boucle.py::test_boucle_piste_courrier_reponse`, `test_courrier_boucle.py::test_backfill_rattache_par_idu_compte_univoque`, `test_dashboard.py::test_ia_log_attribue_au_compte`, `test_front_reliquats.py::test_r5_etudier_deux_marges_chacune_dit_son_referentiel`.

### Sondes de départ (URL du rapport, réellement appelées le 06/09/2026)

Répondent 200 : GPU Atom `download-feed`, WMS-V gpu.xml, API GPU `api/document?documentType[]=SUP&grid=974`, Géorisques, data.arcep.fr `/fixe/maconnexioninternet/`, data.gouv ORT, deal974.lizmap.com, Sextant fiche DPF, data.gouv INPN ENP, data.economie.gouv.fr REI + DFI (API v2.1), data.regionreunion.com DVF + potentiel foncier (API v2.1), Carmen WFS 29 `Cartes_bruit_strategiques` (GetCapabilities OK), PatriNat page temporaire.

**Injoignable au test** : `atlas.patrimoines.culture.fr` (code 000, timeout) — ZPPA, voir lot 1.

### Inventaire SUP 974 réel (API GPU, 06/09/2026)

`GET /api/document?documentType[]=SUP&grid=974` → 20 documents. **En vigueur (document.production)** :

| Catégorie | Gestionnaire (idGest) | Millésime |
|---|---|---|
| AC1 | 172014607 | 20260828 (via partition, l'API liste l'archive) |
| AC2 | 130014368 | 20200812 |
| AC4 | 172014607 | 20260828 |
| PM1 | 130014368 | 20260416 |
| PM2 | 130014368 | 20170707 |
| PM3 | 130014368 | 20210107 |
| PT1 | 180060030 | 20231205 |
| PT2 | 180060030 · 120064019 | 20231205 · 20260825 |
| T5 | 120064019 | 20260707 |

**Non publiées pour le 974** : AC3, AS1, A4, A5, EL3, EL7, I3, I4, T1, T7 (AS1 captages notamment — à surveiller par la sonde).
Téléchargement réel vérifié : `api/document/download-by-partition/172014607_SUP_974_AC1` → 302 → ZIP CNIG `172014607_AC1_974_20260828.zip` (data.geopf.fr).

### État des lieux avant travaux (base locale)

`spatial_layers` contient déjà des kinds proches du mandat, hérités des vagues antérieures : `plu_gpu_prescription` 10 490 (dont typepsc 01=EBC 1 782, 05=ER 2 250), `sup` 417 (pm1/pm2/pm3/el10/ac1-ac4 — pas PT1/PT2/T5), `ravine` 12 716, `sar` 2 453 (7 vocations), `zonage_assainissement` 258, `bruit_route` 1 004 (cat1→5), `parc_national` 3, `ens` 73, `foret_publique` 65, `znieff` 162. Le catalogue `data_sources` (84 lignes) couvre déjà : SUP assiettes GPU, Urbanisme PLU/GPU, INPN/patrinat, Parc national, Classement sonore ITT, RPG, Potentiel foncier Région, GPU zonages d'assainissement, BDNB (`a_faire`). Le travail SOURCES-1 = faire entrer ces données PAR LE CIRCUIT (ligne, sonde, filtre, réservoir, registre, couche, cascade) et ajouter les vraies manquantes.

## Lot 1 — Les prescriptions et périmètres du droit des sols (clos)

Sept sources entrées par la porte du Circuit. **Verrous : 16/16 verts** après le lot.

### Ce qui est entré

| Source (data_sources) | Réservoir | Données | État |
|---|---|---|---|
| GPU — emplacements réservés (prescriptions CNIG) | `gpu_prescriptions_er` (logique, sur `plu_gpu_prescription` typepsc 05 + rescue) | 2 250 ER + 6 rescue | servie |
| GPU — espaces boisés classés (prescriptions CNIG) | `gpu_prescriptions_ebc` (typepsc 01) | 1 782 EBC | servie |
| GPU — droit de préemption urbain (info-surf) | `dpu_perimetres` (kind `dpu`) | **202 périmètres, 4/24 communes** (Saint-Denis, Sainte-Marie, Saint-Benoît…) | servie, partielle DITE |
| PEB (DGAC via annexes GPU) | `peb_dgac` (kind `peb`) | **4 zones A/B/C/D Roland-Garros** (dédoublonnées île) ; 3 entités sans lettre écartées | servie, partielle DITE |
| Zonage ABC (DHUP) | `zonage_abc_dhup` (table `commune_zonage_abc`) | 24/24 — A : Les Avirons, L'Étang-Salé, Saint-Leu, Saint-Paul ; B1 : les 20 autres | servie |
| SUP — assiettes GPU (existante, mise d'équerre) | `sup_gpu` + **sonde catégorielle** | inventaire 9 catégories en vigueur | servie |
| ZPPA (Atlas des patrimoines) | `zppa_culture` (aucune table) | rien — Atlas injoignable | `a_faire`, rappel 180 j |

- **DPU non publié au GPU (20 communes, pour la demande de Vic)** : Bras-Panon, Cilaos, Entre-Deux, L'Étang-Salé, La Plaine-des-Palmistes, La Possession, Le Port, Les Avirons, Les Trois-Bassins, Petite-Île, Saint-André, Saint-Benoît, Saint-Joseph, Saint-Leu, Saint-Louis, Saint-Philippe, Saint-Pierre, Sainte-Rose, Sainte-Suzanne, Salazie.
- **PEB Pierrefonds** : ABSENT du GPU (0 typeinf 27 sur la bbox de Saint-Pierre, vérifié live) — couverture partielle dite partout (fiche, filtre, source) ; aucun flux DGAC versionné 974 sur data.gouv (recherche du 06/09).
- **SUP 974, inventaire réel** (sonde catégorielle = API JSON du service Atom, `api/document?documentType[]=SUP&grid=974`) : en vigueur AC1, AC2, AC4, PM1, PM2, PM3, PT1, PT2, T5 ; **T5/PT1/PT2 restreintes au téléchargement** (403 volontaire du gestionnaire — vérifié) ; **AS1 (captages) et AC3, A4, A5, EL3, EL7, I3, T1, T7 non publiées**. La sonde `temoin` alerte à toute publication (empreinte posée, appel réel OK).
- **ZPPA** : atlas.patrimoines.culture.fr timeout (code 000) + aucun jeu data.gouv national/974 — ligne au catalogue `a_faire`, rappel sentinelle 180 j, rien d'inventé.

### La mécanique (un commit)

- **Catalogue** : 6 lignes `data_sources` neuves (90 sources), `MODE_ET_CADENCE`, seed vert.
- **Vanne** : labels `dpu`, `peb` (→ `labuse ingest-gpu-infos`), `zonage_abc` (→ `labuse ingest-zonage-abc`).
- **Ingestions neuves** : `ingestion/gpu_infos.py` (info-surf : DPU filtré par partition DU_<insee> — attribution stricte ; PEB dédoublonné à l'île, zone lue de `txt`, jamais devinée), `ingestion/zonage_abc.py` (CSV DHUP → `commune_zonage_abc`, domaine fermé), `sup_gpu.inventaire_974()`.
- **Filtres riches** : `gpu_prescriptions_er` (ER hors-code ≤ 6, communes couvertes), `gpu_prescriptions_ebc`, `dpu` (domaine subtypes bloquant, communes non publiées listées), `peb` (zones A-D bloquant, aérodromes 1/2 avertissant), `zonage_abc` (24/24 bloquant, domaine arrêté bloquant), `sup_gpu` (riche). Joués : abc **ok**, dpu/peb **avertissements** (couverture partielle = état réel).
- **Sondes** : SUP `temoin` + ABC `api` (appelées réellement, statut ok) ; ZPPA `rappel` 180 j ; ER/EBC/DPU/PEB : raisons écrites (canal GPU par commune).
- **Cascade** (effet au prochain run candidat seulement) : ER ≥ 50 % **redevient RÉDHIBITOIRE** (annule M129 P1.1 — mandat) ; **EBC ≥ 80 % RÉDHIBITOIRE**, vigilance forte sinon, **part EBC soustraite de l'assiette** (`faisabilite/db.py` : union ER∪EBC, jamais de double soustraction) ; couches neuves `peb` (A/B rédhibitoires ≥ 2 % de part, C moyen, D faible — L112-10) et `dpu` (vigilance faible, renforcé moyen) ; SUP : AC2 info→**fort**, PT1/PT2 **moyen**, AS1 fort (rédhibitoire du périmètre immédiat à la première publication).
- **Fiches de règle** (CIRCUIT-4) : `regles/dispositifs_droit_sols.py` (choix ER 50/EBC 80/DPU), `regles/peb_zone.py` (**L112-10 lu sur Légifrance, extrait cité, version 01/01/2016**), `regles/zonage_abc_commune.py` (CSV de l'arrêté lu, lignes 974 citées), `regles/sup_categories.py`.
- **Registre** : les 5 données FICHE-1 lot 7 (`er_emplacement_reserve`, `ebc_classe`, `dpu_perimetre`, `peb_zone`, `zonage_abc_logement`) **sortent d'en_attente**, réservoirs réels rattachés ; + `er_couche`, `ebc_couche`, `dpu_couche`, `peb_couche`, `sup_couche`, `dispositifs_parcelle` ; robinets `couche_er/ebc/dpu/peb/sup`, `fiche_dispositifs`, `fiche_commune_zonage_abc` ; carte table→réservoir (`registre/tables.py`), pont `NOM_VERS_SLUG`, `reservoirs.csv` (6 lignes + sup mise à jour).
- **Servi** : fiche parcelle clé `dispositifs` (`_dispositifs_block` : ER/EBC avec parts, DPU avec l'état « non déterminée — non publié par la commune », PEB, SUP par catégorie — prouvé sur base réelle : 97402000AE0048 ER 5 % + EBC 4,5 % + SUP PM1 33 % ; 97411000BM0004 PEB zone B + DPU servi) ; fiche commune clé `zonage_abc` ; carte kinds `dpu`/`peb`/`sup` + kinds VIRTUELS `er`/`ebc` (filtre subtype dans `/map/layers.geojson`).
- **Tests** : `tests/test_sources1_lot1.py` (14) ; `test_decisions_1_3.py::test_d3a_er_majoritaire…` mis à jour (le mandat annule M129 P1.1).

## Lot 2 — La nature et l'eau (clos)

Cinq sources. **Découverte qui change le lot** : le WFS Carmen du nœud 29 (`DEAL_REUNION_2020`, MapServer 1.0.0, GML EPSG:2975, 187 couches) **répond** — contrairement à la réserve du rapport (« probablement migré Lizmap »). Les géométries OFFICIELLES du DPF et des zones humides sont servables : **pas de repli BD TOPO**. Verrous : **16/16 verts**.

### Ce qui est entré (ingéré en base réelle, filtres joués)

| Source | Réservoir | Données réelles | État |
|---|---|---|---|
| Ravines — domaine public fluvial (DEAL Carmen) | `deal_dpf_dpe` (kind `dpf`) | **275 tronçons + 6 plans d'eau** (arrêté 06-3077 du 21/08/2006) | servie ; DPE non diffusé → demande DEAL (lot 7) |
| Zones humides — inventaires DEAL (Carmen) | `deal_zones_humides` (kind `zone_humide`) | **3 122 entités, 5 inventaires** (habitats 2011 : 1 507 · 2009 : 187 + 30 · 2003 : 49 · basse altitude 2019 : 1 349) | servie, par secteurs DITE |
| Espaces protégés complémentaires (DEAL Carmen) | `enp_complements_deal` (kind `ens`, purge par subtype) | Ramsar 1 · sites classés/inscrits 7 · **réserves naturelles 3 dont la RÉSERVE MARINE (absente du jeu INPN local)** | servie |
| AZI / TRI (Géorisques GASPAR) | `georisques_azi_tri` (table `azi_communes`) | **30 AZI (22 communes) + 9 TRI (9 communes)** ; sans document : Les Avirons, Les Trois-Bassins | servie (fait par commune) |
| RPG (existante, mise d'équerre) | `rpg_proxy_ign` (kind `safer`) | 38 460 déclarations, `code_cultu` 100 % servi — **CSA (canne) 12 464** | servie + couche + cascade |

- **AZI : géométrie NON dupliquée** — l'`ALEA_INONDATION` Carmen (75 zones) est un doublon vérifié de `georisque_alea/inondation` (76, DEAL Lizmap) déjà servi par la couche cascade `risques` ; l'AZI/TRI entre comme FAIT documentaire par commune (fiche commune, bloc Risques).
- **INPN** : la source existante reste le canal des types apb/réserve biologique/conservatoire/RNN ; le canal Carmen COMPLÈTE (subtypes `ramsar`, `site_classe`, `site_inscrit`, `reserve_naturelle`) avec purge par subtype — chevauchement RNN Étang Saint-Paul dit. Forêts de protection = SUP A7, non publiée pour le 974 (inventaire lot 1).
- La fiche Sextant du rapport (DPF) n'offre AUCUNE distribution (WMS de visualisation seul, vérifié dans le XML) — c'est le WFS Carmen qui sert.

### La mécanique

- Catalogue 94 sources (+4), vanne (`deal_dpf`/`zones_humides`/`enp_complements` → `labuse ingest-deal-carmen` ; `azi_tri` → `labuse ingest-azi-tri`), ingestions neuves `deal_carmen.py` (GML → ogr2ogr → spatial_layers, purge ciblée) et `azi_tri.py` (GASPAR → `azi_communes`).
- **Cascade** (effet au prochain run candidat seulement) : couche `dpf` neuve — **marchepied 3,25 m RÉDHIBITOIRE** (L2131-2 CGPPP **lu sur Légifrance et cité**), bande 10 m portée par la couche `ravine` (anti-double-compte, R.174-2 cité en commentaire) ; couche `zone_humide` neuve — VIGILANCE FORTE, inventaire et part dits ; `ens` durcie — **réserves naturelles (dont marine) + réserves biologiques + APB RÉDHIBITOIRES**, conservatoire moyen, Ramsar faible, sites classés/inscrits info ×0 (anti-double-compte SUP AC2) ; `safer` (RPG) — **zone A × canne CSA ≥ 50 % RÉDHIBITOIRE**, zone A sans RPG → VIGILANCE « friche possible » (AU jamais happée par le préfixe A, testé) ; `context.py` prime la distance dpf.
- Fiches de règle : `dpf_recul` (L2131-2 conforme, extrait cité), `zones_humides_vigilance`, `enp_protections`, `rpg_cultures` (choix assumés). Registre : 5 données (+robinets couches, azi commune), carte tables, pont, réservoirs.csv, `_MAP_LAYER_KINDS` += dpf/zone_humide + kinds virtuels `enp`→ens, `rpg`→safer, `code_cultu` servi à la couche.
- Front : familles « Contraintes » (+ Ravines et reculs) et **« Nature » neuve** (Zones humides, Espaces naturels protégés, Cultures déclarées), DPF en trait d'eau, thème sombre/clair, légende, « i » complets, toast « secteurs partiels » pour les ZH. Fiche commune : ligne « Inondation (AZI/TRI) » au bloc Risques.
- Tests `tests/test_sources1_lot2.py` (12) ; compteurs figés mis à jour (MODE_ET_CADENCE 94, sentinelle 85, couches 29). Variable candidate scoring NOTÉE (part RPG canne / friche possible — banc K0, jamais branchée sans banc).

## Décisions prises en autonomie

- Étape 0 : `main` local étant extrait dans un autre worktree, la branche part de `origin/main` (strictement identique, `ea6fd161`).
- Lot 1 · ER ≥ 50 % : le mandat (« RÉDHIBITOIRE au-delà de 50 % ») CONTREDIT M129 P1.1 (« l'ER n'exclut plus », soft fort). Le mandat étant l'instruction la plus récente de Vic, l'exclusion est rétablie ; le motif conserve « servitude levable » ; le test M129 est mis à jour et la réversion est écrite dans la fiche de règle.
- Lot 1 · inventaire SUP par « flux Atom » : le flux Atom `download-feed` n'est pas filtrable par territoire ; l'inventaire catégoriel passe par l'API JSON du MÊME service (`api/document?documentType[]=SUP&grid=974`), sondée en `temoin`. C'est le même amont, en lisible.
- Lot 1 · réservoirs ER/EBC : réservoirs LOGIQUES sur la table existante `spatial_layers(plu_gpu_prescription)` (familles typepsc 05/01), remplis par le canal GPU existant — pas de table dupliquée pour la même donnée ; la couche carte les sert par kinds virtuels `er`/`ebc` (filtre subtype). La famille ER de la CASCADE inclut le rescue par libellé ; la couche carte affiche le standard (05), l'écart (6 ER de Saint-Louis codés 02) est mesuré au filtre.
- Lot 1 · SUP « un réservoir par catégorie » : UNE ligne de carte `sup_gpu` avec les catégories en sous-couches (subtype) + inventaire catégoriel dans le millésime et la sonde — 9 lignes de réservoir quasi identiques auraient dilué la carte sans rien servir de plus.
- Lot 1 · PEB via GPU : les PEB ne sont diffusés pour le 974 que par la republication GPU (annexes des PLU). Zone lue du champ `txt` UNIQUEMENT (3 entités sans lettre écartées et comptées). AS1/T5 sans géométrie servable : la règle rédhibitoire est ÉCRITE (fiche de règle) et s'armera à la première version réelle publiée.
- Lot 1 · DPU : VIGILANCE faible (renforcé : moyen) — la préemption pèse sur la transaction, pas la constructibilité ; « hors périmètre » n'est dit que si la commune A publié ; sinon « non déterminée — non publié par la commune » (règle 3 du mandat).

- Lot 2 · Carmen vivant : le rapport doutait du nœud Carmen 29 (« probablement migré Lizmap ») — testé, il RÉPOND (Cartes_bruit puis DEAL_REUNION_2020, 187 couches). Les données officielles DEAL (DPF, ZH, Ramsar, sites, RN) sont ingérées de là ; le repli BD TOPO prévu par le mandat n'a pas été nécessaire.
- Lot 2 · AZI sans doublon : le mandat demandait une couche AZI « là où le PPR est absent » — la géométrie d'aléa inondation DEAL est DÉJÀ servie (georisque_alea/inondation, couche cascade risques, couche carte aléa inondation). Créer un kind `azi` aurait dupliqué la même emprise sous deux couches : l'AZI/TRI entre comme fait documentaire par commune (GASPAR), la cascade inondation reste portée par `risques`.
- Lot 2 · bande des 10 m : le RÉDHIBITOIRE du marchepied (3,25 m) est porté par la couche `dpf` (DPF officiel seul) ; la VIGILANCE de la bande de 10 m reste portée par la couche `ravine` existante (BD TOPO, TOUTES les ravines, buffer 10 m) — deux couches complémentaires, jamais deux flags pour la même bande.
- Lot 2 · réserves biologiques : le mandat dit « réserves » rédhibitoires — les réserves biologiques (ONF, 37 entités) sont incluses (protection forte de même nature que les RNN), documenté dans la fiche de règle.
- Lot 2 · canne = CSA : le code culture RPG de la canne à sucre retenu est CSA (12 464 déclarations, culture dominante mesurée en base) ; seuil 50 % de couverture parcelle, choix non calibré, écrit en fiche de règle.

*(chapitres suivants à venir)*
