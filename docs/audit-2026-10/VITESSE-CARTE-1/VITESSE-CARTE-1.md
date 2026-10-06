# VITESSE-CARTE-1 — où la carte et les couches passent leur temps, et comment accélérer sans toucher la donnée

> **Audit de vitesse, LECTURE SEULE.** Aucun correctif, aucun run, aucun `VACUUM`, aucun index créé,
> aucune tuile regénérée, aucune donnée/géométrie modifiée. Seul ce rapport (+ `harnais/` + `mesures/`)
> est commité. Vic tranche ; un mandat **VITESSE-CARTE-FIX-1** suivra.
>
> **Contrainte absolue, re-vérifiée à chaque piste :** aucune donnée ni géométrie altérée — pas de
> simplification de géométrie, pas d'arrondi de coordonnées, pas de généralisation par zoom, pas de
> couche tronquée, pas d'objet écarté. Les couches restent visibles à tous les niveaux de zoom
> (décision du 05/10). Toute piste qui demanderait de dégrader la donnée est **écartée** (§7), pas proposée.

## En-tête — cadre de mesure

| | |
|---|---|
| Branche / worktree | `audit/vitesse-carte-1` · `~/Desktop/labuse-vitessecarte` |
| Commit `main` de départ | `27624c22` (Merge 'origin/fix/revente-libelle') |
| Run servi | **`q_v16`** (`config/served_run.txt` ; tuiles `mvt_meta.run_label = q_v16`, `perime=false`) |
| Base | PostgreSQL **18.4** aarch64 · `localhost:5432/labuse` — **unique et PARTAGÉE** |
| Machine | MacBook Air M1 (8 cœurs) · API sondée **1 worker uvicorn** sur **:8710** · front = **build de PROD** servi par FastAPI `StaticFiles` `/socle/` + `GZipMiddleware` |
| Prod (référence, non re-SSH) | 6 vCores / **5 workers** · Caddy `encode gzip` (ni brotli ni zstd) · **tuiles en `reverse_proxy` NON cachées par Caddy** · assets immuables 1 an (VITESSE-AUDIT-1 §P, `deploy/Caddyfile.prod:24,56,69`) |
| Outillage (rejouable) | `harnais/server_tiles.sh` (banc tuiles serveur curl+ETag) · `harnais/sonde_app.py` (sonde ASGI, split SQL/Python, réutilisée de VITESSE-AUDIT-1) · `harnais/boot_app.mjs` (cascade réseau du boot, Playwright) · `harnais/carte_bench.mjs` (banc **navigateur** carte/couches : activation de couches, pan, 2D/3D). Bruts dans `mesures/`. |

> **⚠ Réserve de fidélité — base sous contention réelle.** Pendant toute la mesure, **~5 autres
> sessions `labuse`** (ports 8709/8814/8815/8817 + un build de tuile de 22 s observé dans
> `pg_stat_activity`) frappaient la base partagée. Les **temps mur absolus sont donc bruités à la
> hausse**. Les conclusions structurelles s'appuient sur des grandeurs **insensibles à la contention** :
> `EXPLAIN (ANALYZE, BUFFERS)` (plan, pages lues), **nombre d'objets par tuile**, **octets des tuiles**,
> et le **split SQL/Python** de la sonde. Les temps sont donnés avec ce caveat ; le **classement** des
> goulots, lui, tient.

---

## 0. Fait majeur d'entrée : l'antériorité est en partie PÉRIMÉE

Le mandat demandait de relire VITESSE-AUDIT-1 et notait que **« FIX-2 cache des tuiles à froid n'a
jamais été fait »**. **Ce n'est plus vrai sur `main`.** L'audit **CARTE-VITESSE-1/2** (sept. 2026) a été
**mergé** (`62cb6f57`, `faa0a3af`, `76eeff9a`, tous ancêtres de HEAD) et a livré, **pour la couche
parcelles uniquement** :

- **R1** — cache **persistant** des tuiles **parcelles** z9-z11 (`mvt_tile_cache`, 64 tuiles, traverse les
  5 workers, pré-chauffé à chaque `build-mvt`) → tuile z9 servie en **~5 ms** au lieu d'un `ST_AsMVT`
  (`tiles.py:575-671`). **Mesuré : présent, 64 tuiles, `perime=false`.**
- **R2** — code-split du monolithe `index` : **276 Ko gz → 52 Ko gz** (mesuré sur le build : `index` 52 Ko,
  `Fiche` 106 Ko et `AdminView` 52 Ko sortis en lazy). FCP froid ~**0,46 s**.
- **R3** — **ETag fort** (md5 du contenu) + 304 sur les tuiles parcelles (`tiles.py:703-718`). **Mesuré.**
- **R4** — mémoïsation du plan des couches (`/map/tuyau/couches`) et des lecteurs YAML (`lru_cache`).

**Conséquence pour ce mandat :** la lenteur « tuile île à froid » de VITESSE-AUDIT-1 est **résolue pour
les parcelles**. Le gisement de lenteur restant n'est **plus** la couche parcelles — il est
**(a) les ~57 couches d'OVERLAY, qui n'ont PAS reçu le cache persistant** (seul un LRU par worker), et
**(b) le fait que la couche `limites_parcelles` est allumée PAR DÉFAUT sur la vue île** et y pèse à elle
seule plus que tout le reste. C'est là que porte ce rapport.

---

## 1. Cinq chiffres en tête

1. **Vue île par défaut = ~4,1 Mo gzip sur le fil (24 tuiles), dont les ⅔ pour UNE couche :
   `limites_parcelles`** (défaut « Repères »), servie **non cachée** en extent 4096 à **5,6 Mo bruts
   (2,0 Mo gz) pour la seule tuile z9 centrale**, générée en **~1,7 s serveur** — alors que l'aplat des
   parcelles, lui, arrive en **~5 ms** (cache R1). La couche la plus chère du boot **duplique une
   géométrie déjà servie** par la source `parcels-ile`.
2. **Les couches d'overlay n'ont AUCUN cache persistant** (seulement un LRU **par worker**, perdu au
   reboot / `build-mvt`, × 5 workers en prod). À froid, une tuile z9 d'overlay coûte **0,5 à 2,5 s de SQL
   pur** (`alea_mvt` 2,5 s, `ppr` 1,7 s, `alea_inondation` 1,5 s, `artificialisation` 0,9 s). **Chaud
   (LRU) : ~4 ms.** Tout l'écart est du `ST_AsMVTGeom`.
3. **Activer les couches coûte au NAVIGATEUR, pas qu'au serveur.** Activer 1 couche lourde = **+1,7 s de
   long-tasks** (parse worker + peinture) ; **5 couches = +4,1 s** ; zoomer à z11 avec 10 couches actives
   = **108 tuiles / 14 Mo / 5,4 s** de fil principal bloqué.
4. **Les 3 outils « île entière » peignent en GeoJSON massif, pas en tuiles** : Piscines = **6,1 Mo**
   (parcelles 3,2 Mo + points 3,0 Mo), **~90 % du temps en sérialisation Python**. Blocs fonciers 54 Ko
   (sain). « Prix neuf » (vefa) est, lui, une **tuile** légère (3,6 Ko) — déjà bon.
5. **Ouvrir une fiche depuis la carte = ~5 s, 241 requêtes SQL en série, chaud ≈ froid** (aucun cache).
   Le clic carte lui-même (`/parcels/at`) est **instantané (32 ms)** ; c'est le **handler de fiche** qui
   est lent (héritage VIT-001/002 ; la grosse requête d'intersection a été matée, le **fan-out N+1
   subsiste** et a même grossi de 148 → 241 requêtes).

---

## 2. Comment la carte est servie (rappel d'architecture, vérifié dans le code)

- **Parcelles** (couche reine) : route dédiée `/map/tiles/{z}/{x}/{y}.pbf` depuis `mvt_parcels` (238 Mo,
  431 663 lignes, geom 3857 GiST). **z9-z11 = cache persistant `mvt_tile_cache` (R1)** ; z12-15 à la volée
  (l'index GiST porte). Simplification par palier **z9=60 m, z10=30 m, z11=15 m, extent 1024** ; z12+ brut,
  extent 4096 (`tiles.py:530-531`). Attributs **maigres** z≤11 (`tier_v2, etage0, zone_fam, commune`).
  **ETag md5** + `Cache-Control: max-age=3600, stale-while-revalidate=86400`. (Déjà optimal — ne pas toucher.)
- **57 couches d'overlay** : un **tuyau unique** `/map/tiles/{kind}/{z}/{x}/{y}.pbf` (`couches_tuyau.py`),
  une requête paramétrique, extent 4096, buffer 64, reprojection 2975→3857 par tuile. Les méga-polygones
  sont **pré-découpés** (`ST_Subdivide` ≤ 256 sommets) dans des tables dérivées — `tuyau_subdivise`
  (1,76 Go, 2,25 M morceaux), `tuyau_sup` (SUP dissoute+subdivisée, 37 Mo), `tuyau_piscines`,
  `tuyau_icpe`… — **l'union des morceaux = la géométrie d'origine, AUCUNE simplification** (verrou
  `verrou_tuiles`). **Cache = LRU `_CACHE` 4096 entrées PAR WORKER, en mémoire** (`couches_tuyau.py:219`).
  **ETag faible** (chaîne `version:kind:z:x:y`, 304 sur match exact). **Aucune table persistante.**
- **Front** (`MapView.tsx`, `CouchesTuyau.tsx`) : maplibre-gl **4.7.1**, `setWorkerCount(min(4, ⌊hc/2⌋))`
  (`MapView.tsx:470-478`), style **inline minimal** (1 calque fond `#181918`), glyphs **Open Sans
  locaux** (plus de Google Fonts). Les couches sont **montées masquées** (`visibility:none`) et activées
  en basculant la visibilité — **une couche masquée ne télécharge PAS de tuile** (vérifié : `addSource`
  ne charge qu'au premier calque visible). **Par défaut, seule la famille « Repères » est cochée**
  (`COCHE_DEFAUT = famille==='reperes'` → `limites_parcelles` + `limites_communes`). Le relief 3D (bouton)
  charge un **DEM externe AWS** (`s3.amazonaws.com/elevation-tiles-prod`) + le bâti par bbox à z≥15.

---

## 3. Tableau des mesures (froid / chaud · serveur / navigateur)

### 3a. Tuiles — coût SERVEUR par couche et par zoom (St-Denis dense : z9 334/286, z11 1339/1145, z14 10715/9164)

Temps = sonde (SQL ≈ 100 % du total à froid ; **chaud = LRU ~4 ms partout**). Octets = **bruts** (le fil
est gzippé ~2,7×, cf. 3c). Objets = features dans la tuile (psql). Bruts : `mesures/server_tiles.csv`,
`mesures/sonde/`, `mesures/EXPLAINS.txt`.

| Couche | table servie | z9 froid | z9 bruts | z9 objets | z11 froid | z14 froid | cache persistant ? |
|---|---|---:|---:|---:|---:|---:|:--:|
| **parcelles** | `mvt_parcels` (+cache R1) | **~5 ms** | 0,57 Mo | 257 k | ~5 ms | 3 ms (GiST) | **OUI (R1)** |
| **limites_parcelles** ⚠défaut | `tuyau_subdivise` | **1 713 ms** | **5,61 Mo** | — | 496 ms | 109 ms | **NON** |
| **alea_mvt** | `tuyau_subdivise` | **2 517 ms** | 2,71 Mo | 51 942 | 210 ms | 47 ms | **NON** |
| **ppr** | `tuyau_subdivise` | **1 721 ms** | 2,20 Mo | 41 818 | 206 ms | 124 ms | **NON** |
| **alea_inondation** | `tuyau_subdivise` | **1 461 ms** | 1,32 Mo | — | 306 ms | 80 ms | **NON** |
| **artificialisation** (≈OCS GE) | `tuyau_subdivise` | 949 ms | 0,89 Mo | 27 043 | 254 ms | 80 ms | **NON** |
| **plu_gpu_zone** | `tuyau_subdivise` | 522 ms | 0,93 Mo | 14 043 | 199 ms | 90 ms | **NON** |
| **ebc** | `tuyau_subdivise` | 557 ms | 0,35 Mo | — | 292 ms | 36 ms | **NON** |
| **sup** | `tuyau_sup` | 559 ms | 0,51 Mo | 11 812 | 125 ms | 43 ms | **NON** |
| **znieff** | `tuyau_subdivise` | 275 ms | 0,15 Mo | — | 79 ms | 23 ms | **NON** |
| **dpu** | `tuyau_subdivise` | 115 ms | 0,08 Mo | — | 63 ms | 7 ms | **NON** |
| **icpe** | `tuyau_icpe` | 43 ms | 0,04 Mo | — | 16 ms | 6 ms | **NON** |
| **limites_communes** | `mvt_communes` | 9 ms | 2,6 Ko | 24 | 5 ms | 4 ms | **NON** |
| *(batiment — latent)* | `tuyau_subdivise` | *2 390 ms* | *2,0 Mo* | *719 349* | *1 124 ms* | *230 ms* | **NON** |

*`batiment` (zoom_min 15, `geometrie=extrusion`, `HORS_PANNEAU`) **n'est pas monté comme tuile d'overlay** :
le bâti 3D est chargé par `getBatiments(bbox)` à z≥15 via le bouton 3D. Sa tuile z9 (719 k morceaux,
2,4 s) est un **chemin latent non exercé** — à ne pas confondre avec une couche île.*

### 3b. Scénarios — NAVIGATEUR (médiane de 3 passes ; `harnais/carte_bench.mjs` + `boot_app.mjs`)

| Scénario | tuiles | octets fil | temps→idle | fil bloqué (long-tasks) | note |
|---|---:|---:|---:|---:|---|
| **1. Boot île** (parcelles + limites, défaut) froid | 53 req | **14,2 Mo** (dont limites 9,9 Mo bruts) | idle 6,5 s · **dernière parcelle 1,3 s** · FCP **0,46 s** | — | `boot_app.mjs` |
| **1. Boot île** chaud | 54 req | 14,3 Mo | idle 2,7 s · dernière parcelle 0,5 s · FCP 0,18 s | — | cache disque navigateur |
| **1bis. Île (banc maplibre)** | 24 | 4,1 Mo gz | 2,1 s | 0,5 s | parcelles+limites seuls |
| **4a. Activer 1 couche lourde** (alea_mvt) | +12 | +2,2 Mo gz | +1,8 s | **+1,7 s** | parse worker + peinture |
| **4b. Activer 5 couches lourdes** | 60 | 4,5 Mo gz | 4,2 s | **4,1 s** | |
| **4c. Activer 10 couches lourdes** | 48 | +0,9 Mo gz | 3,5 s | 3,5 s | cumulatif |
| **2. Zoom île→commune z11** (10 couches actives) | **108** | **14,5 Mo** gz | 5,5 s | **5,4 s** | re-fetch massif tous overlays |
| **2. Zoom commune→parcelle z14** | 72 | 1,8 Mo gz | 0,9 s | 0,9 s | overlays s'allègent |
| **3. Pan latéral z14** | 24 | 0,38 Mo gz | 0,2 s | 0,2 s | **déjà bon** |
| **5. Bascule 2D→3D** | 157 | 2,1 Mo gz | 3,0 s | 2,9 s | ~150 tuiles **DEM AWS externe** |
| **6. Fiche depuis la carte** (`/parcels/{idu}`) | — | 83,7 Ko | **~5,1 s (chaud ≈ froid)** | — | **241 req SQL en série**, 91 % SQL |
| **6. Clic carte** (`/parcels/at`) | — | 24 o | 32 ms | — | **déjà bon** |
| **7. Outil Piscines (île)** | — | **6,1 Mo** (GeoJSON) | ~0,4 s serveur · **~90 % Python** | — | `/prospection-piscines/{parcelles,points}` |
| **7. Outil Blocs fonciers** | — | 54 Ko | 178 ms | — | **déjà bon** |
| **7. Outil Prix neuf (vefa)** | — | 3,6 Ko (tuile) | <10 ms | — | **déjà bon** |

### 3c. Réseau

- **Compression : gzip actif** sur toutes les tuiles (`GZipMiddleware minimum_size=1024`). Ratio mesuré
  ~**2,7×** : `alea_mvt` z9 2,71 Mo → **0,99 Mo** ; `ppr` 2,20 → **0,79 Mo** ; `limites_parcelles` 5,61 →
  **2,52 Mo** ; parcelles 0,57 → **0,16 Mo**. **Ni brotli ni zstd** (ils gagneraient encore ~15-25 % sur
  du MVT, cf. §5).
- **En-têtes de cache** : tuiles parcelles **ETag md5 + SWR** (R3) → **304 à 0 octet** après `max-age`
  (vérifié). Overlays : ETag **faible** fonctionnel (304 sur match). Shell `no-cache`, assets immuables.
- **Pas de requêtes en double** notées au boot hormis le double-GET inhérent à la revalidation.
- **Dépendance externe sur le chemin de rendu** : le relief 3D tire le DEM depuis **AWS S3** (hors
  maîtrise LA BUSE, hors Caddy).

---

## 4. Les cinq goulots réels (du plus coûteux au moins coûteux)

**G1 · `limites_parcelles` allumée par défaut sur l'île, non cachée, et redondante.**
Chaque ouverture de carte (vue île = l'écran d'accueil) télécharge ~**9,9 Mo bruts / ~3,5 Mo gz** de
tuiles `limites_parcelles` en extent 4096, **générées à froid en ~1,7 s/tuile** (× 4 tuiles, × 5 workers
en prod, re-payées après chaque reboot/`build-mvt`). Or ces contours **dessinent les mêmes parcelles**
que la source `parcels-ile` déjà chargée (et cachée R1). C'est le poste n°1 parce qu'il frappe **100 %
des sessions sur l'écran par défaut**. (`CouchesTuyau.tsx:54` `COCHE_DEFAUT`, `MapView.tsx:577-578`.)

**G2 · Les couches d'overlay n'ont pas le cache persistant que les parcelles ont reçu (le « FIX-2 »
à moitié fait).** `couches_tuyau.py` ne connaît qu'un **LRU par worker** (`_CACHE`, 4096). À froid une
tuile z9 d'overlay = **0,5–2,5 s de `ST_AsMVTGeom`** (EXPLAIN : index `tuyau_subdivise_kind` **déjà
utilisé** et optimal — alea_mvt 33 k morceaux/26 k buffers *hit*, ppr 25 k morceaux/15 k buffers *read*
disque ; **ce n'est PAS un index manquant**, c'est du CPU/IO de génération). En prod (5 workers, Caddy ne
cache pas) **chaque worker paie le froid**, et tout `build-mvt` le remet à zéro. C'est exactement le
remède R1 des parcelles, **non étendu aux overlays**.

**G3 · Le navigateur bloque son fil principal sur le parse/peinture des couches lourdes.**
Activer 1 couche lourde = **+1,7 s de long-tasks** ; 5 = **+4,1 s** ; **zoomer à z11 avec 10 couches
actives = 108 tuiles / 14 Mo / 5,4 s de fil bloqué**. maplibre décode le MVT dans des workers plafonnés
à **4** (`setWorkerCount`), puis peint sur le fil principal. Ce coût est **indépendant du cache serveur**
(il reste même tuiles chaudes) — il vient du **volume d'objets** des tuiles d'overlay (extent 4096, des
dizaines de milliers de morceaux) et du nombre de couches montées simultanément.

**G4 · Les outils « île entière » peignent en GeoJSON massif sérialisé en Python.**
Piscines = **6,1 Mo** de GeoJSON (parcelles 3,2 Mo + points 3,0 Mo), **~90 % du temps en sérialisation
Python** (SQL négligeable) — même pathologie que l'ancien « Permis carte 6,45 Mo » de VITESSE-AUDIT-1
(VIT-008). Blocs (54 Ko) et Prix neuf (tuile 3,6 Ko) sont **sains**.

**G5 · La fiche ouverte depuis la carte = ~5 s, 241 requêtes SQL en série, sans cache.**
Le clic carte (`/parcels/at`, 32 ms) est bon ; le **handler de fiche** (`/parcels/{idu}`) reste lent :
**chaud ≈ froid** (aucun précalcul), **91 % SQL**, **241 requêtes en série** (c'était 148 en
VITESSE-AUDIT-1 — la grosse requête d'intersection servitudes a bien été matée par FIX-1/ORACLE-FIX-1,
mais le **fan-out N+1 a grossi**). Hors périmètre strict « carte », mais c'est l'étape 6 du mandat.

---

## 5. Pistes chiffrées — sans toucher la donnée

Gain estimé sur le **froid** (le cas qui pique). « Preuve donnée intacte » = ce qu'exigera le FIX.

| # | Piste | Goulot | Gain froid estimé | Effort | Risque | Preuve d'intégrité à exiger |
|---|---|---|---|---|---|---|
| **P1** | **`limites_parcelles` sur l'île : dessiner le contour depuis la source `parcels-ile` déjà chargée** (un calque `line` de plus sur `mvt_parcels`, qui porte la géométrie), au lieu de monter une 2ᵉ source 4096 non cachée. La couche reste activable/visible à tous zooms. | G1 | **−3,5 Mo gz et −4×1,7 s** à CHAQUE boot île | **S/M** (front) | **nul→à prouver** | capture pixel identique de la trame cadastrale île z9-z11 (le contour vient déjà d'une géométrie servie) |
| **P2** | **Étendre le cache persistant R1 aux overlays** (table `mvt_tile_cache`, pré-chauffe z9-z11 des couches lourdes dans `rebuild_mvt_servies`, invalidée au run — exactement le mécanisme parcelles). Les tuiles z9-z11 de l'île sont un **ensemble borné et figé entre deux builds** (~64/couche). | G2 | **−0,5 à −2,5 s** par tuile d'overlay, × workers, après chaque build | **M** | **nul** (hash pbf identique, mêmes octets) | md5 de chaque tuile cache == tuile à la volée (le code parcelles le fait déjà via `_parcel_tile_bytes`) |
| **P3** | **Cache des tuiles au reverse-proxy prod** (plugin Souin `cache` sur Caddy, ou directive dédiée) **+ ETag fort** (md5) sur les overlays. Supprime le coût froid **× 5 workers** et après déploiement. | G2 | **−2 à −4 s** au 1ᵉʳ visiteur prod | **S/M** | **nul** | mêmes octets, mêmes en-têtes ; 304 vérifié |
| **P4** | **brotli/zstd** en plus de gzip (Caddy `encode zstd gzip`, ou middleware). Le MVT compresse bien. | §3c | **−15 à −25 %** d'octets sur TOUTES les tuiles | **S** | **nul** | octets décompressés identiques |
| **P5** | **Chargement différé des couches lourdes** : ne monter la source qu'à l'activation (déjà le cas pour le fetch ; viser le **nombre de calques montés** et un `minzoom` de SOURCE pour les très lourdes comme on fait pour `zonage_parcelle`, **sans changer leur visibilité une fois actives**). Allège G3 au zoom. | G3 | **−1 à −3 s** de long-tasks à l'activation / au zoom | **M** | **nul→à prouver** | mêmes objets rendus une fois la couche active |
| **P6** | **Outils île en tuiles plutôt qu'en GeoJSON massif** (Piscines : servir via le tuyau `tuyau_piscines` déjà existant, ou un GeoJSON agrégé en SQL) — même pathologie que VIT-008. | G4 | Piscines 6,1 Mo → <1 Mo ; −0,3 à −0,5 s Python | **S/M** | **nul** | mêmes points/parcelles (mêmes IDU, mêmes géométries) |
| **P7** | **Fiche : paralléliser/dédupliquer les 241 requêtes** (héritage VIT-002/FIX-3) + précalcul run-scopé. | G5 | 5 s → ~1-2 s | **M** | nul→à prouver | diff JSON fiche complet sur 3 témoins |
| **P8** | **Réglages serveur** : `statement_timeout` global, pool aligné sur les threads (VIT-011). N'accélère pas le cas nominal mais **protège la carte de la contention** observée (tuiles à plusieurs s). | réserve | assurance | **S** | **nul** | non-régression suite |
| **P9** | **Pré-charger les 2 chunks JS d'entrée + `dns-prefetch`/auto-hébergement du DEM** si le 3D est sur le chemin. | boot/3D | −0,1 à −0,3 s | **S** | **nul** | mêmes octets |

### Classement gain / effort

1. **P1** (`limites_parcelles` par défaut) — frappe **tous les boots**, gros gain, effort faible, risque
   quasi nul. **À faire en premier.**
2. **P2** (cache persistant overlays = le vrai « FIX-2 ») — le plus gros gain froid structurel, **risque
   nul** (octets identiques), effort moyen.
3. **P3 + P4** (cache proxy prod + brotli) — indispensables pour la **prod à 5 workers**, risque nul.
4. **P5 / P6 / P7 / P8 / P9** — incréments, tous à risque nul→à prouver.

---

## 6. Séquence recommandée en 3 lots

- **Lot 1 — « l'écran par défaut » (gain immédiat, risque quasi nul).** P1 (contour île depuis
  `parcels-ile`) + P4 (brotli/zstd) + P9 (preload JS). Cible : boot île **~4 Mo → ~1 Mo** sur le fil et
  suppression de 4 générations froides de 1,7 s.
- **Lot 2 — « le vrai FIX-2 » (structurel, risque nul).** P2 (cache persistant des overlays z9-z11 dans
  `rebuild_mvt_servies`, mêmes octets, invalidé au run) + P3 (cache proxy + ETag fort overlays). Cible :
  activer n'importe quelle couche lourde en **~ms** au lieu de 0,5-2,5 s, sur les 5 workers et après
  chaque déploiement.
- **Lot 3 — « confort navigateur et outils ».** P5 (différé/`minzoom` source des très lourdes),
  P6 (outils île en tuiles), P8 (réglages serveur), puis P7 (fiche) en chantier séparé car hors carte.

---

## 7. Hors d'atteinte sans toucher la donnée — donc écarté

- **Simplifier/ré-échantillonner la géométrie des overlays** au-delà des paliers déjà calibrés des
  parcelles : interdit. Les overlays sont servis en géométrie **entière** (subdivisée sans perte) à
  extent 4096 — c'est ce qui les rend lourds, mais c'est la donnée. On ne peut que **cacher** (P2/P3) ou
  **compresser** (P4) ces octets, pas les réduire.
- **Baisser l'extent ou poser un `minzoom` de contenu** sur une couche d'overlay (cacher des objets sous
  un zoom) : interdit (« visibles à tous les zooms », 05/10). P5 ne touche que le **moment du montage**
  côté client, jamais la visibilité d'une couche active.
- **Dissoudre/agréger davantage** (p. ex. généraliser alea_mvt par zoom) : changerait le rendu/la donnée
  — écarté. La dissolution **sans perte** par famille (ex. `tuyau_sup`, union exacte) est déjà faite.
- **Tronquer un GeoJSON d'outil** (Piscines) : écarté ; P6 le **re-tuile** (mêmes objets), ne l'ampute pas.
- **Descendre le boot île sous ~1 s à froid** : le plancher restera le téléchargement/parse de
  **~0,5 Mo gz de JS** + l'init du worker maplibre — chantier front, pas un sujet « donnée ».

---

## 8. Déjà bon — ne pas toucher

1. **Cache persistant R1 des parcelles** (z9-z11, `mvt_tile_cache`, 64 tuiles, ETag md5, SWR) — tuile île
   servie en ~5 ms. Architecture juste.
2. **Paliers de simplification + attributs maigres** des parcelles (z≤11) — calibrés, **interdits** de
   retouche.
3. **Découpage sans perte des méga-polygones** (`tuyau_subdivise`/`tuyau_sup`/`tuyau_piscines`/`tuyau_icpe`)
   + index `(kind,subtype)` : EXPLAIN montre l'index **utilisé et optimal**. Le coût résiduel est du
   calcul, pas un défaut d'index.
4. **Code-split R2** (`index` 52 Ko gz), **mémoïsation R4**, **gzip**, **clic carte `/parcels/at`**,
   **pan z14**, **Blocs/Prix-neuf**, **montage masqué sans fetch** des couches inactives.

---

## 9. Doutes et limites

- **Base partagée sous contention réelle** (~5 sessions) : temps mur **bruités à la hausse**. Les
  conclusions reposent sur EXPLAIN/buffers, objets par tuile, octets, split SQL/Python — insensibles à la
  contention. Le classement tient.
- **Mono-worker local vs 5 workers prod** : le « × 5 workers » du froid (G2) est **déduit du code**
  (LRU par worker), pas mesuré en charge.
- **Prod non re-SSH** (lecture seule) : les faits Caddy (gzip-only, tuiles non cachées) viennent de
  `deploy/Caddyfile.prod` + VITESSE-AUDIT-1 §P.
- **Banc navigateur = page maplibre autonome** sur l'origine API (mêmes endpoints, même `setWorkerCount`),
  pas l'app complète — pour isoler proprement le coût carte/couches ; le boot de l'app complète est
  mesuré à part (`boot_app.mjs`). Les temps `idle` navigateur incluent la génération serveur (donc la
  contention) ; les octets et le nombre de tuiles, non.
- **`limites_parcelles` par défaut** : la mesure boot le confirme (9,9 Mo fetché). Un compte prod avec
  fond **ortho** ajouterait des tuiles raster IGN (non mesurées ici, fond « Sombre » en local).
- **Hygiène mineure** : `mvt_tile_cache` contient 1 tuile résiduelle à 0 octet sous une **version
  périmée** (`20261005124703262`) non purgée — sans effet (le service filtre sur la version courante).

---

## 10. Reproduire

```bash
# 1) build front prod + node_modules (symlink depuis le dépôt principal) :
cd frontend && ln -s ~/Desktop/labuse/frontend/node_modules node_modules && npm run build && cd ..
# 2) API sondée (venv racine), port 8710, sert /socle/ :
. ~/Desktop/labuse/.venv/bin/activate
export SONDE_DIR="$PWD/docs/audit-2026-10/VITESSE-CARTE-1/mesures/sonde" PYTHONPATH="$PWD/src" LABUSE_ENV=local
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"
uvicorn sonde_app:sonde --app-dir docs/audit-2026-10/VITESSE-CARTE-1/harnais --host 127.0.0.1 --port 8710 --workers 1
# 3) bancs :
export BASE=http://127.0.0.1:8710 CHROME_BIN="$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell"
bash  docs/audit-2026-10/VITESSE-CARTE-1/harnais/server_tiles.sh > docs/audit-2026-10/VITESSE-CARTE-1/mesures/server_tiles.csv
node  docs/audit-2026-10/VITESSE-CARTE-1/harnais/boot_app.mjs      # cascade boot (cold+chaud)
node  docs/audit-2026-10/VITESSE-CARTE-1/harnais/carte_bench.mjs   # activation couches / pan / 2D-3D
# 4) EXPLAIN des tuiles les plus chères : cf. mesures/EXPLAINS.txt (psql, jit off).
```

Bruts : `mesures/server_tiles.csv`, `mesures/sonde/`, `mesures/boot/`, `mesures/carte_bench.csv`,
`mesures/EXPLAINS.txt`.
