# AUDIT — Fonds de carte commutables

**Date** : 2026-08-24 · **Branche** : `audit/fonds-carte` · **Type** : audit seul (aucun code modifié ; tuiles sondées en `GET`, comme le mandat TEMPS).
**Périmètre** : uniquement les **fonds de carte commutables** (le sélecteur). Overlays (AUDIT-COUCHES) et moteur/tuiles parcelles (AUDIT-CARTE-FOND) hors champ.
**Méthode** : lecture du code (`MapToolbar.tsx` = le sélecteur, `basemaps.ts` = le registre, `MapView.tsx` = bascule + attribution) + **sonde réelle des dalles** sur La Réunion (St-Denis, WMTS/CDN, plusieurs zooms).

> App laissée intacte (uvicorn:8000 + vite) : uniquement des `GET` de tuiles.

---

## 0. Le compte : **4 fonds au sélecteur** (Ortho déclinée en 3 millésimes) + Clair sans tuiles

Le sélecteur réel est `MapToolbar.tsx` (`BASEMAPS`, store `basemap`) — **4 fonds** : **Sombre · Clair · Plan IGN · Ortho IGN**. « Ortho IGN » se décline en **3 millésimes** via la sous-ligne « Remonter le temps » (`YEARS` : Actuelle / 2000-2005 / 1950-1965). Donc **5 sources raster distinctes servies** (CARTO, PLANIGNV2, ortho-now/2000/1950) + **Clair**, qui n'est **pas une tuile** (rendu sombre à fond blanc, `applyClairMode`, `active=null`). « ~5 basemaps » ≈ les 5 sources raster ; structurellement c'est 4 fonds dont un à 3 millésimes, plus un mode non-raster. ⚠ À ne pas confondre avec `BASEMAP_CHOICES` (5 entrées) qui est **un autre objet** (label du comparateur TEMPS, §2.5), pas le sélecteur.

---

## 1. Tableau des fonds

Millésime **réel** = période de la couche IGN, **dalles servies vérifiées par sonde** (pas les capabilities).

| Fond (sélecteur) | Source réelle | Millésime annoncé / réel | Couverture 974 (sonde St-Denis) | Verdict | Constat |
|------------------|---------------|--------------------------|--------------------------------|---------|---------|
| **Sombre** (défaut) | CARTO `dark_nolabels` (`basemaps.cartocdn.com`) — OSM | — (rolling) / — | dalles z9→z19 (léger : 4-20 Ko) | ⚠ | CGU/quota CARTO anonyme (§2.1) + attribution raccourcie. |
| **Clair** | *aucune tuile* (`applyClairMode`, fond blanc + parcelles) | — / — | N/A (pas de fond raster) | ⚠ | Affiche « © IGN Géoplateforme » alors qu'**aucune tuile IGN** n'est montrée (§2.3). |
| **Plan IGN** | `GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2` (data.geopf.fr) | — (rolling) / — | dalles z9→z19 (lourd : z12 95 Ko) | ✓ | Plan vectoriel-raster IGN, couverture pleine. |
| **Ortho IGN — Actuelle** | `ORTHOIMAGERY.ORTHOPHOTOS` | « Actuelle » / BD ORTHO en cours | dalles z9→z19 | ✓ | Millésime générique honnête (pas d'année promise). Attribution affichée générique. |
| **Ortho IGN — 2000-2005** | `ORTHOIMAGERY.ORTHOPHOTOS2000-2005` | 2000-2005 / 2000-2005 | dalles z9→z17 (z19 404 = overzoom, `maxzoom 17`) | ✓ | Concorde (nom de couche = période) ; déjà vérifié au mandat TEMPS. |
| **Ortho IGN — 1950-1965** | `ORTHOIMAGERY.ORTHOPHOTOS.1950-1965` | 1950-1965 / 1950-1965 | dalles z9→z17 servies, **capé `maxzoom 15`** (bords de mission) | ⚠ | Concorde, MAIS zones noires (mer/limites de mission) **sans la légende** qui n'existe que dans l'outil TEMPS (§2.4). |

**Bascule (task 3)** : ✓ — le changement de fond est une simple bascule de **visibilité** (`setLayoutProperty` sur les 9 couches raster, une seule visible ; `MapView.tsx:1086`). Les parcelles et overlays sont des couches **séparées**, non touchées → elles survivent, **pas de rechargement, pas de flash**. Ordre z : raster en bas (ajoutés en premier). `applyClairMode` gère le mode Clair.

---

## 2. Détail (là où il y a quelque chose à dire)

### 2.1 — Sombre = CARTO anonyme : CGU / quota ⚠ (moyen)
Le fond par défaut (« Sombre ») charge `basemaps.cartocdn.com/dark_nolabels` **sans clé ni compte**. La sonde sert des dalles aujourd'hui, mais l'usage anonyme du CDN CARTO n'est **pas contractuel** (pas de SLA, limitation de débit possible, TOS CARTO applicable). Pour un produit **commercial**, c'est une dépendance externe fragile (le commentaire `basemaps.ts:2` note « pas de tuiles Google (CGU) » — mais CARTO a ses propres CGU). De plus l'attribution « © OSM · CARTO » est **raccourcie** : la licence ODbL d'OSM attend « © OpenStreetMap contributors » et CARTO « © CARTO ».

### 2.2 — Attribution affichée = binaire codé en dur ⚠ (faible)
L'attribution montrée (`MapView.tsx:1572`) est `basemap==='dark' ? '© OSM · CARTO' : '© IGN Géoplateforme'` — **codée en dur**, non dérivée du fond. Conséquences : tous les fonds IGN (Plan + 3 orthos) affichent le même « © IGN Géoplateforme » ; la mention **spécifique** stockée dans `BASEMAP_SOURCES[].attribution` (« © IGN BD ORTHO », « © IGN ortho 2000-2005 »…) est bien passée à `addSource` (`:611`) mais **jamais affichée** (`attributionControl: false`, `:592`). Le millésime ortho n'est donc pas crédité à l'écran.

### 2.3 — Clair affiche une attribution IGN sans tuile IGN ⚠ (faible)
En mode Clair, `active=null` → **aucune tuile de fond** (fond blanc + parcelles cadastrales DGFiP). Or l'attribution affichée retombe sur la branche « else » = « © IGN Géoplateforme ». Attribution **inexacte** (rien d'IGN n'est montré ; le seul contenu est le cadastre DGFiP).

### 2.4 — Ortho 1950 dans le sélecteur : zones noires sans légende ⚠ (faible)
La légende honnête « Zones noires : secteurs non couverts par l'ortho ancienne… » (ajoutée au mandat TEMPS) vit **uniquement dans `TimeMachine.tsx`** (l'outil comparateur). Le **sélecteur principal** propose pourtant « Ortho IGN → 1950-1965 » comme fond plein écran : les mêmes dalles noires (mer, limites de mission) y apparaissent **sans aucune explication** → un utilisateur peut les prendre pour un bug de chargement. Le correctif TEMPS ne couvre pas cette surface.

### 2.5 — `BASEMAP_CHOICES` : rôle mort ⚠ (très faible)
`BASEMAP_CHOICES` (basemaps.ts:48, 5 entrées) est commenté « Choix proposés au **comparateur de fonds** » — mais **aucun composant ne l'itère comme sélecteur** (grep : zéro consommateur hors basemaps.ts). Depuis la refonte TEMPS, le comparateur utilise `TEMPS_MILLESIMES`. `BASEMAP_CHOICES` ne survit que comme **table de libellés** consultée par `basemapLabel` (utilisé par TimeMachine). Son commentaire/rôle est donc périmé.

### 2.6 — 4 couches basemap mortes dans la carte principale ⚠ (très faible)
`MapView.tsx:610` crée une source+couche raster pour **les 9** clés de `BASEMAP_SOURCES`, dont `bm-ortho-2006/2011/2016/2021`. Or la bascule (`:1082`) ne rend jamais visibles que `bm-carto`/`bm-plan`/`bm-ortho-now|2000|1950` — les 4 orthos récentes ne sont **jamais affichées dans la carte principale** (elles servent l'outil TEMPS, qui a sa **propre** carte). Ce sont 4 couches déclarées-jamais-montrées (sans coût réseau — un raster invisible ne charge pas — mais du bruit dans le style).

### 2.7 — Croisement avec TEMPS_MILLESIMES ⚠ (faible) — l'incohérence demandée
Le sélecteur principal « Remonter le temps » (`MapToolbar` `YEARS`) offre **3 millésimes** (Actuelle / 2000-2005 / 1950-1965). L'**outil TEMPS** (`TEMPS_MILLESIMES`) en offre **6** (ajoute 2006-2010, 2011-2015, 2016-2020, 2021-2023 — tous vérifiés servant des dalles sur le 974 au mandat TEMPS). Deux surfaces « remonter le temps » aux jeux **différents** : les 4 millésimes récents, pourtant vérifiés, sont **absents du sélecteur principal**. Les définitions, elles, sont partagées (`BASEMAP_SOURCES` = source unique) → aucune divergence d'URL/maxzoom, seulement d'exposition.

---

## 3. Classement des problèmes par gravité

| Gravité | # | Problème | Impact |
|---------|---|----------|--------|
| **Moyenne** | B1 | Sombre = CARTO anonyme (CGU/quota) + attribution ODbL/CARTO raccourcie (§2.1) | Dépendance externe fragile pour le fond par défaut d'un produit commercial ; attribution légale insuffisante. |
| **Faible** | B2 | Attribution affichée codée en dur (dark/IGN), millésime ortho non crédité, spécifiques inutilisées (§2.2) | Attribution grossière ; `BASEMAP_SOURCES[].attribution` mort à l'affichage. |
| **Faible** | B3 | Clair affiche « © IGN » sans tuile IGN (§2.3) | Attribution inexacte. |
| **Faible** | B4 | Ortho 1950 du sélecteur : zones noires sans légende (§2.4) | Ressemble à un bug de chargement ; le correctif TEMPS ne couvre pas cette surface. |
| **Faible** | B5 | Sélecteur « Remonter le temps » 3 millésimes vs outil TEMPS 6 (§2.7) | Incohérence entre surfaces ; 4 millésimes vérifiés non offerts au sélecteur. |
| **Très faible** | B6 | `BASEMAP_CHOICES` rôle mort (§2.5) + 4 couches ortho mortes dans la carte principale (§2.6) | Bruit/dette ; commentaire périmé. |

Côté **données/rendu, RAS** : les 5 fonds raster servent des dalles sur toute l'île (z9+), les millésimes annoncés concordent avec les couches IGN réelles (sonde), la bascule est propre (visibilité seule, parcelles/overlays intacts, pas de flash), les `maxzoom` orthos évitent les dalles noires par overzoom. Aucun fond ne casse, aucun style n'écrase les parcelles.

---

## 4. Correctifs candidats à mandater (non faits)

1. **B1** — Sécuriser le fond « Sombre » : obtenir une clé/compte CARTO (ou self-héberger un style sombre, ou basculer sur un fond sombre IGN) ; corriger l'attribution en « © OpenStreetMap contributors, © CARTO ».
2. **B2** — Dériver l'attribution affichée de `BASEMAP_SOURCES[].attribution` (par fond, avec le millésime ortho) au lieu du binaire codé en dur ; ou réactiver un `attributionControl` propre.
3. **B3** — En mode Clair, ne pas afficher « © IGN » (aucune tuile) — afficher l'attribution du cadastre (DGFiP) ou rien.
4. **B4** — Réutiliser la légende « zones noires » du mandat TEMPS quand `orthoYear='1950'` est sélectionné dans le sélecteur principal.
5. **B5** — Décider : étendre le sélecteur principal aux 6 millésimes vérifiés (aligner sur `TEMPS_MILLESIMES`), ou renvoyer explicitement vers l'outil TEMPS ; unifier les deux « remonter le temps ».
6. **B6** — Retirer/renommer `BASEMAP_CHOICES` (c'est une table de libellés, plus un sélecteur) ; ne pas créer dans la carte principale les 4 couches ortho réservées à l'outil TEMPS.

---

## 5. Synthèse

**4 fonds commutables** (Sombre / Clair / Plan IGN / Ortho IGN), Ortho déclinée en **3 millésimes** — soit 5 sources raster + le mode Clair sans tuile ; « ~5 » est donc approximatif, dit ici. Sur le fond des données, **tout est sain** : les 5 fonds raster servent des dalles sur toute La Réunion (sonde), les millésimes concordent avec les couches IGN réelles, la bascule ne recharge rien et ne casse ni parcelles ni overlays. **Six écarts**, un seul de gravité moyenne (le fond par défaut « Sombre » dépend de tuiles CARTO anonymes — CGU/quota — avec une attribution raccourcie) ; les autres sont d'attribution (binaire codé en dur, IGN affiché en mode Clair sans tuile), de cohérence entre surfaces (sélecteur 3 millésimes vs outil TEMPS 6 ; ortho 1950 sans sa légende de zones noires) et de dette (`BASEMAP_CHOICES` rôle mort + 4 couches ortho mortes dans la carte principale). Rien ne casse le rendu — c'est de la conformité légale et de la cohérence de surface, pas des fonds défaillants.
