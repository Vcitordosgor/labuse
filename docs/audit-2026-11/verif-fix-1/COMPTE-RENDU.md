# VERIF-FIX-1 — les corrections de VERIF-2

**Branche** `fix/verif-fix-1` · worktree `~/Desktop/labuse-verif-fix` · Opus · base locale `labuse` (run servi **q_v20**) · **aucun merge, aucun accès prod**. Date : **2026-11-09**.

Ce document corrige les écarts relevés par l'audit `docs/audit-2026-11/verif-2/RAPPORT.md`. Chaque section dit ce qui était faux, le correctif, et la mesure **avant/après** (l'environnement Python du projet est cassé — `sqlalchemy`/`pytest` absents, comme au moment de VERIF-2 ; les captures sont donc des mesures `psql` réelles et les portes front, pas des copies d'écran de l'app bootée).

---

## 1 · La 3D — les bâtiments de l'ortho retrouvent leur volume (Q4)

**Constat VERIF-2.** Le filtre de hauteur `(attrs->>'hauteur') IS NOT NULL` s'appliquait **avant** le JOIN LiDAR : un bâtiment BD TOPO sans hauteur propre mais couvert par un faîtage `batiment_hauteur_lidar` était jeté, alors que sa hauteur mesurée existait à portée de JOIN.

**Correctif** (`src/labuse/api/app.py`, `map_batiments_geojson`). Le filtre devient `(hl.faitage_m IS NOT NULL OR (attrs->>'hauteur') IS NOT NULL)` — on retient le bâtiment dès qu'**une** hauteur existe (LiDAR mesuré OU BD TOPO déclarée). Aucune extrusion inventée : les deux manquantes → toujours exclu. Le `COALESCE(faitage_m, hauteur)` préférant le LiDAR, les ~3 900 bâtiments à `hauteur='0'` dont la parcelle a du LiDAR s'extrudent désormais à leur vraie hauteur.

**Mesure avant/après — part des bâtiments avec volume, 3 communes** (géométries distinctes `kind='batiment'`) :

| Commune | Bâtiments | AVANT (hauteur BD TOPO) | APRÈS (BD TOPO ∪ LiDAR) | sans volume : avant → après |
|---|---|---|---|---|
| Saint-Denis | 60 771 | 50 186 (82,6 %) | **60 734 (99,94 %)** | 10 585 → **37** |
| Saint-Paul | 83 268 | 73 219 (87,9 %) | **83 246 (99,97 %)** | 10 049 → **22** |
| Le Tampon | 74 136 | 65 107 (87,8 %) | **74 127 (99,99 %)** | 9 029 → **9** |

Sur une BBOX dense de Saint-Denis (le chemin réel de l'endpoint) : **3 592 → 4 271** bâtiments servis (+18,9 %), tous avec hauteur, dont 4 253 en faîtage LiDAR mesuré. Le reliquat sans volume (quelques dizaines par commune) = les parcelles sans aucun LiDAR ET sans hauteur BD TOPO (jamais inventé).

**Empreintes CoSIA sans hauteur — coût et méthode (NON fait, demandé en analyse seule).**
- *Gisement.* `batiment_cosia` = **445 190** empreintes (CoSIA 2025, PVA 20 cm), attrs = `classe`/`source_millesime` seulement — **aucune clé de hauteur**. **133 281** sont des slivers < 10 m² (à filtrer). Les ~13 % qui n'intersectent aucun bâti BD TOPO (≈ 58 000) sont le bâti réellement invisible en 3D.
- *Méthode.* Identique à `faisabilite/hauteur_lidar_dalles.py` mais **par empreinte CoSIA** au lieu de par parcelle : pour chaque dalle 1 km de la grille IGN LiDAR HD, télécharger MNS (`…HIGHRES.MNS`) + MNT (`…HIGHRES`), hauteur = **percentile du MNH (MNS−MNT)** sous le polygone CoSIA, écrire dans une table `batiment_cosia_hauteur` (clé géométrique, pas `idu`), supprimer les TIF. Filtrer les slivers < 10 m² en amont.
- *Coût.* Aucune donnée amont nouvelle (le MNS/MNT HIGHRES est déjà la source du LiDAR existant). C'est un **repasse des 2 665 dalles** de l'île (les TIF sont supprimés après mesure, ~3 Go de travail disque, borné), donc **du même ordre que la passe LiDAR île-entière déjà faite** (DB-bound, quelques heures → ~1 jour sur une machine, reprenable par dalle). Stockage : +1 ligne par empreinte retenue (~312 000 après filtre slivers). Aucune ingestion réseau nouvelle.

---

## 2 · Les couches cassées (Q2-b)

### `vefa_neuf` — re-branchée sur sa source
Orpheline (`data_source_id` NULL sur les 24 lignes, millésime/date absents en admin). La donnée vient des **mutations VEFA DVF (DGFiP)** (le prix et la géométrie ; Sitadel ne fournit qu'un attribut d'offre). Re-branchée sur la source **« DVF / valeurs foncières »** (`ingestion/vefa_neuf.py` : résolution de l'id + colonne `data_source_id` à l'INSERT ; backfill des 24 lignes existantes).

**Avant → après :** `vefa_neuf` 24 lignes, `data_source_id` **0/24 → 24/24**.

### `pole_echange` — filtre réparé
Le YAML déclare `filtre subtype=osm` (commentaire explicite : *« seuls les pôles OSM sont peints ; les gtfs étaient à opacité 0 côté legacy »*), mais ce filtre n'était que front : le tuyau servait les 61 lignes. Ajout de `"pole_echange": [("pole_echange", ("osm",))]` à `_RESOLUTION_OVERRIDE` (`api/couches_tuyau.py`) → le filtre s'applique à la source, le verrou lit la même résolution.

**Avant → après :** servi **61 (osm 42 + gtfs 19) → 42** (osm), conforme à la déclaration.

### `courbes_niveau` & `enr_habitation` — source déclarée
Couches raster front-only (WMTS IGN en direct) dont la source n'était qu'une chaîne en dur dans le « i ». Déclarées au **même robinet que toute couche** : ajoutées à `/map/couches-info` (`api/app.py`) avec leur source IGN (ELEVATION.CONTOUR.LINE / ENR.PERIMETRE.HABITATION) ; le front rend `meta.source` et la prose du « i » ne garde que la description (plus de doublon). Test `test_circuit2_lot5` élargi en conséquence.

### `scot` — reste exclue (inchangé, conforme au mandat).

---

## 3 · La fraîcheur côté admin — échéance réelle + « à vérifier » (Q2-c)

**Constat VERIF-2.** Machinerie de fraîcheur **inerte** pour les couches carte (toutes `sans_echeance`) ; et la fraîcheur se mesurait sur la date de **synchro**, pas sur l'âge **réel** de la donnée — une couche re-synchronisée récemment mais dont la géométrie date de 2020 (HTA EDF) paraissait « à jour ».

**Correctif.** Nouveau module `src/labuse/echeances_couches.py` : chaque source de la carte porte une **échéance de revue** ancrée sur la date **réelle** de la donnée (millésime), + une fenêtre de revue de **24 mois**. Au-delà → « à vérifier ». Aucune échéance inventée : les dates réelles sont curées là où le texte amont est muet ou trompeur (EDF : « publié 2025 » mais géométrie 2020) ; une archive figée (cadastre 1877, SCAN 50) ou sans date lisible ne porte **aucune** échéance.
- **Admin / page Données** (`api/dashboard.py` + `circuit_etats.py` + `admin/circuit/Sources.tsx`) : nouvel état **« à vérifier »** (ambre), calculé en direct sur l'âge réel, placé après « nouvelle version » et « sonde en panne ». Les 8 couches anciennes remontent (6 en « à vérifier », CBS bruit déjà en « nouvelle version », OCS GE en « sonde en panne » — toutes surfacées, aucune en vert « à jour »).
- **John** (`john/contexte.py`) : `sources()` expose `couches_a_verifier` — nom, millésime servi, échéance, **amont à surveiller** (producteur + méthode de veille).
- **Côté client : RIEN ne change** — aucune échéance ni millésime affichés (décision PAGE-SOURCES-1 préservée).
- Persistance : `ensure_echeances_couches` écrit `source_horizon_at` (si absent) + `prochain_millesime_at` (l'échéance), appelé au boot ; les lecteurs calculent aussi en direct (immédiat, cohérent).

**Mesure.** 24 sources carte portent désormais une échéance ; **8 remontent « à vérifier »** — exactement les couches anciennes :

| Couche | date réelle | échéance | remonte |
|---|---|---|---|
| Ravines / DPF | 2006-08-21 | 2008 | ✅ à vérifier |
| GéoLittoral (trait de côte) | 2018 | 2020 | ✅ à vérifier |
| Zones humides (inventaires) | 2019 | 2021 | ✅ à vérifier |
| EDF lignes HTA | 2020-02 | 2022 | ✅ à vérifier |
| Parc national | 2021 | 2023 | ✅ à vérifier |
| OCS GE | 2022 | 2024 | ✅ (sonde en panne — surfacé) |
| Cartes de bruit (CBS) | 2022 | 2024 | ✅ (nouvelle version — surfacé) |
| Classement sonore | 2023-12 | 2025 | ✅ à vérifier |

Les couches récentes (BPE 2025, GTFS 2026, PPR 2026…) portent une échéance **future** et ne remontent pas.

---

## 4 · L'ortho IGN — plus codée en dur + contrôle de millésime Réunion (Q3)

**Constat VERIF-2.** Couche `ORTHO-EXPRESS.2025` **codée en dur** (`ortho_proxy.py:54`) ; l'IGN a **renommé** la famille pour 2026 (`ORTHO-EXPRESS.*` → `RVB-EXPRESS.*`) → une bascule future n'est pas automatique, et un simple « +1 année » échouerait.

**Correctif.**
- **De-hardcodé** (`api/ortho_proxy.py`) : la couche servie est une config overridable `LABUSE_ORTHO_EXPRESS` (défaut `…ORTHO-EXPRESS.2025`) — bascule sans toucher au code.
- **Contrôle** (`sentinelle.py`, nouvelle méthode `ortho` sur la source « BD ORTHO 20 cm (IGN) ») : lit le **GetCapabilities WMTS IGN** (tous les millésimes publiés, **ancien ET nouveau nommage** `RVB-EXPRESS`), prend le plus récent, et **confirme la couverture Réunion** par une tuile témoin à Saint-Denis. Une 404 (publié métropole mais pas encore l'île) → on ne crie pas. Dès que l'île est couverte et que c'est plus récent que le servi → **« nouvelle version »** dans la page Données (et chez John via `nouvelles_versions`).

**Comportement vérifié** (logique, http mocké) :
- état actuel (RVB-EXPRESS.2026 existe mais **404** à La Réunion) → **« à jour »**, message « 2026 publiée mais hors Réunion (servi 2025) ».
- futur (2026 couvre l'île) → **« nouvelle version »** (`RVB-EXPRESS.2026`).

---

## Les portes (ce que j'ai pu exécuter ici)

| Porte | Résultat |
|---|---|
| `scan_secrets.sh` | ✅ rien trouvé |
| Front `tsc -b` | ✅ 0 erreur |
| Front `vitest run` | ✅ **308 / 308** (65 fichiers) |
| `py_compile` (10 fichiers modifiés) | ✅ OK |
| Logique `echeances_couches` (stdlib) | ✅ 9/9 cas (8 flag attendus) |
| Logique `sonder_ortho` (mock) | ✅ 3/3 cas |
| **pytest** (unitaires + db) | ⏳ **non exécuté ici** — venv projet cassé (`sqlalchemy`/`pytest` absents, comme à VERIF-2). Tests ajoutés (`tests/test_verif_fix_1.py`) + `tests/test_circuit2_lot5.py` élargi ; à vérifier en CI/hook sur un env Python complet. |
| Cohérence (12 témoins) | ⏳ idem (exige l'app bootée) |

**Tests ajoutés.** `tests/test_verif_fix_1.py` (échéances + ortho, sans base) ; `tests/test_circuit2_lot5.py` (couches-info sert aussi les 2 raster).

## Fichiers touchés
- **Q1** `frontend/src/lib/strings.ts` (exemples du Signal réels, accès/terrain = faisabilité).
- **Q4** `src/labuse/api/app.py` (filtre 3D après JOIN LiDAR).
- **Q2** `src/labuse/api/couches_tuyau.py` (pole_echange), `src/labuse/ingestion/vefa_neuf.py` (source DVF), `src/labuse/api/app.py` (couches-info raster), `frontend/src/components/map/CouchesTuyau.tsx` (prose raster).
- **Q2-c** `src/labuse/echeances_couches.py` (neuf), `src/labuse/api/dashboard.py`, `src/labuse/circuit_etats.py`, `src/labuse/john/contexte.py`, `src/labuse/models.py` (boot), front `admin/circuit/Sources.tsx` + `types.ts`.
- **Q3** `src/labuse/api/ortho_proxy.py` (de-hardcode), `src/labuse/sentinelle.py` (méthode `ortho` + seed).

---

## Note : « Comprendre l'analyse » (Q1)

Le panneau client (`frontend/src/lib/strings.ts`, bloc `comprendre`) est corrigé :
- **Signal** : les exemples deviennent ceux du modèle réel q_v15 — *« rotation des ventes du secteur, ancienneté de détention, ancienneté du dernier permis, sous-densité du bâti »* (fin de « succession / société en difficulté », qui ne sont pas des variables du signal 12 mois).
- **Classement** : accès et terrain ne sont plus présentés comme des *contraintes retirées* mais comme ce qui fait **baisser** la faisabilité : *« une fois retirées les contraintes de zonage et de risques, puis vérifiée la faisabilité du terrain (accès, pente, forme) »* — en accord avec la ligne « Ce qui fait descendre ».

Les écarts Q1-② (le faux négatif `terrain_exigu` sous la bande 0) relève du moteur de faisabilité, hors du périmètre « texte » de ce mandat — laissé tel quel, signalé.
