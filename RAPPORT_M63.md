# RAPPORT M63 — Fond de carte clair — PHASE 0 (constat)

Branche `feat/m63-fond-carte-clair` (de `main`, contient m59 mergé ; **indépendante de m62**).
**Constat seul, aucun correctif.** Objet : ajouter un fond CLAIR à la carte, l'UI restant en
thème sombre. Contrastes **mesurés** (WCAG 2.1), pas estimés.

---

## P0-1 — Le sélecteur de fonds aujourd'hui

`frontend/src/components/map/basemaps.ts` — 5 fonds :
| Libellé | clé | source | type |
|---|---|---|---|
| Fond sombre | `bm-carto` | `basemaps.cartocdn.com/dark_nolabels` (a/b) | raster CARTO |
| Plan IGN | `bm-plan` | WMTS `GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2` | WMTS IGN |
| Ortho actuelle / 2000-2005 / 1950-1965 | `bm-ortho-*` | WMTS `ORTHOIMAGERY.*` | WMTS IGN |

Le sélecteur (bouton « Fond de plan » de `MapToolbar`) liste **sombre + plan IGN + 3 ortho**.
**Aucun fond CLAIR** — ni présent, ni listé-cassé : **absent**. (Le « Plan IGN » est clair mais
c'est un plan topographique labellisé, pas une toile neutre de type Positron.)

## P0-2 — Styles clairs libres, sans clé, licence/attribution

- **CARTO Positron** (`basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png`, a/b) — **miroir EXACT
  du fond sombre actuel** (`dark_nolabels`, même CDN, mêmes tuiles raster, **pas de clé**).
  Attribution requise : **« © OSM · CARTO »** — c'est **déjà** l'attribution servie pour le fond
  sombre (`basemaps.ts:16`). → **coût nul, clé nulle, aucune obligation nouvelle.** ✅ **recommandé.**
- OSM standard raster (`tile.openstreetmap.org`) : attribution « © OpenStreetMap contributors », mais
  la *tile usage policy* OSM **déconseille l'usage applicatif** (pas de CDN garanti) → écarté.
- Plan IGN clair : déjà dispo (`bm-plan`), mais toile chargée (labels/routes) ≠ fond neutre demandé.

→ **Retenu pour arbitrage : CARTO Positron `light_nolabels`**, ajouté au sélecteur existant à côté
de « Sombre », attribution « © OSM · CARTO » (inchangée), variante `light_all` si labels souhaités.

## P0-3 — Inventaire des couleurs de couches + contraste MESURÉ

Fond de mesure : **land Positron clair ≈ `#F5F5F3`** (les routes/eau y sont encore plus clairs,
proches du blanc → le pire cas est encore plus dur). Seuils : **≥3:1 OK · 1.8-3 faible · <1.8
INVISIBLE** (WCAG non-texte AA = 3:1). *Rappel : les remplissages (`fill`) à opacité 0.1-0.4 sont
en réalité PIRES (couleur diluée dans le fond) ; les valeurs ci-dessous sont à pleine opacité.*

| Couche (id) | rôle | hex actuel | contraste /clair | verdict |
|---|---|---|---|---|
| `parcels-sel` / `parcels-ping` | **sélection / survol-pulse** | `#ECF5EF` | **1.02** | **INVISIBLE** |
| `*-zone-label` (texte) | libellé zone PLU | `#ECF5EF` | **1.02** | **INVISIBLE** |
| `communes-bounds` | **limites de communes** | `#5CE6A1` | **1.45** | **INVISIBLE** |
| `ov-zonage` U (mint) | zonage U (fill 0.10) | `#5CE6A1` | **1.45** | **INVISIBLE** |
| verdict **chaude** | tier | `#E8B44C` | **1.74** | **INVISIBLE** |
| zone A (PLU) | zonage agricole | `#E8B23A` | **1.77** | **INVISIBLE** |
| `parcels-limites` | **limites de parcelles** | `#8FA69A` | 2.38 | faible |
| verdict a_creuser | tier | `#8FA69A` | 2.38 | faible |
| verdict réserve | tier | `#6FA8DC` | 2.31 | faible |
| zone N | zonage naturel | `#3FB56A` | 2.40 | faible |
| `ov-renouv` | renouvellement | `#C9834E` | 2.81 | faible |
| `ov-ppr` / verdict brûlante | risque / tier | `#E8695A` | 2.92 | faible |
| `parcels-line` search | résultats recherche | `#B497F0` | 2.23 | faible |
| `parcels-brulantes` | contour brûlante | `#FF6B35` | 2.60 | faible |
| zone U | zonage urbain | `#E5417F` | 3.57 | OK |
| zone AU | zonage à urbaniser | `#4C7DF0` | 3.50 | OK |
| verdict écartée | tier | `#4A5A52` | 6.69 | OK |
| **labels commune** (DOM) | texte hot/cold | `#5CE6A1` / `#8FA69A` | 1.45 / 2.38 | **INV. / faible** |

**Les 2 cas critiques du mandant, CONFIRMÉS par la mesure :**
1. **« limites de parcelles en vert pâle »** → `parcels-limites #8FA69A` (2.38, faible) et le mint
   `#5CE6A1` (1.45, invisible) : **disparaissent** sur fond clair. ✅ confirmé.
2. **« cadastre en traits blancs »** → sélection / pulse / label `#ECF5EF` (**1.02** — quasi
   identique au fond) : **totalement invisibles**. ✅ confirmé.

**Fond de canvas** : `#060A08` (`MapView.tsx:24`) — remplacé par le fond clair, à basculer.
**Couleurs OK telles quelles** sur clair : zones U/AU, verdict écartée. **Tout le reste** (mint,
crèmes, limites, tiers chauds, PPR, renouv, labels) nécessite une valeur claire.

**Source des couleurs** : ~35 couches dans `MapView.tsx` (paint en dur ou via `TOKENS.*`
`lib/tokens.ts` et `ALL_TIER_META`/`ZONE_FAM_META`/`EQUIP_META` `lib/status.ts`). Beaucoup sont
**en dur dans MapView** (`#8FA69A`, `#5CE6A1`, `#ECF5EF`, `#22302A`…) → P1-b (« jamais en dur »)
implique de **tokeniser** ces valeurs avec une paire sombre/clair.

---

## Synthèse
| # | Constat |
|---|---|
| 1 | Sélecteur = sombre CARTO + Plan IGN + 3 ortho. **Fond clair ABSENT.** |
| 2 | **CARTO Positron `light_nolabels`** = miroir exact du sombre, libre, sans clé, attribution « © OSM · CARTO » **déjà servie**. Recommandé. |
| 3 | Sur fond clair (#F5F5F3, mesuré) : **INVISIBLES** = sélection/survol/labels `#ECF5EF` (1.02), communes & mint `#5CE6A1` (1.45), verdict chaude `#E8B44C` (1.74), zone A (1.77) ; **faibles** = limites parcelles `#8FA69A`, PPR/brûlante, renouv, réserve, zone N, violet. Les 2 cas mandant confirmés. Couleurs en dur dans MapView à tokeniser. |

## STOP — PHASE 0
Constat terminé, aucun correctif. Points d'arbitrage P1 :
- **Fond retenu** : CARTO Positron `light_nolabels` (recommandé) ou variante `light_all` (avec labels) ?
- **P1-b** : chaque couche reçoit une **paire de tokens** sombre/clair (rôle inchangé, valeur adaptée) —
  priorité aux INVISIBLES (sélection, survol, limites, communes, mint, tiers chauds, labels).
- **P1-c** : labels commune — 2 jeux de couleurs (le crème/vert actuel invisible sur clair).
- Le fond **SOMBRE reste le défaut, inchangé** (garde-fou).
NE PAS MERGER.

---

# PHASE 1 — correctifs (arbitrage mandant)

Fond clair CARTO Positron retenu. Le vrai travail = les couches, tokenisées en paires sombre/clair.
Vérifié : tsc 0 · vitest 32/32 · build OK · console 0 erreur · **fond SOMBRE inchangé (mesuré)**.

## (a/e) Fond clair au sélecteur existant, persistant
- `basemaps.ts` : `bm-clair` = CARTO Positron `light_nolabels` (miroir exact du sombre, attribution
  **« © OSM · CARTO » — déjà servie**). Ajouté à `BASEMAP_CHOICES`.
- `MapToolbar` : le sélecteur existant liste **« Clair » · « Sombre » · Plan IGN · Ortho IGN** (pas
  de nouveau bouton ; « Sombre (Carto) » simplifié en « Sombre »).
- **Persistance** (`useApp.ts`) : le choix `dark`/`clair` est mémorisé en `localStorage`
  (`labuse.basemap`), restauré au boot. Défaut **`dark`** (le sombre reste le fond par défaut).
- (d) Attribution : `bm-clair` porte « © OSM · CARTO » ; maplibre affiche celle du fond actif.

## (a/b/c) Tokenisation sombre/clair — aucune couleur de couche en dur
- Nouveau point de vérité `lib/mapPalette.ts` : chaque couleur = paire **[sombre, clair]**. **Sombre
  = valeur historique EXACTE** (garde-fou). **Clair = contraste MESURÉ ≥ 3:1** sur land Positron
  (~#F5F5F3), toutes vérifiées via `contrast.py` (ex. limites 6.3:1, sélection 6.0:1, communes 4.6:1,
  verdict chaude 4.3:1, zone A 4.3:1 — les cas invisibles du P0 corrigés).
- `MapView` : l'**init garde les constantes SOMBRES d'origine** (dark non touché) ; une fonction
  `applyTheme(m, C)` **additive** réapplique la palette (sombre OU claire) quand le fond bascule.
  Les expressions sémantiques (verdict `statusColorFor`, zonages `zoneFamColorFor`, overlay zonage
  `zonageOverlayFillFor`) sont reconstruites depuis la palette → **le RÔLE ne change pas** (le verdict
  garde son échelle, les zonages leur code) ; en mode zonage, `parcels-fill` suit la couleur par
  famille (préservé).
- **Vérif directe des paint-properties** (garde-fou absolu) :
  - SOMBRE : `limites #8FA69A · sélection #ECF5EF · communes #5CE6A1 · ppr #E8695A · renouv #C9834E ·
    bg #060A08` — **identiques à l'avant-M63 (pas un pixel)**.
  - CLAIR : `limites #4A5F54 · sélection #0A6B3F · communes #2E7D52 · ppr #C4402F · renouv #9A5A28 ·
    bg #EDEDEA` — sélection ≠ survol (violet #6A4FB0) ≠ communes, verdict lisible sur les 4 tiers.

## (c/d) Libellés de commune lisibles sur les deux fonds
- `MapView` (markers DOM) thématisés : texte/bordure/fond par thème (le crème/mint invisible sur clair
  → vert foncé `#1F7A46`/`#4A5F54` + fond blanc translucide + halo clair). Vérifié à l'écran : texte
  **foncé** (lisible) sur fond clair ; l'effet dépend de `basemap` (rebâti au switch).

## Contrôle final (fond clair)
Parcelles visibles (limites 6.3:1) · commune sélectionnée distinguable (sélection 6.0:1) · survolée
(violet) ≠ sélectionnée (vert foncé) · verdict lisible sur les 4 tiers (brûlante 4.7 / chaude 4.3 /
réserve 4.9 / écartée 6.7) · zonages distinguables (U magenta, AU bleu, A ocre, N vert foncé).

## STOP — PHASE 1
Tout M63-P1 livré. Fond sombre inchangé (mesuré). Commit « M63-P1 fond clair ». **NE PAS MERGER.**
