# CARTE-VITESSE-1 — Pourquoi la carte principale met ~7 s à s'afficher

> **Audit LECTURE SEULE.** Aucun correctif, aucune tuile regénérée, aucune donnée touchée, aucun merge.
> Ce rapport mesure la chronologie d'un chargement de carte, isole la cause du « grand rectangle noir »
> à l'échelle de l'île, et chiffre les remèdes (le codage est le mandat CARTE-VITESSE-2).
> **Prérequis lu** : `VITESSE-AUDIT-1/RAPPORT.md` — ce rapport en reprend les acquis (VIT-005 tuiles
> froides, VIT-010 bundle) sans les refaire, et les précise pour le chemin d'ouverture de la carte.

## En-tête — cadre de mesure

| | |
|---|---|
| Branche / worktree | `audit/carte-vitesse-1` · `~/Desktop/labuse-cartevite` |
| Commit `main` de départ | `ce77ae8d` (Merge branch 'fix/zones-famille-1') |
| Run servi | **`q_v11_m137`** (`config/served_run.txt`) |
| Base | PostgreSQL 18 aarch64 · `localhost:5432/labuse` — **unique, partagée** avec OUTILS-S1/S2 |
| Machine | MacBook Air M1 (8 cœurs), macOS · **API sondée en 1 worker uvicorn** sur port **8475** |
| Front mesuré | **build de PROD** (`npm run build`), servi par FastAPI `StaticFiles` `/socle/` + `GZipMiddleware`. `index` 279 Ko gz · `maplibre` 210 Ko gz · `vendor` 56 Ko gz. |
| Outillage | sonde de timing réutilisée de VITESSE-AUDIT-1 (`harnais/sonde_app.py`) + **nouveau harnais `harnais/boot_waterfall.mjs`** (Playwright chromium-1217, cascade réseau fine cache vidé + cache chaud). Bruts dans `CARTE-VITESSE-1/MESURES/`. |

> **Réserve de fidélité (identique à VITESSE-AUDIT-1).** La base est **partagée avec les sessions
> OUTILS-S1/S2** (un second process `labuse api` tournait). Pendant la mesure, la contention a été
> **visible et violente** : un simple `count(*)` sur `mvt_parcels` a pris **402 s**, et la sonde a
> enregistré des tuiles z9 à **8–15 s** de SQL. Les chiffres **absolus** sont donc bruités **à la
> hausse**. Contre-mesure : les temps **serveur unitaires** ont été **recontrôlés en fenêtre calme**
> (`EXPLAIN ANALYZE`, buffers chauds, `pg_stat_activity` vide) ; ce sont ces valeurs propres qui servent
> au diagnostic. Le chiffre navigateur « cache vidé » (**dernière tuile à 6,7 s**) a été relevé **sous
> cette charge réelle** — or c'est **exactement la condition d'usage de Vic** (machine partagée), donc
> il reste représentatif du ressenti.

---

## 1. Cinq chiffres en tête

1. **Cache vidé : la dernière tuile de parcelles se peint à 6,7 s** (réseau calme à 8,5 s) — c'est le
   « ~7 s » du constat. **Cache chaud : 1,3 s** (tuiles relues du cache disque du navigateur).
2. **Le rectangle noir = les parcelles.** À l'ouverture (île entière, **z9**), la carte ne demande que
   **2 tuiles de parcelles** — mais ce sont les **deux plus chères de toute la pyramide**, et elles
   n'arrivent qu'à **4,1 s puis 6,7 s**.
3. **Deux causes se cumulent, à parts comparables** :
   **(A)** les tuiles **ne partent qu'à ~4 s** (le fil principal est bloqué ~4 s par le JS de démarrage),
   **(B)** chaque tuile z9 **coûte cher** (1,8–2,6 s à froid).
4. **Une tuile z9 = un balayage séquentiel de TOUTE la table `mvt_parcels` (240 Mo, 431 663 lignes).**
   L'index GiST **n'est pas utilisé à z9** (l'enveloppe attrape ~9 % des parcelles = **40 166** dans une
   seule tuile → le planificateur préfère lire toute la table). Chaud/calme : **252 ms** ; froid disque
   / sous charge : **1,8 à 15 s**. À z14 la même requête utilise l'index (**43 ms**).
5. **Boot JS : 16 *long-tasks* = 3,95 s de fil principal bloqué** (cache vidé), contre 2,1 s dans
   VITESSE-AUDIT-1 — le monolithe `index` (279 Ko gz, les 17 outils) a grossi. C'est ce mur qui
   **retarde le lancement des tuiles** (cause A). FCP reste bon (**0,52 s**).

---

## 2. La chronologie d'un chargement (cascade réseau réelle)

Relevé `boot_waterfall.mjs`, port 8475, build prod. `t` = ms depuis `goto('/socle/')`. Bruts :
`MESURES/boot_requests.csv`, `MESURES/boot_resume.csv`, `MESURES/har/boot_cold.har`.

### Cache vidé (contexte navigateur neuf)

| t début | famille | requête | durée | poids |
|---:|---|---|---:|---:|
| 108 | html | `/socle/` | 35 | 1,8 Ko |
| 164–472 | js/css | `maplibre.css`, `index.css`, `vendor.js`, **`maplibre.js` (768 Ko)**, **`index.js` (1 034 Ko)** | ~230 | 2,2 Mo décompressé |
| 686 | js | `MapView` (chunk lazy, 45 Ko) | 160 | |
| 1 645–1 659 | fonts / worker | Google Fonts (gstatic) + **blob worker maplibre 355 Ko** | 916 | |
| 1 701–1 710 | geojson | `ile974.geojson`, `communes974.geojson` | ~90 | 51 Ko |
| 1 809 | api | `/moi`, `/sources/couverture`, **`/events` (68 Ko, 485 ms)**, `/moi/prefs-carte` **→ 401** | | 120 Ko |
| 2 020 | api | `/v2/modele`, 2× `/usage/event` | | |
| **3 037** | api | **`/map/tiles/meta` — 1 334 ms** | | |
| **4 129** | **tuile** | **`/map/tiles/9/334/287.pbf` — 1 845 ms** | | 67 Ko |
| 5 055 | api | **`/map/tuyau/couches` — 4 058 ms** (95 % **Python**) | | 47 Ko |
| 5 166–5 250 | tuile | 4× `limites_communes/9/*` (rapides) | ~10–100 | |
| **6 723** | **tuile** | **`/map/tiles/9/335/287.pbf` — 2 580 ms** | | 126 Ko |

### Décomposition par famille (cache vidé, 3,07 Mo, 31 requêtes)

| Famille | Poids | Remarque |
|---|---:|---|
| **JS** (5 fichiers) | **2,07 Mo décompressé** (~545 Ko gz sur le fil) | `index`+`maplibre`+`vendor` préchargés au boot |
| blob worker maplibre | 0,37 Mo | worker de rendu vectoriel |
| **tuiles parcelles** | 0,20 Mo (2 tuiles) | la couche reine |
| CSS | 0,15 Mo | |
| Google Fonts | 0,12 Mo (4 req, **CDN externe**) | feuille de style **bloquante** |
| API démarrage | 0,12 Mo (7 req) | `/events` = 68 Ko à lui seul |

### Cache chaud (même contexte, cache disque HTTP conservé)

FCP 0,30 s · `load` 0,29 s · **dernière tuile 1,3 s** · calme 2,9 s. Les 2 tuiles de parcelles sont
relues **du cache disque du navigateur** (`Cache-Control: max-age=3600`, 1 ms, aucun aller serveur).
**Mais 6 *long-tasks* = 1,8 s** bloquent encore le fil principal même à chaud.

### Chemin critique (ce qui, instantané, ferait gagner le plus)

```
0 ─── FCP 0,52s ─── bundles+worker ─── [MUR JS ~4s de long-tasks] ─── tuiles partent 4,1s
                                                                       │ tuile1 z9 1,8s ┐
                                                                       └ tuile2 z9 2,6s ┴─► 6,7s "carte complète"
```

Le chemin critique est **JS (0–4 s) → tuiles parcelles (4,1 → 6,7 s)**. Les appels API du démarrage
(`/events`, `/v2/modele`, `/map/tuyau/couches`) sont **en parallèle et ne bloquent pas la peinture des
parcelles** — mais ils **encombrent le fil principal et le pool** pendant que les tuiles se calculent.

---

## 3. Les tuiles de parcelles — la piste n°1, confirmée

**Production : à la volée par PostGIS `ST_AsMVT`**, jamais un fichier. Source = **table matérialisée
`mvt_parcels`** (`src/labuse/api/tiles.py:383-450`), 431 663 lignes, **240 Mo**, index GiST
`mvt_parcels_gix(geom_3857)`. Reconstruite par `labuse build-mvt` (hors requête). Requête servie
(z ≤ 11) :

```sql
WITH b AS (SELECT ST_TileEnvelope(:z,:x,:y) AS env),
mvt AS (SELECT ST_AsMVTGeom(ST_SimplifyPreserveTopology(m.geom_3857, 60), b.env, 1024, 16, true) AS geom,
               m.tier_v2, m.etage0, m.zone_fam, m.commune
        FROM mvt_parcels m, b WHERE m.geom_3857 && b.env)
SELECT ST_AsMVT(mvt.*, 'parcels', 1024, 'geom') FROM mvt;
```

### Le fait central (EXPLAIN ANALYZE, fenêtre calme, buffers chauds)

| Tuile | Plan | Buffers | Lignes | Temps SQL calme |
|---|---|---:|---:|---:|
| **z9 334/287** (boot) | **Parallel Seq Scan** — index **NON utilisé** | **29 290** (≈ 229 Mo = **toute la table**) | 40 166 gardées / 130 499 rejetées | **252 ms** |
| z14 10716/9165 | **Bitmap Index Scan** (`mvt_parcels_gix`) | 2 065 (≈ 16 Mo) | ~4 300 | **43 ms** |

**Pourquoi le seq-scan à z9 ?** L'enveloppe d'une tuile z9 sur La Réunion couvre ~9 % des parcelles ;
à cette sélectivité le planificateur juge (à raison) qu'un balayage parallèle complet bat l'index. **La
conséquence** : chaque tuile z9 **lit les 240 Mo de la table** et **re-simplifie 40 166 géométries**
(`ST_SimplifyPreserveTopology` à 60 m). Chaud en RAM = 252 ms ; **froid disque = lecture de 240 Mo** ;
**sous la contention S1/S2 = 1,8 à 15 s** (mesuré). C'est **la** cause du rectangle noir.

### Réponses aux questions du mandat

- **Simplification par zoom** : oui — z9 = 60 m, z10 = 30 m, z11 = 15 m, `extent` 1024 ; z12+ brut,
  `extent` 4096 (`tiles.py:410-414`). Calibrée sur mesure (z9 5,57 Mo → 0,61 Mo). **Ne pas y toucher**
  (interdit VITESSE-AUDIT-1).
- **Seuil de zoom** : **aucun** en dessous de z9 pour cacher les parcelles (« le cadastre d'abord »,
  revue Vic). z < 9 → 204. **Les parcelles sont donc servies pleines dès z9** — c'est un choix produit,
  pas un bug, mais c'est ce qui met la tuile la plus lourde sur le chemin d'ouverture.
- **Attributs embarqués** : à z ≤ 11, **maigres** — `tier_v2, etage0, zone_fam, commune` (4–5 valeurs
  distinctes, dédupliquées par l'encodage MVT). Déjà optimisé (les 13 champs pesaient 15 Mo/tuile,
  `flags` retiré). **Rien à gratter côté attributs.**
- **`Cache-Control`** : `public, max-age=3600, stale-while-revalidate=86400` (`tiles.py:314`). ✅ Le
  navigateur ne recharge pas dans l'heure (prouvé : cache chaud = 1 ms/tuile). **⚠ Pas d'`ETag`** sur
  la route parcelles (`curl -D` : absent) → après expiration `max-age`, **refetch complet**, pas de 304.
- **Compression** : **gzip** (`GZipMiddleware`), ~3× (tuile z9 67 Ko → 21 Ko sur le fil). Pas de brotli.
- **Tuiles en parallèle / pool** : à l'ouverture seulement **2 tuiles** de parcelles. Pool DB = **5 + 10
  = 15 connexions/worker** (`config.py:50-51`, explicite). Les *handlers* sync tournent dans le
  threadpool Starlette → les 2 tuiles peuvent se calculer en parallèle, mais chacune lance un **Parallel
  Seq Scan (2 workers)** → 4 process backend pour 2 tuiles, **CPU-bound** sur 8 cœurs déjà partagés.
- **Cache serveur** : LRU **4096 entrées, par worker, en mémoire** (`tiles.py:307`), clé
  `(version, z, x, y)`, version mémoïsée 60 s single-flight. **Chaud LRU = 15 ms** (mesuré curl).
  **Perdu au reboot / `build-mvt` / par worker** → en prod (**5 workers**, Caddy ne cache pas les
  tuiles) chaque worker paie le froid, **× 5**.

---

## 4. Le reste (fond de carte, MapLibre, API, prod)

- **Fond de carte** : au démarrage, la préférence vient de `/moi/prefs-carte` qui **répond 401 en
  local** (auth désactivée) → repli sur le fond **« Sombre » (canvas, sans raster)**. Donc **en local
  aucune tuile ortho/IGN n'est chargée** au boot ; sur un compte prod avec fond ortho, s'ajoutent les
  tuiles WMTS IGN / ortho proxy (parallèles aux parcelles, généralement plus légères). Le rectangle noir
  `#181918` (`MapView.tsx:22-32`, couleur de fond du style) est **littéralement** ce que Vic voit tant
  que les parcelles ne sont pas peintes.
- **Démarrage MapLibre** : `maplibre` est **`modulepreload` au boot** (210 Ko gz sur le chemin critique,
  confirmé dans `index.html`). Au `load` de la carte, **~10 sources + ~60 couches sont déclarées d'un
  coup** (la plupart vides/masquées) ; ce n'est pas le goulot (setup synchrone < 200 ms) mais ça
  participe au *long-task* d'init.
- **`/map/tuyau/couches` = 4,0 s dont 3,4 s Python** : endpoint **catalogue de couches** (sans `db`,
  `couches_tuyau.py:538`) qui **relit/agrège les déclarations YAML à chaque appel** (non mémoïsé). Il ne
  bloque pas les parcelles, mais **il retarde les couches d'overlay** (les contours `limites_communes`
  n'arrivent qu'après lui, à 5,2 s) et **prend du temps CPU/pool** pendant le calcul des tuiles.
- **`/events` = 68 Ko / 485 ms** au boot : chargé tôt, non bloquant pour la carte, mais sur le fil.
- **Google Fonts** : feuille de style **bloquante depuis un CDN externe** (`fonts.googleapis.com`) +
  3 fichiers de police (gstatic) à 1,6 s. En prod, dépendance réseau tierce sur le chemin de rendu.
- **Prod (VPS)** : d'après VITESSE-AUDIT-1 §P — **Caddy `encode gzip`, HTTP/2, assets 1 an immutable,
  mais tuiles en `reverse_proxy` NON cachées par Caddy**. Donc en prod les tuiles froides sont payées
  par chaque worker et Caddy ne les mémorise pas. (Non re-vérifié ici : lecture seule, pas de SSH.)

---

## 5. Remèdes chiffrés (à coder en CARTE-VITESSE-2 — ici seulement évalués)

Gain estimé sur le **cold** (le cas qui pique). Rappel objectif : **carte utilisable < 2 s (froid),
< 1 s (chaud)**. Risque « nul » = octets/pixels strictement identiques ; « à prouver » = à vérifier
par diff.

| # | Remède | Cause visée | Gain froid estimé | Coût | Risque |
|---|---|---|---|---|---|
| **R1** | **Pré-générer / pré-chauffer les tuiles z9–z11 de l'île** (cache disque ou pmtiles régénéré à `build-mvt`, ou pré-remplir la LRU au démarrage). Les ~**dizaines** de tuiles z9–z11 couvrant l'île sont peu nombreuses et figées entre deux builds. | §3 (seq-scan 240 Mo) + VIT-005 | **−1,5 à −4 s** (tuile z9 : 1,8 s → ~15 ms) | **M** | **nul** (hash pbf identique) |
| **R2** | **Code-split du monolithe `index`** (17 outils en `lazy()`) + différer l'init MapLibre hors du 1ᵉʳ *paint*. Casse le mur de *long-tasks* qui **retarde le départ des tuiles de ~4 s à ~2 s**. | §1 cause A / VIT-010 | **−1,5 à −2 s** (les tuiles partent plus tôt) | **M** | **nul** (mêmes octets) |
| **R3** | **Cache tuiles au reverse-proxy (Caddy) ou partagé entre workers** + **ajouter un `ETag`** aux tuiles parcelles (304 après `max-age`). Supprime le coût froid **× 5 workers** en prod et après déploiement. | §3 (LRU par worker) / VIT-005 | **−2 à −4 s** au 1ᵉʳ visiteur prod | **S/M** | **nul** |
| **R4** | **Différer les API non bloquantes** (`/events`, `/sources`, `/map/tuyau/couches`) après la 1ʳᵉ peinture + **mémoïser `/map/tuyau/couches`** (YAML lu une fois). Libère fil + pool pendant le calcul des tuiles ; accélère l'apparition des contours communes. | §4 | −0,3 à −0,8 s | **S** | **nul** |
| **R5** | **Réglages serveur** (`statement_timeout` global, pool aligné sur les threads) — reprend **VIT-011**. N'accélère pas le cas nominal mais **protège la carte de la contention** observée (tuiles à 15 s). | réserve de fidélité | assurance | **S** | **nul** |
| **R6** | Auto-héberger les polices (retirer la dépendance Google Fonts bloquante) + `preload` des 2 chunks JS d'entrée. | §4 | −0,1 à −0,3 s | **S** | **nul** |

### Classement gain/coût

1. **R2 (code-split)** — risque nul, casse le mur qui décale tout le reste ; **à faire en premier**.
2. **R1 (tuiles z9–z11 pré-chauffées)** — le plus gros gain froid, risque nul, effort moyen.
3. **R3 (cache proxy + ETag)** — indispensable pour la **prod à 5 workers** ; risque nul.
4. **R4 / R6 / R5** — gains incrémentaux, tous à risque nul, effort faible.

### Objectif atteignable ?

- **Chaud < 1 s** : **oui**, avec R2. Aujourd'hui le chaud est à 1,3 s **uniquement** à cause des
  1,8 s de *long-tasks* ; les tuiles chaudes sont déjà instantanées (cache disque). Casser le monolithe
  suffit.
- **Froid < 2 s** : **serré mais approchable** avec **R2 + R1** : tuiles qui partent à ~2 s (au lieu de
  4) + tuiles z9 à ~15 ms (au lieu de 1,8 s) ⇒ « carte complète » vers **~2,5 s**. Le vrai plancher
  froid restera le **téléchargement + parse des ~545 Ko gz de JS** (~0,7–1 s) et le worker MapLibre.
  **Cible réaliste annoncée : froid ~2,5–3 s, chaud < 1 s** — un facteur ~2,5× sur le froid actuel.
  Descendre **sous 2 s à froid** exigerait de réduire le JS d'entrée sous ~300 Ko gz (au-delà du
  simple lazy-split) — possible mais c'est un chantier front à part.

---

## 6. Ce qui est déjà bon — ne pas toucher

- **`mvt_parcels` matérialisée** (geom pré-projetée 3857, GiST, statuts/zonage pré-joints) : à z ≥ 12
  l'index porte, 43 ms. Architecture juste.
- **Simplification par palier** et **attributs maigres** z ≤ 11 : déjà calibrés, **interdits** de retouche.
- **`Cache-Control` + gzip + cache disque navigateur** : le cache chaud est excellent (1 ms/tuile).
- **LRU single-flight** (anti-stampede sur la version) : correct.
- **Pool explicite 5+10, `pool_pre_ping`, `idle_in_transaction_timeout`** : sain.

---

## 7. Doutes et limites

- **Base partagée sous charge S1/S2** : les temps absolus (6,7 s cold, tuiles 8–15 s dans la sonde) sont
  **bruités à la hausse**. Les diagnostics unitaires reposent sur des `EXPLAIN ANALYZE` recontrôlés au
  calme (252 ms / 43 ms) — c'est sur eux que s'appuient les remèdes, pas sur les pics de contention.
- **Mono-worker local vs 5 workers prod** : la sonde ne capture pas la concurrence prod ; R3/R5 sont
  des raisonnements de code/config, pas des mesures de charge. Le « × 5 workers » du froid LRU est déduit
  du code, pas mesuré.
- **Fond « Sombre » en local** (401 sur `/moi/prefs-carte`) : un compte prod avec fond **ortho** ajoute
  des tuiles raster IGN au boot — non mesurées ici. Le rectangle **noir** que décrit Vic est cohérent
  avec le fond Sombre (couleur `#181918`) OU avec un fond ortho pas encore peint ; dans les deux cas la
  cause du vide **parcellaire** est identique (§3).
- **`ready_ms` = 0** dans le CSV : l'événement `labuse:ready` n'a pas été capté par le hook (timing
  d'`addInitScript`) ; sans effet sur les mesures réseau, qui sont la matière du rapport.
- **Prod non re-vérifiée** (lecture seule, pas de SSH cette fois) : les faits prod viennent de
  VITESSE-AUDIT-1 §P.

---

## 8. Reproduire

```bash
# API sondée (venv racine), port 8475, worktree d'audit :
. ~/Desktop/labuse/.venv/bin/activate
export SONDE_DIR="$PWD/docs/audit-2026-09/CARTE-VITESSE-1/MESURES/sonde" PYTHONPATH="$PWD/src" LABUSE_ENV=local
uvicorn sonde_app:sonde --app-dir docs/audit-2026-09/VITESSE-AUDIT-1/harnais --host 127.0.0.1 --port 8475 --workers 1
# Cascade réseau carte (cache vidé + chaud) :
export BASE=http://127.0.0.1:8475 CHROME_BIN="$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell"
node docs/audit-2026-09/CARTE-VITESSE-1/harnais/boot_waterfall.mjs
# EXPLAIN des tuiles : cf. §3 (psql, statement_timeout court, jit off, buffers chauds).
```

Bruts : `MESURES/boot_requests.csv`, `MESURES/boot_resume.csv`, `MESURES/har/boot_cold.har`,
`MESURES/sonde/`.
