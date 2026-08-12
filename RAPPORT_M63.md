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
