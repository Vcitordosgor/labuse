# G1-MESURE — combien pèse l'ouverture de la carte, et combien on gagnerait

**Mandat :** mesurer le poids de l'ouverture de la vue île et le gain du lot 3 de G1
(suppression du doublon `limites_parcelles`, cf. commit `a3482087` sur `fix/g1`, non mergé).
**Lecture seule** — aucun commit de code, aucun run, aucune écriture en base ; seul ce rapport
est commité. Branche `audit/g1-mesure` depuis `origin/main` (`31e58719`), worktree
`~/Desktop/labuse-g1mesure`, API 8720 / Vite 5920, run servi `q_v16` (431 663 parcelles).

**Méthode insensible à la charge :** tous les octets de tuiles sont mesurés par `curl` direct
sur l'API (déterministes, reproductibles) ; aucun temps n'est utilisé pour conclure. Les
ensembles de tuiles et les poids JS/fond sont relevés dans un vrai navigateur (Playwright,
cache vidé, fenêtre 1440×900, canvas carte 1030×844). Harnais : `harnais/tiles_couverture.py`,
`harnais/simule_z8.py` ; mesures brutes dans `mesures/`.

---

## 0. Le mécanisme du doublon (rappel vérifié)

À l'ouverture, le maillage cadastral de l'île est dessiné **deux fois** :

| Source | Endpoint | Rôle | Géométrie servie |
|---|---|---|---|
| `parcels-ile` | `/map/tiles/{z}/{x}/{y}.pbf` | parcelles cliquables + aplat classement | **simplifiée** par palier (z9 : 60 m, extent **1024**, propriétés *maigres*) |
| `limites_parcelles` (overlay « Limites parcelles », **coché par défaut**) | `/map/tiles/limites_parcelles/{z}/{x}/{y}.pbf` | traits du maillage | **brute** (extent **4096**, aucune simplification) — `tiles.py:332-339` |

Les deux lisent la même table `mvt_parcels`. Le doublon n'est donc pas « deux jeux de
données » mais **la même géométrie servie une fois simplifiée (parcels-ile) et une fois en
pleine résolution (overlay)**. C'est pourquoi, à faible zoom, l'overlay est beaucoup plus lourd
que la couche cliquable.

---

## 1-2. Octets transférés par source et par zoom

Poids **gzip** (ce que sert la prod : Caddy `encode gzip` ; brotli = fonctionnalité du lot 3,
**absente d'`origin/main`** — vérifié : `Accept-Encoding: br` renvoie les octets bruts).
Nombre de tuiles = ce que le navigateur demande réellement à chaque zoom.

### Ouverture — vue île (zoom mesuré **9.92**, tuiles de niveau **z9**)

| Source | tuiles | brut | **gzip** |
|---|---:|---:|---:|
| **`limites_parcelles` (doublon)** | 4 | 9,47 MB | **3,09 MB** |
| JS + CSS critiques (prod, code-splitté) | — | — | 0,35 MB |
| `parcels-ile` | 4 | 1,02 MB | 0,29 MB |
| API/JSON (`/sources`, `/map/tuyau/couches`…) | — | — | 0,05 MB |
| fond de carte (raster mosaïque monde) | 4 | — | 0,03 MB |
| `limites_communes` | 4 | 0,01 MB | 0,005 MB |
| **TOTAL (X)** | | | **≈ 3,81 MB** |

> Note JS : en `npm run dev` le navigateur charge 9 Mo de modules non-bundlés — **non
> représentatif**. Le chiffre ci-dessus est le build de prod (`vite build`) : chunks critiques
> de `index.html` = 0,35 Mo gzip (dont maplibre 0,20 Mo). Total de tous les chunks = 0,60 Mo.

### Commune (z12, centre Saint-Denis urbain — 6 tuiles/source)

| Source | tuiles | brut | **gzip** |
|---|---:|---:|---:|
| `parcels-ile` | 6 | 6,84 MB | **3,18 MB** |
| **`limites_parcelles` (doublon)** | 6 | 2,94 MB | **1,38 MB** |
| `limites_communes` | 6 | ~0 | ~0 |

### Quartier (z14, même centre — 9 tuiles/source)

| Source | tuiles | brut | **gzip** |
|---|---:|---:|---:|
| `parcels-ile` | 9 | 2,37 MB | **1,13 MB** |
| **`limites_parcelles` (doublon)** | 9 | 1,24 MB | **0,59 MB** |
| `limites_communes` | 9 | ~0 | ~0 |

**La bascule de poids.** À l'ouverture (z9), l'overlay pèse **10×** la couche cliquable
(3,09 vs 0,29 Mo) : parcels-ile est fortement simplifiée (extent 1024, propriétés maigres), pas
l'overlay. À partir de z12 le rapport **s'inverse** : parcels-ile sert alors toutes ses
propriétés (idu, surfaces, scores, SDP…) à extent 4096 et devient la plus lourde, l'overlay ne
portant que des contours. Le doublon reste une redondance pure à tous les zooms, mais son
**coût relatif est maximal à l'ouverture**.

---

## 3. Zooms minimum des deux sources — et le « dézoom complet » réel

- `parcels-ile` : source **minzoom 9** / maxzoom 15 (`MapView.tsx:637`). La route **renvoie 204
  pour z < 9** (`tiles.py:761`) — vérifié : `/map/tiles/8/167/143.pbf` → HTTP 204, 0 octet.
- `limites_parcelles` : overlay **zoom_min 0** (source vector minzoom 0, `CouchesTuyau.tsx:496`)
  — vérifié sur `/map/tuyau/couches`. Il sert donc le maillage **y compris sous z9**.

C'est l'origine du « noir au dézoom » du lot 3 : retirer l'overlay laisse parcels-ile seule, et
parcels-ile est muette sous z9.

**MAIS — mesuré — ce cas ne se produit pas à 1440×900.** La vue île est bornée par
`maxBounds: REUNION_MAXBOUNDS` = [55, −21.62, 56.07, −20.65] (`MapView.tsx:491`, posé
*précisément pour ne pas dériver là où les parcelles renvoient 204*). Conséquence mesurée : même
en forçant `setMinZoom(1)`, la carte **se bloque à z9.403** (floor 9). Le zoom le plus éloigné
atteignable sur l'île est donc **z9.4 → tuiles z9 → parcels-ile EST servie**. Le dézoom complet
réel de cette vue n'atteint jamais z8 ; l'île ne noircirait pas.

---

## 4. Simulation — parcels-ile servie dès le dézoom complet (z8)

**Méthode retenue : génération à la volée sans stockage** (et non l'extrapolation). Raison : la
simplification/quantification MVT n'est pas linéaire en zoom — extrapoler depuis z9 fausserait le
chiffre. On génère la tuile z8 de l'île (`8/167/143`, 1 seule tuile couvre l'île) par le **même
SQL** que `_parcel_tile_bytes`, sans écrire ni en cache ni en base (`harnais/simule_z8.py`).

| Scénario à z8 | brut | gzip |
|---|---:|---:|
| overlay `limites_parcelles` **aujourd'hui** (si z8 atteignable) | 4,32 MB | 1,26 MB |
| parcels-ile étendue — code actuel tel quel (simplify 0, extent 1024) | 0,76 MB | 0,17 MB |
| parcels-ile étendue — **palier z8 sensé** (simplify 120 m) | 0,37 MB | **0,10 MB** |

Même dans le cas (moot) où l'on atteindrait z8, une parcels-ile étendue pèserait **0,10 Mo**
contre **1,26 Mo** pour l'overlay. L'extension n'est de toute façon **pas nécessaire** à
1440×900 (cf. §3) ; si un canvas plus grand pouvait atteindre z8, une ligne
`{8: 120}` ajoutée au palier de simplification suffirait.

---

## Le chiffre

> **Aujourd'hui l'ouverture de la vue île pèse ≈ 3,81 Mo (gzip). Sans le doublon
> `limites_parcelles`, le maillage étant porté par `parcels-ile` déjà téléchargée, elle
> pèserait ≈ 0,72 Mo. Gain : ≈ 3,09 Mo = 81 %.**

Y est **très inférieur** à X : à l'ouverture, parcels-ile est maigre (simplifiée, peu
d'attributs) — l'objection « parcels-ile porte plus d'attributs » ne mord **pas** au dézoom,
elle ne joue qu'à partir de z12. Le maillage retiré de l'overlay est redessiné par le calque
`ile-limites` qui chevauche les tuiles parcels-ile **déjà chargées** → **coût net 0 octet**.

Gains du doublon à d'autres zooms (octets gzip épargnés par ouverture de panneau) : z12 ≈
1,38 Mo, z14 ≈ 0,59 Mo.

---

## Recommandation

**Le lot 3 vaut la peine : reprendre.** Le doublon `limites_parcelles` représente **81 % du
poids d'ouverture** (≈ 3,1 Mo gzip payés à chaque ouverture à froid, à chaque client) pour une
géométrie que `parcels-ile` dessine déjà ; le risque « île noire au dézoom » **ne se reproduit
pas** à 1440×900 (maxBounds borne la vue à z9.4, où parcels-ile est servie), donc l'extension de
parcels-ile à z8 — bien que mesurée à 0,10 Mo — n'est même pas requise. Seule contrepartie à
arbitrer par Vic (déjà listée au §3 de G1) : à z9-z11 le maillage parcels-ile est plus grossier
que l'overlay (parcelles sub-pixel quantifiées par l'extent 1024, ≈ −39,5 % d'objets), différence
visuelle, non fonctionnelle.
