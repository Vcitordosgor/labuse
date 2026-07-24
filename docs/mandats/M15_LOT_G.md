# M15 — LOT G : entrées généralisées + RG1 (héritage commune coupé)

**Branche** `fix/m15-g-entrees` — **empilée sur `fix/m15-b-plafonds`** (car G et B retouchent tous deux
M07). Prouvé, **non mergé**. ⚠ **ordre de merge : B d'abord, puis G.**

## Décision Vic appliquée
« Coupe l'héritage commune sur Mode bailleur et Foncier fantôme, généralise les 3 entrées
(IDU / adresse / clic carte). »

## Deux fixes

### 1. RG1 — héritage commune COUPÉ (M06 Mode bailleur, M07 Foncier fantôme)
Le sélecteur commune **global** de l'en-tête se dit lui-même « périmètre de la carte, des compteurs
**et des modules** » → ces deux outils héritaient **silencieusement** du filtre global. Un promoteur
avec « Saint-Denis » sélectionné ouvrait Foncier fantôme et voyait **744** parcelles en croyant voir
**tout** (6 261). Faux positif de contexte = boussole.

**Fix** : M06 et M07 n'écoutent plus `store.commune`. Périmètre = **état local**, défaut **« Toute
l'île »**, exposé par un sélecteur **`CommuneScope`** in-outil (« choisi ici — pas hérité du filtre
global »). Le back (`/bailleur`, `/fantome`) gère déjà `commune=None` (île entière). `modBailleur` /
`modFantome` ne passent plus par `cq()` (bridge store) mais par une commune **explicite**.

### 2. Les 3 entrées généralisées (parcelle : IDU / adresse / clic carte)
- **M09 Courriers (outil 22)** : l'étape « Parcelle » avait IDU + « parcelle sélectionnée » (2/3).
  Ajout de **`AddressAutocomplete`** → l'adresse résout la **parcelle rattachée** (source interne) et
  remplit l'IDU. Message honnête si l'adresse n'a **aucune** parcelle cadastrale rattachée.
- **M10 Due diligence (outil 21)** : batch « collez une liste ». Ajout d'une **barre 3 entrées** qui
  **alimente** le lot (append dédupliqué) : champ IDU + `AddressAutocomplete` + « ajouter la parcelle
  sélectionnée ». Le collage en masse reste possible.

Nouveau composant partagé `CommuneScope` ; imports `getCommunes`, `AddressAutocomplete`.

## Preuve (app `:8060`, `qa/m15/G/prove.mjs`)
| Point | Résultat |
|---|---|
| **07 RG1** | filtre global = **Saint-Denis** → périmètre outil **« Toute l'île » / 6 261** (PAS 744) ✓ ; choix explicite Saint-Denis → **744** ; pagination B intacte |
| **06 RG1** | filtre global = Saint-Denis → périmètre outil **« Toute l'île »** ✓ ; note « choisi ici — pas hérité du filtre global » |
| **09** | IDU ✓ · adresse ✓ · clic carte ✓ ; intro « 3 entrées » ; **« 8 rue de Paris » → 6 suggestions → IDU `97411000AH0303`** (parcelle réelle) |
| **10** | champ IDU ✓ · adresse ✓ · « + ajouter » ✓ ; 2 ajouts → textarea `97415000AC0253 / AC0254` (append + dédup) |

Captures : `07a/07b`, `06`, `09/09b`, `10`.

## Golden
**116/116 PASS** (`LABUSE_DEV_MODE=1`, `LABUSE_API_BASE=http://127.0.0.1:8060`). Zéro touche scoring
(seuls le périmètre d'affichage et les entrées changent ; les données servies sont identiques).

## Notes
- G empilée sur B : merger **B puis G**. Aucun conflit à résoudre à la main (G compose sur le M07 déjà
  paginé de B : le périmètre explicite alimente la même `useInfiniteQuery`).
- En mode île, la **carte** reste cadrée sur la commune globale (viewport), mais la **donnée** de
  l'outil est bien island-wide — le sélecteur `CommuneScope` lève l'ambiguïté explicitement.
- L'entrée « adresse » exige une adresse au **numéro** (résolution parcellaire) ; une rue seule ne
  résout pas → message honnête, pas d'IDU inventé.
