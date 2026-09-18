# COUCHES-REGISTRE-1 — Audit du lien couche ↔ source ↔ Circuit, par la preuve

Branche `feat/couches-tuyau`, départ `5ab61380`. **Lecture seule, aucune correction, aucune tuile touchée.** Ce rapport sert à écrire le mandat de raccordement.

## Méthode

Les 56 couches du tuyau (`/map/tuyau/couches`), quatre contrôles chacune, verdict oui/non :

1. **Registre** — la couche est déclarée dans `donnees.py` / `robinets.py` (ou `registre/tables.py` `RESERVOIR_TABLES`) avec un réservoir nommé. Pas « décor », pas hors_registre.
2. **Réservoir réel** — ce réservoir existe en `data_sources`, statut `connecte`, et c'est **bien lui que la couche lit** — vérifié par le `data_source_id` **réel** porté par les lignes servies (`spatial_layers` / tables du tuyau), pas la déclaration.
3. **Le « i »** — ouvert au survol dans le navigateur : affiche-t-il la **source**, le **millésime**, et la **date du dernier contrôle** ? Une capture par couche (`<kind>_i.png`).
4. **Le Circuit** — la page de détail du réservoir (vue « Sources ») liste-t-elle cette couche parmi ses robinets ? Captures dans `circuit/`.

Preuve : `captures/couches-registre/` (54 `<kind>_i.png` + 4 captures Circuit + `_i_log.json`). Données reproductibles par `scripts/audit_couches_registre.py`.

## Le chiffre

> **0 couche sur 56 est verte aux quatre contrôles.**

| contrôle | vert / 56 | ce qu'il révèle |
|---|:--:|---|
| 1 · Registre | **55 / 56** | tout est déclaré avec un réservoir, sauf `limites_communes` (seed `geo.api.gouv`, aucun `data_source`). |
| 2 · Réservoir réel | **51 / 56** | 5 échouent : `limites_communes` / `limites_parcelles` / `zonage_parcelle` lisent le cadastre-seed (mvt_*, aucun `data_source_id`) ; `parc_national` (3 lignes) et `vefa_neuf` (24 lignes dérivées) portent `data_source_id = NULL`. |
| 3 · « i » complet | **0 / 56** | le « i » du tuyau est la **description YAML en prose** — jamais la source + millésime + date de contrôle structurés. 30/56 mentionnent une source en prose, 5/56 une année, **0/56 une date de dernier contrôle**. Le câblage CIRCUIT-2 (`/map/couches-info`) n'a **pas** été porté au panneau tuyau (`NouvellesCouches` passe `info={c.i}`). |
| 4 · Circuit | **0 / 56** | la page « Sources » porte `source_millesime` + `verified_at` + fraîcheur **par source**, mais **ne liste jamais les couches qu'une source alimente**. Le lien réservoir → couche existe au registre (`RESERVOIR_TABLES.couches`), pas à l'écran. |

**Lecture** : la couche du tuyau est correctement **rattachée dans le registre** (checks 1–2 quasi verts), mais le **lien n'est affiché nulle part** (checks 3–4 à zéro) — ni le « i » de la couche ne nomme sa source/millésime/date, ni le Circuit ne remonte la couche depuis sa source. Le raccordement est une affaire d'**affichage**, pas de données.

## Le tableau (56 couches)

| # | couche (kind) | réservoir | 1·registre | 2·réservoir réel | 3·« i » complet | 4·Circuit | captures |
|--:|---|---|:--:|:--:|:--:|:--:|---|
| 1 | abf | abf_merimee | ✅ | ✅ · ABF / Monuments historiques [connecte] | ❌ | ❌ | abf_i.png |
| 2 | alea_inondation | georisques_api | ✅ | ✅ · DEAL Réunion — PPR / aléas [connecte] | ❌ | ❌ | alea_inondation_i.png |
| 3 | alea_mvt | georisques_api | ✅ | ✅ · DEAL Réunion — PPR / aléas [connecte] | ❌ | ❌ | alea_mvt_i.png |
| 4 | amenite | osm_overpass | ✅ | ✅ · OpenStreetMap / Overpass [connecte] | ❌ | ❌ | amenite_i.png |
| 5 | amenite_bpe | bpe_insee | ✅ | ✅ · BPE INSEE [connecte] | ❌ | ❌ | amenite_bpe_i.png |
| 6 | anru | npnru | ✅ | ✅ · DEAL Réunion (WMS/WFS) [connecte] | ❌ | ❌ | anru_i.png |
| 7 | artificialisation | ocsge | ✅ | ✅ · OCS GE (IGN) — occupation du sol e… [connecte] | ❌ | ❌ | artificialisation_i.png |
| 8 | axe_structurant | gtfs_pan | ✅ | ✅ · BD TOPO IGN [connecte] | ❌ | ❌ | axe_structurant_i.png |
| 9 | bassin_versant | bd_topo | ✅ | ✅ · BD TOPO IGN [connecte] | ❌ | ❌ | bassin_versant_i.png |
| 10 | batiment | bd_topo | ✅ | ✅ · BD TOPO IGN [connecte] | ❌ | ❌ | (hors panneau (bâti 3D)) |
| 11 | bruit_carte | deal_bruit_cartes | ✅ | ✅ · DEAL — cartes de bruit stratégique… [connecte] | ❌ | ❌ | bruit_carte_i.png |
| 12 | bruit_route | bruit_itt_cerema | ✅ | ✅ · Classement sonore ITT (Cerema) [connecte] | ❌ | ❌ | bruit_route_i.png |
| 13 | casias | georisques_casias | ✅ | ✅ · Géorisques — sites et sols pollués [connecte] | ❌ | ❌ | casias_i.png |
| 14 | cavite | georisques_cavites | ✅ | ✅ · Géorisques — cavités souterraines [connecte] | ❌ | ❌ | cavite_i.png |
| 15 | cimetiere | bd_topo | ✅ | ✅ · BD TOPO IGN [connecte] | ❌ | ❌ | cimetiere_i.png |
| 16 | cinquante_pas | cinquante_pas_deal | ✅ | ✅ · 50 pas géométriques — limite haute… [connecte] | ❌ | ❌ | cinquante_pas_i.png |
| 17 | construction_lineaire | bd_topo | ✅ | ✅ · BD TOPO IGN [connecte] | ❌ | ❌ | construction_lineaire_i.png |
| 18 | construction_surfacique | bd_topo | ✅ | ✅ · BD TOPO IGN [connecte] | ❌ | ❌ | construction_surfacique_i.png |
| 19 | dpf | deal_dpf_dpe | ✅ | ✅ · Ravines — domaine public fluvial (… [connecte] | ❌ | ❌ | dpf_i.png |
| 20 | dpu | dpu_perimetres | ✅ | ✅ · GPU — droit de préemption urbain (… [connecte] | ❌ | ❌ | dpu_i.png |
| 21 | ebc | gpu_plu_api_carto | ✅ | ✅ · Urbanisme PLU/GPU (API Carto) [connecte] | ❌ | ❌ | ebc_i.png |
| 22 | endiguement | endiguement | ✅ | ✅ · Systèmes d'endiguement et zones pr… [connecte] | ❌ | ❌ | endiguement_i.png |
| 23 | enp | enp_complements_deal | ✅ | ✅ · Espaces protégés complémentaires —… [connecte] | ❌ | ❌ | enp_i.png |
| 24 | er | gpu_plu_api_carto | ✅ | ✅ · Urbanisme PLU/GPU (API Carto) [connecte] | ❌ | ❌ | er_i.png |
| 25 | foret_publique | forets_onf_bdtopo | ✅ | ✅ · Forêts publiques (ONF) [connecte] | ❌ | ❌ | foret_publique_i.png |
| 26 | friche | cartofriches | ✅ | ✅ · Cartofriches (Cerema) [connecte] | ❌ | ❌ | friche_i.png |
| 27 | frr | frr_ex_zrr | ✅ | ✅ · FRR ex-ZRR — zone spéciale d'actio… [connecte] | ❌ | ❌ | frr_i.png |
| 28 | icpe | georisques_icpe | ✅ | ✅ · Géorisques — ICPE [connecte] | ❌ | ❌ | icpe_i.png |
| 29 | ligne_ht | edf_hta | ✅ | ✅ · BD TOPO IGN [connecte] | ❌ | ❌ | ligne_ht_i.png |
| 30 | ligne_mt | edf_hta | ✅ | ✅ · EDF Réunion — lignes moyenne tensi… [connecte] | ❌ | ❌ | ligne_mt_i.png |
| 31 | limites_communes | — | ❌ | ❌ · — [—] | ❌ | ❌ | limites_communes_i.png |
| 32 | limites_parcelles | cadastre_api_carto | ✅ | ❌ · — [—] | ❌ | ❌ | limites_parcelles_i.png |
| 33 | parc_national | parc_national_inpn | ✅ | ❌ · — [None] | ❌ | ❌ | parc_national_i.png |
| 34 | peb | peb_dgac | ✅ | ✅ · PEB — plans d'exposition au bruit … [connecte] | ❌ | ❌ | peb_i.png |
| 35 | piscine_cosia | cosia | ✅ | ✅ · CoSIA (couverture du sol IA, IGN) [connecte] | ❌ | ❌ | piscine_cosia_i.png |
| 36 | plu_gpu_zone | gpu_plu_api_carto | ✅ | ✅ · Urbanisme PLU/GPU (API Carto) [connecte] | ❌ | ❌ | plu_gpu_zone_i.png |
| 37 | pole_echange | gtfs_pan | ✅ | ✅ · OSM — transport (pôles d'échange &… [connecte] | ❌ | ❌ | pole_echange_i.png |
| 38 | ppr | deal_ppr | ✅ | ✅ · DEAL Réunion — PPR / aléas [connecte] | ❌ | ❌ | ppr_i.png |
| 39 | qpv | qpv_2024 | ✅ | ✅ · QPV 2024 (ANCT) [connecte] | ❌ | ❌ | qpv_i.png |
| 40 | safer | rpg_proxy_ign | ✅ | ✅ · RPG — déclarations agricoles (IGN/… [connecte] | ❌ | ❌ | safer_i.png |
| 41 | sar | potentiel_foncier_region | ✅ | ✅ · data.regionreunion.com — Potentiel… [connecte] | ❌ | ❌ | sar_i.png |
| 42 | sis | georisques_casias | ✅ | ✅ · Géorisques — sites et sols pollués [connecte] | ❌ | ❌ | sis_i.png |
| 43 | sup | sup_gpu | ✅ | ✅ · SUP — assiettes GPU (API Carto) [connecte] | ❌ | ❌ | sup_i.png |
| 44 | tcsp | tcsp_osm | ✅ | ✅ · TCSP — voies bus en site propre (O… [connecte] | ❌ | ❌ | tcsp_i.png |
| 45 | telepherique | osm_transport | ✅ | ✅ · OSM — transport (pôles d'échange &… [connecte] | ❌ | ❌ | telepherique_i.png |
| 46 | trait_de_cote | erosion_cotiere_geolittoral | ✅ | ✅ · Cerema / GéoLittoral — indicateur … [connecte] | ❌ | ❌ | trait_de_cote_i.png |
| 47 | transport_arret | gtfs_pan | ✅ | ✅ · Transport public — GTFS (PAN, 7 ré… [connecte] | ❌ | ❌ | (fusionné (transport_public)) |
| 48 | transport_ligne | gtfs_pan | ✅ | ✅ · Transport public — GTFS (PAN, 7 ré… [connecte] | ❌ | ❌ | transport_ligne_i.png |
| 49 | tri_zone | georisques_azi_tri | ✅ | ✅ · AZI / TRI — inondation (Géorisques… [connecte] | ❌ | ❌ | tri_zone_i.png |
| 50 | tva_primo | zfang | ✅ | ✅ · QPV 2024 (ANCT) [connecte] | ❌ | ❌ | tva_primo_i.png |
| 51 | vefa_neuf | dvf | ✅ | ❌ · — [None] | ❌ | ❌ | vefa_neuf_i.png |
| 52 | zfang | zfang | ✅ | ✅ · ZFANG — zone franche d'activité no… [connecte] | ❌ | ❌ | zfang_i.png |
| 53 | znieff | znieff_inpn | ✅ | ✅ · ZNIEFF (INPN/MNHN) [connecte] | ❌ | ❌ | znieff_i.png |
| 54 | zonage_parcelle | gpu_plu_api_carto | ✅ | ❌ · — [—] | ❌ | ❌ | zonage_parcelle_i.png |
| 55 | zone_activite | bd_topo | ✅ | ✅ · BD TOPO IGN [connecte] | ❌ | ❌ | zone_activite_i.png |
| 56 | zone_humide | deal_zones_humides | ✅ | ✅ · Zones humides — inventaires DEAL (… [connecte] | ❌ | ❌ | zone_humide_i.png |
*Colonne 2 : le nom entre crochets est la source **réelle** portée par `data_source_id`, pas le réservoir déclaré. Colonne captures : `<kind>_i.png` sauf `batiment` (hors panneau — bâti 3D) et `transport_arret` (fusionné dans « Transport public » avec `transport_ligne`).*


**Détail check 3 (« i » — ce que le survol affiche réellement) :**

| couche | montre source | montre millésime | montre date contrôle | extrait « i » |
|---|:--:|:--:|:--:|---|
| abf | · | · | · | Périmètres ABF / monuments (arrêtés). |
| alea_inondation | O | · | · | Aléa inondation (Géorisques), gradué par classe (faible / moyen / fort |
| alea_mvt | O | · | · | Aléa mouvement de terrain (Géorisques), gradué par classe (faible → tr |
| amenite | · | · | · | Aménités OpenStreetMap : mairie, école, santé, commerce, police, march |
| amenite_bpe | O | · | · | Base Permanente des Équipements (INSEE) par domaine A–G : services aux |
| anru | · | · | · | Périmètres NPNRU / ANRU (nouveau programme national de renouvellement  |
| artificialisation | · | O | · | Occupation du sol OCS GE : sols artificialisés 2022 + évolution renatu |
| axe_structurant | O | · | · | Axes routiers structurants (BD TOPO, importance IGN 1-2) — l'armature  |
| bassin_versant | · | · | · | Territoire de drainage — bassins versants (BD Carthage / hydrographie) |
| batiment | — | — | — | *hors panneau (bâti 3D)* |
| bruit_carte | · | · | · | Cartes de bruit stratégiques — zones de dépassement des seuils (inform |
| bruit_route | · | · | · | Classement sonore des voies (catégories 1 à 5) — isolement acoustique  |
| casias | O | · | · | Inventaire historique des sites industriels/de service (Géorisques CAS |
| cavite | O | · | · | Cavités souterraines (Géorisques). |
| cimetiere | O | · | · | Cimetières (BD TOPO) — servitude de voisinage (100 m). |
| cinquante_pas | · | · | · | Réserve des 50 pas géométriques (bande littorale du domaine public, ~8 |
| construction_lineaire | O | · | · | Murs de soutènement et constructions linéaires (BD TOPO) — enjeu de te |
| construction_surfacique | O | · | · | Ouvrages surfaciques construits (BD TOPO) : barrages, ponts, dalles. 3 |
| dpf | O | · | · | Ravines du domaine public fluvial (DEAL) et leurs reculs — inconstruct |
| dpu | · | · | · | Périmètres de DPU (simple / renforcé) — la commune peut se substituer  |
| ebc | · | · | · | Espaces boisés classés du PLU — protection stricte du boisement, tout  |
| endiguement | O | · | · | Digues et zones protégées (DEAL). ⚠ Ni classe ni niveau de protection  |
| enp | O | · | · | ENP par type (réserves naturelles dont marine, APB, conservatoire du l |
| er | · | · | · | Emplacements réservés du PLU (voirie, équipement, espace vert) — l'emp |
| foret_publique | O | · | · | Forêts domaniales et publiques (ONF/BD TOPO). |
| friche | · | · | · | Friches recensées (Cartofriches + recensement AGORAH des friches urbai |
| frr | · | · | · | France Ruralités Revitalisation (ex-ZRR) — exonérations fiscales et so |
| icpe | O | · | · | Installations classées (Géorisques), par régime. |
| ligne_ht | O | · | · | Réseau de transport 63/90 kV (BD TOPO, aérien) — servitude de voisinag |
| ligne_mt | O | · | · | Réseau HTA 15-20 kV EDF (aérien + souterrain) — tracé indicatif (sécur |
| limites_communes | O | · | · | Limites administratives des 24 communes de La Réunion (contours IGN). |
| limites_parcelles | · | · | · | Contour cadastral de chaque parcelle (DGFiP). Repère de base pour se s |
| parc_national | · | · | · | Périmètre du Parc national de La Réunion. Deux assiettes : le CŒUR (~4 |
| peb | · | · | · | Plan d'Exposition au Bruit aérien : zones A (fort) à D — opposable (co |
| piscine_cosia | O | · | · | Trois niveaux de confiance. Aucune n'est fiscale (signal « piscine non |
| plu_gpu_zone | O | · | · | Zones du PLU telles que publiées au Géoportail de l'Urbanisme (GPU). D |
| pole_echange | O | · | · | Pôles d'échange multimodaux (gares routières OSM) — les nœuds du résea |
| ppr | · | · | · | Plan de Prévention des Risques (document multirisque, opposable). |
| qpv | · | O | · | Quartiers Prioritaires de la politique de la Ville (2024) — abattement |
| safer | O | · | · | Parcelles agricoles déclarées (RPG) — même géométrie que le périmètre  |
| sar | O | · | · | Schéma d'Aménagement Régional — vocations. C'est aussi le « potentiel  |
| sis | O | · | · | Secteurs d'Information sur les Sols (Géorisques) — servitude opposable |
| sup | · | · | · | Servitudes d'utilité publique, opposables au PLU. Colorées PAR FAMILLE |
| tcsp | O | · | · | Transport en commun en site propre : voies en site propre (OSM) + stat |
| telepherique | O | O | · | Téléphérique urbain de Saint-Denis. En service : le Papang (CINOR, rés |
| trait_de_cote | O | · | · | Recul du trait de côte (Cerema/GéoLittoral). |
| transport_arret | — | — | — | *fusionné (transport_public)* |
| transport_ligne | O | · | · | Réseau de transport en commun (bus + téléphérique) : lignes et arrêts  |
| tri_zone | O | · | · | Territoires à risque important d'inondation (Géorisques). |
| tva_primo | · | · | · | Périmètre de TVA à taux réduit (5,5 %) pour l'accession sociale — buff |
| vefa_neuf | · | · | · | Prix médian du neuf VEFA par commune (DVF, ventes en l'état futur d'ac |
| zfang | · | · | · | Zone Franche d'Activité Nouvelle Génération — exonérations fiscales po |
| znieff | O | O | · | Inventaire du patrimoine naturel (INPN/MNHN PatriNat, maj 2025). Type  |
| zonage_parcelle | · | · | · | Zone du PLU CALIBRÉE parcelle par parcelle (famille U urbaine / AU à u |
| zone_activite | · | · | · | Zones d'activité économique (vocation, distinct des équipements BPE). |
| zone_humide | O | O | · | Inventaires DEAL par secteurs (2003, 2009 + espaces fonctionnels, habi |
## Liste A — provenance affichée / déclarée fausse

Le cas `toiture_lidar → batiment_hauteur_lidar` : le registre **crédite la mauvaise source**. Vérifié par le `data_source_id` réel des lignes :

| couche | réservoir DÉCLARÉ | source RÉELLE (data_source_id) | nature |
|---|---|---|---|
| `axe_structurant` | `gtfs_pan` (Transport GTFS) | **BD TOPO IGN** | mauvais réservoir : les axes sont BD TOPO, pas GTFS. |
| `ligne_ht` | `edf_hta` (EDF open data) | **BD TOPO IGN** | la HTB (63/90 kV) vient de BD TOPO ; `edf_hta` ne couvre que la HTA (`ligne_mt`). Le réservoir crédite EDF pour de la donnée BD TOPO. |
| `tva_primo` | `zfang` | **QPV 2024 (ANCT)** | dérivée d'un buffer QPV+500 m : la source réelle est le QPV, pas la ZFANG. |
| `parc_national` | `parc_national_inpn` | **— (`data_source_id` NULL, 3 lignes)** | provenance déclarée mais **aucune ligne rattachée** : invérifiable au niveau donnée. |
| `vefa_neuf` | `dvf` | **— (`data_source_id` NULL, 24 lignes dérivées)** | agrégat commune non rattaché à sa source. |
| `tcsp` (sous-type `tcsp_zone`) | `tcsp_osm` | **— (`data_source_id` NULL)** | la zone 800 m est une géométrie dérivée non rattachée (les tronçons/stations, eux, sont bien OSM). |
| `limites_communes` | — (aucun) | **seed `geo.api.gouv`** | contours embarqués, hors `data_sources` : aucun réservoir. |

Nuance (pas « faux », mais **la source ne peut pas être nommée à l'écran**) : les réservoirs `georisques_api`, `npnru`, `ocsge`, `endiguement`, `forets_onf_bdtopo`, `potentiel_foncier_region` alimentent des couches mais sont **absents de `_RESERVOIR_NAME_ILIKE`** — `/map/couches-info` ne sait pas résoudre leur nom de source (la donnée, elle, est bien `connecte`). Un « i » qui câblerait `couches-info` afficherait « source inconnue » pour `artificialisation`, `endiguement`, `foret_publique`, `sar`, `alea_*`, `anru`.

## Liste B — réservoirs géographiques sans couche

Réservoirs dont les tables sont géographiques (`spatial_layers` / `mvt_*` / `parcels`) mais qui ne déclarent **aucune couche** (`RESERVOIR_TABLES.couches` vide) :

| réservoir | tables | verdict |
|---|---|---|
| `cadastre_api_carto` | `parcels` | **à raccorder** — alimente `limites_parcelles` + `zonage_parcelle` (via `mvt_parcels`) mais ne les déclare pas. Le lien inverse est cassé. |
| `cadastre_etalab_bulk` | `parcels` | idem (source cadastrale alternative). |
| `bd_ortho` | `ortho_tiles`, `ortho_detections`, `parcel_equipements` | légitime — fond de plan ortho (raster/basemap), pas une couche vectorielle du tuyau. |
| `bd_ortho_irc` | `ortho_detections`, `parcel_vegetation` | légitime — détection végétation (outil solaire/fiche), pas une couche carte. |
| `ban` | `adresses`, `adresse_parcelles` | légitime — géocodage adresse (fiche), pas une couche carte. |
| `dgfip_parcelles_pm` | `parcelle_personne_morale` | légitime — propriétaire personne morale (fiche/outil), pas une couche carte. |
| `pvgis` | `solar_grid`, `parcel_solar` | légitime — potentiel solaire (fiche/outil), pas une couche carte. |

**À signaler** : `cadastre_api_carto` / `cadastre_etalab_bulk` sont géographiques ET alimentent des repères de la carte, mais ne les déclarent pas dans `.couches` → le sens inverse (source → couche) est muet pour le cadastre. Les cinq autres sont géographiques mais nourrissent la fiche / le fond de plan, pas une couche du panneau : normal.

## Sens inverse — réservoir → couches (récapitulatif)

Chaque réservoir de la vitrine et les couches qu'il alimente sont dérivés de `RESERVOIR_TABLES.couches` (croisé au `data_source_id` réel). Les cas où le réservoir déclaré ≠ la source réelle (Liste A) sont les points de rupture du sens inverse : depuis « BD TOPO IGN » on ne voit pas `axe_structurant`/`ligne_ht` (déclarés ailleurs), depuis « QPV 2024 » on ne voit pas `tva_primo`.

## Conclusion — ce que le mandat de raccordement devra faire

1. **Câbler le « i » du tuyau sur `/map/couches-info`** (source + millésime + date de dernier contrôle), par `kind` — aujourd'hui `couches-info` est clé par 38 anciennes clés front, pas par les 56 kinds. Sans ça, checks 3 restent à 0.
2. **Compléter `_RESERVOIR_NAME_ILIKE`** pour les 6 réservoirs non résolus (`georisques_api`, `npnru`, `ocsge`, `endiguement`, `forets_onf_bdtopo`, `potentiel_foncier_region`).
3. **Corriger les 3 réservoirs faux** (`axe_structurant`→BD TOPO, `ligne_ht`→BD TOPO/HTB, `tva_primo`→QPV) dans `RESERVOIR_TABLES`.
4. **Rattacher les lignes orphelines** (`data_source_id` NULL) de `parc_national` / `vefa_neuf` / `tcsp_zone`, ou déclarer leur dérivation.
5. **Afficher, sur la page Sources, les couches qu'une source alimente** (le sens inverse — check 4). La donnée existe déjà au registre.
6. **Trancher `limites_communes`** (seed sans `data_source`) et **déclarer les couches du cadastre** (`cadastre_api_carto`).

*Aucune de ces corrections n'est faite ici — lecture seule.*
