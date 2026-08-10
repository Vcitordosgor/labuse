# RAPPORT M55-A — Section « Couches » de la carte

Branche `feat/m55-a-couches` (base `main` cb4bf0c5). **CC ne merge jamais — STOP review Vic.**
Mesures faites en base locale (`labuse`, DB vivante) ; captures via le dev server vite (HMR →
reflète le working tree). `tsc --noEmit` : 0 erreur. `vitest run` : 26/26. `npm run build` : vert
(le fantôme `vite.config.js` local a été supprimé par Vic — le caveat build initial est levé).

---

## MISE À JOUR 10/08 — décisions Vic implémentées (4 commits, un par point)

Après les mesures ci-dessous, Vic a tranché. Implémenté :

1. **Fusion A** (commit 4763fc1c) — `zonage_colorise` supprimée, fusionnée dans la couche
   parcellaire unique « Zonage PLU par parcelle (calibré) » ; la GPU brute renommée « Zones du PLU
   officiel (document brut) » (le « couvre aussi voirie/domaine public » passe dans le « i »).
   Saint-Philippe : toast « commune au RNU — pas de zonage PLU ». **Panneau : 2 couches zonage.**
2. **OSM élargi, borné** (commit d0e63008) — +marché forain (`amenity=marketplace`), +crèche
   (`amenity=childcare`), +collège/lycée (`amenity=school` filtré au nom `coll.ge|lyc.e`). CLI
   `ingest-amenites-affichage` (ingest_poi_affichage était orpheline). « i » commerce explicité.
   Prouvé Saint-Pierre (5/10/25) ; ingestion île en local (à rejouer VPS). **Affichage seul.**
3. **parc_national dédupliqué** (commit d790e274) — 72 → 3 (Cœur/2 adhésions), `commune=NULL`
   île entière ; ingestion corrigée (stockage 1×, idempotent). Scoring intact (intersection par
   bbox, pas par commune). **SQL de nettoyage à rejouer sur VPS** (ci-dessous).
4. **Chevrons uniformisés** (commit 6729843f) — FiltreLabuse + ResultsSection passent au patron
   fermé→gauche / ouvert→bas, comme Couches/Verdict.

Vérifs : `tsc` 0, `vitest` 26/26, `pytest test_amenites` 5/5, cascade/etage 57/57 (échec
`test_residuel` = pré-existant, session None, sans lien), `npm run build` vert. Captures
`item4/item5/point2/point4_*` dans `reports/m55-a-couches/captures/`.

**SQL de nettoyage parc_national à rejouer sur le VPS** (le code empêche la ré-duplication,
mais les 72 lignes déjà en base doivent être purgées une fois) :
```sql
DELETE FROM spatial_layers a USING spatial_layers b
 WHERE a.kind='parc_national' AND b.kind='parc_national'
   AND a.subtype=b.subtype AND a.name IS NOT DISTINCT FROM b.name AND a.id > b.id;
UPDATE spatial_layers SET commune=NULL WHERE kind='parc_national';
```
**Ingestion élargissement OSM à rejouer sur le VPS** : `labuse ingest-amenites-affichage`.

---

_Ci-dessous : les mesures et propositions initiales (contexte des décisions ci-dessus)._

| # | Objet | Type | État |
|---|-------|------|------|
| 1 | 3 couches « zonage PLU » | **MESURE + proposition** | **STOP Vic** (rien codé) |
| 2 | Couverture île entière par couche | MESURE | Tableau ci-dessous |
| 3 | Contenu réel des Équipements (OSM) | **MESURE** | Mapping + « commerce = X » ; **STOP si élargir** |
| 4 | Bulles équipements cliquables | FIX | ✅ livré + capture |
| 5 | Flèche de la section Couches | FIX | ✅ livré + captures |
| 6 | Audit des « i » | FIX | ✅ livré (avant/après) |

---

## 1. STOP — les trois couches « zonage PLU »

### Ce que fait chacune, réellement (mesuré en code + base)

| | **Zonage PLU (zones officielles)** | **Zonage PLU (par parcelle)** | **Colorisation par type de zonage** |
|---|---|---|---|
| Clé | `zonage` | `zonage_parcelle` | `zonage_colorise` |
| **Source données** | `spatial_layers` kind=`plu_gpu_zone` — flux GPU / Géoportail de l'urbanisme | `parcel_zone_plu.zone_fam` — jointure parcelle ↔ GPU, **calée sur le cadastre par LABUSE** | `parcel_zone_plu.zone_fam` — **la même** |
| **Rendu** | polygones **bruts** du document, 2 teintes (U vs reste), opacité 0,10, contours d'origine | remplissage de **chaque parcelle** par famille (palette U/AU/A/N) **+ étiquette du code au zoom ≥16 + popup au clic** | remplissage de **chaque parcelle** par famille — **fill identique, SANS étiquette ni clic** |
| **Mode** | commune seulement (`!ile`) ; en île via tuiles `ovmvt-zonage` | commune (geojson) + île (tuiles) | idem |
| **Couverture** | 5 845 polygones, **23/24 communes** (Saint-Philippe = 0) | **427 419 parcelles (99,0 %)** | idem |
| **Info unique** | le **document opposable continu** : couvre aussi l'espace **non parcellaire** (voirie, ravines, domaine public) | zone précise lisible parcelle par parcelle + **code exact au clic** | **lecture d'ensemble** sans clic |

Preuve du fill partagé (MapView.tsx:218) : `zonageColor = layers.zonage_parcelle || layers.zonage_colorise`
→ les deux pilotent le **même** `ZONE_FAM_COLOR`/`ZONE_FAM_OPACITY` sur `parcels-fill`. Seul
`zonage_parcelle` allume l'étiquette (`parcels-zone-label`, l.580) et le popup au clic (l.426).

### Verdict de mesure
- **`zonage_parcelle` et `zonage_colorise` = MÊME donnée, MÊME remplissage.** La seule différence
  est l'étiquette (zoom) + le popup (clic). → **ce sont ces DEUX couches parcellaires qui sont
  quasi-redondantes**, pas le trio entier.
- **`zonage` (GPU brut) est réellement distinct** : polygones continus du document opposable,
  palette et couverture différentes.

### Le cas signalé par Vic (couleurs là où le calibrage n'a rien)
C'est l'effet **document continu vs parcelles discrètes** : le GPU brut colore aussi la voirie,
les ravines, le domaine public **non cadastré**, et les communes où la jointure parcellaire est
absente. **Confirmé en base** : Saint-Philippe a **0** polygone GPU **et** seulement 9/4 162
parcelles avec `zone_fam` → la commune n'a pas de PLU numérisé (RNU / carte communale). Ailleurs,
la différence est l'espace non-parcellaire. **C'est une information de couverture — à ÉCRIRE dans
le libellé, pas à cacher** (conforme à la consigne).

### Proposition (à valider AVANT tout code)

**Option A — fusion (recommandée).** Fusionner « Colorisation par type de zonage » **dans**
« Zonage PLU (par parcelle) » : une seule couche parcellaire qui colore d'emblée toutes les
parcelles (lecture d'ensemble) **et** révèle le code au zoom/clic. On retire la case redondante.
Restent **2** couches, nettement distinctes et renommées :
- **« Zonage par parcelle (calibré LABUSE) »**
- **« Zonage officiel (document GPU brut) »**

**Option B — garder 3, renommer** (si Vic tient à séparer le geste « colorer tout » du geste
« détail ») :
- `zonage_colorise` → **« Familles de zones (aperçu, sans clic) »**
- `zonage_parcelle` → **« Zone précise à la parcelle (code au clic) »**
- `zonage` → **« Zonage officiel — document GPU brut »**

Réécriture des 3 « i » (pour l'une ou l'autre option) :
- *officielle* : « Les zones du PLU telles que déposées par la commune sur le Géoportail de
  l'urbanisme (flux GPU). Aplats **bruts** du document opposable, contours d'origine — **non
  rattachés au cadastre** : ils couvrent aussi l'espace non parcellaire (voirie, ravines, domaine
  public), d'où des couleurs là où les couches « par parcelle » n'en montrent pas. Couverture :
  23 des 24 communes — **Saint-Philippe n'a pas de PLU numérisé au GPU**. »
- *par parcelle* : « Chaque parcelle prend la couleur de sa famille de zone (U urbaine, AU à
  urbaniser, A agricole, N naturelle), calée sur le cadastre par LABUSE. Au zoom ou au clic, le
  code exact (U1a, 1AUc…) s'affiche. Couverture : 99 % des parcelles ; absente là où la commune
  n'a pas de PLU (Saint-Philippe). »
- *colorisation* (si conservée) : « La même colorisation par famille appliquée d'emblée à toutes
  les parcelles — lecture d'ensemble de la constructibilité, sans cliquer. Même donnée que « par
  parcelle », en vue rapide. »

**→ Aucune de ces trois n'est modifiée dans le code tant que Vic n'a pas tranché A vs B.**

---

## 2. Couverture couche × commune

Panel = 12 couches. Les couches **dérivées des parcelles** (Parcelles, Limites, les 2 zonages
parcellaires, Renouvellement) couvrent mécaniquement les 24 communes. Celles issues de
`spatial_layers` sont ventilées en base :

| Couche (panneau) | Source | Volumétrie | Couverture communes | Trou |
|---|---|---|---|---|
| Parcelles | `parcels` (DGFiP + avis LABUSE) | 431 663 | 24/24 | — |
| Limites parcelles | `parcels` (DGFiP) | 431 663 | 24/24 | — |
| Colorisation / Zonage par parcelle | `parcel_zone_plu.zone_fam` | 427 419 (99,0 %) | 24/24 sauf **Saint-Philippe (9/4 162)** ; St-Leu 91 manquants | voir §1 |
| Zonage PLU (zones officielles) | `plu_gpu_zone` (GPU) | 5 845 | **23/24** | **Saint-Philippe = 0** |
| PPR multirisque | `ppr` (DEAL / Géorisques) | 164 | **24/24** | — |
| Équipements | `amenite` (OSM) | 14 933 | **24/24** | — |
| Limites communes | `communes974.geojson` (IGN) | 24 | 24/24 | — |
| Parc national | `parc_national` | 72 = **3 polygones île répliqués 24×** | île entière | tag `commune` = **artefact** (voir ci-dessous) |
| ANRU (NPNRU) | `anru` | 8 | **6/24** (Le Port, St-André, St-Benoît, St-Denis, St-Louis, St-Pierre) | **ciblé (légitime)** |
| 50 pas géométriques | `cinquante_pas` (commune NULL) | 163 | **littoral** | **Hauts (légitime)** |
| Renouvellement | `parcel_renouvellement` (LABUSE) | 68 445 | île | OFF par défaut |

### Trous LÉGITIMES (étiquetés dans les « i », cf. §6)
- **ANRU** : 6 communes — dispositif d'État ciblé (la couche vide ailleurs est déjà signalée par toast).
- **50 pas** : bande littorale — absente des communes sans littoral (les Hauts).
- **Parc national** : Hauts et centre de l'île — absent du littoral urbanisé.

### Constats à RAPPORTER (non expliqués / à décider)
1. **Saint-Philippe — aucun zonage PLU** : 0 polygone GPU **et** 9/4 162 parcelles calibrées. La
   commune n'a pas de PLU numérisé au Géoportail (RNU / carte communale probable). Les 3 couches
   « zonage » y sont donc vides. → à dire dans le « i » officielle (fait, §6) ; confirmer que
   c'est bien un RNU et non un défaut d'ingestion.
2. **Parc national — champ `commune` non signifiant** : les 3 zones (Cœur, Aire ouverte à
   l'Adhésion, Aire d'Adhésion) sont **répliquées à l'identique pour les 24 communes**, chaque
   ligne portant la géométrie **île entière** (1 932 km² identiques pour Cilaos, Le Port,
   Saint-Denis). Le rendu carte est correct (on affiche le parc entier), mais toute stat « parc
   par commune » est fausse. Constat d'hygiène, sans impact visuel.
3. **Hygiène hors-panneau** : `bruit_route` (pas dans le panneau Couches) porte des communes en
   MAJUSCULES sans accents avec un doublon `SAINT JOSEPH` / `SAINT-JOSEPH` → 25 libellés au lieu
   de 24. Signalé pour info, non corrigé (hors périmètre).

---

## 3. STOP (si élargir) — contenu réel des Équipements

Source : **OpenStreetMap via Overpass** (`src/labuse/ingestion/amenites.py`). 7 sous-types,
tous présents sur les 24 communes. **Volumétrie LIVE (base locale, 14 933 POI)** :

| Sous-type (écran) | Tags OSM requêtés | n | dont nommés |
|---|---|---|---|
| Transport (`tcsp`) | `highway=bus_stop` | 6 464 | 6 021 |
| Sport | `leisure ∈ {sports_centre, stadium, pitch, swimming_pool}` | 5 639 | 543 |
| École (`ecole`) | `amenity ∈ {school, kindergarten, college}` | 960 | 878 |
| Commerce | `shop ∈ {supermarket, convenience, bakery, mall}` | 946 | 839 |
| Santé (`sante`) | `amenity ∈ {pharmacy, hospital, clinic, doctors}` | 689 | 578 |
| Mairie | `amenity=townhall` | 151 | 151 |
| Police / gendarmerie | `amenity=police` | 84 | 80 |

### Réponses directes aux questions de Vic
- **« Commerce = quoi ? »** → **uniquement** supermarché, supérette (`convenience`), boulangerie,
  centre commercial (`mall`). **PAS toutes les boutiques** (ni habillement, ni électronique, etc.).
- **Écoles ET hôpitaux présents ?** → **Oui** — écoles (`school|kindergarten|college`) et santé
  (dont `hospital`). Pas de distinction collège/lycée : OSM les tague tous `amenity=school`.
- Le mapping OSM→sous-type est **1:1, aucun tag requêté n'est jeté**.

### Manques évidents (décision de PÉRIMÈTRE DONNÉES — STOP avant d'élargir la requête OSM)
Non requêtés aujourd'hui : **marché** (`amenity=marketplace`), **gare** (`railway=station`),
**pompiers** (`amenity=fire_station`), **bibliothèque/musée** (`amenity=library|museum`),
**crèche** (`amenity=childcare`), **lieux de culte**, **dentiste**. Élargir la requête = plus de
POI ingérés + éventuel impact sur les distances de la fiche → **je ne touche pas sans arbitrage.**

---

## 4. FIX — bulles équipements cliquables ✅

**Cause réelle du « ne réagit pas au clic »** : un handler `ov-equip` existait déjà, MAIS le clic
tombait **aussi** dans le handler `parcels-fill`/clic universel → il **ouvrait la fiche de la
parcelle sous l'icône**, éclipsant le geste sur l'équipement.

**Fix (MapView.tsx)** :
- Le handler `ov-equip` appelle `ev.preventDefault()` ; `parcels-fill` et le clic universel
  testent `defaultPrevented` et se retirent → **la bulle équipement est le seul effet du clic**.
- Bulle enrichie : **nom + catégorie CLIENT** (« Santé », « Commerce » via `EQUIP_META`, plus la
  clé technique) **+ distance à la parcelle sélectionnée** si une est choisie et à l'écran
  (`haversine` + `roughCentroid` de `lib/geo.ts`, réutilisés).

**Capture** (`reports/m55-a-couches/captures/item4_equip_popup_zoom.png`) — bulle observée :
`Pharmacie Des Isles · Santé · à ~546 m de la parcelle sélectionnée`.

---

## 5. FIX — flèche de la section Couches ✅

Avant : `⌄` (bas) replié, `rotate-180` (haut) déplié → logique inversée.
**Après** : **replié → chevron GAUCHE** (`⌄` pivoté 90°), **déplié → chevron BAS** (`⌄` au repos).
Captures `item5_panel_replie.png` (gauche) et `item5_panel_deplie.png` (bas).

**Cohérence (vérification demandée)** :
- **Aligné** : le chevron « Verdict · Classement servi » de la légende (`Legend.tsx`) — même
  idiome `⌄`, même en-tête de section — passe au même patron gauche/bas.
- **À arbitrer** : `FiltreLabuse` (sous-tiroirs) utilise des triangles `▸`/`▾` = **droite/bas**
  (accordéon conventionnel) ; `ResultsSection` (« pourquoi ? ») utilise `▾`/`▴` = bas/haut
  (expandeur inline classique). Ce sont des idiomes différents des en-têtes de section. Je ne les
  ai **pas** basculés en « gauche » unilatéralement : « fermé → gauche » est inhabituel pour un
  accordéon de filtres et c'est un choix d'UX à confirmer. **Dis-moi si tu veux les uniformiser.**

---

## 6. FIX — audit des « i » (avant / après)

Fichier réel = `frontend/src/lib/layers.ts` (`LAYER_INFO`), pas `strings.ts`. Chaque « i »
réécrit dit désormais **(a) ce que montre la couche, (b) sa source, (c) sa couverture si
partielle**. Les **3 « i » du zonage** sont **laissés en l'état** (traités en §1, attente Vic).

| Couche | Avant (extrait) | Après (extrait) |
|---|---|---|
| Parcelles | « Les parcelles cadastrales, colorées selon l'avis… couche de travail principale. » | + « **431 663** … source **DGFiP** … présente sur les **24 communes**. » |
| PPR | « …inscrites dans un PPR — utile pour écarter tôt… » | + « Source : **la DEAL (via Géorisques)**. Couverture : **les 24 communes**. » |
| Parc national | « …urbanisation très restreinte voire interdite. » | + « source **établissement public du Parc** … couvre surtout **les Hauts et le centre** — normalement **absent du littoral urbanisé**. » |
| Limites | « …contour de toutes les parcelles… » | + « source **DGFiP** … **Toute l'île**. » |
| Communes | « frontières officielles entre les communes… » | + « **24** communes … source **IGN / geo.api.gouv**. » |
| ANRU | « quartiers inscrits dans un programme… soutenus par l'État. » | + « **NPNRU**, source **ANRU** … présent sur **6 communes seulement** (nommées) ; ailleurs la couche est vide et LABUSE le signale. » |
| 50 pas | « bande littorale… régime propre à l'outre-mer… » | + « source **cadastre** … ne longe que le rivage — normalement **absente des communes sans littoral**. » |
| Équipements | « …(mairie, écoles, santé, commerces, transport, sport)… distance… » | + « relevés dans **OpenStreetMap** (24 communes) … **commerces (supermarché, supérette, boulangerie, centre commercial — pas toutes les boutiques)** … » |
| Renouvellement | « …potentiel de renouvellement urbain… rien ne dit qu'elles se vendront. » | + « Segment calculé par LABUSE (**68 445 parcelles**)… » |

---

## Périmètre & garde-fous respectés
- Panneau Couches (front) + **lecture** des sources. **Aucun changement de données.**
- Fichiers modifiés (4) : `MapView.tsx`, `LeftPanel.tsx`, `Legend.tsx`, `layers.ts`.
- **STOP en attente Vic** : §1 (A vs B), §3 (élargir OSM ?), §5 (uniformiser triangles ?),
  §2 constats 1 (RNU St-Philippe) & 2 (artefact Parc).
- CC ne merge jamais.
