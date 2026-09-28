# GEOPF-1 — Quelles couches de cartes.gouv touchent La Réunion

**Branche** `audit/geopf-1` (worktree `labuse-geopf`) · **lecture seule** · audit du 2026-09-25.
Aucune écriture dans `src/` ni en base. Tout est ici, sous `docs/audit-2026-09/GEOPF-1/`.

> **Verdict court.** Sur les **1 407 données** distinctes publiées par la Géoplateforme,
> **643** *déclarent* une emprise qui croise La Réunion, mais seulement **433** *couvrent
> réellement* l'île une fois testées (218 sont déclarées sur un pavé large et sont **vides**
> au-dessus de Réunion, 16 restent indéterminées). Sur ces **433 qui couvrent** :
> LABUSE en a déjà **266** (33 rendues en couche + 233 présentes en base) et **167 sont
> absentes** — mais ces 167 se ramènent à **35 familles de produit**, dont la moitié sont
> soit des fonds de carte cosmétiques, soit des POI dont LABUSE a l'équivalent (BPE/OSM),
> soit des couches de test. **Vic tranche.**

---

## 1. Inventaire (GetCapabilities des 5 services)

Téléchargés et mis en cache le 2026-09-25 (`cache/getcap_*.xml`) :

| Service | URL | Couches brutes |
|---|---|--:|
| WMTS | `data.geopf.fr/wmts` | 719 |
| WMS raster | `data.geopf.fr/wms-r/ows` | 451 |
| WMS vecteur | `data.geopf.fr/wms-v/ows` | 474 |
| WFS | `data.geopf.fr/wfs/ows` | 825 |
| TMS | `data.geopf.fr/tms/1.0.0` | 816 |
| **Total brut (lignes)** | | **3 285** |

**Dédoublonnage** (`01_parse.py`) — clé canonique = identifiant, préfixe de namespace WFS retiré,
millésimes 4 chiffres / dates / `.LATEST` / `.Vn` rabotés, puis regroupement. Une donnée publiée
en WMTS **et** en WMS **et** en TMS ne compte qu'une fois ; ADMIN EXPRESS 2017…2026 = une ligne.

> **Total dédoublonné : 1 407 données** (dont 204 groupes fusionnant ≥2 identifiants).

### Écart avec les 1 164 du catalogue (+243)

Notre 1 407 dépasse le catalogue officiel de **+243**. L'écart n'est pas un défaut de comptage :
il vient de ce que **notre canon ne fusionne que les doublons de chaîne exacts et les millésimes
à 4 chiffres**, alors que le catalogue compte des *données curées*. Les familles décomposées
expliquent tout l'écart :

- **CORINE Land Cover** : **110** lignes dans notre dédoublonné pour ~1 produit (sous-produits
  CLC/CHA × millésimes 2000→2018 × vecteur/raster/DOM/révisée × noms techniques WFS
  `CLC_CLC_BDD_WLD_WM_…` qui ne string-matchent pas leur jumeau WMTS `LANDCOVER.CLC18`).
- **BD TOPO** : **79** lignes (le WFS décompose le produit en ~79 types d'objets : bâtiment,
  troncon_de_route, canalisation…). **BD CARTO** : **57**. **INSEE Filosofi** : **22**
  (une couche par indicateur). **OCS GE** : 11. Habillage/informations/prescriptions du Plan
  IGN : 16.
- **872 / 1 407** données ne sont publiées que dans **un seul service** (surtout des types
  d'objets WFS et des rasters WMS) : elles ne se fusionnent avec rien.

Autrement dit : le catalogue compte « CORINE Land Cover » une fois ; nous comptons ses 110
couches publiées. Les deux chiffres sont défendables ; le nôtre est un décompte de *couches
servies*, le leur de *jeux de données*.

## 2. Filtre sur l'emprise déclarée

Emprise Réunion retenue : **lon 55,20 → 55,85 ; lat −21,40 → −20,85**.
Une donnée est retenue si sa `WGS84BoundingBox` (WMTS/WFS) ou son `EX_GeographicBoundingBox`
(WMS) croise ce pavé. Les 72 couches **TMS sans emprise déclarée** ont vu leur bbox résolue via
leur `TileMap` (reprojection 3857→WGS84) pour ne rien perdre en silence.

> **643 données** déclarent une emprise croisant La Réunion (dont **164** via une bbox
> quasi-mondiale `-180…180` — les suspectes « déclarées partout, peut-être vides ici »).
> ~740 sont déclarées métropole/autre DOM uniquement → écartées.

## 3. Test réel (le déclaré ne suffit pas)

`02_probe.py` puis `04_reprobe.py`, **≤ 5 requêtes/s**. 3 points témoins :
**Saint-Denis** (55,448 / −20,882), **Saint-Pierre** (55,481 / −21,339), **Cilaos** (55,471 / −21,136).

- **WFS** → `RESULTTYPE=hits` sur la boîte Réunion (`> 0` features ?). Preuve quantitative, 1 requête.
- **WMS / WMTS / TMS** → une image sur chaque point témoin, jugée **non vide** si elle a >2 couleurs
  (raster) ou une tuile PBF non triviale (vecteur TMS). Tuiles WMTS re-testées à bas zoom (z≤13) pour
  les couches petite échelle dont z15 renvoie 404.

Verdict par couche : **couvre / déclarée mais vide / indéterminé**.

| Verdict | Nombre | Lecture |
|---|--:|---|
| **couvre La Réunion** | **433** | données réellement présentes sur l'île |
| **déclarée mais vide** | **218** | bbox large (souvent métropole/monde), 0 donnée au-dessus de Réunion |
| **indéterminé** | **16** | non testable par la sonde |

Les 218 « vides » sont cohérentes : Conservatoire du littoral, zonage Pinel, réseaux de chaleur
métropolitains, cartes CORINE métropole, couche test « Le Havre »… déclarés sur un pavé large,
transparents sur les 3 témoins. Les **16 indéterminés** sont **14 rasters altimétriques bruts**
(RGE ALTI, LiDAR HD MNT/MNS/MNH, pentes, estompage — non rendus par une sonde image, **mais que
LABUSE possède déjà**) + 2 types WFS en erreur 400 (extension BD TOPO, RPG codes cultures — aussi
présents chez LABUSE).

> ⚠️ **Limite de méthode.** Pour les couches **vecteur servies seulement en WMS** (sans WFS),
> le test est une image : une couche à objets très épars pourrait être jugée « vide » si les 3
> témoins tombent à côté. Le WFS (exact) a servi de juge dès qu'il était disponible (≈240 couches).

## 4. Comparaison avec LABUSE

Deux référentiels : les **couches déclarées** (`declarations/couches/*.yaml`, 52 surfaces) et les
**sources en base** (`data_sources`, 118 actives). Rapprochement (`03_match.py`) par, dans l'ordre :
(1) **identifiant geopf cité en dur dans le dépôt** (preuve la plus forte — ex. `ORTHOIMAGERY.ORTHOPHOTOS`,
`BDTOPO_V3:`, `IGNF_LIDAR-HD_MNH…`), (2) **règles de titre curées** (espaces protégés, GPU/PLU, EPCI…),
(3) **recouvrement d'au moins 2 jetons** du titre avec un nom de couche puis de source (le seuil à 2
évite les faux positifs du type « CORINE *haute* résolution » ↔ « lignes *haute* tension »).

> Sur les **433 qui couvrent La Réunion** :
> - **déjà en couche : 33**
> - **en base mais pas en couche : 233**
> - **absente : 167**

Le rapprochement est **sémantique et best-effort** : LABUSE ingère souvent la donnée IGN par un
autre chemin que la couche geopf (ex. ZNIEFF via l'INPN, PLU via l'API Carto GPU). Les cas limites
sont notés ci-dessous ; **Vic tranche**.

---

## 5. Les absentes qui couvrent La Réunion — par famille de produit

Les 167 couches absentes se ramènent à **35 familles** (le détail couche par couche est dans
`GEOPF-REUNION.csv`, colonne `presence_labuse = absente`). Groupées par thème :

### Occupation du sol
- **CORINE Land Cover** — *55 couches* (CLC/CHA 2000→2018, vecteur + raster + DOM). Produit
  **européen grossier** ; LABUSE a déjà l'OCS GE, CoSIA et BD CARTO (occupation fine). Redondant
  sur le fond, mais c'est la seule série *historique harmonisée* 2000→2018. → *doublon fonctionnel*.

### Points d'intérêt & équipements — *28 couches*
- POI IGN : écoles (maternelle/élémentaire/secondaire/supérieur), gares, hôpitaux/santé,
  établissements pour personnes âgées, thermes, pompiers-secours, police-gendarmerie, campings,
  musées, stades, complexes sportifs, **piscines**, offices de tourisme, POI social/santé,
  droit/justice, sécurité/défense, travail/emploi, associations/culture, administration locale.
- **LABUSE a l'équivalent** via **BPE INSEE** + **OSM équipements**. → *équivalent existant*
  (l'apport serait la maille et la fraîcheur IGN, pas la donnée).

### Fonds de carte / habillage — *16 couches* → *cosmétique*
- SCAN 25 / SCAN 50 (1950), Carte littorale SHOM/IGN, Carte des pentes (+ PAC), Plan IGN J+1,
  Natural Earth / mini-vue / carte mondiale, EduGéo Réunion 1980, habillages du Plan IGN,
  estompage du relief. LABUSE a déjà le Plan IGN v2 et la BD ORTHO comme fonds.

### Environnement / biodiversité — *~12 couches* → *pertinent, à regarder*
- **Mesures compensatoires** des atteintes à la biodiversité (5), **CarHab** habitats naturels
  Réunion (2), **OFB** zones nécessitant l'avis du gestionnaire (2), **INPE** inventaire national
  des plans d'eau (1), **régions écologiques** (1), **stations qualité de l'air** (1).

### Énergie / EnR — *~6 couches* → *pertinent, à regarder*
- **Potentiel éolien / photovoltaïque « clé en main »** (4) + **unités foncières avec surfaces de
  stationnement** photovoltaïsables (2, loi APER) + **contraintes réglementaires EnR près des
  habitations** (1) + **consommation d'électricité par commune** (1). Directement utile au foncier.

### Patrimoine — *7 couches*
- Atlas des patrimoines : patrimoine architectural/urbain, culturel, naturel, conservation.
  LABUSE a déjà l'ABF/monuments et la ZPPA ; recouvrement partiel.

### Urbanisme — *2 couches* → *pertinent*
- **SCOT** (schéma de cohérence territoriale) + son périmètre. LABUSE a le SAR et les PLU, **pas
  le SCOT**.

### Tourisme (labels) — *5 couches*
- Stations classées / stations vertes, Pavillon bleu, Clef verte. → *marginal*.

### Aérien / réglementaire — *3 couches*
- Zones interdites à la captation aérienne (2), restrictions drones UAS (1). → *niche*.

### Réseaux géodésiques IGN — *8 couches* → *hors-sujet foncier*
- RGP (GNSS permanent), réseau de détail, nivellement, points matérialisés, RBF. Techniques.

### Divers à signaler
- **Sites et territoires d'exception de La Réunion** (1, spécifique Réunion) ;
  **Prairies permanentes 2024 / zones humides BCAE** (1, PAC) ; **Prédictions de marée SHOM** (1) ;
  **Toponymes / noms géographiques** (2) ; **Nature en Ville 2021-2023** (1) ; **Parkings >500 m²**
  (1, équivalent OSM APER chez LABUSE) ; **Régions 2017 / Académies** (admin, LABUSE a ADMIN EXPRESS).

### Couches de test / hors-sujet — *8 couches* → *à ignorer*
- `voeuxWFS`, `festivals par département`, `régions test cerema`, `test datacenters`,
  `Produits`, `Communication` / `télécommunication`, `tests sur carroyage INSEE`,
  `DGCL DGF voirie retenue`, `RPG Métropole de Lyon` (métropole — faux « couvre » de bbox WFS).

---

## 6. Chiffres récapitulatifs

| Étape | Nombre |
|---|--:|
| Couches brutes (5 services) | 3 285 |
| **Dédoublonnées** | **1 407** |
| … dont emprise déclarée croise Réunion | 643 |
| **Couvrent réellement La Réunion (testé)** | **433** |
| Déclarées mais vides sur Réunion | 218 |
| Indéterminées | 16 |
| Couvrent & **déjà chez LABUSE** (33 couche + 233 base) | **266** |
| Couvrent & **absentes de LABUSE** | **167** (≈ **35 familles**) |

## 7. Fichiers produits

- **`GEOPF-REUNION.csv`** — les 667 couches testées : `identifiant, titre, producteur_theme,
  service, verdict_reunion, presence_labuse, labuse_quoi, labuse_preuve, methode_test, detail_test`.
- `layers_raw.json` / `layers_dedup.json` — inventaires brut & dédoublonné.
- `probe_results.json` / `matched.json` — résultats du test réel + rapprochement LABUSE.
- `absentes_familles.json` — les 35 familles absentes.
- `cache/getcap_*.xml` — les 5 GetCapabilities (preuve, reproductible).
- Scripts : `01_parse.py` (inventaire+dédoublonnage) · `02_probe.py` (filtre+test) ·
  `04_reprobe.py` (re-test des indéterminés) · `03_match.py` (rapprochement LABUSE) ·
  `05_rapport.py` (agrégation). `venv/` (Pillow) non versionné.

*Pas de recommandation : ce rapport dresse la carte, Vic choisit les couches à ajouter.*
