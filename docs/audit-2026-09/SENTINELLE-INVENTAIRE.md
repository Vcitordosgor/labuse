# SENTINELLE-INVENTAIRE — les 64 sources, une par une (SENTINELLE-2)

**Vérification réelle** : chaque URL de veille ci-dessous a été APPELÉE POUR DE VRAI via la couche `_http` de production (UA `LABUSE-sentinelle/1.0`), sa réponse LUE, et la sonde a renvoyé **`ok`** — le 2026-09-01. Aucune URL supposée. Une candidate qui échouait au semis n'a pas été inscrite (elle figure en « non surveillée » avec ce qui a été essayé).

**Bilan** : **35 surveillées** · 2 doublons couverts par leur canonique · 27 non surveillées = **64**.

## X3.1 — ventilation des surveillées par méthode

| Méthode | N | Détail |
|---|---|---|
| `api` | 32 | data.gouv `last_update`, Opendatasoft `metas.default.modified`, data-fair `dataUpdatedAt`, Dido `last_update`, ArcGIS `count` témoin |
| `page` | 1 | DVF (index géo-DVF, regex millésime — cas phare) |
| `entete` | 2 | téléchargements directs stables (ETag/Last-Modified) : cadastre, DGFiP-PM, érosion |
| **Total** | **35** | |

## X3.1 — ventilation par fournisseur

| Fournisseur | Surveillées | Non surveillées | Doublons |
|---|---|---|---|
| ADEME | 1 | 0 | 0 |
| ANCT | 1 | 0 | 0 |
| Autres | 0 | 3 | 0 |
| Cerema | 3 | 0 | 0 |
| DEAL Réunion | 0 | 3 | 0 |
| DGFiP / Etalab | 2 | 1 | 1 |
| Géorisques (BRGM) | 2 | 3 | 0 |
| IGN / Géoplateforme | 12 | 5 | 1 |
| INPN / Culture | 2 | 1 | 0 |
| INSEE | 5 | 1 | 0 |
| Légifrance | 0 | 1 | 0 |
| Manuel / interne | 0 | 2 | 0 |
| OpenStreetMap | 0 | 3 | 0 |
| Région Réunion / ODS / DILA | 6 | 2 | 0 |
| SDES / Sitadel | 1 | 0 | 0 |
| SIRENE / entreprises | 0 | 2 | 0 |

## Familles débloquées d'un coup (gisement principal, X1/X2)

- **IGN / Géoplateforme** : le jeu data.gouv officiel de chaque produit expose `last_update` — une clé qui débloque 10 sources servies en WFS (PCI, BD TOPO, Forêts=BDTOPO forêt publique, BD ORTHO + IRC, RGE ALTI, BD CARTO, LiDAR MNH, Contours IRIS, RPG) d'un seul mécanisme.
- **data.gouv.fr en général** : `/api/1/datasets/{slug}` → `last_update` couvre aussi INSEE (BPE, Filosofi, RP2022), ANCT (QPV), Cerema (Cartofriches), INPN (ZNIEFF), Culture (MH/ABF), BRGM (Géorisques gaspar + ICPE), DINUM (BAN, SIRENE, SIRENE géoloc), transport (GTFS), IGN (CoSIA).
- **Opendatasoft v2.1** : `/catalog/datasets/{ds}` → `metas.default.modified` couvre la Région Réunion (Parc National, Potentiel foncier ×2, Trafic RN) et la DILA (BODACC — dont le chemin JSON de SENTINELLE-1 était FAUX, corrigé ici).

## Inventaire complet — par fournisseur

### ADEME

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| DPE ADEME (logements existants) | — | SURVEILLÉE · `api` | https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant  (sél. `dataUpdatedAt`) |

### ANCT

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| QPV 2024 (ANCT) | génération 2024 | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/quartiers-prioritaires-de-la-politique-de-la-ville-qpv/  (sél. `last_update`) |

### Autres

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Office de l'eau Réunion — Chroniques de l'eau | — | non surveillée | Seed CSV extrait à la main d'un PDF (chronique numérotée) — chaque édition = nouvelle URL, non surveillable proprement. |
| PEIGEO (hub régional) | — | non surveillée | Hub AGORAH injoignable depuis l'infra (HTTP 000) — pas de jeu unique à sonder. |
| PVGIS (Commission européenne) | PVGIS v5.3 · modèle SARAH3 (relevé | non surveillée | API de calcul (v5.3 dans l'URL) — pas de jeu à millésime ; le service ne versionne pas de données à comparer. |

### Cerema

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Cartofriches (Cerema) | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/cartofriches/  (sél. `last_update`) |
| Cerema / GéoLittoral — indicateur d'érosion côtière | millésime 2018 | SURVEILLÉE · `entete` | https://geolittoral.din.developpement-durable.gouv.fr/telechargement/couches_sig/N_evolution_trait_cote_S_reunion_epsg2975_062018_shape.zip |
| Classement sonore ITT (Cerema) | arrêtés déc. 2023 | SURVEILLÉE · `api` | https://cartagene.cerema.fr/server/rest/services/Hosted/Routes_classement_sonore_La_Reunion_V2/FeatureServer/0/query?where=1%3D1&returnCountOnly=true&f=json  (sél. `count`) |

### DEAL Réunion

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| 50 pas géométriques — limite haute (DEAL) | cadastre 1877 (géoréf. 2012/1950) | non surveillée | WFS Lizmap DEAL (requête) — pas de millésime lisible. |
| DEAL Réunion (WMS/WFS) | NPNRU — QP génération 2024 (DEAL/A | non surveillée | Hôte carto DEAL injoignable (servi par proxys) — aucune URL amont stable. |
| DEAL Réunion — PPR / aléas | PPR/PPRL approuvés 2011–2026 (arrê | non surveillée | WFS Lizmap DEAL (requête) — pas de millésime lisible ; hôte souvent indisponible. |

### DGFiP / Etalab

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| DGFiP — parcelles des personnes morales | Panel millésimes 2019→2025 (situat | SURVEILLÉE · `entete` | https://data.economie.gouv.fr/api/v2/catalog/datasets/fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/fichier_des_parcelles_situation_2025_dpts_57_a_976_zip |
| DVF / valeurs foncières | — | SURVEILLÉE · `page` | https://files.data.gouv.fr/geo-dvf/latest/csv/  (sél. `20\d{2}`) |
| Cadastre Etalab (bulk DGFiP/Etalab) | Etalab cadastre — « latest » ingér | DOUBLON couvert | amont identique à « Cadastre (API Carto PCI) » (une seule veille, l'alerte vaut pour les deux) |
| Fichiers fonciers (Cerema) | — | non surveillée | Sous convention, non ingérée — aucune URL amont publique. |

### Géorisques (BRGM)

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Géorisques | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/base-nationale-de-gestion-assistee-des-procedures-administratives-relatives-aux-risques-gaspar/  (sél. `last_update`) |
| Géorisques — ICPE | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/installations-classees-pour-la-protection-de-lenvironnement-icpe-france-metropolitaine-et-drom-3/  (sél. `last_update`) |
| Géorisques — cavités souterraines | — | non surveillée | Base BRGM cavités servie par l'API Géorisques live ; pas de jeu data.gouv national à millésime trouvé. |
| Géorisques — mouvements de terrain | — | non surveillée | Base BRGM BDMvt servie par l'API Géorisques live ; pas de jeu data.gouv national à millésime trouvé. |
| Géorisques — sites et sols pollués | — | non surveillée | Bases BRGM (BASIAS/BASOL/SIS) servies par l'API Géorisques live ; pas de jeu data.gouv national à millésime trouvé. |

### IGN / Géoplateforme

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| BD ORTHO 20 cm (IGN) | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/bd-ortho-r/  (sél. `last_update`) |
| BD ORTHO IRC (IGN) | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/bd-ortho-r/  (sél. `last_update`) |
| BD TOPO IGN | BD TOPO® V3 (IGN) — édition non en | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/bd-topo-r/  (sél. `last_update`) |
| Base Adresse Nationale | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/base-adresse-nationale/  (sél. `last_update`) |
| Cadastre (API Carto PCI) | PCI Parcellaire Express (DGFiP) —  | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/parcellaire-express-pci/  (sél. `last_update`) |
| CoSIA (couverture du sol IA, IGN) | CoSIA 2025 (PVA juil.-août 2025, 2 | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/cosia/  (sél. `last_update`) |
| Contours IRIS (IGN/INSEE) | Contours IRIS — géographie 2024 (I | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/contours-iris/  (sél. `last_update`) |
| Forêts publiques (ONF) | BD TOPO® V3 — forêt publique (IGN) | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/bd-topo-r/  (sél. `last_update`) |
| IGN BD CARTO V5 — occupation du sol | BD CARTO® V5 — occupation du sol ( | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/bd-carto-r-1/  (sél. `last_update`) |
| LiDAR HD — MNH 50 cm (IGN) | LiDAR HD MNH — dalles publiées 25/ | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/mnh-lidar-hd/  (sél. `last_update`) |
| RGE ALTI (altimétrie) | RGE ALTI® (IGN) — édition non enre | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/rge-alti-r/  (sél. `last_update`) |
| RPG — déclarations agricoles (IGN/ASP) | proxy RPG (IGN) — RPG.LATEST, anné | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/rpg/  (sél. `last_update`) |
| GPU — zonages d'assainissement | GPU — idurba par commune ; SIG 4/2 | non surveillée | API Carto GPU interrogée à la demande — aucun millésime global lisible. |
| GPU — zonages d'assainissement (info-surf typeinf 19) | GPU — idurba par commune ; SIG 4/2 | non surveillée | Doublon du GPU assainissement (canal info-surf) — même amont, non re-surveillé. |
| Géoplateforme IGN | — | non surveillée | Hub IGN (WFS/WMS) — pas un jeu unique ; les produits IGN servis sont surveillés individuellement. |
| RGE ALTI 5 m (IGN) | RGE ALTI® 5 m (IGN) — édition non  | DOUBLON couvert | amont identique à « RGE ALTI (altimétrie) » (une seule veille, l'alerte vaut pour les deux) |
| SUP — assiettes GPU (API Carto) | — | non surveillée | API Carto GPU interrogée à la demande — aucun millésime global lisible. |
| Urbanisme PLU/GPU (API Carto) | — | non surveillée | API Carto GPU interrogée à la demande (idurba par commune) — aucun millésime global lisible. |

### INPN / Culture

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| ABF / Monuments historiques | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/immeubles-proteges-au-titre-des-monuments-historiques-2/  (sél. `last_update`) |
| ZNIEFF (INPN/MNHN) | INPN, mise à jour 29/08/2025 | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/inventaire-des-zones-naturelles-dinteret-ecologique-faunistique-et-floristique-znieff/  (sél. `last_update`) |
| INPN / patrinat — espaces protégés | INPN/patrinat espaces protégés — p | non surveillée | Couches patrinat servies en WFS Géoplateforme ; pas de jeu data.gouv national espaces protégés à millésime trouvé. |

### INSEE

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| BPE INSEE | millésime 2025 (géographie au 01/0 | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/base-permanente-des-equipements-3/  (sél. `last_update`) |
| Filosofi INSEE (carreaux 200 m) | millésime 2021 | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/donnees-carroyees-a-200-m-sur-la-population/  (sél. `last_update`) |
| INSEE RP2022 — fichier détail Logements (EGOUL) | RP2022 — fichier détail Logements, | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/recensement-de-la-population-fichiers-detail-logements-ordinaires/  (sél. `last_update`) |
| SIRENE | Sirene INSEE — état courant (non v | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/  (sél. `last_update`) |
| SIRENE établissements géolocalisés | SIRENE géolocalisé — publication m | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques/  (sél. `last_update`) |
| MOBPRO (mobilités domicile-travail, INSEE) | MOBPRO INSEE — fichier détail (mil | non surveillée | Import CSV manuel (abandonné pour l'étude de zone) — pas d'URL de version stable. |

### Légifrance

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| ZFANG — zone franche d'activité nouvelle génération (Légifrance) | — | non surveillée | Page Légifrance rendue en JS (aucun millésime lisible côté serveur) ; un texte modifié reçoit un nouvel identifiant. |

### Manuel / interne

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| Radar (pige d'annonces) | Collecte manuelle — biens en vente | non surveillée | Collecte 100 % humaine — non surveillable par nature. |
| VRD / assainissement (SPANC) | — | non surveillée | Champ manuel EPCI — aucune donnée ouverte fine, pas d'URL. |

### OpenStreetMap

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| OSM — transport (pôles d'échange & téléphérique) | — | non surveillée | OSM en flux continu — pas de version ; requête live. |
| OpenStreetMap / Overpass | — | non surveillée | OSM en flux continu (planet) — pas de version ; requête live. |
| Parkings OSM (loi APER) | — | non surveillée | OSM en flux continu — pas de version ; requête live. |

### Région Réunion / ODS / DILA

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| BODACC (procédures collectives) | — | SURVEILLÉE · `api` | https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales  (sél. `metas.default.modified`) |
| Parc National de La Réunion (INPN) | millésime 2021 | SURVEILLÉE · `api` | https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/pnrun_2021  (sél. `metas.default.modified`) |
| Potentiel foncier Région (Région ODS) | — | SURVEILLÉE · `api` | https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/potentiel-foncier  (sél. `metas.default.modified`) |
| Trafic RN (Région Réunion — SIR) | Trafic RN Région — comptages (mill | SURVEILLÉE · `api` | https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/trafic-mja-rn-lareunion  (sél. `metas.default.modified`) |
| Transport public — GTFS (PAN, 7 réseaux) | — | SURVEILLÉE · `api` | https://www.data.gouv.fr/api/1/datasets/horaire-du-reseau-citalis/  (sél. `last_update`) |
| data.regionreunion.com — Potentiel foncier | — | SURVEILLÉE · `api` | https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/potentiel-foncier  (sél. `metas.default.modified`) |
| FRR ex-ZRR — zone spéciale d'action rurale (Légifrance) | — | non surveillée | Page Légifrance rendue en JS (aucun millésime lisible côté serveur) ; un texte modifié reçoit un nouvel identifiant. |
| Région Réunion Open Data (Opendatasoft) | — | non surveillée | Hub/catalogue ODS (275 jeux) — pas un jeu unique ; les jeux servis sont surveillés individuellement. |

### SDES / Sitadel

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| SITADEL (autorisations d'urbanisme) | — | SURVEILLÉE · `api` | https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datasets/6513f0189d7d312c80ec5b5b  (sél. `last_update`) |

### SIRENE / entreprises

| Source | Millésime servi | État | Veille / raison |
|---|---|---|---|
| INPI RNE (dirigeants) | — | non surveillée | API authentifiée interrogée par SIREN — pas de millésime global. |
| Recherche d'entreprises (DINUM) | Sirene INSEE / RNE INPI (api.gouv. | non surveillée | API de recherche live (agrégat Sirene/RNE) — pas de millésime ingéré à comparer. |

## X6 — « Injecter cette version » (le pont supervisé)

Depuis la notification (son lien ouvre la page Sources) **et** le panneau, chaque source qui a une
nouvelle version ET une commande d'ingestion connue porte un bouton **« Injecter cette version »** :
confirmation explicite (nomme source + millésime) → lancement du **job d'ingestion EXISTANT** (la même
commande que le cron, détachée) → suivi visible (message + trace `injection_lancee_at` au tableau +
panneau CRON / `ingestion_runs`). **Aucune ingestion ne part sans ce clic humain ; la sentinelle, elle,
n'ingère jamais** (doctrine intacte — vérifié par test : détecter une version ne pose pas `injection_lancee_at`).

Sources **injectables en un clic** (commande mappée dans `config/sources_ingestion.yaml`, 5) : **DVF,
BODACC, DPE ADEME, Base Adresse Nationale, SITADEL**. Les autres surveillées affichent « injection
manuelle » (pas de commande auto — honnête, pas de faux bouton) ; ajouter une entrée au YAML les rend
injectables sans changer de code.
