# GEOPF-3 — Ingestion de 10 couches (décision Vic du 25/09/2026)

Worktree `labuse-geopf3`, branche `feat/geopf-3`, base main `df386bfc`. App 8445 / 5645.
Un commit par couche. Règles : filtrée 974 · inscrite `data_sources` (+ sentinelle si version
amont) · servie par le tuyau unique des couches (jamais un rendu à part) · légende + « i » ·
pas de camaïeu de vert. Si licence non commerciale ou couverture Réunion vide → on s'arrête et
on le note.

Preuves par couche : nombre d'objets 974 + capture sur un témoin (Saint-Denis / Saint-Paul /
Saint-Pierre), dans `captures/`.

## Bilan des 10 couches

| # | Couche | Source (WFS/WMTS/liste) | Objets 974 | État |
|---|--------|-------------------------|-----------:|------|
| 1 | Pylônes électriques (Réseaux) | BD TOPO `BDTOPO_V3:pylone` | 1187 | ✅ ingérée |
| 2 | Postes de transformation (Réseaux + fiche) | BD TOPO `poste_de_transformation` | 20 | ✅ ingérée |
| 3 | Mesures compensatoires (contraintes) | GéoMCE `MESURES_COMPENSATOIRES` | 24 | ✅ ingérée |
| 4 | SCOT + périmètre (couche + fiche commune) | GPU `wfs_scot` | 3 | ✅ ingérée |
| 5 | EnR interdit hors toiture — APER (Énergie + solaire) | OFB `zones_exclues…sauf_toiture` | 3 | ✅ ingérée |
| 6 | Contraintes EnR près habitations (Énergie + solaire) | geopf ENR.PERIMETRE.HABITATION | raster | ✅ ingérée |
| 7 | Lieux-dits (recherche + fiche Secteur) | BD NYME (BD TOPO toponymes) | 1762 | ✅ ingérée |
| 8 | Stations classées / communes touristiques (fiche commune) | liste DGE | 0 | ⛔ arrêtée (source indisponible) |
| 9 | Cartes anciennes SCAN 50 1950 / EduGéo 1980 (Remonter le temps) | IGN WMTS | raster | ✅ ingérée |
| 10 | ZAC | recherche source officielle 974 | 0 | ⛔ arrêtée (source partielle) |

Bilan : **8 couches ingérées, 2 arrêtées et documentées** (8 stations DGE, 10 ZAC).

### 3 — Mesures compensatoires ERC ✅
- **Source** : GéoMCE (MTE/OFB/DREAL), `MESURES_COMPENSATOIRES:emprises_polygones/lineaires/ponctuelles`
  (Géoplateforme WFS, Licence Ouverte 2.0). Maître d'ouvrage « non diffusable » à la source (jamais inventé).
- **Objets 974** : 24 (20 surface + 2 ligne + 2 point). kind=`mesures_compensatoires`.
- **data_sources** : « GéoMCE — mesures compensatoires » (+ sonde sentinelle témoin WFS date_decision).
- **Tuyau** : famille environnement (magenta #C0508F, geometrie mixte). **Contraintes** : ajoutée au point
  unique `servitudes.contraintes_parcelle` (_KINDS + _detail) → visible dans « Pièges et risques » + fiche.

### 4 — SCOT (GPU) ✅
- **Source** : GPU, `wfs_scot:scot` + `wfs_scot:perimetre_scot` (WFS, Licence Ouverte). Date d'approbation
  lue dans l'idurba CNIG.
- **Objets 974** : 3 — SCOT TCO (approuvé 2022-10-03), SCOT CINOR (approuvé), SCOT Grand Sud (en projet 2024-09-02).
- **data_sources** : « SCOT (GPU) » (+ sonde sentinelle) + réservoir scot_gpu.
- **Tuyau** : famille urbanisme (contour seul bleu #3B6FB0, périmètre large). **Fiche commune** : carte
  Urbanisme, ligne « SCOT : <nom> — approuvé le <date> », rattachement par **ST_Contains(centroïde commune)**
  (correct : Saint-Denis→CINOR, Saint-Paul→TCO, Saint-Pierre→Grand Sud, Saint-Benoît→aucun).

### 5 — EnR interdites hors toiture (loi APER) ✅
- **Source** : OFB/INPN, `OFB_ZONES.EXCLUES.SAUF.TOITURE:zones_exclues_aires_acceleration_sauf_toiture`
  (WFS, Licence Ouverte). Nouvelle **famille de couches « energie »**.
- **Objets 974** : 3 — Parc national (cœur + aire d'adhésion), Réserve naturelle Étang de Saint-Paul.
- **data_sources** : « Zones exclues EnR sauf toiture (OFB/APER) » (+ sentinelle) + réservoir enr_aper_ofb.
- **Tuyau** : groupe Énergie (rouge #D64550 faible opacité). **Prospection solaire** : filtre d'exclusion
  sur la fiche soleil — « projet au sol exclu ici / toiture OK » (ST_Intersects) + export courrier.

### 6 — Contraintes EnR près des habitations ✅
- **Source** : Géoplateforme WMTS `ENR.PERIMETRE.HABITATION` (style PERIMETRE.HABITATION, PM_6_18, PNG).
  **Pas de vecteur WFS** → couche RASTER. Couverture 974 VÉRIFIÉE (tuiles z12/z14 Saint-Paul/Saint-Denis/
  Saint-Pierre non vides).
- **Relais** : `/map/tiles/enr_habitation` (ortho_proxy, PNG brut + cache, patron courbes de niveau).
- **data_sources** : « Contraintes EnR près des habitations (Géoplateforme) ».
- **Tuyau** : couche front-déclarée (comme les courbes), groupe Énergie. **Prospection solaire** : note +
  couche superposable.

### 7 — Lieux-dits (BD NYME) ✅
- **Source** : BD TOPO IGN, `zone_d_habitation` (habités) + `lieu_dit_non_habite` (WFS, Licence Ouverte).
- **Objets 974** : 1762 (1334 habités + 428 non habités) → table `lieux_dits`, commune = parcelle la plus proche.
- **data_sources** : « BD NYME — lieux-dits (IGN) » (+ sonde sentinelle bd-topo-r).
- **(a) Recherche** : 5ᵉ grammaire `/api/recherche/suggest` « Lieu-dit · Le Guillaume, Saint-Paul »
  (match jetons + unaccent), active dans toutes les barres via `ParcelInput` ; un clic zoome au secteur
  (lon/lat). Tests OK : « Guillaume »→le Guillaume/Saint-Paul, « Bois de Nèfles », « Grand Fond ».
- **(b) Fiche parcelle** : ligne « Secteur : <lieu-dit le plus proche> » sous l'adresse (rayon borné 600 m,
  sinon rien). Témoin AB0001 → « le Cabestan ».

### 8 — Stations classées / communes touristiques ⛔ ARRÊTÉE
- **Recherche menée** : page DGE (entreprises.gouv.fr) — pas de fichier téléchargeable ; portail ODS du
  ministère (data.economie.gouv.fr) — aucun jeu ; data.gouv.fr — seulement des jeux **régionaux** (DDT
  Haute-Savoie, Hauts-de-France), **aucun équivalent 974** ; pas de carte DGE avec backend accessible.
- **Constat** : le classement est dispersé (décrets pour les stations classées de tourisme + arrêtés
  préfectoraux pour les communes touristiques) ; **aucune liste nationale fiable, complète et
  machine-lisible** couvrant La Réunion.
- **Décision** : rien ingéré, conformément à la règle. Charger une liste partielle hand-picked afficherait
  « non classée » pour des communes potentiellement classées mais non sourcées — un « zéro menteur »
  interdit par la doctrine LABUSE. À rouvrir si la DGE publie un fichier 974.

### 9 — Cartes anciennes (SCAN 50 1950 / EduGéo Réunion 1980) ✅
- **Sources** : IGN WMTS `GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN50.1950` (jpeg) et
  `GEOGRAPHICALGRIDSYSTEMS.EDUGEO.LA-REUNION1980` (png), Licence Ouverte. Couverture 974 VÉRIFIÉE
  (SCAN50 = carte IGN 1950 de Saint-Paul : Bellemène, le Guillaume ; EduGéo bbox = l'île).
- **Relais** : route dédiée `/map/tiles/carte-ancienne` — **relais BRUT** (pas de masque mer : ce sont des
  CARTES, pas des photos).
- **Remonter le temps** : 2 millésimes de plus (SCAN 50 1950 avant l'ortho 1950-1965, EduGéo 1980 après),
  `basemaps.ts` (TEMPS_MILLESIMES) + OrthoYear étendu. 2 sources data_sources.

### 10 — ZAC ⛔ ARRÊTÉE (source partielle)
- **Recherche menée** : WFS Géoplateforme — aucune couche ZAC ; GPU (API Carto) — les ZAC existent en
  **prescription typepsc 45 « Zone d'aménagement concerté »**, DÉJÀ en base via `plu_gpu_prescription`,
  mais seulement **10 ZAC, toutes à Saint-Denis** (documents GPU qui les publient) ; potentiel foncier
  Région — 355 îlots annotés « en ZAC … en cours/projet » (Cambrai, Mont Vert, PRU Saint-Paul…), mais
  c'est une annotation foncière **indicative**, pas un périmètre autoritatif ; ni DEAL ni EPCI ne publient
  de registre ZAC 974 complet.
- **Constat** : la seule source officielle (GPU typepsc 45) est **fiable mais partielle** (Saint-Denis seul).
- **Décision** : rien de neuf ingéré, conformément à la règle (« si aucune fiable **et complète** »). Créer
  une couche « ZAC » qui ne montrerait que Saint-Denis donnerait une fausse exhaustivité. Les ZAC du GPU
  restent visibles via la couche « Emplacements réservés / prescriptions » existante. À rouvrir si un
  registre ZAC 974 complet est publié (EPCI/DEAL).

## Discipline commune (toutes les couches ingérées)
- Filtrées **974** (bbox île `55.20,-21.42,55.90,-20.85` pour les WFS ; couverture WMTS vérifiée par tuiles).
- Inscrites dans **data_sources** (producteur, millésime, licence, cadence) ; **sentinelle** pour les
  sources à version amont (témoin WFS ou data.gouv `last_update`).
- Servies par le **tuyau unique des couches** (`declarations/couches/` pour le vecteur ; front-déclaré pour
  le raster, fusionné au même plan/panneau/légende) — jamais un rendu à part.
- **Légende + « i »** pour chacune. **Pas de camaïeu de vert** : teintes choisies distinctes des verts déjà
  pris (pylône acier, poste ambre, mesures comp. magenta, SCOT bleu, APER rouge, EnR habitation ambre).
- Aucune licence non commerciale (tout Licence Ouverte 2.0 Etalab), aucune couverture 974 vide sur les
  couches livrées.

## Exécution
- Commandes CLI : `labuse pylones-build`, `postes-transformation-build`, `mesures-compensatoires-build`,
  `scot-build`, `enr-exclue-toiture-build`, `bd-nyme-build`, `seed-sources`.
- Un commit par couche (10 commits). Base main `df386bfc`, branche `feat/geopf-3`.

## Détail par couche

### 1 — Pylônes électriques ✅
- **Source** : IGN BD TOPO® V3, `BDTOPO_V3:pylone` (Géoplateforme WFS, Licence Ouverte 2.0).
- **Objets 974** : 1187 (points). `spatial_layers` kind=`pylone`, commune=NULL, île entière.
- **data_sources** : « BD TOPO IGN » (déjà au catalogue ; sonde sentinelle bd-topo-r partagée).
- **Tuyau** : famille Réseaux (section « Réseaux d'énergie »), point acier anneau #7E8A94,
  zoom_min 11, distinct des lignes HT/MT. Légende + « i ». CLI `labuse pylones-build`.

### 2 — Postes de transformation ✅
- **Source** : IGN BD TOPO® V3, `BDTOPO_V3:poste_de_transformation` (WFS, Licence Ouverte 2.0).
- **Objets 974** : 20 (emprises MultiPolygon ; BD TOPO ne cartographie que les postes principaux).
- **data_sources** : « BD TOPO IGN ».
- **Tuyau** : famille Réseaux, emprise ambre #E8873A + centroïde (visible île). Légende + « i ».
- **Fiche parcelle** : distance au poste le plus proche servie au tiroir Réseaux (bloc
  « Raccordement électrique », seuil 300 m) + export courrier. CLI `labuse postes-transformation-build`.
