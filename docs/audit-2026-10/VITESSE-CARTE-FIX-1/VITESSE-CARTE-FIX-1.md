# VITESSE-CARTE-FIX-1 — le « vrai FIX-2 » : cache persistant des 57 overlays (G2)

> **Mandat de correctif perf, périmètre G1 + G2.** Suite de l'audit `VITESSE-CARTE-1` (commit
> `a6a5f6ce`, branche `audit/vitesse-carte-1`, non mergée — ne pas la supprimer : rapport + harnais).
> **Contrainte absolue, re-vérifiée à chaque pas :** aucune donnée ni géométrie altérée — pas de
> simplification, pas d'arrondi de coordonnées, pas de seuil de zoom, pas d'objet écarté, aucune couche
> rendue moins visible qu'aujourd'hui. Chaque correctif est prouvé neutre sur le rendu.

## En-tête — cadre de mesure

| | |
|---|---|
| Branche / worktree | `fix/vitesse-carte-1` · `~/Desktop/labuse-vitessefix` (depuis `origin/main` `27624c22`) |
| Ports | API sondée **:8711** (1 worker uvicorn, sert `/socle/` = build de prod) · Vite :5911 (non requis — G2 est back) |
| Base | PostgreSQL 18.4 · PostGIS **3.6.4** · `localhost:5432/labuse` — **unique et PARTAGÉE** |
| Run servi | **`q_v16`** (`mvt_meta.run_label=q_v16`, `perime=false`, résiduel seq 13) |
| Outillage (rejouable) | `harnais/` : `server_tiles.sh` (banc tuiles serveur) · `boot_app.mjs` · `carte_bench.mjs` · `sonde_app.py` (repris de l'audit) **+ nouveaux** : `gen_g2_tiles.py` (octets avant/après), `neutralite_g2.mjs` (neutralité pixel du `ORDER BY`), `neutralite_g1.mjs` (laissé pour le futur mandat G1). Bruts : `mesures/avant/`, `mesures/apres/`. |

> **⚠ Réserve de fidélité — base sous contention réelle (inchangée depuis l'audit).** Pendant TOUTES
> les mesures, une autre session CC (`~/Desktop/labuse-chasse3`, pid 752 quasi permanent + rafales de
> workers parallèles) a frappé la base partagée : **médiane de 4 sessions actives voisines** (max 7–9),
> échantillonnée toutes les 2 s (`/tmp/cont_*.txt`). Je **ne pouvais pas** la libérer (règle : ne jamais
> mass-kill les backends voisins). Les **temps mur absolus sont donc bruités à la hausse**, à l'identique
> « avant » et « après ». Les conclusions structurelles reposent sur des grandeurs **insensibles à la
> contention** : octets des tuiles, md5 (identité octet-par-octet), comptes de pixels, et l'écart
> froid→cache (de l'ordre de ×100 à ×400, robuste au bruit). Le classement et les gains tiennent.

---

## 0. Décision du mandat et fait majeur d'entrée

Le mandat demandait **G1** (contour île depuis `parcels-ile`) **+ G2** (cache des overlays). **Avant toute
modification, en montant la preuve de neutralité de G1, j'ai découvert que la source `parcels-ile` est
CASSÉE sur `origin/main`** (§6). G1 tel que spécifié y est **impossible à rendre neutre**. J'ai arrêté et
demandé l'arbitrage (« au moindre écart visible, on s'arrête et on le dit »).

**Décision Vic (06/10) : « Reporter G1, faire G2 seul ».** Ce mandat livre donc **le Lot 2 (G2)** —
le « vrai FIX-2 » : le cache persistant que les parcelles ont reçu (R1), **étendu aux 57 overlays**. G1 et
le bug `parcels-ile` partent dans un mandat dédié (§6 documente tout ce qu'il faut pour l'attaquer).

---

## 1. Ce qui a changé (G2) — en bref

| | Avant (`origin/main`) | Après (ce commit) |
|---|---|---|
| Tuile d'overlay z9-z11 à **froid** | `ST_AsMVTGeom` recalculé : **0,5–2,9 s** (ppr, alea_mvt, limites_parcelles en tête), **par worker**, re-payé à chaque reboot/build | servie depuis **`mvt_tile_cache`** : **5–57 ms** (lecture `bytea` indexée), **traverse les 5 workers**, survit aux reboots/builds |
| Mécanisme de cache | LRU **par worker** (4096 entrées, en mémoire, perdu au reboot) uniquement | LRU par worker **+ cache PERSISTANT** `mvt_tile_cache` (z9-z11) — **exactement** le mécanisme des parcelles (mêmes fonctions) |
| Octets des tuiles | **non déterministes** (ordre des features variable → md5 différent à chaque calcul) | **déterministes** (`ORDER BY mvt.geom`) → cache == à-la-volée au **bit près**, comparable, revalidable |
| ETag des overlays | **faible** (chaîne `version:kind:z:x:y`) | **fort** (md5 du contenu) → 304 propre, invalidation au changement de contenu |
| Pré-chauffe | parcelles z9-z11 seules | parcelles **+ overlays lourds z9-z11** dans le geste unique `rebuild_mvt_servies` (**+1,8 min** au build, non bloquant) |

**Aucun octet de rendu, aucun pixel, aucune géométrie ne change** (§4). Le seul effet visible pour le
client est que les couches s'allument **en millisecondes** au lieu de secondes.

---

## 2. Le correctif en détail

### 2.1 Le cache persistant, repris tel quel des parcelles
La table `mvt_tile_cache` (colonnes `version, z, x, y, layer, data, etag`, PK `(version,z,x,y,layer)`)
existait déjà pour les parcelles (`layer='parcels'`). On la **réutilise sans en inventer une seconde** :

- `tiles._tile_cache_get/_tile_cache_put` reçoivent un paramètre **`layer`** (défaut `'parcels'` → les
  appelants parcelles sont inchangés). Pour un overlay, `layer` = le kind-front (`ppr`, `alea_mvt`…).
- `couches_tuyau.couche_tuile` applique les **mêmes 3 étages, dans le même ordre** que `tiles.mvt_tile` :
  1. **LRU** en mémoire (par worker) — le plus rapide ;
  2. **cache persistant** `mvt_tile_cache` (z9-z11, `layer=kind`) — traverse les workers, survit aux reboots ;
  3. **miss** → génération `_construire_tuile` + alimentation du cache (best-effort).
- Zooms persistés = **z9-z11** (`_WARM_ZOOMS`, identiques aux parcelles) : les tuiles chères à froid et
  bornées (≈26/couche). z≥12 reste en LRU (génération rapide, l'index GiST porte). Lazy-fill : la 1ʳᵉ
  demande d'une couche **non pré-chauffée** (ex. `icpe`) la génère et la met en cache (vérifié : 1er hit
  8,9 ms → 2ᵉ 5,5 ms).

### 2.2 Déterminisme — `ORDER BY mvt.geom`, placé correctement
`_construire_tuile` faisait `ST_AsMVT(mvt.*, :layer, 4096, 'geom')` **sans ORDER BY** → le Parallel Seq
Scan renvoie les features dans un ordre variable → **md5 différent à chaque calcul** (mesuré : 3 appels, 3
md5). Impossible alors de comparer « cache == à-la-volée ». Correctif : `ORDER BY mvt.geom` **en fin
d'arguments** → octets **déterministes** (3 appels, 1 seul md5) et **nom de layer préservé** (= kind).

> ⚠ **Le placement est critique.** `ST_AsMVT(x ORDER BY g, 'nom', extent, …)` (ORDER BY après le 1er
> argument) fait **avaler `'nom'`, `extent`, `'geom'` comme clés de tri** → la tuile retombe au nom
> `default` et à l'extent par défaut 4096. **C'est exactement le bug qui casse `parcels-ile` (§6).** Ici le
> `ORDER BY` est **après tous les arguments** → nom et extent conservés (vérifié en psql et par le nom de
> layer servi).

### 2.3 ETag fort + réponse conditionnelle
Les overlays réutilisent `tiles._tile_response` → **ETag = md5 du contenu**, `If-None-Match` → **304** (0
octet). Vérifié : `ETag == md5(corps)` pour ppr/alea_mvt/sup, 304 renvoyé.

### 2.4 Pré-chauffe dans le geste unique
`rebuild_mvt_servies` (le point d'orchestration unique, appelé par `build-mvt` et chaque bascule) appelle
maintenant `warm_overlay_tiles` **après** `warm_parcel_tiles`, **non bloquant** (try/except comme les
parcelles). Périmètre pré-chauffé = couches **lourdes** z9-z11 : les méga-polygones subdivisés
(`tuyau_subdivise`/`tuyau_sup`) **+ `limites_parcelles`** (contour cadastral **coché par défaut** sur
l'île, ~2 s / 5,6 Mo à froid = la pire tuile du boot). **Exclus** : le bâti 3D (`extrusion`,
`HORS_PANNEAU`, chargé par bbox au bouton 3D — jamais une tuile île) et `zonage_parcelle` (source minzoom
11 côté front → z9/z10 jamais demandées ; lazy-fill au 1er z11). **Mesuré : 49 couches, 1274 tuiles,
≈106 s (~1,8 min)** — largement dans le budget de rebuild de 15 min (`SEUIL_RECONSTRUCTION_MIN`).

---

## 3. Invalidation du cache — le seul vrai risque, traité à la ceinture et aux bretelles

> **Règle :** une tuile en cache ne doit JAMAIS survivre à un changement de la donnée qu'elle dessine.

Trois verrous, cumulés :

1. **Clé de version** (entre dans la clé LRU, dans la clé du cache persistant, et dans l'ETag faible
   historique) = **`run . max(created_at spatial_layers) . tuyau_rev`**.
   - **Bascule de run** → `run` change → tout rate les anciennes clés.
   - **Réingestion** d'une couche → `max(created_at)` de `spatial_layers` change → idem.
2. **Sel `tuyau_rev`** (nouveau) = horodatage dans `mvt_meta`, **bumpé à chaque rebuild d'une table
   source d'overlay** (`build_tuyau_subdivise`/`_sup`/`_piscines`/`_icpe`/`_telepherique`,
   `build_mvt_communes`, via `_invalider_cache_persistant_overlays`). Ferme l'**edge case** « table
   dérivée rebâtie SANS réingestion de `spatial_layers` » : `created_at` ne bougerait pas, mais `tuyau_rev`
   oui → la version servie change → **LRU + cache persistant + un éventuel proxy** ratent tous les
   anciens octets. (Vérifié : la version passe de `…234141.` à `…234141.20261006025724320` après un bump.)
3. **Purge directe** : à chaque rebuild de table tuyau, `_invalider_cache_persistant_overlays` fait
   `DELETE FROM mvt_tile_cache WHERE layer <> 'parcels'` (**les parcelles ne sont jamais touchées**).
   Vérifié : 1415 overlays → 0, 77 parcelles intactes ; un GET suivant relazy-fill.
   `warm_overlay_tiles` purge aussi les versions périmées (`DELETE … WHERE layer<>'parcels' AND version<>courante`).

**Comment on le vérifie** (rejouable) : `mesures/apres/invalidation.txt` montre (a) la version servie =
celle des tuiles en cache ; (b) le bump de `tuyau_rev` ; (c) la purge overlays-seuls ; (d) la relecture
lazy. **Délai de propagation** : la version est mémoïsée 60 s (TTL single-flight anti-stampede, hérité) —
après un rebuild, au plus 60 s avant que les workers servent la nouvelle version ; négligeable (les builds
sont rares, la grâce `stale-while-revalidate` est de 24 h).

---

## 4. Preuves de neutralité (rendu inchangé)

### 4.1 Identité octet-par-octet : cache == à-la-volée
Exigence du mandat : « comparer octet par octet la tuile servie par le cache et la tuile calculée au vol,
sur 5 couches lourdes × 3 niveaux de zoom. Zéro différence. »

- **Niveau fonction** (`_tile_cache_get` vs `_construire_tuile`) : **15/15 tuiles IDENTIQUES** (ppr,
  alea_mvt, plu_gpu_zone, sup, ebc × z9/z11/z13).
- **Niveau HTTP** (corps servi par l'API vs génération fraîche) : **IDENTIQUE** (ppr 2 141 723 o,
  alea_mvt 2 713 637 o, sup 513 792 o). ETag md5 cohérent, 304 OK.

C'est **le déterminisme** (`ORDER BY`) qui rend cette égalité possible — sans lui, « à-la-volée » tirait
un ordre différent et ne pouvait jamais égaler le cache.

### 4.2 Neutralité pixel du `ORDER BY` (le seul changement qui touche les octets servis)
Le `ORDER BY` change l'**ordre** des features dans la tuile (donc ses octets), jamais la géométrie ni les
propriétés. Reste à prouver que l'**ordre** ne change pas les **pixels**. Harnais `neutralite_g2.mjs` :
pour 5 couches lourdes × 3 zooms, on rend la tuile **avant** (sans ordre) et **après** (ordonnée) avec le
**style réel du front** (un calque `fill` par niveau + contour), on lit le framebuffer (`gl.readPixels`),
on compare pixel par pixel. Résultats (`mesures/apres/neutralite_g2/`) :

- **4 couches sur 5** (ppr, alea_mvt, sup, ebc) : **delta canal max ≤ 2** à tous les zooms — bruit
  d'anti-aliasing imperceptible, **couverture de pixels IDENTIQUE** (ex. ppr z9 : 84 936 px des deux côtés).
- **`plu_gpu_zone`** (fond translucide **opacité 0,1** sur pièces subdivisées qui se **touchent**) :
  delta max **32** à z9 (354 px /810 000). **Mais** c'est un effet d'ordre **déjà présent aujourd'hui** :
  le code actuel n'a **pas** d'`ORDER BY` → l'ordre est **aléatoire** → **deux chargements consécutifs de
  la même tuile diffèrent déjà d'autant**. Contrôle décisif (`mesures/apres/neutralite_g2_controles/`) :
  - **random1 vs random2** (deux tirages aléatoires, = variance ACTUELLE entre deux chargements) :
    delta max **32**, 310 px > 8 à z9 — **la même magnitude** que « avant vs après ».
  - **octets identiques vs eux-mêmes** (plancher de bruit de rendu) : **0 pixel de différence** (rendu
    déterministe à octets égaux).

  **Conclusion :** le `ORDER BY` **n'introduit AUCUNE différence au-delà de la variance déjà existante**
  entre deux chargements ; il **fige** une non-déterminisme pré-existante (coutures AA translucides) en un
  rendu **déterministe** — donc, de fait, **plus consistant** qu'avant. Aucune couche n'est rendue moins
  visible, aucun objet écarté, aucune géométrie altérée.

### 4.3 Captures
`captures/avant/` et `captures/apres/` : vue île (le rendu île est **inchangé** — G2 n'y touche pas ; la
trame colorée par tier reste absente à cause du bug `parcels-ile` §6, identique avant/après) + overlays
ppr / alea_mvt / plu_gpu_zone z9 (avant vs après = visuellement indiscernables).

---

## 5. Gains mesurés

### 5.1 Serveur — tuile z9 à froid (1ᵉʳ hit, LRU vide) · `mesures/{avant,apres}/server_tiles.csv`
Contention médiane 4 des deux côtés. « Après » = 1ᵉʳ hit lu depuis le cache persistant (pré-chauffé).

| Couche | avant (froid) | après (1er hit cache) | octets servis |
|---|---:|---:|---:|
| `ppr` | **2 496 ms** | 378 ms¹ | 2 141 723 |
| `alea_mvt` | **2 866 ms** | 32 ms | 2 713 637 |
| `alea_inondation` | **1 526 ms** | 17 ms | 1 318 732 |
| `artificialisation` | 960 ms | 13 ms | 886 632 |
| `plu_gpu_zone` | 624 ms | 20 ms | 905 620 |
| `ebc` | 504 ms | 13 ms | 349 967 |
| `sup` | 440 ms | 12 ms | 513 792 |
| `znieff` | 131 ms | 9 ms | 146 482 |
| `limites_parcelles` (défaut île) | **1 992 ms** | 57 ms | 5 612 035 |
| `limites_communes` | 18 ms | 7 ms | 2 657 |

¹ `ppr` 1er hit 378 ms = lecture `bytea` 2,1 Mo + pic de contention ; hits suivants ~6 ms (LRU). Même
ainsi, **×6,6**. Les autres : **×30 à ×170**.

### 5.2 Navigateur — scénarios (médiane de 3 passes) · `mesures/{avant,apres}/carte_bench.csv`
Inclut le coût navigateur (parse/peinture = G3, **hors périmètre, lot 3**) + la contention ; directionnel.

| Scénario | avant | après |
|---|---:|---:|
| Activer 5 couches lourdes | 14 185 ms | **6 748 ms** |
| Activer 10 couches lourdes | 16 836 ms | **5 233 ms** |
| Bascule 2D→3D | 8 557 ms | **4 632 ms** |
| Boot île (parcelles + limites) | 3 565 ms | **2 620 ms** |
| Activer 1 couche lourde | 4 153 ms | **2 481 ms** |
| Zoom parcelle z14 | 2 198 ms | 1 276 ms |
| Pan z14 | 897 ms | 588 ms |
| Zoom commune z11 | 10 528 ms | 10 384 ms² |

² Peu de gain : à z11 les overlays sont déjà plus légers et le temps est dominé par le **parse/peinture
navigateur** (G3) — hors périmètre. Le cache serveur ne peut rien pour le fil principal du navigateur.

### 5.3 Boot île — octets inchangés (G2 est neutre sur les octets)
`mesures/{avant,apres}/boot/boot_resume.csv` : octets des tuiles parcelles **1 068 851 = 1 068 851**
(identiques). G2 ne retire aucun octet du boot (c'était le rôle de **G1**, reporté) ; il accélère la
**génération** côté serveur (ex. `limites_parcelles` par défaut : 1 992 ms → 57 ms).

---

## 6. G1 REPORTÉ — pourquoi, et le bug `parcels-ile` à corriger (mandat dédié)

G1 (« dessiner le contour île depuis `parcels-ile` déjà chargée au lieu d'une 2ᵉ source ») repose sur
l'hypothèse que `parcels-ile` **affiche** une géométrie. **Elle ne l'affiche pas :** un bug pré-existant
casse le rendu MVT parcelles de l'île.

### 6.1 Le bug — un `ORDER BY` mal placé dans `tiles._parcel_tile_bytes`
```sql
SELECT ST_AsMVT(mvt.* ORDER BY mvt.geom, 'parcels', {extent}, 'geom') FROM mvt
```
Le `ORDER BY mvt.geom` est placé **après le 1ᵉʳ argument** → PostgreSQL le lit comme une clause de tri
**multi-clés** : `ORDER BY mvt.geom, 'parcels', {extent}, 'geom'`. Les trois arguments `'parcels'`,
`{extent}`, `'geom'` sont **avalés comme clés de tri** (constantes, tri no-op). `ST_AsMVT` retombe donc
sur ses **valeurs par défaut** : **nom de layer `default`** (au lieu de `parcels`) et **extent 4096** (au
lieu de `{extent}` = 1024 à z9-z11). Introduit par CARTE-VITESSE-2 lot A (l'`ORDER BY` ajouté pour des
octets déterministes). Prouvé en psql : la requête exacte rend `('default', 4096)` ; corrigée
(`ST_AsMVT(mvt.*, 'parcels', 1024, 'geom' ORDER BY mvt.geom)`) → `('parcels', 1024)`.

### 6.2 Conséquence — l'île MVT ne peint rien
Le front monte `parcels-ile` avec `source-layer: 'parcels'` (calques `ile-fill` coloré par tier,
`ile-line`, `ile-sel`, `ile-pick`, `ile-zone-label`…). Or la tuile servie est nommée **`default`**.
Vérifié dans l'app LIVE : `querySourceFeatures('parcels-ile', {sourceLayer:'parcels'})` = **0**,
`{sourceLayer:'default'}` = **36 361**. **Tous les calques `ile-*` ne peignent rien** : sur l'île, seule
`limites_parcelles` (overlay, `source-layer:'limites_parcelles'`, correct) dessine le maillage — ce qui
explique a posteriori pourquoi l'audit la voyait « dupliquer parcels-ile » et « dominer le boot ».

### 6.3 Pourquoi G1 est donc impossible à rendre neutre aujourd'hui
Tirer le contour de `parcels-ile` imposerait son `source-layer` réel `default`, dont la géométrie est, à
z9-z11, **encodée en extent 1024 mais déclarée 4096 → écrasée au quart**. Mesuré (`neutralite_g1.mjs`,
variante `default`) : à z9 le contour tiré de `parcels-ile` couvre **7 733 px contre 92 734** pour
`limites_parcelles` (12–24 % de pixels divergents à z9-z11). **Non neutre.** G1 propre exige d'abord de
**corriger le bug** (nom + extent), ce qui **fait réapparaître le fond coloré par tier de l'île** — un
changement de rendu VISIBLE, hors périmètre G2 et à faire valider.

### 6.4 Ce qui reste pour le mandat G1 dédié
1. **Corriger `_parcel_tile_bytes`** (déplacer l'`ORDER BY` en fin d'arguments — 1 ligne) → restaure nom
   `parcels` + extent correct + la simplification B1.3 + le rendu île coloré. **Re-chauffer**
   `mvt_tile_cache` (layer parcels) car les tuiles z9-11 en cache portent le bug.
2. Revue visuelle Vic du rendu île restauré (fond coloré réapparaît).
3. Alors seulement : G1 (contour depuis `parcels-ile`, −9,9 Mo/boot) + prouver la neutralité pixel du
   contour **simplifié** z9-z11 vs full-res (harnais `neutralite_g1.mjs` prêt — à relancer avec le
   `source-layer 'parcels'` corrigé).
4. Compression (brotli/zstd, Caddy + API) — était le reste de G1.

> **Je n'ai touché NI `tiles._parcel_tile_bytes`, NI le front, NI `parcels-ile`.** Le bug reste tel quel
> (hors périmètre, décision Vic) ; les captures île « avant » et « après » sont donc identiques.

---

## 7. Caddy (part Lot 2) — ce qui est livré, ce qui reste à la prod

- **« En-têtes de cache et ETag cohérents »** — **LIVRÉ, côté API** : chaque tuile d'overlay porte
  `Cache-Control: public, max-age=3600, stale-while-revalidate=86400` + **ETag fort md5**. Caddy
  (`reverse_proxy`) **relaie les en-têtes du backend tels quels** (cf. en-tête du `Caddyfile.prod`) → le
  navigateur et un proxy amont cachent et revalident (304) sur une clé forte. Vérifié localement.
- **Cache proxy PARTAGÉ côté Caddy** — **NON committé, documenté comme étape prod.** Caddy core ne cache
  pas ; un cache partagé exige un **plugin** (Souin / `caddy-cache-handler`) donc un **build Caddy
  custom**. **Je ne touche pas au `Caddyfile.prod` vivant** : y poser un bloc `cache { … }` **sans** le
  plugin **ferait planter Caddy au démarrage**. De plus, pas de Caddy en local et prod non re-SSH'ée
  (même posture que l'audit). La config recommandée (à appliquer après installation du plugin) :

  ```caddy
  # Prérequis : binaire Caddy construit avec github.com/caddyserver/cache-handler (Souin).
  # Bloc global :
  {
      cache {
          ttl 1h
          stale 24h
          # ne cache QUE les tuiles ; respecte l'ETag fort et Cache-Control du backend
      }
  }
  # Dans le site, AVANT le reverse_proxy, matcher les tuiles :
  @tiles path /map/tiles/*
  route @tiles {
      cache
      reverse_proxy 127.0.0.1:8000
  }
  ```
  Marginalement utile : le cache **persistant côté API** rend déjà la génération ~ms sur les 5 workers ; le
  cache Caddy n'économise que le saut proxy + la lecture `bytea` pour le 1ᵉʳ visiteur inter-navigateurs.

---

## 8. Recette

- **Harnais rejoué à vide** (à la contention près, documentée) : §5 — tableau avant→après, 7 scénarios
  froid/chaud (`mesures/{avant,apres}/`).
- **Neutralité** : identité octet cache==à-la-volée **15/15** + HTTP **3/3** (§4.1) ; neutralité pixel du
  `ORDER BY` prouvée **dans l'enveloppe de variance existante** (§4.2).
- **Couches « zoomez pour voir » restent visibles à tous les niveaux** (décision 05/10) : G2 ne touche ni
  `zoom_min`, ni la visibilité, ni l'extent, ni la géométrie — uniquement **où** les octets sont stockés.
- **Tests** : `tsc` **0 erreur** · `vitest` **235/235** · `pytest` tuiles/couches **18/18**
  (`test_carte_tuiles`, `test_algofix1_point4_tuiles`, `test_peremption_tuiles`,
  `test_outils_s2_couches_source` verts). **1 échec pré-existant** `test_backup_tuile::test_repertoire_absent_dit_non_configure`
  (`'local'≠'non_configure'`) — **sans lien** (test de backup ; **échoue aussi sans mes modifs**, vérifié
  par `git stash` ; la machine a un répertoire `~/labuse-backups` local, cf. DASHBOARD-FIX-1).
- **Cas limites** du nouveau `couche_tuile` : kind inconnu → 404 ; z hors plage → 404 ; couche
  non pré-chauffée (`icpe`) → lazy-fill (8,9→5,5 ms) ; z14 (hors `_WARM_ZOOMS`) → à la volée, LRU seul ;
  tuile océan vide → 200 / 0 octet. Tous conformes.

---

## 9. Ce qui reste (hors de ce mandat)

- **Mandat G1 dédié** : corriger le bug `ST_AsMVT`/`parcels-ile` (§6.4), restaurer le rendu île coloré
  (revue Vic), puis G1 (contour depuis `parcels-ile`, −9,9 Mo/boot) + compression (brotli/zstd).
- **Lot 3 de l'audit** (hors de CE mandat et du mandat G1) : confort navigateur (G3 — parse/peinture, le
  plafond du zoom z11), outils île en GeoJSON massif (G4 — Piscines 6,1 Mo), fiche 241 requêtes (G5).
- **Prod** : installer le plugin Souin + appliquer le bloc `cache` (§7) ; purger la tuile résiduelle à 0
  octet sous une version périmée dans `mvt_tile_cache` (hygiène notée à l'audit §9, sans effet).

---

## 10. Reproduire

```bash
# API sondée (venv racine), port 8711, sert /socle/ :
. ~/Desktop/labuse/.venv/bin/activate
export PYTHONPATH="$PWD/src" LABUSE_ENV=local \
  LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
  SONDE_DIR="$PWD/docs/audit-2026-10/VITESSE-CARTE-FIX-1/mesures/apres/sonde" \
  BASE=http://127.0.0.1:8711 \
  CHROME_BIN="$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell"
uvicorn sonde_app:sonde --app-dir docs/audit-2026-10/VITESSE-CARTE-FIX-1/harnais --host 127.0.0.1 --port 8711 --workers 1
D=docs/audit-2026-10/VITESSE-CARTE-FIX-1/harnais
LC_ALL=C bash $D/server_tiles.sh                 # tuiles serveur froid/chaud (LC_ALL=C : décimales)
node $D/gen_g2_tiles.py /tmp/g2 ; node $D/neutralite_g2.mjs /tmp/g2 mesures/apres/neutralite_g2
node $D/boot_app.mjs ; node $D/carte_bench.mjs
```
`LC_ALL=C` est requis : sans lui, `curl -w %{time_total}` rend `2,034` (virgule FR) que `awk` tronque à la
seconde. Un unique worker uvicorn + tuiles froides énormes fait que `boot_app.mjs` déclare « idle » avant
que les tuiles lourdes ne répondent (pré-chauffer le serveur avant de mesurer les octets du boot).
