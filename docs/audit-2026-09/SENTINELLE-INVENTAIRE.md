# SENTINELLE-INVENTAIRE — les 64 sources, une par une (SENTINELLE-3)

> **Fichier GÉNÉRÉ** — ne pas éditer à la main. Régénéré depuis le catalogue (`seed_sources.SOURCES`) croisé avec `sentinelle.SEED` / `RAPPELS_MANUELS` / `RAISONS_NON_SURVEILLEES` / `DOUBLONS_COUVERTS` par `labuse sentinelle-inventaire`. Ce qui est ici EST l'état du code.

**Vérification réelle** : chaque URL de veille ci-dessous a été APPELÉE POUR DE VRAI (couche `_http` de production, UA `LABUSE-sentinelle/1.0`), sa réponse LUE, et la sonde a renvoyé **`ok`** — le 2026-09-01. Aucune URL supposée. Une candidate qui échouait au semis n'est pas inscrite (elle figure en « non surveillée » avec ce qui a été essayé, cf. `RAISONS_NON_SURVEILLEES`).

**Bilan** : **40 surveillées** · 4 rappels manuels (Y4) · 2 doublons couverts par leur canonique · 22 non surveillées = **64**.

## Ventilation des surveillées par méthode

| Méthode | N | Nature |
|---|---|---|
| `api` | 32 | version détectable |
| `page` | 1 | version détectable |
| `entete` | 2 | changement détectable |
| `temoin` | 5 | changement détectable (requête témoin) |
| **Total** | **40** | |

## Ventilation par fournisseur

| Fournisseur | Surveillées | Rappel manuel | Non surveillées | Doublons |
|---|---|---|---|---|
| ADEME | 1 | 0 | 0 | 0 |
| AGORAH | 0 | 0 | 1 | 0 |
| ANCT (Agence nationale cohésion des territoires) | 1 | 0 | 0 | 0 |
| AOM Réunion (Région, CINOR, TCO, CIVIS, CIREST, CASUD) via transport.data.gouv.fr | 1 | 0 | 0 | 0 |
| BRGM | 5 | 0 | 0 | 0 |
| Base Mérimée (Ministère Culture) | 1 | 0 | 0 | 0 |
| CE | 0 | 0 | 1 | 0 |
| Cerema | 2 | 0 | 0 | 0 |
| Cerema (Cartagène) | 1 | 0 | 0 | 0 |
| DAAF (propre non public) · proxy RPG | 1 | 0 | 0 | 0 |
| DEAL Réunion | 0 | 0 | 1 | 0 |
| DEAL Réunion (Lizmap) | 1 | 0 | 1 | 0 |
| DGFiP | 2 | 1 | 0 | 1 |
| DILA (Opendatasoft) | 1 | 0 | 0 | 0 |
| DINUM | 1 | 0 | 0 | 0 |
| DINUM (api.gouv.fr) | 0 | 0 | 1 | 0 |
| EPCI | 0 | 1 | 0 | 0 |
| IGN | 9 | 0 | 4 | 1 |
| IGN (Géoportail de l'urbanisme) | 0 | 0 | 1 | 0 |
| INPI (Registre National des Entreprises) | 0 | 0 | 1 | 0 |
| INPN | 2 | 0 | 1 | 0 |
| INSEE | 5 | 0 | 0 | 0 |
| INSEE (RP) | 0 | 0 | 1 | 0 |
| LABUSE | 0 | 1 | 0 | 0 |
| Légifrance | 0 | 0 | 2 | 0 |
| ONF | 1 | 0 | 0 | 0 |
| OSM | 0 | 0 | 1 | 0 |
| Office de l'eau Réunion | 0 | 1 | 0 | 0 |
| OpenStreetMap | 0 | 0 | 2 | 0 |
| Région Réunion | 1 | 0 | 0 | 0 |
| Région Réunion (Opendatasoft) | 2 | 0 | 0 | 0 |
| Région Réunion (Système d'Information Routier) | 1 | 0 | 0 | 0 |
| SDES (Dido) | 1 | 0 | 0 | 0 |

## Les quatre natures (Y5.4)

- **version détectable** (`api`, `page`) — on lit un millésime comparable ; l'alerte le nomme.
- **changement détectable** (`entete`, `temoin`) — pas de version lisible ; l'alerte dit « la donnée amont a changé » (en-tête de fichier, ou empreinte d'une requête témoin figée).
- **rappel manuel** (Y4) — source saisie à la main, aucun amont ; rappel de rafraîchissement au-delà de la cadence attendue (ce n'est pas une sonde).
- **non surveillable** — aucune sonde possible ; la raison précise ce qui a été essayé.

## Inventaire complet — par fournisseur

### ADEME

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| DPE ADEME (logements existants) | — | SURVEILLÉE · `api` | https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant  (sél. `dataUpdatedAt`) |

### AGORAH

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| PEIGEO (hub régional) | — | non surveillée | Y2 : peigeo.re répond désormais (200) mais c'est un site WordPress — plus de GeoNetwork/CSW ni d'API de catalogue à sonder (les chemins /geonetwork renvoient 404). Pas un jeu unique. |

### ANCT (Agence nationale cohésion des territoires)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| QPV 2024 (ANCT) | génération 2024 | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/quartiers-prioritaires-de-la-politique-de-la-ville-qpv/  (sél. `last_update`) |

### AOM Réunion (Région, CINOR, TCO, CIVIS, CIREST, CASUD) via transport.data.gouv.fr

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Transport public — GTFS (PAN, 7 réseaux) | 7 jeux PAN, màj 2025-12-29 → 2026-08-17 | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/horaire-du-reseau-citalis/  (sél. `last_update`) |

### BRGM

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Géorisques | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/base-nationale-de-gestion-assistee-des-procedures-administratives-relatives-aux-risques-gaspar/  (sél. `last_update`) |
| Géorisques — cavités souterraines | — | SURVEILLÉE · `temoin` | https://www.georisques.gouv.fr/api/v1/cavites?code_insee=97411&page=1&page_size=1  (sél. `results`) |
| Géorisques — ICPE | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/installations-classees-pour-la-protection-de-lenvironnement-icpe-france-metropolitaine-et-drom-3/  (sél. `last_update`) |
| Géorisques — mouvements de terrain | — | SURVEILLÉE · `temoin` | https://www.georisques.gouv.fr/api/v1/mvt?code_insee=97411&page=1&page_size=1  (sél. `results`) |
| Géorisques — sites et sols pollués | — | SURVEILLÉE · `temoin` | https://www.georisques.gouv.fr/api/v1/ssp?code_insee=97411&page=1&page_size=200 |

### Base Mérimée (Ministère Culture)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| ABF / Monuments historiques | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/immeubles-proteges-au-titre-des-monuments-historiques-2/  (sél. `last_update`) |

### CE

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| PVGIS (Commission européenne) | PVGIS v5.3 · modèle SARAH3 (relevé au run du builder solaire) | non surveillée | API de CALCUL (v5.3 dans l'URL) — pas de jeu à millésime, le service ne versionne pas de données à comparer ; aucune requête témoin actionnable (réponse dérivée d'un modèle, pas d'une donnée ingérée). |

### Cerema

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Cartofriches (Cerema) | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/cartofriches/  (sél. `last_update`) |
| Cerema / GéoLittoral — indicateur d'érosion côtière | millésime 2018 | SURVEILLÉE · `entete` | https://geolittoral.din.developpement-durable.gouv.fr/telechargement/couches_sig/N_evolution_trait_cote_S_reunion_epsg2975_062018_shape.zip |

### Cerema (Cartagène)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Classement sonore ITT (Cerema) | arrêtés déc. 2023 | SURVEILLÉE · `api` | https://cartagene.cerema.fr/server/rest/services/Hosted/Routes_classement_sonore_La_Reunion_V2/FeatureServer/0/query?where=1%3D1&returnCountOnly=true&f=json  (sél. `count`) |

### DAAF (propre non public) · proxy RPG

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| RPG — déclarations agricoles (IGN/ASP) | proxy RPG (IGN) — RPG.LATEST, année non pinnée | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/rpg/  (sél. `last_update`) |

### DEAL Réunion

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| DEAL Réunion (WMS/WFS) | NPNRU — QP génération 2024 (DEAL/ANCT) | non surveillée | Y1 : hôte carto DEAL (deal974.lizmap.com) de nouveau joignable mais sans URL amont datée ; le seul jeu data.gouv « NPNRU » est DÉPARTEMENTAL (Bouches-du-Rhône), pas Réunion → inscrire son `last_update` serait une fausse veille. La couche QP génération 2024 servie ici est, elle, déjà couverte par « QPV 2024 (ANCT) ». |

### DEAL Réunion (Lizmap)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| 50 pas géométriques — limite haute (DEAL) | cadastre 1877 (géoréf. 2012/1950) | non surveillée | Y1 : WFS Lizmap DEAL de nouveau joignable mais sans projet/date lisible ; 0 jeu data.gouv (« 50 pas », « pas géométriques »). Limite domaniale dérivée du cadastre 1877 géoréférencé — donnée quasi statique, aucun millésime ni empreinte amont. |
| DEAL Réunion — PPR / aléas | PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Lizmap) | SURVEILLÉE · `temoin` | https://georisques.gouv.fr/api/v1/gaspar/pprn?codeInsee=97411&page=1&page_size=50  (sél. `content`) |

### DGFiP

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Cadastre Etalab (bulk DGFiP/Etalab) | Etalab cadastre — « latest » ingérée (DGFiP) | DOUBLON couvert | amont identique à « Cadastre (API Carto PCI) » (une seule veille, l'alerte vaut pour les deux) |
| DGFiP — parcelles des personnes morales | Panel millésimes 2019→2025 (situation 1ᵉʳ janvier) | SURVEILLÉE · `entete` | https://data.economie.gouv.fr/api/v2/catalog/datasets/fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/fichier_des_parcelles_situation_2025_dpts_57_a_976_zip |
| DVF / valeurs foncières | géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020 | SURVEILLÉE · `page` | https://files.data.gouv.fr/geo-dvf/latest/csv/  (sél. `20\d{2}`) |
| Fichiers fonciers (Cerema) | — | rappel manuel · cadence 365 j | Rappel de rafraîchissement — cadence attendue 365 j (aucune sonde amont : source saisie à la main). Sous convention, non ingérée en libre — aucune URL amont publique. Y4 : rappel de rafraîchissement posé (échéance de convention à porter si connue). |

### DILA (Opendatasoft)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| BODACC (procédures collectives) | — | SURVEILLÉE · `api` | https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales  (sél. `metas.default.modified`) |

### DINUM

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Base Adresse Nationale | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/base-adresse-nationale/  (sél. `last_update`) |

### DINUM (api.gouv.fr)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Recherche d'entreprises (DINUM) | Sirene INSEE / RNE INPI (api.gouv.fr) — courant | non surveillée | Y3 : requête témoin `?departement=974` testée → `total_results` plafonné à 10000 (non exploitable) ; agrégat Sirene/RNE en direct, déjà couvert par la veille SIRENE (data.gouv). |

### EPCI

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| VRD / assainissement (SPANC) | — | rappel manuel · cadence 365 j | Rappel de rafraîchissement — cadence attendue 365 j (aucune sonde amont : source saisie à la main). Champ manuel EPCI — aucune donnée ouverte fine, pas d'URL amont. Y4 : rappel de rafraîchissement posé. |

### IGN

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| BD ORTHO 20 cm (IGN) | BD ORTHO IGN 974 — millésime 2025 (piscine, 90,7 %) | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/bd-ortho-r/  (sél. `last_update`) |
| BD ORTHO IRC (IGN) | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/bd-ortho-r/  (sél. `last_update`) |
| BD TOPO IGN | BD TOPO® V3 (IGN) — édition non enregistrée | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/bd-topo-r/  (sél. `last_update`) |
| Cadastre (API Carto PCI) | PCI Parcellaire Express (DGFiP) — « latest » ingérée | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/parcellaire-express-pci/  (sél. `last_update`) |
| Contours IRIS (IGN/INSEE) | Contours IRIS — géographie 2024 (IGN/INSEE) | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/contours-iris/  (sél. `last_update`) |
| CoSIA (couverture du sol IA, IGN) | CoSIA 2025 (PVA juil.-août 2025, 20 cm) | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/cosia/  (sél. `last_update`) |
| GPU — zonages d'assainissement | GPU — idurba par commune ; SIG 4/24 au 11/07/2026 | non surveillée | API Carto GPU par géométrie (mêmes limites que « Urbanisme PLU/GPU » : pas de millésime global, interrogé en direct sans snapshot ingéré). |
| GPU — zonages d'assainissement (info-surf typeinf 19) | GPU — idurba par commune ; SIG 4/24 au 11/07/2026 | non surveillée | Doublon du GPU assainissement (canal info-surf) — même amont, non re-surveillé. |
| Géoplateforme IGN | — | non surveillée | Y2 : GetCapabilities WFS `data.geopf.fr` répond (200) mais SANS attribut `updateSequence` ni date, et le catalogue n'est pas exposé en JSON. Hub — les produits IGN servis sont surveillés individuellement (data.gouv `last_update`). |
| IGN BD CARTO V5 — occupation du sol | BD CARTO® V5 — occupation du sol (IGN, proxy) | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/bd-carto-r-1/  (sél. `last_update`) |
| LiDAR HD — MNH 50 cm (IGN) | LiDAR HD MNH — dalles publiées 25/06/2025 (IGN) | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/mnh-lidar-hd/  (sél. `last_update`) |
| RGE ALTI (altimétrie) | RGE ALTI® (IGN) — édition non enregistrée | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/rge-alti-r/  (sél. `last_update`) |
| RGE ALTI 5 m (IGN) | RGE ALTI® 5 m (IGN) — édition non enregistrée | DOUBLON couvert | amont identique à « RGE ALTI (altimétrie) » (une seule veille, l'alerte vaut pour les deux) |
| Urbanisme PLU/GPU (API Carto) | GPU/PLU par commune (révisions — détail en fiche) | non surveillée | API Carto GPU interrogée par géométrie à l'usage. Y3 : le point d'entrée `/municipality` ne porte aucun millésime (gid/insee/is_rnu seulement), `/document` exige une géométrie, aucun jeu data.gouv « documents GPU » à `last_update` ; un témoin par parcelle détecterait un changement de PLU commune par commune, mais LABUSE interroge le GPU EN DIRECT (aucun snapshot ingéré à réinjecter). |

### IGN (Géoportail de l'urbanisme)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| SUP — assiettes GPU (API Carto) | — | non surveillée | API Carto GPU (assiette-sup-s) par géométrie — pas de millésime global lisible ; interrogé en direct. |

### INPI (Registre National des Entreprises)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| INPI RNE (dirigeants) | — | non surveillée | API AUTHENTIFIÉE interrogée par SIREN (pas de requête témoin publique possible) — aucun millésime global à comparer. |

### INPN

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| INPN / patrinat — espaces protégés | INPN/patrinat espaces protégés — passe 05/07/2026 | non surveillée | Couches patrinat servies en WFS Géoplateforme ; pas de jeu data.gouv national « espaces protégés » à millésime trouvé, ni de requête témoin à agrégat stable. |
| Parc National de La Réunion (INPN) | millésime 2021 | SURVEILLÉE · `api` | https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/pnrun_2021  (sél. `metas.default.modified`) |
| ZNIEFF (INPN/MNHN) | INPN, mise à jour 29/08/2025 | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/inventaire-des-zones-naturelles-dinteret-ecologique-faunistique-et-floristique-znieff/  (sél. `last_update`) |

### INSEE

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| BPE INSEE | millésime 2025 (géographie au 01/01/2025) | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/base-permanente-des-equipements-3/  (sél. `last_update`) |
| Filosofi INSEE (carreaux 200 m) | millésime 2021 | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/donnees-carroyees-a-200-m-sur-la-population/  (sél. `last_update`) |
| INSEE RP2022 — fichier détail Logements (EGOUL) | RP2022 — fichier détail Logements, publié le 16/10/2025 (INSEE) | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/recensement-de-la-population-fichiers-detail-logements-ordinaires/  (sél. `last_update`) |
| SIRENE | Sirene INSEE — état courant (non versionné) | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/  (sél. `last_update`) |
| SIRENE établissements géolocalisés | SIRENE géolocalisé — publication mensuelle INSEE | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques/  (sél. `last_update`) |

### INSEE (RP)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| MOBPRO (mobilités domicile-travail, INSEE) | MOBPRO INSEE — fichier détail (millésime RP) | non surveillée | Import CSV manuel ABANDONNÉ pour l'étude de zone — pas d'URL de version stable, et pas de rafraîchissement attendu (aucun rappel Y4). |

### LABUSE

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Radar (pige d'annonces) | Collecte manuelle — biens en vente (faits + lien) | rappel manuel · cadence 7 j | Rappel de rafraîchissement — cadence attendue 7 j (aucune sonde amont : source saisie à la main). Collecte 100 % humaine — non surveillable par nature (aucun amont public). Y4 : rappel de rafraîchissement posé (cadence attendue). |

### Légifrance

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| FRR ex-ZRR — zone spéciale d'action rurale (Légifrance) | ZSAR 1978 · FRR 01/07/2024 · réf. ZRR 2017 (Région) | non surveillée | Y1 : les jeux data.gouv « FRR » trouvés sont DÉPARTEMENTAUX (Charente, Corrèze, Nièvre), aucun national ni Réunion ; la page JORF n'a ni ETag ni Last-Modified et son HTML n'est pas déterministe → ni `entete` ni `page` fiable. |
| ZFANG — zone franche d'activité nouvelle génération (Légifrance) | Décret n° 2026-421 du 29 mai 2026 (LF 2026, art. 18) | non surveillée | Y1 : 0 jeu data.gouv (ZFANG/zone franche outre-mer) ; la page JORF n'a ni ETag ni Last-Modified (Cache-Control no-store → `entete` illisible) et son HTML n'est pas déterministe (jetons dynamiques) → `page` non fiable ; un texte modifié reçoit un nouvel identifiant JORFTEXT. |

### ONF

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Forêts publiques (ONF) | BD TOPO® V3 — forêt publique (IGN) | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/bd-topo-r/  (sél. `last_update`) |

### OSM

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| OpenStreetMap / Overpass | — | non surveillée | Y3 : témoin de comptage testé (Overpass `out count`) → stable localement mais OSM est un flux continu (planet) et LABUSE l'interroge EN DIRECT (aucun snapshot ingéré) ; un compte sur zone stable ne représente pas l'île et n'est pas actionnable. |

### Office de l'eau Réunion

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Office de l'eau Réunion — Chroniques de l'eau | Chronique n°149 — données 2023 | rappel manuel · cadence 365 j | Rappel de rafraîchissement — cadence attendue 365 j (aucune sonde amont : source saisie à la main). Seed CSV extrait à la main d'un PDF (chronique numérotée) — chaque édition = nouvelle URL, non surveillable proprement. Y4 : rappel de rafraîchissement posé. |

### OpenStreetMap

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| OSM — transport (pôles d'échange & téléphérique) | extraction Overpass (base OSM vivante, ODbL) | non surveillée | OSM en flux continu, interrogé en direct (cf. « OpenStreetMap / Overpass ») — témoin de comptage non représentatif ni actionnable. |
| Parkings OSM (loi APER) | — | non surveillée | OSM en flux continu, interrogé en direct (cf. « OpenStreetMap / Overpass ») — témoin de comptage non représentatif ni actionnable. |

### Région Réunion

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Potentiel foncier Région (Région ODS) | — | SURVEILLÉE · `api` | https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/potentiel-foncier  (sél. `metas.default.modified`) |

### Région Réunion (Opendatasoft)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| data.regionreunion.com — Potentiel foncier | — | SURVEILLÉE · `api` | https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/potentiel-foncier  (sél. `metas.default.modified`) |
| Région Réunion Open Data (Opendatasoft) | — | SURVEILLÉE · `temoin` | https://data.regionreunion.com/api/explore/v2.1/catalog/datasets?limit=0  (sél. `total_count`) |

### Région Réunion (Système d'Information Routier)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Trafic RN (Région Réunion — SIR) | Trafic RN Région — comptages 1992–2023 | SURVEILLÉE · `api` | https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/trafic-mja-rn-lareunion  (sél. `metas.default.modified`) |

### SDES (Dido)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| SITADEL (autorisations d'urbanisme) | 2026-06 | SURVEILLÉE · `api` | https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datasets/6513f0189d7d312c80ec5b5b  (sél. `last_update`) |
