# LABUSE — Rapport de vérification des sources de données pour La Réunion (974)

*Recherche approfondie du 06/09/2026. Vingt sources, chacune avec : existence et couverture 974, URL testée, format, licence, producteur et millésime, sonde de fraîcheur, apport, pièges.*

## Tableau récapitulatif

| # | Source | Verdict 974 | URL principale | Format | Licence | Effort |
|---|--------|-------------|----------------|--------|---------|--------|
| 1 | SUP (GPU) | Disponible | geoportail-urbanisme.gouv.fr/atom/download-feed | Atom→ZIP CNIG (shp) | Licence Ouverte | M |
| 2 | Ravines DPF/DPE DEAL | Partiel | reunion.developpement-durable.gouv.fr / sextant.ifremer.fr | couche SIG + PDF | Licence Ouverte | M |
| 3 | SAR Réunion | Disponible (non opposable tiers) | deal974.lizmap.com / Région | SIG/WMS/WFS | Licence Ouverte | M |
| 4 | INPN espaces protégés | Disponible | inpn.mnhn.fr / patrinat.fr / data.gouv | shp/GeoJSON standard ENP | Licence Ouverte | S |
| 5 | Géorisques (SIS/CASIAS/TRI…) | Disponible | georisques.gouv.fr/donnees | CSV/GeoJSON/API | Licence Ouverte | S |
| 6 | Zones humides DEAL | Partiel | deal974.lizmap.com / carmen | WFS/shp | Licence Ouverte | M |
| 7 | Zonage assainissement | Absent (open data SIG) | EPCI / GPU annexes PLU | PDF surtout | variable | L |
| 8 | Classement sonore ITT | Partiel (SIG interne, PDF public) | reunion.developpement-durable.gouv.fr | PDF + SIG DEAL | Licence Ouverte | M |
| 9 | ZPPA archéologie | À vérifier (Atlas patrimoines) | atlas.patrimoines.culture.fr | shp/WFS | Licence Ouverte | M |
| 10 | ACV/PVD/ORT | Disponible (liste) / Partiel (périmètres) | data.gouv ORT + Région | CSV/XLSX | Licence Ouverte | S |
| 11 | Inventaire ZAE | À demander EPCI | sites EPCI / Cerema | PDF/tableur | variable | L |
| 12 | Arcep fibre | Disponible | data.arcep.fr / data.gouv | CSV immeuble/commune | Licence Ouverte | S |
| 13 | REI DGFiP | Disponible | data.economie.gouv.fr | CSV | Licence Ouverte | S |
| 14 | Demande logement social SNE | Partiel (EPCI, pas commune) | data.logement.gouv.fr | CSV | Licence Ouverte | M |
| 15 | Observatoire loyers (OLL) | Publications + données agrégées | observatoires-des-loyers.org | PDF + CSV agrégé | restreint/agrégé | M |
| 16 | OPAH/PIG | Partiel (localisation, pas périmètre) | anah.gouv.fr / data.gouv | carto commune | Licence Ouverte | L |
| 17 | ZAC | À demander (EPCI/GPU) | data.gouv CNIG / EPCI | shp CNIG/PDF | variable | L |
| 18 | DFI DGFiP | Disponible | data.economie.gouv.fr / data.gouv | CSV | Licence Ouverte | S |
| 19 | Cerema FF/LOVAC/DV3F | Sous convention | datafoncier.cerema.fr | PostgreSQL/CSV | convention CGU | M |
| 20 | Catalogues PEIGEO / Région | Disponible | peigeo.re / data.regionreunion.com | WMS/WFS/CSV | Licence Ouverte/ODbL | M |

## A. Contraintes réglementaires

### Fiche 1 — Servitudes d'utilité publique (SUP) sur le Géoportail de l'urbanisme
1. Couverture 974 : oui. Documents SUP au standard CNIG trouvés pour La Réunion : T5 (id 120064019, millésime 20210111), AC1 (id 172014607, 20250225), PM1 (id 130014368, millésimes 20230810 et 20240717). Au moins AC1, PM1, T5 sont publiées.
2. URL : flux Atom `https://www.geoportail-urbanisme.gouv.fr/atom/download-feed` (version filtrable `https://www.geoportail-urbanisme.gouv.fr/atom/download-feed.html`). Téléchargement par partition `https://www.geoportail-urbanisme.gouv.fr/api/document/download-by-partition/<partition>` avec la syntaxe `{idGest_}SUP_<codeGeo>_<categorie>` où codeGeo peut être 974. WMS filtré : `https://data.geopf.fr/annexes/ressources/wms-v/gpu.xml`. Avertissement « perturbations des services GPU en cours » vu sur certaines fiches.
3. Format : ZIP standard CNIG (SHP + PDF), maille polygone de servitude rattaché au gestionnaire (SIREN), plusieurs projections.
4. Licence Ouverte.
5. Gestionnaires de SUP ; millésime AAAAMMJJ dans le nom du document ; alimentation quotidienne/hebdomadaire.
6. Sonde : flux Atom (dernière entrée datée) + suffixe date de l'identifiant + Last-Modified HTTP.
7. Apport : contrainte réglementaire majeure (constructibilité, reculs, protections AC/AS/PT/I/T/PM).
8. Pièges : couverture inégale par catégorie et par commune ; inventaire catégorie par catégorie obligatoire ; certaines fiches « métadonnée non trouvée » ; perturbations de service.

### Fiche 2 — Ravines : DPF (~1 800 km) et DPE (~1 700 km), DEAL Réunion
1. Couverture 974 : oui. Couche « Domaine Public Fluvial - DPF » définie par arrêté préfectoral n°06-3077/SG/DRCTV du 21/08/2006 (gestion : arrêté 06-4709/SG/DRCTCV du 26/12/2006), construite à partir de la BD Carthage Réunion. Dans le 974 les sources et eaux souterraines appartiennent au domaine public de l'État (L.5121-1 CGPPP).
2. URL : métadonnée hébergée temporairement sur Sextant/Ifremer `https://sextant.ifremer.fr/geonetwork/srv/api/records/351ed8de-e7fd-45b4-9d55-d4bde4b0f9b8` ; page DEAL `https://www.reunion.developpement-durable.gouv.fr/domaine-public-fluvial-dpf-et-domaine-prive-de-l-a285.html` (« service en cours de mise à jour » au test). Couche annoncée « bientôt accessible sur le serveur DEAL via CARMEN ».
3. Format : vecteur linéaire (tronçons), EPSG:2975 (RGR92/UTM40S).
4. Licence Ouverte.
5. DEAL Réunion ; base 2006, schéma de délimitation mis à jour 08/09/2023.
6. Sonde : fiche GeoNetwork Sextant ; WFS DEAL.
7. Apport : DPF inaliénable/imprescriptible ; servitude de marchepied 3,25 m ; bande de 10 m du code forestier (R.174-2) sur les parcelles riveraines. Géométrie : couche DEAL, à défaut BD TOPO hydrographie / BD Carthage Réunion.
8. Pièges : hébergement instable ; limite exacte « plenissimum flumen » pas toujours géométrisée ; distinguer DPF et DPE.

### Fiche 3 — SAR de La Réunion
1. Couverture 974 : oui. SAR approuvé par décret en Conseil d'État le 22/11/2011 ; une modification approuvée ; révision « SAR 2050 » engagée.
2. URL : DEAL `https://www.reunion.developpement-durable.gouv.fr/schema-d-amenagement-regional-sar-r76.html` ; Région `https://regionreunion.com` ; Lizmap DEAL `https://deal974.lizmap.com/cartes/` ; GeoNetwork Carmen nœud 29 `http://metadata.carmencarto.fr/geonetwork/29` (à re-tester) ; « Espaces Naturels Remarquables du Littoral » aussi sur Sextant.
3. Format : zonages surfaciques ; WMS/WFS/shp ; EPSG:2975.
4. Licence Ouverte.
5. Région (élaboration) / État (approbation) ; 2011 + modification.
6. Sonde : fiche GeoNetwork Carmen/Sextant ; actualités Région.
7. Apport : cadre structurant (zones préférentielles d'urbanisation vs espaces agricoles/naturels) ; les PLU doivent être compatibles.
8. Pièges : **le SAR n'est PAS opposable aux tiers ni aux permis** (sauf dispositions valant SMVM/loi littoral) — indication schématique, jamais un zonage parcellaire. SAR 2050 : état à confirmer.

### Fiche 4 — Espaces naturels protégés (standard ENP INPN)
1. Couverture 974 : oui — Parc national (cœur + aire d'adhésion), RNN Étang Saint-Paul et Réserve marine, APB, sites classés/inscrits, Conservatoire du littoral, forêts, standard COVADIS ENP v1.
2. URL : `https://www.data.gouv.fr/datasets/inpn-donnees-du-programme-espaces-proteges` ; historique `http://inpn.mnhn.fr/isb/download/fr/maps.jsp` ; **page temporaire PatriNat** `https://www.patrinat.fr/fr/page-temporaire-de-telechargement-des-referentiels-de-donnees-lies-linpn-7353` (cyberattaque du MNHN, sites INPN inaccessibles pour une durée indéterminée) ; fiches régionalisées `https://catalogue.open-datara.fr`.
3. Format : shapefile/GeoJSON ENP v1 ; polygone par espace.
4. Licence Ouverte.
5. MNHN/PatriNat + OFB ; mise à jour au moins annuelle.
6. Sonde : fiche data.gouv ; page PatriNat.
7. Apport : inconstructibilité en cœur de parc, protections biotope, sites classés — filtre d'exclusion prioritaire.
8. Pièges : accès perturbé (passer par PatriNat) ; reprojection outre-mer ; ENS = Conseil départemental (à demander) ; Ramsar/biosphère par type.

### Fiche 5 — Géorisques pour le 974
1. Couverture : nationale, DROM inclus — SIS, CASIAS (ex-BASIAS), SSP (ex-BASOL), TRI, AZI, canalisations TMD, cavités, mouvements de terrain, sismicité, radon, RGA.
2. URL : `https://www.georisques.gouv.fr/donnees/bases-de-donnees` ; SIS `https://www.georisques.gouv.fr/donnees/bases-de-donnees/secteurs-dinformations-sur-les-sols-sis` ; CASIAS `https://www.georisques.gouv.fr/donnees/bases-de-donnees/inventaire-historique-de-sites-industriels-et-activites-de-service` (export par région) ; API et exports par département ; ERRIAL `https://errial.georisques.gouv.fr/`.
3. Format : CSV (SIS, CASIAS), GeoJSON/shp selon couche, API REST ; maille parcelle/point/polygone.
4. Licence Ouverte.
5. MTE/BRGM ; SIS mis à jour quotidiennement.
6. Sonde : API + fréquence par jeu ; Last-Modified des CSV.
7. Apport : SIS = obligation d'étude de sols au PC et d'information de l'acheteur (L125-7) ; TRI/AZI, mouvements de terrain, volcanisme pertinents à La Réunion.
8. Pièges : **RGA quasi nul à La Réunion, radon catégorie faible** — sans intérêt ; SIS non exhaustifs ; CASIAS ≠ pollution avérée.

### Fiche 6 — Zones humides de La Réunion
1. Couverture 974 : oui, trois inventaires majeurs DEAL depuis 2011 (cartographie d'habitats, échelle fine).
2. URL : `https://www.reunion.developpement-durable.gouv.fr/les-cartographies-d-habitats-a320.html` ; catalogue Carmen `https://administration.carmencarto.fr/services/catalogue/29` (bloqué aux robots) ; WFS modèle `http://ws.carmen.developpement-durable.gouv.fr/WFS/29/DEAL_REUNION_2020` (à re-tester) ; Lizmap `https://deal974.lizmap.com/cartes/`.
3. Format : WFS/shp, EPSG:2975.
4. Licence Ouverte.
5. DEAL ; inventaires 2011→2019 par secteurs.
6. Sonde : fiche Carmen ; WFS GetCapabilities.
7. Apport : loi sur l'eau, séquence ERC ; réduit fortement la constructibilité.
8. Pièges : couverture par secteurs, pas exhaustive ; habitats de zones humides ≠ zones humides réglementaires ; migration Carmen → Lizmap.

### Fiche 7 — Zonages d'assainissement
1. Documents existants (obligation légale) mais aucune couche SIG unifiée.
2. URL : par EPCI — ex. CIVIS `https://www.civis.re/index.php/telechargements-dac` ; PEIGEO `https://peigeo.re/index.php/catalogue/` (non confirmé) ; annexes PLU sur le GPU `https://data.geopf.fr`.
3. Format : PDF majoritairement.
4. Variable.
5. EPCI (CINOR, TCO, CIVIS, CASUD, CIREST) ou régies.
6. Sonde : pages EPCI ; dates de délibération.
7. Apport : raccordement collectif possible ou coût ANC.
8. Pièges : PDF, pas de standard ; vérifier les annexes sanitaires des PLU au GPU pour une version CNIG.

### Fiche 8 — Classement sonore des infrastructures de transport
1. Couverture 974 : oui — arrêtés préfectoraux des 14 et 15 décembre 2023 (révision du classement de 2014), ~682 km de routes.
2. URL : `https://www.reunion.developpement-durable.gouv.fr/3-le-classement-sonore-des-itt-et-les-a53.html` ; consultation `https://www.reunion.developpement-durable.gouv.fr/8-consultation-des-donnees-a62.html` ; cartes de bruit stratégiques WFS `http://ws.carmen.developpement-durable.gouv.fr/WFS/29/Cartes_bruit_strategiques`.
3. Format : arrêtés + tableaux + cartes PDF ; SIG interne DEAL ; cartes de bruit stratégiques en WFS/WMS (EPSG:2975). Catégories : 1 = 5,96 %, 2 = 14,01 %, 3 = 40,44 %, 4 = 35,23 %, 5 = 4,36 %.
4. Licence Ouverte.
5. DEAL/Préfet ; décembre 2023 ; cartes de bruit 2022.
6. Sonde : page DEAL ; WFS.
7. Apport : isolement acoustique obligatoire dans les secteurs affectés.
8. Pièges : géométrie fine en PDF/annexe PLU ; les cartes de bruit stratégiques ne sont pas le classement réglementaire.

### Fiche 9 — Zones de présomption de prescription archéologique (ZPPA)
1. Couverture 974 : la DAC de La Réunion gère les ZPPA — page `https://www.culture.gouv.fr/regions/dac-de-la-reunion/la-direction-des-affaires-culturelles-de-la-reunion/patrimoine-architecture-environnement/archeologie/Zones-de-presomption-de-prescription-archeologique-ZPPA`.
2. URL : Atlas des patrimoines (atlas.patrimoines.culture.fr) — couverture 974 à confirmer au téléchargement/WFS.
3. Format : shapefile / WFS.
4. Licence : libre sous mention de la source et de la date.
5. DRAC/DAC + ministère ; MAJ par arrêtés.
6. Sonde : fiche Atlas.
7. Apport : saisine préfet, diagnostic archéologique — délais/coûts.
8. Pièges : **pas une servitude** ; couverture DOM parfois incomplète.

## B. Valeur et dispositifs

### Fiche 10 — ACV / PVD / ORT et Denormandie
1. **ACV à La Réunion = Le Port, Saint-André, Saint-Joseph, Saint-Louis, Saint-Pierre** (Saint-Denis et Saint-Paul n'en font pas partie). PVD = Les Trois-Bassins, Cilaos, Salazie, Bras-Panon, La Plaine-des-Palmistes, Sainte-Rose, Saint-Philippe, Petite-Île, Entre-Deux, L'Étang-Salé, Les Avirons.
2. URL : liste ACV Région `https://data.regionreunion.com/explore/assets/listes-des-villes-action-coeur-de-ville-a-la-reunion/` ; communes ORT `https://www.data.gouv.fr/datasets/liste-des-communes-couvertes-par-des-operations-de-revitalisation-de-territoire` (CSV+XLSX, MAJ 14/05/2025) ; fiche ANCT Réunion `https://fiches.incubateur.anct.gouv.fr/fiches/territoires/région/04/`.
3. Format : CSV/XLSX commune (INSEE, EPCI, date de signature, durée, flags ACV/PVD, centroïde) — **pas de polygone**.
4. Licence Ouverte.
5. DGALN + ANCT ; liste ORT annuelle.
6. Sonde : date data.gouv ; JO annuel.
7. Apport : éligibilité Denormandie (12/18/21 %, travaux ≥ 25 %, jusqu'au 31/12/2027).
8. Pièges : ville ACV ≠ commune ORT ; périmètre Denormandie infra-communal → convention ORT de l'EPCI (PDF).

### Fiche 11 — Inventaire des ZAE (loi Climat et résilience)
1. Obligation légale (L.318-8-2, finalisation avant 24/08/2023, révision tous les 6 ans) portée par les EPCI ; publication réunionnaise non centralisée.
2. URL : sites des 5 EPCI ; offre Cerema/Banque des Territoires.
3. Format : état parcellaire (unités foncières, propriétaires, occupants, vacance) ; PDF/tableur, parfois SIG.
4. Variable.
5. EPCI.
6. Sonde : délibérations.
7. Apport : parcelles vacantes en ZAE, requalification.
8. Pièges : à demander aux EPCI ; données propriétaires (RGPD).

### Fiche 12 — Fibre à l'adresse (Arcep « Ma connexion internet »)
1. Couverture 974 : oui.
2. URL : `https://data.arcep.fr/fixe/maconnexioninternet/` (dossiers base_imb, eligibilite, fermeture_cuivre, reference, statistiques, par millésime AAAA_TX, répertoire `/last`) ; `https://www.data.gouv.fr/datasets/ma-connexion-internet` ; `https://cartefibre.arcep.fr/`.
3. Format : CSV ; maille immeuble et commune/département/région.
4. Licence Ouverte.
5. Arcep ; T1 2026 (31/03/2026, publié 11/06/2026) ; trimestriel.
6. Sonde : `/last` + année_trimestre ; data.gouv.
7. Apport : raccordabilité FttH d'un immeuble/programme.
8. Pièges : FttH fiable (IPE), autres technos déclaratives ; taux communal = estimation.

### Fiche 13 — Fichier REI de la DGFiP
1. Couverture : nationale, DROM inclus, maille commune.
2. URL : `https://www.data.gouv.fr/datasets/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-directe-locale-rei-4` ; source `https://data.economie.gouv.fr/explore/dataset/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-dir/` (depuis 2009).
3. Format : CSV commune.
4. Licence Ouverte.
5. DGFiP ; annuel.
6. Sonde : date data.economie.gouv.fr.
7. Apport : taux TFPB (commune + interco), bases, TEOM, IFER, TSE.
8. Pièges : impositions primitives ; **la taxe d'aménagement n'y est pas** ; libellés techniques.

### Fiche 14 — Demande de logement social (SNE)
1. Maille EPCI/département ; pas de commune en open data. ~44 500 familles en demande au 31/12/2023 (CDHH Réunion, mars 2024).
2. URL : `https://www.data.gouv.fr/datasets/demande-de-logement-social` ; `data.logement.gouv.fr`.
3. Format : CSV EPCI, **sans code officiel géographique**.
4. Licence Ouverte.
5. GIP SNE ; annuel.
6. Sonde : millésime data.logement.gouv.fr.
7. Apport : tension de la demande (PLAI/PLUS/PLS).
8. Pièges : recodage COG manuel ; granularité EPCI.

### Fiche 15 — Observatoire local des loyers (ADIL Réunion)
1. ADIL agréée OLL par arrêté du 28/08/2024 ; couverture départementale. Loyer médian 2024 : 10,90 €/m² hors charges (12,70 Ouest, 11,90 Saint-Denis, 9,20 Est).
2. URL : `https://www.observatoires-des-loyers.org/connaitre-les-loyers/carte-des-niveaux-de-loyers/ile-de-la-reunion` ; `https://www.adil974.com` ; plaquette `https://www.agorah.com/upload/habitat/Plaquette-Observatoire-Loyers-Prives-v-2025-light.pdf`.
3. Format : PDF + données agrégées CSV (réseau OLL, data.gouv).
4. Agrégées ouvertes ; micro-données restreintes.
5. ADIL + AGORAH ; résultats 2024 ; annuel.
6. Sonde : page réseau OLL ; plaquette annuelle.
7. Apport : valeur locative par type/surface/localisation.
8. Pièges : historiquement limité à Saint-Denis avant 2024 ; agrégé seulement ; encadrement IRL depuis le décret du 25/08/2023.

### Fiche 16 — OPAH et PIG
1. Dispositifs actifs (ex. PILHI CIREST) sans périmètre polygone ouvert.
2. URL : `https://www.anah.gouv.fr/collectivites/support/cartographie` ; `https://www.data.gouv.fr/reuses/operations-programmees-anah-votre-commune-est-elle-couverte`.
3. Format : localisation commune/point ; périmètre exact = convention Anah/EPCI (PDF).
4. Licence Ouverte (carto Anah).
5. Anah + EPCI.
6. Sonde : carto Anah.
7. Apport : subventions Anah dans le périmètre.
8. Pièges : pas de polygone ; conventions EPCI.

### Fiche 17 — Périmètres de ZAC
1. Pas de couche « ZAC 974 » fiable en open data.
2. URL : `https://www.data.gouv.fr/datasets/zones-damenagement-concerte-zac-respectant-le-standard-du-cnig` (couverture 974 non confirmée) ; PEIGEO acquisitions EPFR `https://peigeo.re/index.php/cartostat/visualiseurs-thematiques/acquisition-retrocession-epfr/` ; `https://epf.re/` ; annexes PLU au GPU.
3. Format : shp CNIG si disponible, sinon PDF.
4. Variable.
5. Communes/EPCI ; EPF Réunion.
6. Sonde : GPU ; délibérations.
7. Apport : aménagements en cours.
8. Pièges : à reconstituer ; EPFR ≠ référentiel ZAC.

## C. Propriété

### Fiche 18 — Documents de filiation informatisés (DFI)
1. Couverture : fichiers départementaux, DROM inclus (extraction Guyane existante → 974 disponible).
2. URL : `https://www.data.gouv.fr/datasets/agregation-des-fichiers-de-documents-de-filiation-informatises-dfi-des-parcelles` ; `https://data.economie.gouv.fr/explore/dataset/documents-de-filiation-informatises-dfi-des-parcelles/` (+ descriptif PDF) ; `https://www.data.gouv.fr/datasets/historique-des-parcelles-cadastrales-filiation`.
3. Format : CSV ; parcelle mère → fille ; id dép+commune+section+n°DFI+lot.
4. Licence Ouverte.
5. DGFiP ; **trimestriel**.
6. Sonde : date data.economie.gouv.fr.
7. Apport : divisions/remembrements récents ; généalogie d'une parcelle ; rattachement des permis orphelins.
8. Pièges : modifications depuis l'informatisation seulement (1980-1990) ; exclut les aménagements fonciers ruraux ; géomètre anonymisé.

### Fiche 19 — Cerema : fichiers fonciers, LOVAC, DV3F
1. Nationale, DROM inclus, **sous convention**.
2. URL : `https://datafoncier.cerema.fr/fichiers-fonciers` ; `https://datafoncier.cerema.fr/actualites/portail-donnees-foncieres-ouvert` (Portail Données Foncières depuis 01/10/2024) ; `https://datafoncier.cerema.fr/actualites/millesime-2025-lovac-disponible`.
3. Format : PostgreSQL (28 tables) / CSV ; parcelle/local.
4. CGU restreintes ; pas de re-diffusion ; pas de ré-identification.
5. Cerema ; FF 2024, DV3F 2024-2, LOVAC 2025 ; FF annuel, DV3F semestriel.
6. Sonde : actualités Datafoncier.
7. Apport : propriétaires, locaux, vacance, transactions enrichies.
8. **Pièges : LOVAC détail réservé aux collectivités, services de l'État, Anah et leurs prestataires désignés — un éditeur privé n'y a pas accès en propre** ; FF/DV3F sous convention ; délai médian 27 jours ; guichet = Portail Données Foncières ; passer par une collectivité mandante, sinon DVF ouvert + MAJIC + DFI.

## D. Catalogues

### Fiche 20 — PEIGEO (AGORAH) et open data Région Réunion
1. Plateformes régionales dédiées.
2. URL : `https://peigeo.re/`, `https://peigeo.re/index.php/catalogue/` ; `https://data.regionreunion.com/explore/` ; Lizmap DEAL `https://deal974.lizmap.com/cartes/` (EPSG:2975, WMS 1.3.0 / WMTS / WFS 1.0.0).
3. Format : WMS/WFS, CSV, GeoJSON/shp ; EPSG:2975.
4. Licence Ouverte / ODbL ; PEIGEO : accès pro sous charte pour certaines données.
5. AGORAH (PEIGEO depuis 2013) ; Région.
6. Sonde : fiches GeoNetwork ; API Opendatasoft `data.regionreunion.com/api/`.
7. Jeux utiles : **DVF Réunion** `/explore/dataset/demande-de-valeurs-foncierespublic/`, **potentiel foncier** `/explore/dataset/potentiel-foncier/` (îlots non urbanisés — estimation), liste ACV, cadastre solaire `https://la-reunion.cadastre-solaire.fr/` ; PEIGEO : zones d'activités, acquisitions EPFR, visualiseur PLU+PPR ; Lizmap DEAL : projets, risques, QPV, bruit.
8. Pièges : PEIGEO mélange ouvert et réservé ; certains jeux visualisables sans téléchargement ; potentiel foncier = estimation ; DEAL a migré de Carmen (nœud 29) vers Lizmap — vérifier l'obsolescence des WFS Carmen.

## Ordre proposé

Lot 1 (contraintes) : SUP GPU · Géorisques SIS/CASIAS/TRI/AZI · INPN ENP · SAR + DPF/DPE · zones humides, classement sonore, ZPPA.
Lot 2 (valeur) : REI · Arcep · DFI · ACV/PVD/ORT · OLL · SNE · OPAH/PIG · Cerema (engager tôt).

## À demander à la Région / AGORAH-PEIGEO / EPCI
Zonages d'assainissement · inventaires ZAE · périmètres ORT infra-communaux · OPAH/PIG et ZAC · micro-données OLL et SNE commune · état SAR 2050 et couches SAR.

## Réserves
URLs à valider avant ingestion : WFS Carmen nœud 29 (probablement migré Lizmap) ; couche ZPPA 974 sur l'Atlas ; couche assainissement PEIGEO. Accès perturbés au test : INPN (PatriNat), page DPF/DPE DEAL, GPU. Restrictions : LOVAC, FF/DV3F, micro-données OLL. Non opposables : SAR, ZPPA. Fiabilité variable : Arcep hors FttH, SIS/CASIAS, potentiel foncier Région.
