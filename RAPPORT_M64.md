# RAPPORT M64 — PHASE 0 (diagnostic) — teinte rouge/brun au chargement

**Mesuré, rien corrigé.** Sur `main` (M62 `44ef7274` + M63 `2881776d` mergés). Symptôme :
vue île entière au chargement, toutes les parcelles teintées rouge/brun ; disparaît dès qu'on
touche un filtre (ou une couche).

## 1. Couche coupable + couleur exacte

**Couche `ile-fill`** (vue île, tuiles MVT) — source `parcels-ile`, `source-layer` `parcels`.
Jumelle en vue commune : **`parcels-fill`** (source geojson `parcels`), même défaut.

**Peinture mesurée AU CHARGEMENT** (via `getPaintProperty`) :
- `fill-color` = **l'expression STATUS_COLOR** (palette VERDICT) :
  `["case", [">=", ["to-number", ["coalesce", ["get","etage0"],0]], 1], "#E8695A", ["match", tier_v2, …]]`
- `fill-opacity` = **0.28**
- `visibility` = `visible`, `filter` = `["all"]` (match-all)

La palette verdict donne, pour l'état de chargement (aucun run) : **étage 0 / tier « écartée » →
`#E8695A` (braise/ROUGE)**, **6 tiers de déclassement → `#8C7468` (terre/BRUN)**. Normalement ces
tiers sont peints à l'opacité `STATUS_OPACITY` (0.04, quasi éteints). **Ici ils sont à 0.28** (car
c'est l'opacité de la branche NEUTRE) → le rouge/brun devient **visible sur toute la carte**.

## 2. État initial de la couche vs état attendu

L'effet de peinture principal (`MapView.tsx`, branche « verdict éteint », ~L834-838) doit peindre,
au chargement (ni opinion, ni tri factuel, ni zonage), un remplissage **NEUTRE** :
`fill-color = "#22302A"`, `fill-opacity = 0.28` (« trame cadastrale, aucune couleur »).

Le **filtre** de la couche n'est PAS en cause : `["all"]` (match-all) est NORMAL — la trame neutre
est censée peindre toutes les parcelles… **en gris**. Le défaut est la **COULEUR** : elle est
STATUS_COLOR (verdict) au lieu de `#22302A` (neutre), à opacité 0.28.

**Mesure comparée** (même session) :
| | `ile-fill` fill-color |
|---|---|
| au chargement | **`EXPR(status)`** — palette verdict (rouge/brun) ❌ |
| après toggle d'une couche / filtre | **`#22302A`** — neutre ✅ |

## 3. Ce qui fait disparaître le rouge

Toute manipulation qui change `filters` OU `layers` **re-déclenche l'effet de peinture principal**
(ses deps), qui ré-écrit `fill-color = "#22302A"` (branche neutre) → le rouge disparaît. La cause
racine (ci-dessous) n'écrase la couleur **qu'au chargement** (elle s'exécute en dernier au boot) et
**ne se ré-exécute pas** sur un simple changement de filtre (ses deps ne couvrent pas tout `filters`),
d'où « le symptôme disparaît et ne revient plus » après le premier geste.

## 4. Commit responsable

**`90fc0344` — « M63-P1 fond clair »** (vérifié `git log -S applyTheme`). Ce commit a ajouté la
fonction **`applyTheme(m, C)`** (thématisation sombre/clair du fond), appelée dans l'effet « fond de
plan » de `MapView`. Elle réapplique la palette de TOUTES les couches quand le fond bascule — mais
elle pose `parcels-fill` / `ile-fill` **`fill-color = statusColorFor(C)` de façon INCONDITIONNELLE**
(`applyTheme`, ~L175), sans respecter le mode courant (zonage / opinion / factuel / neutre) que gère
l'effet de peinture principal. Au boot, `applyTheme` s'exécute après l'effet principal → il écrase le
neutre `#22302A` par la palette verdict, tandis que l'opacité (0.28, non touchée) reste celle du
neutre → parcelles rouges/brunes. **Aucun rapport avec le rouge du verdict lui-même** : c'est un
écrasement de la couleur de remplissage en mode « verdict éteint ».

*(M62 n'y est pour rien : ses changements sur MapView — bouton zoom 60 px, libellé « · Fiche commune »
— ne touchent ni le remplissage ni les filtres.)*

## Proposition de correction (une phrase)

Dans `applyTheme`, **ne pas** régler `fill-color` de `parcels-fill` / `ile-fill` inconditionnellement :
en laisser la couleur à l'effet de peinture principal (qui connaît le mode) et **le ré-exécuter au
changement de thème** (p. ex. retirer ces deux couches de `applyTheme` et ajouter `basemap` aux deps
de l'effet principal), ou faire respecter à `applyTheme` la même logique zonage/opinion/factuel/neutre.

## STOP
Diagnostic terminé, aucune correction, aucun commit.
