# PAU CoSIA — Phase 2 : BLOCAGE source canonique (STOP avant construction)

**Exigence #1 (Vic) : « pointe la couche CoSIA CANONIQUE, jamais qa_cosia_bati. Si la couche
canonique n'existe pas en base, dis-le AVANT de construire — on l'ingérera au standard
plutôt que de servir un proxy de mesure. »**

## Constat : la couche CoSIA canonique EN GÉOMÉTRIE n'existe pas.

Le recalcul PAU (`build_pau`, `rnu.py:149-158`) clusterise des **géométries de bâtiments**
(`ST_ClusterDBSCAN(ST_Centroid(geom))`). Il lui faut donc une couche de **footprints CoSIA**.
État mesuré en base :

| objet | contenu | géométrie ? | statut | verdict |
|-------|---------|-------------|--------|---------|
| `qa_cosia_bati` | 445 190 polygones (24 communes) | **oui** | écrit uniquement par `qa/dette4/*` et `qa/cosia/*` | **QA — interdit** (préfixe `qa_`) |
| `p_model_bati_cosia` | 321 314 lignes, `emprise_cosia_m2` par idu | **non** (aire seule) | canonique (lu par `bati_revele.py`, `verdict_servi.py`, `p_model/sql.py`, faisabilité) | **canonique mais inclusterisable** |
| `spatial_layers kind='batiment_cosia'` | — | — | n'existe pas | absent |
| `src/labuse/ingestion/cosia.py` | — | — | **n'existe pas** | absent |

- **Aucun module d'ingestion CoSIA** dans `src/labuse/ingestion/` (40 modules y sont, dont le
  patron bâtiment `layers_ingest.py:607 ingest_batiments` → `_insert_layer(…, "batiment", …)`).
- **Aucune source brute CoSIA versionnée** sur disque (pas de `.gpkg/.shp/.parquet/.geojson`).
- `p_model_bati_cosia` a été peuplée **hors dépôt** (aucun INSERT/CREATE dans le code) ; seule
  survit l'aire par parcelle, pas les footprints.
- La seule géométrie CoSIA (`qa_cosia_bati`) est un **artefact de contrôle** — recoupé à 0,5 %
  près avec le canonique (valable pour CHIFFRER en Phase 1, cf. `PAU_COSIA_MESURE.md`, mais
  **pas** pour SERVIR en production).

**Conclusion : on ne peut pas faire un échange de source propre (BD TOPO → BD TOPO + CoSIA)
aujourd'hui, parce que la source CoSIA canonique en géométrie n'est pas en base.** Câbler
`build_pau` sur `qa_cosia_bati` reviendrait exactement à « servir un proxy de mesure » — ce que
l'exigence #1 interdit. Je m'arrête donc AVANT de construire, comme demandé.

## Ce qu'il faut pour lever le blocage — ingestion au STANDARD

Path recommandé (**A**) :
1. **Source brute CoSIA** (classe « bâtiment » PVA juil.-août 2025, 20 cm) fournie/re-téléchargée
   — le même jeu qui a produit `p_model_bati_cosia`.
2. Nouveau module `src/labuse/ingestion/cosia.py` au patron des autres ingestions
   (idempotent, `source_millesime`, CLI `labuse ingest-cosia`), matérialisant une couche
   canonique de footprints — au choix arbitré :
   - `spatial_layers kind='batiment_cosia'` (réutilise l'infra couches, le plus léger), **ou**
   - table dédiée `cosia_bati(geom_2975, source_millesime, computed_at)`.
3. (Optionnel, cohérence) re-dériver `p_model_bati_cosia` DEPUIS cette couche canonique, pour
   qu'aire-par-parcelle et footprints aient la même provenance tracée.

Path compromis (**B**, NON recommandé) : promouvoir les polygones déjà en base
(`qa_cosia_bati`) vers une table canonique via une ingestion propre. Rapide, mais ça
**blanchit un artefact QA** — contraire à l'esprit de l'exigence #1. À n'envisager que si la
source brute est irrécupérable.

## Ce qui est PRÊT à couler dès que la couche canonique existe (déjà spécifié, non écrit)

- `build_pau` : `src` = BD TOPO **∪** CoSIA canonique, **déduplication DANS le geste** —
  la clause `AND NOT EXISTS (SELECT 1 FROM <bdtopo> b WHERE ST_Intersects(b.geom, c.geom))`
  écarte les 2 390 footprints partagés AVANT le clustering (jamais comptés deux fois).
- **Test** prouvant la dédup : sur St-Philippe, `count(source clustering)` =
  `count(BD TOPO) + count(CoSIA nouveaux)` et **≠** `count(BD TOPO) + count(CoSIA total)` ;
  assert `footprints_partagés = 2 390` retirés.
- **Avertissement PAU inchangé** (`rnu.py:36 AVERTISSEMENT_PAU`) : la PAU gagne en qualité mais
  reste **Estimé** — nature inchangée. Test que `rnu_block` sert toujours `avertissement_pau`.
- **Vérif cible** (jeu médian, source dédupliquée) : PAU **2 655 parcelles / 47 noyaux**,
  plancher **1 145**, **0 sortant** ; golden 119/119, tsc 0, build.

## Décision attendue de Vic
- Fournir la source brute CoSIA (Path A, recommandé), **ou** autoriser le Path B (promotion de
  l'artefact), **ou** trancher le réceptacle canonique (`spatial_layers kind='batiment_cosia'`
  vs table dédiée). Rien n'est construit tant que ce n'est pas tranché.

## DÉCISION VIC (22/08/2026)
- **Path A** — source brute CoSIA fournie, ingestion `cosia.py` écrite au standard.
- Réceptacle : **`spatial_layers kind='batiment_cosia'`**.

### Bloquant restant : le fichier source
Vérifié : **aucune source brute CoSIA sur le système** (ni dans le dépôt, ni dans
~/Desktop · ~/Downloads · ~/Documents · /tmp · /Volumes — seuls des PDF de QA survivent).
`p_model_bati_cosia` et `qa_cosia_bati` ont été peuplés hors dépôt à partir d'un fichier qui
n'est plus sur disque.

**À fournir par Vic pour couler la Phase 2 :** le fichier CoSIA « bâtiment » PVA 2025 (Réunion),
format vectoriel (`.gpkg` / `.shp` / `.parquet` / `.geojson`), déposé p. ex. dans `data/cosia/`.
Dès qu'il est là : j'inspecte son schéma réel, j'écris `ingestion/cosia.py` (idempotent,
`source_millesime`, CLI `labuse ingest-cosia`) → `spatial_layers kind='batiment_cosia'`, puis je
câble `build_pau` (union + dédup dans le geste), le test des 2 390 partagés, la vérif
avertissement PAU inchangé, et les cibles 2 655 / 47 / 1 145 / 0 sortant + golden/tsc/build.
Le module sera écrit contre le schéma RÉEL du fichier (pas deviné).

## SOURCE OFFICIELLE TROUVÉE (IGN Géoplateforme, vérifiée en ligne 22/08/2026)

CoSIA v1.0, département **D974 La Réunion**, millésime **2025** (= celui déjà en base,
« CoSIA 2025 PVA juil.-août 2025 »). C'est du **VECTEUR GPKG** (pas du raster) :
`gpf_dl:mime_type = application/geopackage+sqlite3`, classe **« Bâtiment » = classe 1 des 15**
de la nomenclature. Cohérent avec les polygones `qa_cosia_bati` déjà en base (mêmes footprints).

| champ | valeur |
|-------|--------|
| Produit | CoSIA 1.0 — Couverture du Sol par IA (dérivé OCS GE, segmentation d'ortho) |
| Zone | D974 La Réunion |
| Millésimes dispo | 2017, 2022, **2025** (prendre 2025) |
| Format | GPKG vecteur (polygones), archive **.7z** |
| **CRS** | **EPSG:2975 (RGR92 / UTM 40S)** — identique à `geom_2975`, **aucune reprojection** |
| Taille | **517 812 160 octets ≈ 494 Mio** (compressé .7z) |
| MD5 | `e377864d3b75a45d28c0da11321e28f2` |
| Licence | **Licence Ouverte 2.0 (Etalab)** |
| URL directe | `https://data.geopf.fr/telechargement/download/COSIA/COSIA_1-0__GPKG_RGR92UTM40S_D974_2025-01-01/COSIA_1-0__GPKG_RGR92UTM40S_D974_2025-01-01.7z` |
| Catalogue | `https://geoservices.ign.fr/telechargement-api/COSIA` (filtre zone D974) |
| API liste | `https://data.geopf.fr/telechargement/resource/COSIA?zone=D974` |

HEAD vérifié vivant : `HTTP/2 200`, `content-type: application/x-7z-compressed`, `content-length: 517812160`.

### Commande de téléchargement (depuis le dépôt)
```
mkdir -p data/cosia && cd data/cosia
curl -L -o COSIA_D974_2025.7z \
  "https://data.geopf.fr/telechargement/download/COSIA/COSIA_1-0__GPKG_RGR92UTM40S_D974_2025-01-01/COSIA_1-0__GPKG_RGR92UTM40S_D974_2025-01-01.7z"
md5 COSIA_D974_2025.7z   # attendu : e377864d3b75a45d28c0da11321e28f2
7z x COSIA_D974_2025.7z  # nécessite p7zip : brew install p7zip
```
Prérequis outils Phase 2 (absents localement, mesuré) : **p7zip** (extraction) et **GDAL/ogr2ogr**
(lecture GPKG → PostGIS) — `brew install p7zip gdal`. À défaut de GDAL, lecture possible via
Python (fiona/geopandas dans le venv) — à vérifier au moment de l'ingestion.
