# COMPTE-RENDU SOURCES-1 — vingt-deux sources par la porte du Circuit

Branche `feat/sources-1` depuis `origin/main` (`ea6fd161`, FICHE-1 mergé). Un chapitre par lot.
Reprise : « continue SOURCES-1 depuis docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md » — repartir au premier lot non clos.

## SYNTHÈSE FINALE — les vingt-deux sources (mandat clos)

| # | Source (mandat) | Réservoir | État final |
|---|---|---|---|
| 1 | Emplacements réservés (GPU) | `gpu_prescriptions_er` | **servie** (2 250 + 6 rescue ; cascade ER ≥ 50 % rédhibitoire) |
| 2 | Espaces boisés classés (GPU) | `gpu_prescriptions_ebc` | **servie** (1 782 ; ≥ 80 % rédhibitoire, assiette soustraite) |
| 3 | Droit de préemption urbain | `dpu_perimetres` | **servie, partielle DITE** (202 périmètres, 4/24 — 20 communes non publiées listées, demande) |
| 4 | PEB Roland-Garros / Pierrefonds | `peb_dgac` | **servie, partielle DITE** (R-Garros A/B/C/D ; Pierrefonds non publié au GPU) |
| 5 | Zonage A/B/C (DHUP) | `zonage_abc_dhup` | **servie** (24/24 : 4 A, 20 B1, arrêté 23/06/2026) |
| 6 | SUP du GPU (inventaire catégoriel) | `sup_gpu` + sonde | **servie + sondée** (9 en vigueur ; T5/PT1/PT2 restreintes ; AS1 non publiée, armée) |
| 7 | ZPPA (Atlas des patrimoines) | `zppa_culture` | **a_faire** (Atlas injoignable — rappel 180 j) |
| 8 | Espaces naturels protégés INPN | `inpn` + `enp_complements_deal` | **servie** (réserves/APB rédhibitoires ; Réserve marine récupérée ; ENS Département → demande) |
| 9 | Ravines DPF/DPE | `deal_dpf_dpe` | **servie** (DPF officiel 275 tronçons, marchepied 3,25 m rédhibitoire ; DPE non diffusé → demande DEAL) |
| 10 | Zones humides DEAL | `deal_zones_humides` | **servie** (3 122 entités, 5 inventaires, secteurs dits) |
| 11 | AZI / TRI (Géorisques) | `georisques_azi_tri` | **servie** (fait par commune : 30 AZI + 9 TRI ; géométrie = doublon de l'aléa servi, non dupliquée) |
| 12 | RPG (IGN/ASP) | `rpg_proxy_ign` | **servie** (code_cultu 100 %, canne 12 464 ; zone A × canne ≥ 50 % rédhibitoire) |
| 13 | SIS (Géorisques) | `georisques_sis` | **servie** (4 SIS 974, vigilance forte, L556-2 + L125-7 cités) |
| 14 | CASIAS (Géorisques) | `georisques_casias` | **servie** (453 sites + 56 instructions, « pas une pollution avérée ») |
| 15 | Classement sonore (DEAL/Cerema) | `bruit_itt_cerema` + `deal_bruit_cartes` | **servie** (1 004 secteurs réglementaires + 6 zones de dépassement CBS) |
| 16 | SAR (Région/DEAL) | `sar_region` | **a_faire** (couche officielle introuvable en vecteur — 4 canaux fouillés ; proxy D2 conservé, divergence servie ; SAR 2050 à la sentinelle → demande Région) |
| 17 | DVF Région | `region_dvf` | **contrôle** (échantillon producteur du filtre DVF : écarts −3,1 %/−1,9 %/+1,5 % ; jeu figé mi-2021) |
| 18 | Potentiel foncier Région | `potentiel_foncier_ods` | **contrôle** (convergence 44,6 % des parcelles d'îlots en tiers hauts, comparaison permanente au filtre) |
| 19 | Fibre Arcep | `arcep_fibre` | **servie** (330 051 immeubles 2026_T1, 97,5 % FttH) |
| 20 | Taux TFPB REI (DGFiP) | `dgfip_rei` | **servie** (24/24, colonnes tracées : 29,55 → 68,40 %) |
| 21 | ACV/PVD/ORT (ANCT/DGALN) | `anct_ort` | **servie** (19 communes, 13 ORT ; écart producteur DIT : Saint-Louis absent de la table DGALN ; Denormandie servie) |
| 22 | Loyers DHUP + OLL | `loyers_dhup` + `loyers_oll` | **servie** (OLL 2024 canonique 16/24 mono-zone, DHUP repli motivé) |
| + | Coût de construction (EPTB SDES) | `cout_construction_sdes` | **servie** (table sourcée remplace la constante, EPTB 2024 cité, écart témoins 0) |
| + | Recensement IRIS (INSEE RP2022) | `insee_rp_iris` | **servie** (344 IRIS : vacance, âge bâti, ménages — fiche/commune/étude de zone) |
| + | DFI (DGFiP) | `dgfip_dfi` | **servie** (409 623 liens ; **985 permis orphelins rattachés, 1 887 → 902**) |
| + | Chantiers lot 7 (7 lignes) | — | **a_faire, demandes prêtes** (`DEMANDE-REGION-EPCI.md`) ; Cerema ×3 sous convention ; BDNB retirée |

Verrous 16/16 verts (`--complet` : 0 cassé, 0 à décider) · pytest 2 77x verts / 4 échecs pré-existants · tsc 0 · vitest 187 · run candidat `q_v13_sources1` produit (note ci-dessous), **jamais basculé**.

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
| GPU — droit de préemption urbain (info-surf) | `dpu_perimetres` (kind `dpu`) | **202 périmètres, 4/24 communes** (Le Tampon, Saint-Denis, Saint-Paul, Sainte-Marie) | servie, partielle DITE |
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

## Lot 3 — Les sols et le bruit (clos)

Trois sources, dont deux DÉJÀ à moitié en base (découverte) : le canal Géorisques SSP
(`/api/v1/ssp`) ingérait déjà SIS et CASIAS dans le kind `sol_pollue` — le lot les fait entrer
comme SOURCES à part entière (réservoirs logiques, doctrine ER/EBC du lot 1). **Verrous : 16/16.**

### Ce qui est entré

| Source | Réservoir | Données réelles (mesurées 07/09) | État |
|---|---|---|---|
| Géorisques — SIS | `georisques_sis` (logique, `sol_pollue`/sis) | **4 périmètres MultiPolygon** (Le Port, Saint-Benoît, Saint-Louis, Sainte-Marie) ; id_sis absent 1/4 (dit au filtre) | servie |
| Géorisques — CASIAS | `georisques_casias` (logique, `sol_pollue`/casias+instruction) | **453 CASIAS + 56 instructions** (480 points géocodés, 29 emprises — part dite) | servie |
| DEAL — cartes de bruit stratégiques | `deal_bruit_cartes` (kind `bruit_carte`) | **6 zones de dépassement** type c (Lden 68/Ln 62, RN/RD/VC — WFS Carmen vivant) | servie |
| Classement sonore ITT (existante, mise d'équerre) | `bruit_itt_cerema` | 1 004 bandes cat1-5, largeur réglementaire `sect_bruit_m` (flux Cerema RÉEL, pas une reconstruction BD TOPO) | servie |

- **SIS/CASIAS sans API dédiée** (vérifié : /api/v1/sis et /api/v1/casias → 404 ; pages Géorisques sans lien d'export lisible) — le canal réel est `/api/v1/ssp`, déjà sondé (témoin bi-commune). Réservoirs LOGIQUES, aucune table dupliquée.
- **Classement sonore : meilleur que le mandat.** Le mandat prévoyait des tampons BD TOPO « reconstitués » ; la réalité en base est le flux Cerema Cartagène (axes classés + largeur réglementaire `sect_bruit_m` par tronçon, arrêtés 14-15/12/2023) — les bandes sont matérialisées depuis la donnée d'origine, rien à reconstituer. La couche carte manquait : branchée (violet gradué cat 1→5).
- **Cartes de bruit stratégiques** : type c ingérées (dépassements) ; **type b NON ingérées (doublon vérifié des bandes sect_bruit)** ; type a (isophones) écartées (exposition, pas d'effet réglementaire propre). Le « i » dit « ≠ classement sonore réglementaire ».
- **Coût d'isolation au bilan : PAS de chiffre.** L'arrêté fixe des exigences d'isolement (DnT,A,tr), pas un coût €/m² — aucun montant sourcé disponible → le coût reste porté par la VIGILANCE (motif cascade + fiche), jamais un chiffre inventé.

### La mécanique (un commit)

- **Catalogue 97 sources** ; vanne `bruit_cartes` ; ingestion neuve `bruit_cartes.py` (WFS Carmen → ogr2ogr) ; RAISONS sentinelle ×3 (canal SSP déjà sondé ; Carmen sans en-tête).
- **Cascade** (effet au prochain run candidat) : SIS `severity_sis` moyen → **FORT**, motif citant **L556-2 ET L125-7** (information écrite de l'acheteur/locataire) ; CASIAS : motif « inventaire historique, **pas une pollution avérée** » ; sources des verdicts = lignes SIS/CASIAS propres (SRC_SIS/SRC_CASIAS).
- **Fiche de règle** `regles/sis_information_sols.py` — **L125-7 CE lu sur Légifrance, extrait cité** (« le vendeur ou le bailleur… est tenu d'en informer par écrit l'acquéreur ou le locataire »), version 25/08/2021.
- **Registre** : `sis_classe`, `casias_statut`, `sols_parcelle` + 4 couches (`sis_couche`, `casias_couche`, `bruit_couche`, `bruit_carte_couche`) ; robinets `couche_sis/casias/bruit/bruit_carte` + `fiche_parcelle_sols` ; carte table→réservoir, pont slug, reservoirs.csv (93 lignes).
- **Servi** : fiche parcelle clé `sols` (`_sols_block` — prouvé sur base réelle : 97407000AT0063, Le Port : SIS « SOC INDUSTRIELLE DE BOURBON » + instruction clôturée SUR PLACE) ; PDF Dossier section « SOLS (SIS/CASIAS) » ; carte : kinds virtuels `sis`/`casias` (sol_pollue filtré) + `bruit_route` + `bruit_carte`, famille « Contraintes » (bruit) et « Risques et protections » (sols), légende groupe « Sols », thème sombre/clair.
- **Filtres joués** : bruit_itt_cerema **ok**, bruit_cartes **ok**, sis/casias **avertissements** (id_sis 1/4 absent ; 94 % de points sans emprise — l'état réel, dit).
- **Tests** : `tests/test_sources1_lot3.py` (8) ; compteurs figés 94→97 (modes), 85→88 (sentinelle), 29→33 (couches).

## Lot 4 — Le cadre régional (clos)

Deux sources. **Verrous : 16/16 verts** après le lot. Catalogue : 99 sources.

### Ce qui est entré

| Source (data_sources) | Réservoir | État |
|---|---|---|
| SAR — schéma d'aménagement régional (Région/DEAL) | `sar_region` (LOGIQUE sur le proxy kind `sar`) | **`a_faire` — couche SIG officielle NON diffusée** ; rappel sentinelle 180 j (+ suivi SAR 2050) |
| DVF Réunion (Région, data.regionreunion.com) | `region_dvf` (aucune table) | servie comme **échantillon producteur** du filtre DVF — aucune donnée servie (mandat) |
| Potentiel foncier Région (existante, mise d'équerre) | `potentiel_foncier_region`/`potentiel_foncier_ods` | filtre riche neuf + **contrôle de comparaison** avec notre analyse ; millésime déclaré |

### Le SAR officiel n'est diffusé nulle part en vecteur (recherche du 07/09/2026)

- **Carmen 29** : 187 couches de `DEAL_REUNION_2020` lues une à une — 0 couche SAR (pas de coupures d'urbanisation, pas d'ENR littoral SAR, pas de zones préférentielles). Services `SAR*`/`DEAL_REUNION*` : 404.
- **Lizmap DEAL** : 5 dépôts (carto générale, risques SPRINR, SHLS, CBS, tache urbaine) — 0 projet SAR ; le dépôt « carto générale » (projet `deal_reunion`, 91 couches WFS) n'en a pas non plus.
- **Sextant** : 2 fiches SAR trouvées — « Espaces Naturels Remarquables du Littoral (SAR/SMVM) » et « Extrait du SAR du TCO (GIML) » — mais **WMS IMAGE seulement** (`DCE_POLMAR_RUN_ERLAP_SAR2010_P` ; le WFS `polmar_reunion` n'existe pas — 404 ; le WFS `ocean_indien` (18 couches) n'a aucune couche SAR).
- **ODS Région** : 283 jeux scannés — 0 jeu SAR.

→ La source entre `a_faire` avec réservoir logique sur le PROXY de vocations (doctrine D2 conservée : zéro pouvoir d'exclusion, divergence en warning, AU remonté en vigilance) ; la couche officielle est demandée à la Région (lot 7) ; fiche de règle `regles/sar_indication.py` (règle 5 verrouillée : indication, jamais rédhibitoire seule) ; donnée `sar_divergence` au registre (servie par les vigilances de la fiche).

### DVF Région → échantillon producteur (filtre DVF)

Le jeu Région est un **DV3F public FIGÉ 2014→mi-2021** (54 449 mutations — bornes mesurées à l'API) ; les ids sont des empreintes md5 sans correspondance Etalab (appariement par mutation IMPOSSIBLE, vérifié). L'échantillon (`filtres/echantillons/dvf.json`, remplace le squelette CIRCUIT-3 `a_valider`) compare les comptes de mutations DISTINCTES par fenêtre, tolérance 5 % :

| Fenêtre | Région (producteur) | LABUSE | Écart |
|---|---|---|---|
| Île 2019 | 8 224 | 7 969 | −3,1 % |
| Île 2020 | 7 886 | 7 733 | −1,9 % |
| Saint-Paul 2020 | 1 108 | 1 125 | +1,5 % |

Joué le 07/09/2026 : **3/3 conformes** (contrôle `d_echantillon` du filtre dvf).

### Potentiel foncier Région → contrôle de comparaison (rapport)

Mesuré le 07/09/2026 sur le run servi (2 453 îlots, 2 607 ha) : **15 776 parcelles** intersectent un îlot ; **7 043 (44,6 %)** sont en tiers hauts LABUSE (brûlante/chaude/à creuser) — convergence réelle sur le non-urbanisé. En sens inverse, **277 de nos 1 478 brûlantes/chaudes (18,7 %)** seulement sont en îlot : notre tête valorise AUSSI la densification du bâti, hors du champ « îlots non urbanisés » du producteur — écart de PÉRIMÈTRE, pas de désaccord. Contrôle permanent : `d_potfoncier_convergence` (filtre `potentiel_foncier_region`, avertissant, plancher 25 % = moitié de la référence) — joué **ok (44,7 %)**.

### La mécanique (un commit)

- Catalogue : 2 lignes neuves + millésime déclaré sur « Potentiel foncier Région » (levait le KO `u_millesime`) ; `MODE_ET_CADENCE` 99 ; seed vert.
- Sentinelle : rappel 180 j SAR (couche officielle + SAR 2050) ; raisons écrites (DVF Région couvert par la sonde témoin du hub ODS).
- Filtres : échantillon producteur DVF rempli (3 fenêtres) ; filtre riche `potentiel_foncier_region` (universels + convergence) — joués réellement.
- Registre : donnée `sar_divergence` (moteur cascade, robinet Risques de la fiche), fiche de règle `sar_indication` ; carte table→réservoir, pont NOM_VERS_SLUG, reservoirs.csv (95 lignes).
- Tests : `tests/test_sources1_lot4.py` (7) ; compteurs figés 97→99 (MODE_ET_CADENCE) et 88→90 (sentinelle).

## Lot 5 — La valeur (clos)

Cinq sources. **Verrous : 16/16 verts** après le lot. Toutes les URL testées RÉELLEMENT (07/09/2026).

### Ce qui est entré

| Source | Réservoir | Données | État |
|---|---|---|---|
| Fibre Arcep (immeuble) | `arcep_fibre` (table `arcep_immeubles`) | **330 051 immeubles 974, 321 739 raccordables FttH (97,5 %)**, opérateurs FRTE/MIAS/MILK/SRR/ZEOP, millésime 2026_T1 | servie |
| Taux TFPB — REI (DGFiP) | `dgfip_rei` (table `commune_rei`) | 24/24 — TFPB commune (E12 : 29,55 % Les Avirons → 68,40 % Saint-Louis), TFPB EPCI (E32), TEOM (F22) | servie |
| ACV/PVD/ORT (DGALN) | `anct_ort` (table `commune_ort`) | 19 communes, 13 ORT signées ; ACV : Le Port, Saint-André, Saint-Joseph, Saint-Pierre ; PVD : 11 | servie ; **écart producteur DIT** |
| Loyers OLL (ADIL/AGORAH) | `loyers_oll` (`oll_loyers` + `oll_zonage` IRIS→zone) | 245 agrégats, 6 zones + agglo, **médiane agglo 10,9 €/m² = plaquette** (contrôle bloquant) ; 16 communes mono-zone | servie, **CANONIQUE** |
| Loyers DHUP (annonces) | `loyers_dhup` (extrait embarqué 2025) | source EXISTANTE mise d'équerre (ligne catalogue + sonde + filtre) | servie, **REPLI** |
| Coût de construction | `cout_construction_sdes` (table `cout_construction_ref`) | ligne servie 2 300-2 800 €/m² SDP (choix) + ligne contexte EPTB 2024 | servie |

### Les points saillants

- **Arcep** : découpage DÉPARTEMENTAL découvert (`base_imb/last/departement/base_imb_974.csv.gz`, 13,8 Mo + éligibilité 13,2 Mo/2,86 M lignes) — pas besoin du national. Seul le FttH est servi (IPE fiable, fiche 12). Fiche « Réseaux et accès » : immeuble le plus proche + DISTANCE DITE (preuve : 97411000BM0004 → FttH, 4 opérateurs, 66 m) ; Étude de zone : part raccordable de la zone ; PDF Dossier. 26 immeubles hors emprise au filtre (avertissant, l'état réel).
- **REI** : colonnes identifiées par la TRACE officielle (lue, citée dans `regles/rei_taux.py`) : E12/E32/F22 — jamais devinées parmi les 1 043. La taxe d'aménagement n'y est pas (dit).
- **ORT — ÉCART PRODUCTEUR MESURÉ** : la fiche 10 attendait 5 ACV (avec **Saint-Louis**) ; la table DGALN n'en porte que 4 — **Saint-Louis (97414) est ABSENT de la table**. Écart contrôlé au filtre (avertissant), jamais corrigé en silence. Piège documenté : l'export data.gouv « viewSection » est FILTRÉ (78 lignes) ; l'export `tableId=BDD` rend les 2 440. Denormandie : condition COMMUNALE seule servie (les périmètres conventionnés ne sont pas publiés — demande EPCI, lot 7).
- **Loyers — bascule canonique/repli** (règle CIRCUIT-4 réécrite, `regles/loyer_median_eur_m2.py`) : OLL = loyers OBSERVÉS par zone ; le « secteur » = la zone OLL ; une commune mono-zone (16/24) est servie OLL, une multi-zone (8/24 : Saint-Denis 6 zones…) reste DHUP avec motif — aucune moyenne inter-zones inventée ; détail par zone servi à la parcelle (IRIS→zone). **Preuve live** : Bras-Panon → « Sourcé · OLL 2024 (zone 5) » 10,3 €/m² (2 006 obs) ; Saint-Denis → « Sourcé · DHUP 2025 » avec motif de repli. Piège encodage documenté (Base_OP latin-1, zonage UTF-8 BOM).
- **Coût de construction** : l'EPTB 2024 Réunion EXISTE et a été LU (« coût moyen 145 500 € en 2024, −4 % sur un an », 96 m² ≈ 1 516 €/m² habitable — cité dans `regles/cout_construction_ref.py`) mais mesure la MAISON INDIVIDUELLE, pas la promotion en SDP → la fourchette 2 300-2 800 €/m² SDP reste un choix LABUSE, désormais en table SOURCÉE (`cout_construction_ref`, ligne servie) lue par `Hypotheses.charger` avec repli constantes. **Écart bilan sur les 4 témoins : 0 par construction** (valeurs servies = anciennes constantes — le mandat voulait la constante SOURCÉE, pas un changement de chiffrage). Le « jeu CDC » du mandat est INTROUVABLE (aucun jeu identifiable — dit).
- **Sondes réelles** : 5 `api` data.gouv OK (Arcep 2026-06-11, REI 2026-05-11, ORT 2025-05-14, OLL 2026-08-05 — via api/2, le JSON api/1 à 520 ressources dépassait la coupe de lecture, piège documenté —, DHUP 2024-12-23) + 1 rappel annuel (EPTB). Filtres joués : rei/oll/cout **ok**, ort/arcep **avertissements** (écarts réels dits).

## Lot 6 — Le foncier et les gens (clos)

Deux sources entrées par la porte du Circuit. **Verrous : 16/16 verts** après le lot.

### Ce qui est entré

| Source (data_sources) | Réservoir | Données | État |
|---|---|---|---|
| DFI — documents de filiation informatisés (DGFiP) | `dgfip_dfi` (table `dfi_filiation`) | **409 623 liens mère→fille**, 24 communes, 1989-12-06 → 2025-12-29, 156 787 parcelles mères | servie |
| INSEE RP2022 — bases IRIS (logement, population) | `insee_rp_iris` (table `iris_rp`) | **344 IRIS / 24 communes**, 0 sans volet population — vacants, âge du bâti (ACH), statuts d'occupation, ménages, tranches d'âge | servie |

- **DFI, découverte de canal** : l'API ODS data.economie du jeu est VIDE (total_count = 0, vérifié) — la vraie diffusion est le fichier agrégé data.gouv (CSV national 3,5 Go / parquet 199 Mo, situation 19/06/2026). Lecture DISTANTE du parquet via duckdb/httpfs filtrée `code_departement='974'` : rien des 3,5 Go téléchargé.
- **Deux codes AMONT légitimes** dans la filiation (pas des IDU difformes) : fille `PDP` = passage au domaine public (5 032), mère `EDNC` = issue du non-cadastré (1 797) — servis ÉTIQUETÉS en fiche, jamais joints à `parcels` ; le filtre les compte à part (1,7 % des liens) et ne bloque que le reste (0 mesuré).
- **Rejeu des permis orphelins par la filiation officielle (mandat)** : l'état de départ n'était plus les 2 894 de RETOURS-14 mais **1 887** sans géométrie (le canal géométrique « cadastre d'époque » + BD PARCELLAIRE 2008 de RETOURS-21 était passé depuis). La filiation DFI (mère disparue → filles TERMINALES, descente récursive ≤ 8 niveaux, point = `ST_PointOnSurface(ST_Union(filles))`) en rattache **985 : 1 887 → 902 restants** (52,2 % du reliquat récupéré). Les 902 restants : parcelles hors informatisation DFI (avant 1980-90), aménagements fonciers exclus, ou mères elles-mêmes jamais cadastrées — état réel, dit. Provenance tracée (`raw.geoloc = « filiation DFI (mère → filles, DGFiP) »`, filles listées, `origine_redecoupee` dès 2 filles). Preuve : permis 97441820E0003 (Sainte-Marie) posé sur BI0356 → filles BI0368/369/370.
- **IRIS RP2022** : bases infra-communales officielles insee.fr (parution 16/10/2025, géographie 01/01/2024 = LA MÊME que les Contours IRIS déjà servis — contrôle bloquant « chaque IRIS adossé à un contour » : 0 écart). Dérivées à un seul point de calcul (fiche de règle) : vacance, part bâti ≤ 1990, taille des ménages (NPER_RP/RP), part 60+, part locataires/HLM.

### Servi

- **Fiche parcelle** : « Historique cadastral (filiation officielle) » dans Le bien (mères/filles datées + natures + drapeau division récente ≥ 2023 ; contrôle croisé avec le cadastre d'époque DIT) ; « Le quartier INSEE » dans Autour (vacance, âge du bâti, ménages, 60+, HLM — maille IRIS DITE). Preuve réelle : 97410000BH0103 (Saint-Benoît) → filles BH0450/451 du 05/08/2024, division récente ; IRIS « La Confiance-Chemin de Ceinture », vacance 20,0 %, bâti ≤ 1990 : 28,1 %, 2,83 pers./ménage.
- **Fiche commune** : bloc Population + « Par quartier (n IRIS) : vacance min → max (méd.) » — l'IRIS AFFINE, `commune_insee_logement` reste la vérité communale.
- **Étude de zone** : overlay `iris` de `population_zone` (n IRIS intersectés, vacance, part bâti ≤ 1990) — complète Filosofi, ne le remplace pas.
- **Variables candidates scoring NOTÉES (banc K0, conversation Scoring)** : `division_recente` (DFI — signal de mouvement foncier), vacance IRIS, âge du bâti IRIS. Rien au modèle sans banc.

### La mécanique (un commit)

Catalogue 107 sources (+2) · vanne `dfi`/`iris_rp` · CLI `ingest-dfi` (avec rejeu permis + filtre) et `ingest-iris-rp` · filtres riches joués (**dfi ok** après la leçon PDP/EDNC, **iris_rp ok**) · sondes RÉELLES : DFI api data.gouv (`2026-06-19` lu), IRIS page insee.fr (millésime `2022` lu — pas de data.gouv pour les bases IC) · registre : `filiation_parcelle`, `iris_quartier`, `iris_commune_quartiers` + robinets `fiche_parcelle_filiation`/`fiche_parcelle_quartier`/`fiche_commune_quartiers` + `iris_quartier` déclaré NON_SONDES (un seul producteur, fiche + zone) · `tables.py`, `NOM_VERS_SLUG`, `reservoirs.csv`, `valeur.py` · fiches de règle `regles/filiation_parcelle.py` (choix rattachement) et `regles/iris_quartier.py` (dérivées + dénominateurs INSEE) · tests `tests/test_sources1_lot6.py` + compteurs figés (MODE_ET_CADENCE 105→107, sentinelle 96→98).

## Lot 7 — Le catalogue mis d'équerre (clos)

Aucune donnée nouvelle : le catalogue dit désormais l'état VRAI de tout ce qui manque encore.
**Verrous : 16/16 verts** après le lot. Catalogue en base : **116 lignes** (107 au code + alias/legacy).

### BDNB retirée de la vitrine

`BDNB` passe `a_faire` → **`retiree`** par le mécanisme RETRAITS existant (comme EDF SEI/MOBPRO),
raison : « ne couvre pas le 974 au millésime courant (2026-02-a métropole seule — 0 ligne 974
sur 22,3 M vérifiées, SCORING-3 L3) ». **Rien de détruit** : l'ingestion (`bdnb.py`), le banc K0
(`l3_bdnb.py`), le CRON re-sonde et la **sonde sentinelle data.gouv restent actifs** (vérifié en
base : `source_veille` methode=api, actif=true) — le retrait tombera de lui-même au premier
millésime couvrant le 974.

### Sept chantiers nommés (en attente de demande)

Une ligne `data_sources` chacune — statut **`a_faire`** (l'enum n'a pas de statut « chantier »,
décision), organisme à solliciter en tête des notes, mode `absente`, raison de non-surveillance
« CHANTIER — en attente de la demande », slug + carte + réservoir posés (aucune table tant que
rien n'est remis) :

| Chantier | À solliciter |
|---|---|
| Zonages d'assainissement SIG complets (20 communes hors GPU) | 5 EPCI / régies |
| Inventaires ZAE (L.318-8-2 CU) | 5 EPCI |
| Périmètres de ZAC | EPCI / communes / EPF Réunion |
| OPAH / PIG (périmètres exacts) | Anah / EPCI |
| Périmètres ORT infra-communaux (Denormandie au périmètre) | EPCI |
| ENS + zones de préemption ENS | Conseil départemental |
| Micro-données OLL | ADIL / AGORAH |

### Cerema — une convention pour trois

`Fichiers fonciers (Cerema)` (entrée M74 EXISTANTE enrichie — pas doublée), **`LOVAC`** et
**`DV3F`** (lignes neuves) : statut `manuel` + fiabilité **`SOUS_CONVENTION`** (l'enum
ReliabilityLevel l'a ; DataSourceStatus n'a pas de statut convention — décision), avec la note
du mandat : **« LOVAC réservé aux collectivités et à leurs prestataires »** (un éditeur privé
n'y a pas accès en propre — passer par une collectivité mandante, geste Vic). En attendant :
DVF ouvert + MAJIC PM + DFI (servis), vacance INSEE RP par IRIS (lot 6), échantillon
producteur Région (lot 4).

### DEMANDE-REGION-EPCI.md

`docs/CIRCUIT/DEMANDE-REGION-EPCI.md` prêt à envoyer, par destinataire (Région, les 5 EPCI,
Département, AGORAH/ADIL, DEAL, communes) — chaque demande avec l'usage LABUSE concret et le
format souhaité. Les listes REPRENNENT ce que les lots ont mesuré : les 20 communes sans DPU au
GPU (lot 1 — au passage, la liste des 4 publiantes est CORRIGÉE : Le Tampon, Saint-Denis,
Saint-Paul, Sainte-Marie, mesurée en base), le DPE des ravines non diffusé (lot 2), la couche
SAR officielle introuvable + SAR 2050 (lot 4), les périmètres ORT infra-communaux (lot 5), et
la section 4 de SOURCES-CANDIDATES.md (SIG PEIGEO, cadastre solaire, TCSP, observatoires
AGORAH, LiDAR régional, republication du DVF Région figé).

### Gardes

`tests/test_sources1_lot7.py` (5 tests : retrait avec veille vivante, chantiers avec organisme,
convention Cerema, demande committée, pont/carte) ; compteurs figés 107→116 (MODE_ET_CADENCE)
et 98→107 (noms du catalogue code).

## Lot 8 — Ce que ça déclenche (clos)

### Les filtres, joués sur leur première version (07/09/2026)

| verdict | filtres |
|---|---|
| **ok** (14) | zonage_abc · sup_gpu · deal_dpf · zones_humides · enp_complements · rpg_ign · bruit_itt_cerema · bruit_cartes · potentiel_foncier_region · dgfip_rei · loyers_dhup · loyers_oll · cout_construction · dfi · iris_rp |
| **avertissements** (10) | gpu_prescriptions_er (6 ER hors code, rescue) · gpu_prescriptions_ebc · dpu (4/24) · peb (1/2 aérodromes) · azi_tri (2 communes sans document) · georisques_sis · georisques_casias (part sans emprise) · arcep_fibre · anct_ort (Saint-Louis absent chez le producteur) · dvf (échantillon Région figé mi-2021) |
| quarantaine | **aucune** |

Les avertissements sont l'état RÉEL des couvertures partielles — dits, jamais des zéros. Les sources servies sont sur le Circuit (`/admin/flux` : 23 des 24 marqueurs testés) ; ZPPA et les 7 chantiers vivent au Catalogue avec leur raison (hors vitrine, verrou V2b).

### Ce qui existe chez les producteurs (recherches réelles du 07/09/2026)

- **SAR 2050** : planning officiel Région — projet finalisé et présenté **début du 2ᵉ semestre 2026**, transmission aux personnes publiques associées puis **enquête publique en 2027** (sar.regionreunion.com, CIREST 20/05/2026). Le rappel sentinelle 180 j est bien calibré.
- **Ravines DPE** : rien de diffusé (page DEAL toujours « en cours de mise à jour ») — la demande DEAL reste le seul canal.
- **Zones humides** : projet national de **prélococalisation des milieux humides DROM lancé en 2024** (réunions mi-parcours océan Indien **septembre 2025**, PatriNat) ; le RPDZH publie des inventaires effectifs depuis **juin 2026** — à surveiller pour un 4ᵉ inventaire 974.
- **Classement sonore** : arrêtés 14-15/12/2023 en vigueur ; révision réglementaire au minimum tous les 5 ans → **prochaine ~2028**.
- **OLL** : **publication détaillée du 10/07/2025** (AGORAH) déjà exploitée au lot 5 ; **micro-données accessibles via le CASD** (source « ADIL Réunion / AGORAH » déposée) — une piste concrète pour la demande AGORAH/ADIL, notée dans DEMANDE-REGION-EPCI.md.

### Registre, verrous, seuils

- `labuse registre fiche parcelle` + `fiche autres` régénérés : **0 « source absente »** dans les deux documents (les 5 réglementaires de FICHE-1 lot 7 sont toutes servies ; les vrais absents — ZPPA, chantiers — n'ont pas de donnée déclarée, c'est le catalogue qui les porte).
- `labuse circuit verrous --complet` : **16/16 verts, 0 à décider** (204 données, 76 tables de réservoir).
- `CHOIX-LABUSE.md` : **11 seuils SOURCES-1 ajoutés** avec leurs références (ER 50, EBC 80 + assiette, PEB A/B ≥ 2 % L112-10, DPU vigilance, marchepied 3,25 m L2131-2, réserves/APB, RPG canne 50, SIS L556-2/L125-7, SUP AC2/AS1, OLL canonique, coût de construction) — total 60 choix écrits.

### Le run candidat `q_v13_sources1` — produit, jamais basculé

**Deux bugs latents attrapés par le premier passage du run — corrigés à la racine :**

1. **`spatial_layers_sub` périmé** : le cache pré-subdivisé de la cascade (prime, ×64) n'était
   JAMAIS reconstruit après une ingestion. Le premier passage du run a évalué AVEUGLE aux couches
   entrées par SOURCES-1 (peb, dpu, zone_humide, compléments ENP : PASS partout — alors que la
   base réelle intersecte 798 parcelles en PEB C, 129 919 en DPU, 8 642 en zones humides).
   Correctif : `flux-run` reconstruit le cache AVANT la cascade (`ensure_spatial_layers_sub
   force=True`, quelques minutes amorties) ; run purgé et RECALCULÉ en entier sur cache frais.
2. **`division-or` en sous-processus cassé** : `pompe calculer` lançait `python -m labuse.cli
   division-or` — une commande TARDIVE invisible par ce chemin (garde `__main__` en milieu de
   fichier) → exit 2 systématique. Correctif : invocation de l'app complète via `-c`.

Le run candidat **`q_v13_sources1`** est produit EN ENTIER (24/24 communes, 431 663 parcelles,
cascade + scoring/tiers), **jamais servi** — `q_v11_m137` reste le run servi, aucun verrou de
bascule touché. Recette scoring inchangée (m36 servie) : le run ne change QUE la cascade (les
nouveaux motifs SOURCES-1), pas le modèle P.

**Ce qui change vs le run servi `q_v11_m137`** (mesuré sur les 431 663 parcelles) :

- **7 931 parcelles changent de statut** (1,8 %). Solde par statut : écartées 145 882 → **150 260**
  (+4 378), à-creuser 268 110 → 263 676 (−4 434), opportunités 17 671 → **17 727** (+56).
  L'effet net est un resserrement : les nouvelles servitudes opposables retirent des parcelles
  du gisement « à creuser », très peu d'opportunités bougent.
- **Nouveaux RÉDHIBITOIRES par couche** (absents du run servi) : prescriptions PLU **17 001**
  (dont **EBC ≥ 80 % : 11 871** et **ER ≥ 50 % : 5 130** — la réversion de M129 P1.1), **DPF
  marchepied 3,25 m : 10 335**, RPG/agricole 6 612, espaces protégés (réserves/APB) 1 100,
  **PEB zones A/B : 441**.
- **Nouvelles VIGILANCES servies** : SUP par catégorie 188 692, prescriptions PLU 163 899,
  **DPU 111 875**, RPG 66 181, sites/sols (SIS/CASIAS) 10 507, **PEB C/D 3 880**, **zones
  humides 2 972**, ENP hors réserve 1 536.

**Note de version** (registre `bascule_flux.note_version`) et rapport candidat produits par la
pompe ; la division d'or du label a été rejouée à part (deux SIGTERM externes ont interrompu la
pompe — arrêt Postgres puis arrêt de la machine ; le run est résumable et a été repris à chaque
fois sans perte, cascade et scoring persistés par lots).

### Captures (docs/CIRCUIT/RECETTE-SOURCES-1/)

- `fiche-97402000AE0048-er-ebc-sup.png` — Bras-Panon, tiroir « Dispositifs et périmètres » ouvert : ER 5 %, EBC 4,5 %, DPU « non déterminée — non publié par la commune », SUP PM1.
- `fiche-97411000BM0004-peb-dpu.png` — Saint-Denis : PEB zone B + DPU servi.
- `fiche-97409000AY1303-zone-humide.png` — Saint-André, parcelle en zone humide (l'effet cascade porte sur le run candidat, la fiche montre l'état servi).
- `carte-contraintes-nature.png` — les familles « Contraintes » et « Nature » : 9 couches neuves activées (ER, EBC, DPU, PEB, SUP, DPF, zones humides, ENP, RPG).
- `circuit-reservoirs-neufs.png` — la page Données/Circuit avec les réservoirs neufs.
- Serveurs locaux : API du worktree sur :8001 + vite :5174 (les ports 8000/5173 étaient tenus par une AUTRE session — labuse-s1b — laissée intacte) ; `vite.config.ts` accepte désormais `LABUSE_API_DEV` pour pointer l'API de dev.

## Ce qui reste à Vic

1. **Lire la note de version du run candidat `q_v13_sources1`** (ci-dessus + page Données/Mise à jour) et **basculer depuis la page** s'il convient — rien n'a été basculé, `q_v11_m137` reste servi.
2. **Envoyer `docs/CIRCUIT/DEMANDE-REGION-EPCI.md`** (Région, 5 EPCI, Département, AGORAH/ADIL — piste CASD pour les micro-données OLL —, DEAL, les 20 communes sans DPU au GPU).
3. **Lire les seuils dans `docs/CIRCUIT/CHOIX-LABUSE.md`** (11 lignes SOURCES-1, marquées vic/cc — dont la réversion de M129 P1.1 sur l'ER).
4. **Engager la convention Cerema par une collectivité mandante** (FF/LOVAC/DV3F — LOVAC inaccessible en propre à un éditeur privé).

## Décisions prises en autonomie

- Étape 0 : `main` local étant extrait dans un autre worktree, la branche part de `origin/main` (strictement identique, `ea6fd161`).
- Lot 3 · SIS/CASIAS : réservoirs LOGIQUES sur le kind `sol_pollue` (canal SSP existant) — pas de table dupliquée ; les endpoints dédiés /api/v1/sis et /api/v1/casias n'existent pas (404 vérifié), les pages d'export Géorisques n'exposent aucun lien lisible ; le canal SSP est déjà sondé (témoin bi-commune), pas de seconde sonde sur le même flux.
- Lot 3 · CBS : type b (« secteurs affectés ») NON ingérées — doublon vérifié des bandes `sect_bruit_m` du classement Cerema ; type a (isophones) écartées (cartographie d'exposition sans effet réglementaire propre) ; type c (dépassements) seules servies, « ≠ classement » dit partout.
- Lot 3 · coût d'isolation acoustique : AUCUN montant au bilan promoteur — l'arrêté du classement fixe des exigences d'isolement, pas un coût ; le renchérissement reste porté par la vigilance (motif cascade + fiche), conformément à « aucun seuil sans référence ni mesure ».
- Lot 3 · réservoir « deal_classement_sonore » du mandat : l'identifiant canonique EXISTANT `bruit_itt_cerema` est conservé (renommer un slug de la carte churne data_sources/reservoirs/pont sans rien servir de plus) — le mandat est satisfait par la mise d'équerre de la ligne existante.
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

- Lot 4 · SAR : la couche officielle étant introuvable en vecteur (4 canaux testés), le proxy de vocations n'est PAS affiché comme couche « SAR » sur la carte (mensonge d'étiquette) — la source entre `a_faire`, réservoir logique, doctrine D2 conservée ; la VIGILANCE simple s'armera à la couche officielle (fiche de règle).
- Lot 4 · DVF Région : appariement par mutation impossible (ids md5 producteur) → échantillon producteur AGRÉGÉ par fenêtres commune×année, limité aux années pleines du jeu figé (2019-2020) ; tolérance 5 % (écarts de périmètre DV3F/géo-DVF mesurés 1,5-3,1 %).
- Lot 4 · potentiel foncier : la comparaison est un CONTRÔLE avertissant (plancher 25 % = moitié de la convergence mesurée 44,6 %) — jamais une quarantaine : une divergence avec une ESTIMATION du producteur ne bloque pas nos données.
- Lot 4 · pas de nouvelle donnée servie (mandat) : ni le DVF Région ni le potentiel foncier n'alimentent une fiche/couche/cascade — contrôles seulement.

- Lot 5 · loyers : le « secteur » de la bascule OLL/DHUP = la ZONE OLL (maille publiée) ; une commune multi-zones n'a pas de valeur communale OLL publiée → repli DHUP dit, jamais une moyenne de zones fabriquée.
- Lot 5 · coût de construction : l'EPTB (maison individuelle, habitable) et la promotion (SDP) sont des segments INCOMPARABLES — l'EPTB entre en CONTEXTE sourcé, le choix promotion 2 300-2 800 reste servi (valeurs inchangées : aucun bilan ne bouge, écart témoins = 0). Le « jeu CDC » du mandat, introuvable, est dit.
- Lot 5 · ORT : l'écart producteur (Saint-Louis attendu ACV, absent de la table DGALN) est SERVI comme un écart (filtre avertissant), pas corrigé à la main ; Denormandie = phrase d'état sur la condition communale, aucun calcul d'avantage sans le périmètre conventionné.
- Lot 5 · Arcep : seul le FttH (IPE) est servi — les technos déclaratives (4GF/CU/SAT) sont ingérées côté éligibilité mais non affichées ; distance à l'immeuble TOUJOURS dite, jamais un booléen nu.

- Lot 6 · filtre DFI : le premier passage a mis la source en quarantaine sur « 6 829 IDU difformes » — c'étaient les codes amont PDP/EDNC (légitimes). Le contrôle a été corrigé (bloquant hors codes amont seulement, part des codes mesurée à part) et la leçon est écrite : un code producteur n'est pas une difformité.
- Lot 6 · rattachement des permis : la filiation DFI ne se joue QUE sur les permis encore sans géométrie après le canal géométrique (cadastre d'époque premier — sa géométrie est exacte là où elle existe) ; l'écart entre canaux est un contrôle croisé, pas un conflit.
- Lot 6 · sonde IRIS : les bases infra-communales INSEE n'existent pas sur data.gouv — sonde `page` sur le sommaire insee.fr (regex millésime « Logement en (20\d{2}) »), à défaut d'un `last_update` machine.
- Lot 6 · duckdb : lecture distante du parquet DFI via duckdb/httpfs (déjà en dépendance pyproject depuis ZONE-DONNÉES) — jamais le CSV national de 3,5 Go.

- Lot 7 · statut « chantier » : l'enum DataSourceStatus n'en a pas — les chantiers entrent en `a_faire` avec « CHANTIER (SOURCES-1 lot 7) » en tête des notes et l'organisme à solliciter ; pas de statut inventé en base.
- Lot 7 · statut « convention » : DataSourceStatus n'a pas `sous_convention` mais ReliabilityLevel OUI — les trois lignes Cerema restent `manuel` (hors automatisation) avec fiabilité `SOUS_CONVENTION`.
- Lot 7 · « Fichiers fonciers (Cerema) » existait déjà au catalogue code (entrée M74, riche des interdits de l'acte d'engagement) — enrichie de la convention lot 7, jamais doublée (un doublon de nom = deux vérités).
- Lot 7 · BDNB : retrait par le mécanisme RETRAITS existant, ingestion/banc K0/CRON/sonde CONSERVÉS — la vitrine dit « retirée », le chantier reste armé pour le prochain millésime.

*(chapitres suivants à venir)*
