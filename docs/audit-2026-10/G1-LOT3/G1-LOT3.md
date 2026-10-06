# G1-LOT3 — l'ouverture de la carte 5× plus légère, sans île noire à aucune taille d'écran

Branche `fix/g1-lot3` (depuis `origin/main` `0f36c913`) · worktree `~/Desktop/labuse-g1lot3` ·
API **8721** / Vite **5921** · Opus · **rien poussé, rien mergé** — Vic valide le visuel avant merge.

| Lot | Commit | Objet |
|---|---|---|
| 1 | `87c00c05` | `parcels-ile` servie dès **z8** (plancher dur de la carte) → plus d'île noire |
| 2 | `115d3542` | doublon `limites_parcelles` retiré sur l'île (`ile-limites`) + **brotli** (reprise a3482087) |
| 3 | *(ce commit)* | preuve : captures avant/après, mesures, recette |

---

## Étape 0

- `git status -sb | head -1` = `## fix/g1-lot3...origin/main` ; worktree depuis `origin/main` `0f36c913`
  (= le merge des lots 1-2 de G1 ; **le lot 3 de G1, `a3482087`, n'était PAS mergé** — c'est lui qu'on reprend).
- Lu : `docs/audit-2026-10/G1/G1.md` §3 (sur `fix/g1`) et `docs/audit-2026-10/G1-MESURE/G1-MESURE.md`.
- Pas de merge, pas de push, aucun run, aucune écriture de données. DA existante. Aucun backend Postgres tué.
- Arrêt propre en fin de course (ports 8721/5921 libérés, 0 transaction idle-in-transaction).

---

## Lot 1 — couvrir tous les zooms atteignables

### Le zoom minimum réellement atteignable — **mesuré**, pas supposé

La vue île est bornée par `maxBounds = REUNION_MAXBOUNDS` **et** par `minZoom: 8`
(`MapView.tsx:491-492`, commentaire : « sous z8 l'île déborde du cadre »). J'ai mesuré le floor
imposé par `maxBounds` dans le vrai navigateur, à plusieurs tailles (hook `window.__labuse_map`,
`setMinZoom(0)` puis `jumpTo(zoom:0)` → le floor réel) :

| Fenêtre | Canvas (css px) | Floor maxBounds | Tuiles | 
|---|---|---|---|
| 1440×900 | 1030×844 | **z9.40** | z9 |
| 2560×1440 | 2150×1384 | **z10.46** | z10 |
| 3840×2160 | 3430×2104 | **z11.14** | z11 |
| 600×470* | 530×414 | **z8.44** | **z8** |

\* petite fenêtre **ou** zoom navigateur (≈ 240 %) : le canvas css rétrécit.

**Conclusion — et correction d'un point de la prémisse.** Le floor `maxBounds` **MONTE avec le
canvas** : plus l'écran est grand, moins on peut dézoomer (la carte refuse de montrer au-delà de
La Réunion). Donc **un grand écran ne descend JAMAIS sous z9** (4K → z11,1). C'est le **petit
canvas** — fenêtre réduite ou, le plus plausible, **zoom navigateur** sur un grand écran — qui
atteint le zoom le plus bas. Le **plancher absolu** est le `minZoom: 8` de la carte, atteint dès
que le canvas est assez petit (mesuré 600×470 → z8.44). **z8 est donc la tuile la plus basse que
la carte puisse JAMAIS demander**, quelle que soit la taille d'écran.

Sous z9, la route renvoyait **204** → à z8, l'île perdait parcelles **et** maillage → silhouette
noire (le défaut qui a fait rejeter l'essai 1 du lot 3, une fois l'overlay doublon retiré).

### Le correctif — servir z8, le choix retenu

Puisque le zoom atteignable ne descend jamais **sous** z8 (minZoom dur), **servir `parcels-ile`
dès z8 suffit** et couvre tous les écrans. Je n'ai donc **pas eu à abaisser `minZoom`** (la carte
est déjà bornée à z8) : c'est l'option « servir jusqu'au zoom couvert », pas « borner la carte ».

- `tiles.py` : route borne basse **z9 → z8** (z7 reste 204).
- `tiles.py` : palier de simplification **z8 = 120 m**. À z8, 1 px ≈ 570 m, soit le **double** de z9
  (285 m / 60 m) → **même tolérance visuelle (~0,2 px)** que z9 : extension cohérente du même LOD
  (et non 60 m littéral, qui serait deux fois plus fin que nécessaire). extent 1024 (comme z9-z11).
- `MapView.tsx` : source `parcels-ile` **minzoom 9 → 8**.
- z8 n'est **pas** pré-chauffée (hors `_WARM_ZOOMS`) : 1 seule tuile couvre l'île, générée à la volée.

### Poids réel de la tuile z8 (mesuré)

Tuile z8 de l'île (`8/167/143`) : **raw 0,384 Mo · gzip 0,102 Mo · brotli 0,100 Mo** — exactement
le chiffre de G1-MESURE §4 (0,10 Mo). Décodée : `layer=parcels`, `extent=1024` (consistant avec
z9-z11). 12× plus léger que l'overlay au même zoom (1,26 Mo) et, en vue île, **ride sur une tuile
déjà chargée** → coût net ≈ 0 ; le maillage z8 remplace le trou qui noircissait.

---

## Lot 2 — supprimer le doublon (reprise de `a3482087`)

Les hunks de code de `a3482087` ont été appliqués (3-way, propre) **par-dessus** le lot 1 :

- Nouveau calque neutre **`ile-limites`** (ligne sur `parcels-ile`, même style par fond que
  l'overlay commune via `paintParcellesParFond` exporté), piloté par le toggle « Limites parcelles »,
  **île seule**. Avec le lot 1 (source minzoom 8), il porte le maillage **jusqu'à z8**.
- `CouchesTuyau` : en vue île, l'overlay `tuyau-limites_parcelles` est **éteint** → MapLibre ne
  charge plus ses tuiles (extent 4096, ~3,2 Mo gz/ouverture). **Vue commune inchangée.**
- **Brotli** gardé : `tiles._tile_response` sort en brotli si accepté (`Content-Encoding: br`,
  `Vary`), repli gzip via `GZipMiddleware`, 304 préservé ; `brotli` déclaré dans `pyproject`.
  Caddy : `encode gzip` → `encode zstd gzip` (les tuiles arrivent déjà brotli de l'API, passthrough).

---

## Lot 3 — preuve

### 1. Aucune île noire, à aucune taille d'écran

**Reproduction fidèle de l'essai 1** (overlay éteint sur l'île + `parcels-ile` muette à z8) à
600×470 / z8.44 :

| | AVANT (essai 1 reproduit) | APRÈS (ce lot) |
|---|---|---|
| capture | `avant/z8_600x470_ESSAI1_ile_noire.png` | `apres/z8_600x470_corrige_maillage.png` |
| `parcels-ile` features @ z8 | **0** | **29 376** |
| `ile-limites` | absent | **visible** |
| rendu | **silhouette noire** | **maillage présent** |

Dézoom maximal aux trois résolutions mandatées (floors mesurés z9,4 / z10,5 / z11,1 — **tous ≥ z9**,
donc jamais noirs même **avant**, ce que confirment les captures) :

| résolution | avant | après |
|---|---|---|
| 1440×900 (z9) | `avant/01_dezoom_1440x900_z9.png` | `apres/01_dezoom_1440x900_z9.png` |
| 2560×1440 (z10) | `avant/02_dezoom_2560x1440_z10.png` | `apres/02_dezoom_2560x1440_z10.png` |
| 3840×2160 (z11) | `avant/03_dezoom_3840x2160_z11.png` | `apres/03_dezoom_3840x2160_z11.png` |

> Nota : les trois résolutions **ne reproduisent pas** l'île noire (leur floor est ≥ z9, où
> `parcels-ile` était déjà servie). Le cas noir n'existe qu'au **plancher dur z8** (petit canvas /
> zoom navigateur) — d'où la capture 600×470 dédiée, qui est le vrai critère de rejet de l'essai 1.

### 2. Avant/après à trois zooms (mêmes cadrages) + différences visuelles

Dézoom (ci-dessus), commune z12 (`04_commune_1440x900_z12.png`), quartier z14
(`05_quartier_1440x900_z14.png`), avant et après.

**Différence visuelle listée** (métrique du mandat — objets dessinés, `queryRenderedFeatures`, centre
St-Denis) :

| zoom | overlay (avant) | `ile-limites` (après) | écart |
|---|---|---|---|
| z9 | 308 202 | 36 292 | **−88,2 %** |
| z11 | 102 345 | 61 885 | **−39,5 %** |
| z12 | 49 423 | 49 419 | ≈ 0 (−4) |
| z13 | 25 751 | 25 907 | ≈ 0 (bruit) |

→ **identique à z12 et au-delà** (parcels-ile y est aussi en extent 4096) ; **maillage plus léger à
z9-z11** : l'extent 1024 + simplification (120/60/30/15 m) **écarte les parcelles sub-pixel**
(à z11, 1 px ≈ 71 m ; une parcelle de 200 m² ≈ 0,2 px). C'est **exactement le LOD déjà utilisé par
l'aplat des parcelles** — le maillage neutre s'aligne sur le reste du rendu île. C'est d'où vient le
gain. (Le −39,5 % à z11 reproduit à l'identique la mesure de G1 §3.)

### 3. Clic parcelle et sélection

- **Vue zoomée (z17)** : clic réel sur la toile → `#f=1&idu=97411000AL0479`, fiche ouverte,
  `ile-sel` filtré sur l'IDU (liseré blanc) — `apres/06_clic_zoom_z17_fiche_selection.png`.
- **Vue commune (Saint-Denis)** : overlay `tuyau-limites_parcelles-outline` = **visible** (inchangé),
  `ile-limites` = none — `apres/07_commune_selectionnee_overlay_inchange.png`. Le comportement commune
  n'est pas touché.
- **Dézoom (z ≤ 11)** : les tuiles maigres ne portent **pas** d'`idu` → le clic parcelle n'ouvre pas
  de fiche (navigation par **marqueurs de commune**). **Comportement pré-existant**, non modifié par
  ce lot (le clic/fiche au clic vit à z ≥ 12, où l'`idu` est présent).

### 4. Fond coloré éteint par défaut

`ile-fill` `fill-opacity = 0` par défaut (fond neutre, règle Vic). Avec **« Analyse LABUSE »**,
l'opacité devient une **expression** (0,72 pour les tiers chauds, 0 sinon) et `ile-line` apparaît —
`apres/08_analyse_labuse_fond_colore.png`. Aucune couleur de classement sans analyse demandée.

### 5. Couches « zoomez pour voir mieux »

Vérifié en vue île à z10 : `sup` (zoom_min 0) **et** `amenite_bpe` (zoom_min 12, couche à hint
« zoomez pour voir mieux ») restent **visibles** (toggle honoré). Le lot ne special-case **que**
`limites_parcelles` sur l'île (`!(ile && kind==='limites_parcelles')`) ; toutes les autres couches
gardent `tuyauActives[kind]`.

### 6. Gain mesuré (octets, méthode G1-MESURE — curl direct, base au repos)

Ouverture (maillage, tuiles z9×4) : **AVANT 3,549 Mo gz → APRÈS 0,303 Mo** (parcels-ile en brotli,
overlay = 0) = **GAIN 3,246 Mo (−91,5 %)**. Ouverture complète estimée (maillage + JS + fond + API) :
**≈ 3,99 Mo → ≈ 0,74 Mo** (G1-MESURE annonçait 3,81 → 0,72 ; même ordre). Le gros du gain = l'overlay
doublon éliminé ; le brotli grappille en plus (~2 % sur parcels).

### 7. Recette

- **tsc -b** : 0 erreur. **vitest** : **243/243** (53 fichiers).
- **pytest tuiles** (`test_carte_tuiles` + `test_retours14/16_carte`) : **11 passés, 1 skip** (garde
  layer/extent : `mvt_parcels` absente en base de test). Vérifié **contre la base réelle** par décodage
  MVT : **z8 → `parcels`/1024** (nouvelle tuile, consistante), z9/z11 → parcels/1024, z13 → parcels/4096.
- Test `test_zoom_borne_a_15_comme_la_source` mis à jour : z7 → 204, z16/z22 → 204, **z8 n'est plus
  rejetée par la borne** (8/1/1 mer → 200 vide avec données). Brotli : `test_brotli_sur_les_tuiles_et_repli_gzip`.

---

## Rapport — synthèse

- **Zoom minimum atteignable** : mesuré par résolution (1440 → z9,4 · 2560 → z10,5 · 4K → z11,1 ·
  petit canvas → z8,4). Le floor **monte** avec le canvas ; le plancher dur est **z8** (`minZoom: 8`).
  **Choix retenu** : servir `parcels-ile` dès z8 (pas d'abaissement de `minZoom`, la carte y est déjà
  bornée). L'île ne peut donc plus noircir à aucune taille d'écran.
- **Poids des nouvelles tuiles z8** : 0,102 Mo gz / 0,100 Mo br (= chiffre G1-MESURE).
- **Captures multi-écrans** : `captures/{avant,apres}/` (z8 noir→corrigé, dézoom 1440/2560/4K,
  commune, quartier, clic/sélection, fond coloré).
- **Différences visuelles** : identique à z12+ ; maillage −39,5 % d'objets à z11 (parcelles sub-pixel,
  = LOD de l'aplat) — différence visuelle, non fonctionnelle, à arbitrer par Vic.
- **Gain mesuré** : ouverture maillage −91,5 % (3,549 → 0,303 Mo).
- **Vérifications** : clic/sélection OK, commune inchangée, fond coloré off par défaut, couches
  « zoomez » intactes, tsc/vitest/pytest verts.

**Un commit par lot. Rien poussé. Vic valide le visuel sur son propre écran avant merge.**

## Fichiers touchés
```
src/labuse/api/tiles.py                        palier z8 + route z<8 (lot 1) ; brotli _tile_response (lot 2)
frontend/src/components/map/MapView.tsx        parcels-ile minzoom 8 (lot 1) ; calque ile-limites + effet (lot 2)
frontend/src/components/map/CouchesTuyau.tsx   paintParcellesParFond exporté + overlay éteint sur l'île (lot 2)
pyproject.toml                                 brotli déclaré (lot 2)
deploy/Caddyfile.prod/.example                 encode zstd gzip (lot 2)
tests/test_carte_tuiles.py                     borne z8 + gardes brotli/layer-extent
docs/audit-2026-10/G1-LOT3/…                   rapport, mesures/, captures/{avant,apres}/
```

---

## §8 — Correctif « zones noires dans les hauts » (retour Vic, après lot 3)

**Symptôme (Vic) :** à certains crans de zoom, une zone des hauts de l'île (secteurs peu denses)
restait noire **indéfiniment**, avec une **frontière droite** (bord de tuile) entre partie dessinée
et partie vide ; **un cran de plus (z12) et tout s'affichait**. **Absent sur main au même endroit.**

**Diagnostic (écarte d'abord les fausses pistes, mesuré) :** tuiles toutes **HTTP 200** (rien de
manquant, ni 204 ni erreur) ; **brotli octet-parfait** (`decompress == brut`, `Content-Encoding: br`
+ `Content-Length` cohérents) ; **cache sans tuile vide sur du bâti** (les 102 tuiles vides du cache
sont toutes en mer) ; **aucun gap minzoom/maxzoom** (`ile-limites` couvre z8-15 via la source +
sur-zoom au-delà ; overlay éteint sur l'île ; en commune l'overlay reste servi). **Cause réelle :
l'`extent 1024` à z9-z11** (≈ 5-19 m/unité) quantifiait les parcelles de **taille moyenne** jusqu'à
les rendre dégénérées → `ST_AsMVTGeom` les **écarte**. Dans un secteur peu dense, une tuile de
maillage perdait l'essentiel de ses parcelles → **tuile vide**. Ce maillage LOD ne portait l'île
**que depuis le lot 2** (overlay retiré) ; sur main le maillage venait de l'overlay **full-res
(extent 4096)** → pas de trou. Pertes mesurées vs full-res : **z9 89 %, z10 76 %, z11 19 %**.

**Correctif :** **extent 1024 → 4096 dès z9** (`tiles.py`). z8 garde 1024 (dézoom extrême : tout y
est sous le pixel, aucune parcelle *visible* n'est écartée). La simplification par palier **reste**
(elle n'enlève que le détail sous-pixel → poids maîtrisé).

**Preuve — parité de couverture avec main, z8→z17 (aucun cran noir) :**

| zoom | `ile-limites` AVANT | `ile-limites` APRÈS | overlay main | 
|---|---|---|---|
| z9 (île entière) | — | **221 814** | dense |
| z10 (Salazie) | 89 493 | **360 767** | 373 447 |
| z11 (Palmistes) | 136 779 | **150 933+** | dense |
| z12-z17 | inchangé (déjà 4096) | inchangé | ≈ |

Captures `captures/correctif-zones-noires/` : **01 AVANT** (z10 maillage clairsemé) vs **02 MAIN**
(dense) vs **03 APRÈS** (dense, = main) ; **04** z11 Palmistes complet ; **05** z9 île complète.
Balayage 0,25 z10→z17 : toutes tuiles `loaded`, maillage dense à chaque cran.

**Poids — gain honnête révisé :** l'ouverture z9 passe de **0,30 → 1,47 Mo br** (extent 4096). C'est
**toujours ≈ 59 % plus léger que main** (parcels 0,3 + overlay doublon 3,2 = 3,5 Mo) — et **sans
trou**. Le « −91,5 % » annoncé au §6 était l'artefact du maillage LOD trop agressif qui causait
précisément les zones noires : **le gain réel, sans trou, est ~59 %** (doublon supprimé + brotli +
propriétés maigres). La ligne « −39,5 % d'objets à z11 » du §3 **n'est plus** : le maillage z9-z11
rejoint la densité de l'overlay.

**⚠ Déploiement :** le cache tuiles (`mvt_tile_cache`, clé = version *donnée*) contient encore les
tuiles z9-z11 en extent 1024 → **purger** (`DELETE FROM mvt_tile_cache WHERE layer='parcels'`,
overlays intacts) puis laisser la route relancer en 4096 (ou `warm_parcel_tiles`). Fait en dev.

**Recette :** tsc 0 · vitest 243/243 · pytest tuiles 11 passés/1 skip (extent attendu z8→1024,
z9/z11/z13→4096 ; vérifié base réelle : z8 `parcels/1024`, z9/z11/z13 `parcels/4096`).
