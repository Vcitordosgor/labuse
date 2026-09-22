# PAGE-SOURCES-1 — Inventaire des sources + audit de la page Sources cliente

**Branche** `feat/couches-tuyau` · **départ** `364ff676` · lecture + nettoyage (frontend), inventaire (lecture DB), aucun endpoint touché.

Ce document est le livrable du **lot 3** (le tableau d'inventaire) et porte aussi les **vérifications du lot 2** (doublons, cohérence registre, test de tous les liens).

---

## 1. Le tableau d'inventaire (94 sources vitrine)

Une ligne par source **affichée au client** (`sources_catalog.WHERE_AFFICHEES` : `connecte ∪ manuel`, hors doublon / retiré / dormant / masquée). Colonnes :

- **Mise à jour** — *robot* si LABUSE récupère la donnée par un mécanisme automatisé (API en direct, cron, job, ingestion depuis l'URL du producteur), *manuelle* si le fichier est déposé à la main (`mode_remplissage = depot_manuel`).
- **Rythme producteur** — dérivé de `cadence_attendue_jours` (l'intervalle de republication attendu) : **régulier** = ≤ 180 j ou interrogée en direct ; **rare** = > 180 j (≈ annuel ou moins souvent) ; **figé** = aucun mécanisme de mise à jour (seed unique). ⚠️ Réserve : 72/94 cadences sont **estimées** (`cadence_statut = proposée`), non confirmées par le producteur — « régulier/rare » reflète la cadence *attendue*, pas une observation.
- **Couche carte** — la source alimente-t-elle une couche de la carte (présente dans `/sources/couches`).
- **Sentinelle** — surveillée par la sonde de veille (`source_veille.methode ∈ {api, page, entete, temoin}` et active). `rappel` (source manuelle) et absence de veille = *non*.

**Totaux** : 94 sources · **89 robot / 5 manuelle** · rythme **20 régulier / 73 rare / 1 figé** · **45 couches carte** · **78 surveillées par la sentinelle**.

| Source | Mise à jour | Rythme producteur | Couche carte | Sentinelle |
|---|---|---|---|---|
| 50 pas géométriques — limite haute (DEAL) | robot | rare | oui | oui |
| ABF / Monuments historiques | robot | rare | oui | oui |
| ACV / PVD / ORT (DGALN — liste des communes) | robot | rare | non | oui |
| Annuaire de l'administration (service-public.fr / DILA) | robot | régulier | non | oui |
| AZI / TRI — inondation (Géorisques GASPAR) | robot | rare | oui | oui |
| BAN PLUS — lien adresse ↔ bâtiment (IGN) | robot | régulier | non | oui |
| Base Adresse Nationale | robot | régulier | non | oui |
| BD ORTHO 20 cm (IGN) | robot | rare | non | oui |
| BD ORTHO IRC (IGN) | robot | rare | non | oui |
| BD TOPO IGN | robot | rare | oui | oui |
| BODACC (procédures collectives) | robot | régulier | non | oui |
| BPE INSEE | robot | rare | oui | oui |
| Cadastre (API Carto PCI) | robot | rare | oui | oui |
| Cadastre d'époque (Etalab / PCI vecteur DGFiP) | robot | rare | non | oui |
| Cartofriches (Cerema) | robot | rare | oui | oui |
| CatNat (arrêtés GASPAR / Géorisques) | robot | rare | non | oui |
| Cerema / GéoLittoral — indicateur d'érosion côtière | robot | rare | oui | oui |
| Classement sonore ITT (Cerema) | robot | rare | oui | oui |
| Communes La Réunion — contours (IGN ADMIN EXPRESS via geo.api.gouv, seed) | robot | figé | oui | non |
| Consommation d'espaces NAF (Cerema — portail de l'artificialisation) | robot | rare | non | oui |
| Contours IRIS (IGN/INSEE) | robot | rare | non | oui |
| CoSIA (couverture du sol IA, IGN) | robot | rare | oui | oui |
| Coût de construction (EPTB SDES + choix LABUSE) | robot | rare | non | non |
| data.regionreunion.com — Potentiel foncier | robot | rare | non | oui |
| DEAL Réunion (WMS/WFS) | robot | rare | non | oui |
| DEAL Réunion — PPR / aléas | robot | rare | oui | oui |
| DEAL — cartes de bruit stratégiques (CBS) | robot | rare | oui | non |
| DFI — documents de filiation informatisés (DGFiP) | robot | régulier | non | oui |
| DGFiP — parcelles des personnes morales | robot | rare | non | oui |
| DPE ADEME (logements existants) | robot | régulier | non | oui |
| DVF / valeurs foncières | robot | rare | oui | oui |
| EDF Réunion — lignes moyenne tension HTA (open data) | robot | rare | oui | oui |
| Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen) | robot | rare | oui | oui |
| Fibre Arcep — Ma connexion internet (immeuble) | robot | régulier | non | oui |
| Filosofi INSEE (carreaux 200 m) | robot | rare | non | oui |
| Forêts publiques (ONF) | robot | rare | oui | oui |
| FRR ex-ZRR — zone spéciale d'action rurale (Légifrance) | robot | rare | oui | non |
| GPU — droit de préemption urbain (info-surf) | robot | rare | oui | oui |
| GPU — emplacements réservés (prescriptions CNIG) | robot | régulier | oui | oui |
| GPU — espaces boisés classés (prescriptions CNIG) | robot | régulier | oui | oui |
| GPU — zonages d'assainissement | robot | rare | non | oui |
| Géorisques | robot | rare | oui | oui |
| Géorisques — CASIAS (anciens sites industriels) | robot | régulier | oui | oui |
| Géorisques — cavités souterraines | robot | rare | oui | oui |
| Géorisques — ICPE | robot | rare | oui | oui |
| Géorisques — mouvements de terrain | robot | rare | non | oui |
| Géorisques — secteurs d'information sur les sols (SIS) | robot | régulier | oui | oui |
| Géorisques — sites et sols pollués | robot | rare | oui | oui |
| IGN BD CARTO V5 — occupation du sol | robot | rare | non | oui |
| INPI RNE (dirigeants) | robot | rare | non | non |
| INPN / patrinat — espaces protégés | robot | rare | oui | non |
| INSEE RP Logement 2023 | robot | rare | non | non |
| INSEE RP2022 — bases IRIS (logement, population) | robot | rare | non | oui |
| INSEE RP2022 — fichier détail Logements (EGOUL) | robot | rare | non | oui |
| Inventaire SRU (DHUP) | robot | rare | non | non |
| LiDAR HD — MNH 50 cm (IGN) | robot | rare | non | oui |
| Loyers DHUP — carte des loyers (annonces) | manuelle | rare | non | oui |
| Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires) | robot | rare | non | oui |
| NPNRU (DEAL Réunion / ANCT) | robot | rare | oui | non |
| OCS GE (IGN) — occupation du sol et artificialisation | robot | rare | oui | oui |
| OpenStreetMap / Overpass | robot | rare | oui | non |
| OSM — transport (pôles d'échange & téléphérique) | robot | rare | oui | oui |
| Parc National de La Réunion (INPN) | robot | rare | oui | oui |
| Parkings OSM (loi APER) | robot | rare | non | oui |
| PEB — plans d'exposition au bruit (DGAC via annexes GPU) | robot | rare | oui | oui |
| PLH des 5 EPCI (extraction documentaire) | manuelle | rare | non | non |
| PVGIS (Commission européenne) | robot | rare | non | non |
| QPV 2024 (ANCT) | robot | rare | oui | oui |
| Radar (pige d'annonces) | manuelle | régulier | non | non |
| Ravines — domaine public fluvial (DEAL Carmen) | robot | rare | oui | oui |
| Recherche d'entreprises (DINUM) | robot | régulier | non | oui |
| RGE ALTI (altimétrie) | robot | rare | non | oui |
| RNB — Référentiel National des Bâtiments | robot | régulier | non | oui |
| RNIC — registre national des copropriétés (Anah) | robot | rare | non | oui |
| RPG — déclarations agricoles (IGN/ASP) | robot | régulier | oui | oui |
| RPLS — répertoire des logements locatifs sociaux (SDES) | robot | rare | non | oui |
| RTAA DOM (textes réglementaires) | robot | rare | non | non |
| SIRENE | robot | régulier | non | oui |
| SIRENE établissements géolocalisés | robot | régulier | non | oui |
| SITADEL (autorisations d'urbanisme) | robot | régulier | non | oui |
| Sudocuh (procédures d'urbanisme) | manuelle | rare | non | oui |
| SUP — assiettes GPU (API Carto) | robot | régulier | oui | oui |
| Systèmes d'endiguement et zones protégées (DEAL Lizmap) | robot | rare | oui | oui |
| Taux de taxe foncière — fichier REI (DGFiP) | robot | rare | non | oui |
| Taxe d'aménagement — taux communaux (délibérations) | robot | rare | non | oui |
| TCSP — voies bus en site propre (OSM) | robot | rare | oui | oui |
| Trafic RN (Région Réunion — SIR) | robot | rare | non | oui |
| Transport public — GTFS (PAN, 7 réseaux) | robot | rare | oui | oui |
| Urbanisme PLU/GPU (API Carto) | robot | régulier | oui | oui |
| VRD / assainissement (SPANC) | manuelle | rare | non | non |
| ZFANG — zone franche d'activité nouvelle génération (Légifrance) | robot | rare | oui | non |
| ZNIEFF (INPN/MNHN) | robot | rare | oui | oui |
| Zonage ABC des communes (DHUP) | robot | rare | non | oui |
| Zones humides — inventaires DEAL (Carmen) | robot | rare | oui | oui |

---

## 2. La phrase de vérification (justification)

La nouvelle phrase de la page (« La plupart de nos sources sont vérifiées automatiquement chaque jour… ») a été **vérifiée sur la couverture réelle de la sentinelle** avant d'être écrite :

- **78 des 94** sources vitrine sont sondées par la sentinelle, **toutes à cadence 24 h** (une passe par nuit → vérification quotidienne).
- **16** ne le sont pas : **9** portent un `rappel` (source manuelle, aucun amont public interrogeable) et **7** n'ont aucune veille.

Comme **toutes** les sources ne sont **pas** vérifiées quotidiennement, la formulation dit « **la plupart** », jamais « toutes » (l'affirmation globale serait fausse — conforme à la consigne du mandat).

---

## 3. Vérifications du lot 2

### 3.1 Doublons / cohérence registre
**Aucun doublon** de nom dans les 94 sources vitrine (vérifié par comptage sur `data_sources` filtré `WHERE_AFFICHEES`). La liste cliente == la sélection canonique du registre (même filtre que le compteur d'accueil).

### 3.2 Test de tous les liens externes (page producteur)
Les 94 `documentation_url` ont été testés (HTTP, suivi des redirections, UA navigateur ; les cas ambigus revérifiés dans un vrai Chrome). **85 OK (2xx/3xx) · 3 sans lien · 6 en anomalie.** Détail des 6 :

| Source | Code | Verdict |
|---|---|---|
| Consommation d'espaces NAF (Cerema — portail artificialisation) | ~~404~~ → **200** | **CORRIGÉ (PAGE-SOURCES-2)** — nouvelle page `…/mesurer-la-consommation-despaces/telecharger-les-donnees`. |
| RPLS — répertoire des logements locatifs sociaux (SDES) | ~~404~~ → **200** | **CORRIGÉ (PAGE-SOURCES-2)** — page data.gouv du jeu SDES `…/repertoire-des-logements-locatifs-des-bailleurs-sociaux/`. |
| LiDAR HD — MNH 50 cm (IGN) | **503** | Transitoire — serveur IGN en maintenance (« IGN-MUT : 503 »), lien valide hors incident. |
| FRR ex-ZRR (Légifrance) | 403 | **Valide** — Légifrance bloque les non-navigateurs (challenge Cloudflare « Just a moment… ») ; s'ouvre en navigateur. |
| RTAA DOM (Légifrance) | 403 | **Valide** — idem Cloudflare. |
| ZFANG (Légifrance) | 403 | **Valide** — idem Cloudflare. |

**Aucun lien « faux »** (pointant vers le mauvais producteur). **Les 2 liens cassés (404) ont été corrigés par PAGE-SOURCES-2** (seed `seed_sources.py` + ligne `data_sources` en base ; testés → **200/200** ; servis par `/sources`). Les 3 « 403 » sont des faux positifs de robot (Cloudflare), pas des liens morts ; le 503 IGN est transitoire.

La liste complète des 94 liens testés avec leur code figure en **annexe** ci-dessous.

### 3.3 Réserve manquante ailleurs ? (signalé, non ajouté)
En retirant le bloc « détail technique », l'**avertissement de recalibration / censure du modèle** (`/v2/modele.avertissement_censure`) a quitté la page. C'est la seule réserve *utile* qui disparaît avec ce bloc : si l'on veut la conserver côté client, elle mériterait d'être reformulée en une phrase de réserve simple (comme celle sur les ventes). **Signalé, non ajouté** (conforme à la consigne).

---

## 4. D'où vient le « 94 sources » du client (et pourquoi pas 88 ni 92) — PAGE-SOURCES-2

Le « 94 » n'est **jamais un chiffre en dur** : c'est `COUNT(*)` sur `data_sources` filtré par l'expression **canonique** `sources_catalog.WHERE_AFFICHEES` — `lower(status) IN ('connecte','manuel')`, moins les `DOUBLON` / `RETIRÉ` / `DORMANT` / masquées / `affichage_desactive`. La **même** expression est lue par le compteur d'accueil (`accueil.py`), la liste `/sources` (page cliente) **et** l'admin « Données » (Circuit) → les trois affichent le même nombre par construction, aucune divergence possible.

Décomposition (mesurée en base aujourd'hui) : **121 sources au total = 94 en vitrine + 27 hors vitrine** (hors vitrine = `partenariat_requis` 13 · `alias` 5 · `retiree` 5 · `hub` 3 · `a_faire` 1).

- **94 (client)** = `connecte` (92) **+** `manuel` (2). Les 2 `manuel` = **VRD / assainissement (SPANC)** et **Radar (pige d'annonces)** : câblées et alimentées à la main, aucun amont public auto. La règle M123 les rend visibles (« la vitrine montre ce qui SERT », pas seulement l'auto-branché).
- **92** = le sous-ensemble `status = 'connecte'` **strict** (sans les 2 `manuel`). C'est l'ancienne définition de la vitrine (avant M123) et le compte qui apparaît si l'on filtre `connecte` seul. La différence 94 − 92 = exactement ces 2 sources manuelles.
- **88** = **pas un compteur en vigueur.** Le nombre de vitrine est **dynamique** et a bougé au fil des connexions / retraits / re-tags (mesuré : 91→92 à COUCHES-REGISTRE-2 ; 93 / 95 / 96 dans les rapports SOURCES antérieurs, quand 13 sources sont passées `partenariat_requis` = invisibles client). 88 correspond à un **état antérieur** (moins de sources branchées), pas à une définition actuelle ; aucun filtre canonique d'aujourd'hui ne rend 88 (le seul qui tombe dessus — retirer les 6 lignes annotées « proxy » — est fortuit, et ne colle même pas au badge « proxy » servi, qui en compte 5). **Le chiffre en vigueur est 94** ; 88 est périmé.

---

## Annexe — les 94 liens testés

| Source | Lien producteur | Code HTTP |
|---|---|---|
| 50 pas géométriques — limite haute (DEAL) | https://deal974.lizmap.com/cartes/ | 200 |
| ABF / Monuments historiques | https://data.culture.gouv.fr/explore/dataset/liste-des-immeubles-proteges-au-titre-des-monuments-historiques/ | 200 |
| ACV / PVD / ORT (DGALN — liste des communes) | https://www.data.gouv.fr/datasets/liste-des-communes-couvertes-par-des-operations-de-revitalisation-de-territoire | 200 |
| Annuaire de l'administration (service-public.fr / DILA) | https://api-lannuaire.service-public.fr/ | 200 |
| AZI / TRI — inondation (Géorisques GASPAR) | https://www.georisques.gouv.fr/doc-api | 200 |
| BAN PLUS — lien adresse ↔ bâtiment (IGN) | https://www.data.gouv.fr/datasets/ban-plus | 200 |
| Base Adresse Nationale | https://adresse.data.gouv.fr | 200 |
| BD ORTHO 20 cm (IGN) | https://geoservices.ign.fr/bdortho | 200 |
| BD ORTHO IRC (IGN) | https://geoservices.ign.fr/bdortho | 200 |
| BD TOPO IGN | https://geoservices.ign.fr/bdtopo | 200 |
| BODACC (procédures collectives) | https://bodacc-datadila.opendatasoft.com/explore/dataset/annonces-commerciales/ | 200 |
| BPE INSEE | https://www.insee.fr/fr/statistiques/8217525 | 200 |
| Cadastre (API Carto PCI) | https://apicarto.ign.fr/api/doc/cadastre | 200 |
| Cadastre d'époque (Etalab / PCI vecteur DGFiP) | https://cadastre.data.gouv.fr/datasets/cadastre-etalab | 200 |
| Cartofriches (Cerema) | https://schema.data.gouv.fr/cnigfr/schema-friches | 200 |
| CatNat (arrêtés GASPAR / Géorisques) | https://www.georisques.gouv.fr/doc-api | 200 |
| Cerema / GéoLittoral — indicateur d'érosion côtière | https://www.geolittoral.developpement-durable.gouv.fr/indicateur-national-de-l-erosion-cotiere-a1434.html | 200 |
| Classement sonore ITT (Cerema) | https://cartagene.cerema.fr | 200 |
| Communes La Réunion — contours (IGN ADMIN EXPRESS via geo.api.gouv, seed) | — | ABSENT |
| Consommation d'espaces NAF (Cerema — portail de l'artificialisation) | https://artificialisation.developpement-durable.gouv.fr/mesurer-la-consommation-despaces/telecharger-les-donnees | 200 (corrigé PAGE-SOURCES-2) |
| Contours IRIS (IGN/INSEE) | https://geoservices.ign.fr/contoursiris | 200 |
| CoSIA (couverture du sol IA, IGN) | https://geoservices.ign.fr/cosia | 200 |
| Coût de construction (EPTB SDES + choix LABUSE) | https://dreal.statistiques.developpement-durable.gouv.fr/eptb/2024/la_reunion/index.html | 200 |
| data.regionreunion.com — Potentiel foncier | https://data.regionreunion.com/explore/dataset/potentiel-foncier/ | 200 |
| DEAL Réunion (WMS/WFS) | https://www.reunion.developpement-durable.gouv.fr | 200 |
| DEAL Réunion — PPR / aléas | https://deal974.lizmap.com/cartes/index.php/view/map?repository=02sprinr&project=01risque | 200 |
| DEAL — cartes de bruit stratégiques (CBS) | https://www.reunion.developpement-durable.gouv.fr/8-consultation-des-donnees-a62.html | 200 |
| DFI — documents de filiation informatisés (DGFiP) | https://www.data.gouv.fr/datasets/agregation-des-fichiers-de-documents-de-filiation-informatises-dfi-des-parcelles | 200 |
| DGFiP — parcelles des personnes morales | https://data.economie.gouv.fr/explore/dataset/fichiers-des-locaux-et-des-parcelles-des-personnes-morales/ | 200 |
| DPE ADEME (logements existants) | https://data.ademe.fr/datasets/dpe03existant | 200 |
| DVF / valeurs foncières | https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/ | 200 |
| EDF Réunion — lignes moyenne tension HTA (open data) | https://opendata-reunion.edf.fr/datasets/lignes-haute-tension-hta-aerien-run | 200 |
| Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen) | https://www.reunion.developpement-durable.gouv.fr/informations-geographiques-r104.html | 200 |
| Fibre Arcep — Ma connexion internet (immeuble) | https://www.data.gouv.fr/datasets/ma-connexion-internet | 200 |
| Filosofi INSEE (carreaux 200 m) | https://www.insee.fr/fr/statistiques/8735162?sommaire=8735243 | 200 |
| Forêts publiques (ONF) | https://geoservices.ign.fr/bdtopo | 200 |
| FRR ex-ZRR — zone spéciale d'action rurale (Légifrance) | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049746820 | 403 |
| GPU — droit de préemption urbain (info-surf) | https://apicarto.ign.fr/api/doc/gpu | 200 |
| GPU — emplacements réservés (prescriptions CNIG) | https://apicarto.ign.fr/api/doc/gpu | 200 |
| GPU — espaces boisés classés (prescriptions CNIG) | https://apicarto.ign.fr/api/doc/gpu | 200 |
| GPU — zonages d'assainissement | https://apicarto.ign.fr/api/doc/gpu | 200 |
| Géorisques | https://www.georisques.gouv.fr/doc-api | 200 |
| Géorisques — CASIAS (anciens sites industriels) | https://www.georisques.gouv.fr/donnees/bases-de-donnees/inventaire-historique-de-sites-industriels-et-activites-de-service | 200 |
| Géorisques — cavités souterraines | https://www.georisques.gouv.fr/doc-api | 200 |
| Géorisques — ICPE | https://www.georisques.gouv.fr/doc-api | 200 |
| Géorisques — mouvements de terrain | https://www.georisques.gouv.fr/doc-api | 200 |
| Géorisques — secteurs d'information sur les sols (SIS) | https://www.georisques.gouv.fr/donnees/bases-de-donnees/secteurs-dinformations-sur-les-sols-sis | 200 |
| Géorisques — sites et sols pollués | https://www.georisques.gouv.fr/doc-api | 200 |
| IGN BD CARTO V5 — occupation du sol | https://geoservices.ign.fr/ocsge | 200 |
| INPI RNE (dirigeants) | https://www.inpi.fr/ressources/propriete-intellectuelle/acces-aux-api-et-ftp | 200 |
| INPN / patrinat — espaces protégés | https://inpn.mnhn.fr/ | 200 |
| INSEE RP Logement 2023 | https://www.insee.fr/fr/statistiques/8997194?sommaire=9003154 | 200 |
| INSEE RP2022 — bases IRIS (logement, population) | https://www.insee.fr/fr/statistiques/8647012 | 200 |
| INSEE RP2022 — fichier détail Logements (EGOUL) | https://www.insee.fr/fr/statistiques/8647099 | 200 |
| Inventaire SRU (DHUP) | https://www.data.gouv.fr/datasets/communes-et-inventaire-sru | 200 |
| LiDAR HD — MNH 50 cm (IGN) | https://diffusion-lidarhd.ign.fr/mnx/ | 503 |
| Loyers DHUP — carte des loyers (annonces) | https://www.data.gouv.fr/datasets/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2024 | 200 |
| Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires) | https://www.data.gouv.fr/datasets/resultats-des-observatoires-locaux-des-loyers-par-agglomeration | 200 |
| NPNRU (DEAL Réunion / ANCT) | https://www.data.gouv.fr/datasets/le-nouveau-programe-national-de-renouvellement-urbain | 200 |
| OCS GE (IGN) — occupation du sol et artificialisation | https://geoservices.ign.fr/ocsge | 200 |
| OpenStreetMap / Overpass | https://wiki.openstreetmap.org/wiki/Overpass_API | 200 |
| OSM — transport (pôles d'échange & téléphérique) | https://wiki.openstreetmap.org/wiki/Key:public_transport | 200 |
| Parc National de La Réunion (INPN) | https://data.regionreunion.com/explore/dataset/pnrun_2021/ | 200 |
| Parkings OSM (loi APER) | https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dparking | 200 |
| PEB — plans d'exposition au bruit (DGAC via annexes GPU) | https://apicarto.ign.fr/api/doc/gpu | 200 |
| PLH des 5 EPCI (extraction documentaire) | https://www.reunion.developpement-durable.gouv.fr/IMG/pdf/20191205_rapport-cdhh-091219.pdf | 200 |
| PVGIS (Commission européenne) | https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en | 200 |
| QPV 2024 (ANCT) | https://www.data.gouv.fr/datasets/quartiers-prioritaires-de-la-politique-de-la-ville-qpv | 200 |
| Radar (pige d'annonces) | — | ABSENT |
| Ravines — domaine public fluvial (DEAL Carmen) | https://www.reunion.developpement-durable.gouv.fr/domaine-public-fluvial-dpf-et-domaine-prive-de-l-a285.html | 200 |
| Recherche d'entreprises (DINUM) | https://recherche-entreprises.api.gouv.fr/docs/ | 200 |
| RGE ALTI (altimétrie) | https://geoservices.ign.fr/services-geoplateforme-altimetrie | 200 |
| RNB — Référentiel National des Bâtiments | https://rnb.beta.gouv.fr/doc | 200 |
| RNIC — registre national des copropriétés (Anah) | https://www.data.gouv.fr/fr/datasets/registre-national-dimmatriculation-des-coproprietes/ | 200 |
| RPG — déclarations agricoles (IGN/ASP) | https://geoservices.ign.fr/services-geoplateforme-diffusion | 200 |
| RPLS — répertoire des logements locatifs sociaux (SDES) | https://www.data.gouv.fr/datasets/repertoire-des-logements-locatifs-des-bailleurs-sociaux/ | 200 (corrigé PAGE-SOURCES-2) |
| RTAA DOM (textes réglementaires) | https://www.legifrance.gouv.fr/loda/id/JORFTEXT000020530547 | 403 |
| SIRENE | https://recherche-entreprises.api.gouv.fr/docs | 200 |
| SIRENE établissements géolocalisés | https://www.data.gouv.fr/fr/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques/ | 200 |
| SITADEL (autorisations d'urbanisme) | https://www.statistiques.developpement-durable.gouv.fr/donnees-des-permis-de-construire-et-autres-autorisations-durbanisme | 200 |
| Sudocuh (procédures d'urbanisme) | https://www.data.gouv.fr/datasets/planification-nationale-des-documents-durbanisme-plu-plui-cc-rnu-donnees-sudocuh-dernier-etat-des-lieux-annuel-au-31-decembre-2024 | 200 |
| SUP — assiettes GPU (API Carto) | https://apicarto.ign.fr/api/doc/gpu | 200 |
| Systèmes d'endiguement et zones protégées (DEAL Lizmap) | https://deal974.lizmap.com/cartes/index.php/view/map?repository=02sprinr&project=03digues | 200 |
| Taux de taxe foncière — fichier REI (DGFiP) | https://www.data.gouv.fr/datasets/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-directe-locale-rei-4 | 200 |
| Taxe d'aménagement — taux communaux (délibérations) | https://data.economie.gouv.fr/explore/dataset/delta_deliberation_tam_17_01_23/ | 200 |
| TCSP — voies bus en site propre (OSM) | https://wiki.openstreetmap.org/wiki/Tag:highway%3Dbusway | 200 |
| Trafic RN (Région Réunion — SIR) | https://data.regionreunion.com/explore/dataset/trafic-mja-rn-lareunion/ | 200 |
| Transport public — GTFS (PAN, 7 réseaux) | https://transport.data.gouv.fr/datasets/region/04?format=GTFS | 200 |
| Urbanisme PLU/GPU (API Carto) | https://apicarto.ign.fr/api/doc/gpu | 200 |
| VRD / assainissement (SPANC) | — | ABSENT |
| ZFANG — zone franche d'activité nouvelle génération (Légifrance) | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000054153903 | 403 |
| ZNIEFF (INPN/MNHN) | https://www.data.gouv.fr/datasets/inventaire-des-zones-naturelles-dinteret-ecologique-faunistique-et-floristique-znieff | 200 |
| Zonage ABC des communes (DHUP) | https://www.data.gouv.fr/datasets/liste-des-communes-selon-le-zonage-abc | 200 |
| Zones humides — inventaires DEAL (Carmen) | https://www.reunion.developpement-durable.gouv.fr/les-cartographies-d-habitats-a320.html | 200 |
