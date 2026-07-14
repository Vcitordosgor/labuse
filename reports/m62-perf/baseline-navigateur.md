# M6.2 PERF — Lot 1 : baseline NAVIGATEUR (mesure pure)

**Instance mesurée** : `http://127.0.0.1:8011/socle/` (dev-mode, sans rate-limit)
**Branche** : `feat/m62-perf` · **Viewport** : 1440×900 · **Répétitions** : 5 (médiane + P95)
**Outil** : Playwright/Chromium (headless) piloté par `frontend/qa/perf_baseline_nav.mjs`
**Date** : 2026-07-14 · **Données brutes** : `baseline-navigateur.json`

> ⚠️ Aucune optimisation, aucun changement de code produit, aucun commit. Ce document ne fait que **mesurer**.

---

## Méthode de mesure (résumé)

| Métrique | Comment |
|---|---|
| **TTFB** | `PerformanceNavigationTiming.responseStart` |
| **FCP** | entrée `paint` « first-contentful-paint » (`performance.getEntriesByType('paint')`) |
| **TTI** | **proxy** : 1ʳᵉ fenêtre de calme réseau de 500 ms après FCP (bornée par `domInteractive`). Le vrai TTI Lighthouse n'est pas exposé par l'API navigateur → proxy documenté. |
| **Poids / requêtes** | **CDP `Network`** (source de vérité) : `encodedDataLength` = octets réels sur le fil, `response.fromDiskCache` = cache-hit. Ventilé par type (js/css/pbf/fonts/images/json). |
| **FROID** | contexte Chromium **neuf** + route `Cache-Control: no-cache` sur toutes les requêtes (cache vierge). |
| **CHAUD** | contexte neuf, `goto` de préchauffage (peuple le cache — tuiles `max-age=3600`), puis `goto` **mesuré** (assets servis du cache). |
| **1ʳᵉ tuile carte** | délai `goto` → 1ʳᵉ réponse `/map/tiles/….pbf` (écoute réseau). |
| **Fluidité pan/zoom** | 3 pans + 2 zooms programmés ; compteur d'événements MapLibre `render` (frames réellement dessinées) + écart inter-frame p95/max. **Voir caveat headless ci-dessous.** |
| **Bascule couche** | clic sur la case → carte `idle` (`loaded() && areTilesLoaded()`) ; octets pbf/GeoJSON téléchargés capturés. |
| **Fiche** | saisie IDU dans l'omnibox → en-tête affiche l'IDU cible **exact** + badge verdict présent (= data `f` chargée). |
| **Filtre** | clic chip/commune → nombre de cartes `[data-results-scroll] button` **stable** sur 2 lectures espacées. |

**Caveat fluidité (headless)** : Chromium headless ne pilote pas de vsync 60 fps continu ; le nombre de frames MapLibre `render` par seconde est une **borne basse** (une session « headed » en montrerait davantage). On rapporte donc l'écart **inter-frame** comme proxy de saccade, pas un « fps » comparable à la réalité.

**Caveat cache (FROID/CHAUD)** : le poids « décodé » (≈1,77 Mo) est le poids **décompressé** des ressources ; le poids **transféré** (574 Ko froid, 21 Ko chaud) est ce qui passe réellement sur le réseau (pbf/JS/CSS gzippés). C'est le transféré qui compte pour le temps de chargement.

---

## 1. Premier chargement

### 1.1 Temps (médiane / P95, ms)

| Métrique | FROID médiane | FROID P95 | CHAUD médiane | CHAUD P95 |
|---|--:|--:|--:|--:|
| TTFB | 3,6 | 5,6 | 3,7 | 4,0 |
| **FCP** | **152** | 176 | **104** | 108 |
| TTI (proxy) | 1 160 | 1 250 | 727 | 1 087 |
| domContentLoaded | 75 | 94 | 58 | 60 |
| load event | 83 | 103 | 59 | 60 |

TTFB négligeable (serveur local). FCP froid 152 ms, chaud 104 ms. La montée jusqu'au TTI (~1,2 s froid) est dominée par le parse/exécution du bundle JS.

### 1.2 Poids transféré (sur le fil) et requêtes — médiane sur 5 runs

| Type | FROID transféré | FROID décodé | Req | CHAUD transféré | Cache-hits |
|---|--:|--:|--:|--:|--:|
| **JS** | **346 Ko** | 1 240 Ko | 3 | 0 Ko | ✓ cache |
| Fonts | 100 Ko | 100 Ko | 3 | 0 Ko | ✓ cache |
| Images | 89 Ko | 84 Ko | 24 | 0 Ko | ✓ cache |
| JSON (API) | 20 Ko | 235 Ko | 5 | 20 Ko | re-fetch |
| CSS | 17 Ko | 110 Ko | 2 | 0 Ko | ✓ cache |
| Tuiles pbf | 0 Ko* | 0 Ko | 1 | 0 Ko | — |
| HTML | 1 Ko | 1 Ko | 1 | 1 Ko | re-fetch |
| **TOTAL** | **574 Ko** | **1 770 Ko** | **39** | **21 Ko** | 24/39 du cache |

\* À la vue d'accueil (île, zoom bas `#v=1`) les tuiles pbf initiales sont vides/minuscules (`content-length: 0`) → le poids carte se paie au **premier zoom**, pas au chargement (voir §2). Le poids d'accueil est donc porté par le **bundle JS (346 Ko sur le fil, 1,24 Mo décodé)**.

**Cache** : à chaud, 24/39 requêtes servies du cache disque → 574 Ko → **21 Ko** transférés (seuls HTML + 5 JSON d'API sont re-demandés). Le cache navigateur fonctionne.

---

## 2. Carte

### 2.1 Affichage initial des tuiles

| | médiane | P95 |
|---|--:|--:|
| goto → 1ʳᵉ tuile pbf rendue | **2 100 ms** | 2 532 ms |

### 2.2 Fluidité pan/zoom (3 pans + 2 zooms) — proxy headless

| | médiane |
|---|--:|
| frames MapLibre `render`/s (borne basse headless) | 1,7 |
| écart inter-frame p95 | **772 ms** |
| écart inter-frame max | 772 ms |

En headless, MapLibre ne dessine que ~7 frames sur toute la séquence d'animations (pas de compositeur vsync). **Non fiablement mesurable en headless** : le « fps » réel exige une session headed / DevTools rendering. Le proxy retenu (écart inter-frame) montre des à-coups de l'ordre de plusieurs centaines de ms entre deux dessins — à re-mesurer en headed avant toute conclusion sur la fluidité perçue.

### 2.3 Bascule de couche (clic case → carte idle) — vue île zoom ~10,5

Le temps inclut l'attente `idle` (téléchargement + rendu de TOUTES les tuiles/GeoJSON du viewport déclenchés par la couche).

| Couche | médiane | P95 | Réseau téléchargé | Req | Déclenche réseau ? |
|---|--:|--:|--:|--:|:--|
| **PPR multirisque** | **6 359 ms** | 6 549 | **4 496 Ko** (tuiles MVT `ovmvt-ppr`) | 6 | **OUI — le plus lourd** |
| Équipements | 5 223 ms | 5 242 | 921 Ko (GeoJSON `layers.geojson?kind=amenite`) | 1 | OUI |
| 50 pas géométriques | 5 036 ms | 5 132 | 91 Ko (GeoJSON `cinquante_pas`) | 1 | OUI |
| Vue mer | 4 339 ms | 5 260 | 0 Ko | 0 | non (filtre sur tuiles déjà chargées) |
| Zonage PLU (parcelles) | 3 612 ms | 3 640 | 0 Ko | 0 | non (recoloration des tuiles île déjà servies) |
| ANRU (NPNRU) | 2 767 ms | 2 803 | 0 Ko | 1 (vide) | non (aucun périmètre au viewport) |

**Lecture** : PPR est servi en **tuiles vectorielles MVT** → l'activer à l'échelle île re-télécharge ~4,5 Mo de pbf PPR = 6,4 s. Équipements/50 pas passent par un fetch GeoJSON unique. Zonage/Vue mer ne touchent pas le réseau (recoloration/filtre sur les tuiles parcelles déjà chargées).

---

## 3. Fiche parcelle (10 parcelles variées)

La data de fiche (`/parcels/{idu}`) est mise en cache côté client (React Query) : **rouvrir le même IDU** mesure le cache (~220 ms), pas l'ouverture réelle. On rapporte donc l'**ouverture FROID** (1 fois par parcelle, contexte neuf = cache client + HTTP vierges) = latence d'ouverture d'une fiche **jamais consultée** (cas d'usage réel), plus la **réouverture** comme référence.

| | P50 | P95 |
|---|--:|--:|
| **Fiche FROID (1ʳᵉ ouverture)** | **3 351 ms** | **3 382 ms** |
| Réouverture (cache client) | 224 ms | 326 ms |

Détail par parcelle (ouverture FROID, ms) — très homogène :

| IDU | commune / tier | FROID | Réouv. |
|---|---|--:|--:|
| 97410000AS1425 | Saint-Benoît · brûlante *(mandaté)* | 3 382 | 195 |
| 97423000AB1908 | Les Trois-Bassins · brûlante *(mandaté)* | 3 303 | 217 |
| 97423000AB1341 | Les Trois-Bassins · écartée *(mandaté)* | 3 308 | 230 |
| 97404000AT0870 | L'Étang-Salé · chaude | 3 375 | 203 |
| 97411000KA0296 | Saint-Denis · brûlante | 3 362 | 326 |
| 97413000AV2267 | Saint-Leu · brûlante | 3 308 | 282 |
| 97408000AP1647 | La Possession · chaude | 3 336 | 241 |
| 97416000EY1406 | Saint-Pierre · brûlante | 3 341 | 265 |
| 97419000AE0500 | Sainte-Rose · chaude | 3 380 | 161 |
| 97406000AI0941 | La Plaine-des-Palmistes · chaude | 3 360 | 156 |

La constance ~3,35 s (indépendante de commune/tier) indique un coût **fixe** d'ouverture (appels API de fiche en série : fiche + faisabilité + solaire + watch + pipeline), pas un coût lié à la richesse de la parcelle.

---

## 4. Panneau résultats (application d'un filtre)

Temps clic → liste/compteur DOM stable (2 lectures stables espacées de 250 ms).

| Action | médiane | P95 |
|---|--:|--:|
| Filtre **tier = brûlante** (clic chip, 119 brûlantes île) | 2 415 ms | 2 509 ms |
| Puis **commune = Saint-Paul** (omnibox → bascule périmètre) | **10 294 ms** | 10 330 ms |

Le filtre tier (chip) refiltre la liste servie : ~2,4 s. La **bascule de commune est le geste le plus lent de tout le parcours (~10,3 s)** : elle change le périmètre, recharge le GeoJSON parcelles de la commune (~60 k features) et refait la requête liste. Extrêmement stable (10,26–10,33 s sur 5 runs) → latence serveur/data réelle, pas du bruit.

---

## Les métriques les plus lentes (cibles d'optimisation)

| # | Métrique | Chiffre (médiane) | Cause probable |
|---|---|--:|---|
| 1 | **Bascule commune (liste)** | **10 294 ms** | rechargement périmètre + GeoJSON commune (~60 k parcelles) + refetch liste |
| 2 | **Bascule couche PPR** | **6 359 ms** (4,5 Mo pbf) | tuiles MVT PPR re-téléchargées à l'échelle île |
| 3 | **Bascule couche Équipements / 50 pas** | 5 223 / 5 036 ms | fetch GeoJSON + rendu plein viewport |
| 4 | **Fiche parcelle (1ʳᵉ ouverture)** | 3 351 ms (P95 3 382) | coût fixe des appels API de fiche en série |

À titre indicatif : 1ʳᵉ tuile carte 2,1 s ; filtre tier 2,4 s ; chargement froid FCP 152 ms (léger).
