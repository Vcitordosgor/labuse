# CONTENANCE-1 — la surface du terrain = la contenance cadastrale

Rédigé le 09/10/2026. Branche `fix/contenance-1` (worktree `~/Desktop/labuse-contenance`), depuis
`origin/main` `a883cabc`. Ports 8730/5930. **3 commits** (un par lot A/B/C) **non poussés, non mergés.**

## Décision

LABUSE affichait et calculait partout l'aire du **dessin du plan cadastral**
(`parcels.surface_m2 = ST_Area`). Le client connaît la **contenance cadastrale** — le chiffre de
son acte. Décision de Vic : **la contenance devient la surface du terrain, à l'écran ET dans les
calculs** ; le dessin ne sert plus qu'aux formes.

Témoins du mandat (A8 de CORRECTIFS-1), reproduits au m² près après backfill :

| Parcelle | Dessin (ST_Area) | Contenance (acte) | Écart |
|---|---|---|---|
| CW 0658 Saint-Paul | 27 156 m² | **25 633 m²** | +5,9 % |
| AS 0772 Saint-Paul | 664 m² | **694 m²** | −4,3 % |

---

## Lot A — stocker la contenance

| Geste | Fichier |
|---|---|
| Colonne `parcels.contenance_m2` (integer, nullable) | `src/labuse/models.py` (classe `Parcel`) |
| `ensure_parcel_contenance` (ADD COLUMN gardé par `information_schema`, boot SANS verrou) + registre | `src/labuse/models.py` (`_ensure_schema_steps`) |
| `parse_etalab` : contenance normalisée en entier m² (`_contenance_int`) | `src/labuse/ingestion/cadastre_bulk.py` |
| `ingest_parcels` écrit `contenance_m2` (INSERT + UPSERT) — **aucune géométrie ni `surface_m2` touchée** | `src/labuse/ingestion/cadastre_ingest.py` |
| CLI `backfill-contenance` (re-télécharge Etalab par commune en base, UPDATE par IDU, idempotent) | `src/labuse/cli.py` |

Le champ `contenance` est **déjà** présent dans la source Etalab déjà chargée (`parse_etalab`) : Lot A
est de la plomberie, aucune nouvelle source.

### A2 — couverture & distribution (base `labuse`, backfill des 24 communes exécuté)

- **Couverture : 430 283 / 431 663 = 99,68 %** (1 380 parcelles sans contenance à la source → repli
  sur le dessin, mention « mesurée sur le plan »).
- **Écart absolu dessin↔contenance** (sur 430 283) : **médiane 1,62 %**, P90 7,73 %, P99 39,72 %.
  **30 327** parcelles > 10 % ; 274 305 > 1 %.
- Sens : dessin < contenance 233 790 · dessin > contenance 196 493 · égal 37 219. Proche de l'équilibre.
- **20 plus gros écarts** : quelques polygones de dessin manifestement erronés (digitalisation) —
  ex. `97415000AO0009` dessin 660 230 m² vs contenance 4 937 m² (+13 273 %), `97419000BH0010`
  966 633 vs 9 657. Sur ces cas extrêmes, **la contenance est la valeur de confiance** ; le passage à
  la contenance corrige silencieusement des aberrations d'affichage (table complète : §annexe SQL).

A3 : la ré-ingestion remplit la colonne — couvert par `tests/test_contenance1_lot_a.py`
(`test_reingestion_actualise_la_contenance`).

---

## Lot B — affichage : une seule fonction `surface_terrain`

**Back** `src/labuse/surface.py` : `surface_terrain(dessin, contenance) → (valeur, source, dessin,
contenance)` (contenance si présente, sinon dessin avec `source='plan'`), `champs_terrain(...)`
(les 3 champs servis, sans toucher `surface_m2`), `SURFACE_TERRAIN_SQL = COALESCE(contenance_m2,
surface_m2)` (filtres/tris).
**Front** `frontend/src/lib/surface.ts` : `surfaceTerrain / surfaceDessin / surfaceSource /
montrerDessin`.

Tous les payloads client portent désormais `surface_terrain_m2` + `surface_source` (+ `surface_dessin_m2`
/ `contenance_m2`), `surface_m2` restant le dessin pour compat :

- **Back** : fiche (`app.py:_q_v2_fiche`), liste (`_q_v2_list`), recherche, geojson carte, patrimoine
  (`modules.py`, source de `OwnerParcelles`), parcours & CarteDecision (`projets.py`), partenaire API
  (`partners.py`), Copilote (`assistant.py`), Flash (`flash/data.py` + `templates/rapport.html.j2`),
  Dossier (`exports/robinet_fiche.py` + `oracle_dossier.py` + `builder.py`, blocs), KMZ (`app.py`).
- **Front** lisent `surfaceTerrain(p)` : `Fiche.tsx`, `ResultsSection.tsx` (affichage **et tri**),
  `ParcelInput.tsx`, `OwnerParcelles.tsx`, `ParcoursTinder.tsx`, **filtre de surface** (`lib/filters.ts`),
  **filtre + survol carte** (`MapView.tsx`).
- **Filtres/tris SQL** = surface de terrain (`COALESCE`) : filtre `surface_min/max` + tris
  `surface`/`surface_asc` (niveau requête et page), `app.py`.

**B3** — Fiche, sous la Surface : ligne discrète « Dessin du plan : 27 156 m² » + infobulle
(« Surface mesurée sur le plan cadastral… celle de l'acte »), **masquée si l'écart < 1 %**.
**B4** — repli sans contenance : la surface affiche le dessin avec la mention « mesurée sur le plan ».
Flash : idem (contenance + ligne « Dessin du plan » ; sinon « mesurée sur le plan »).

Captures avant/après : `captures/contenance1/` (dry-run textuel ; l'UI se vérifie en recette).

---

## Lot C — calculs

### C1 — ratios/proportions sur la CONTENANCE

Un seul levier porte l'essentiel : `faisabilite/db.py` → `ParcelContext.surface_m2 =
COALESCE(contenance_m2, ST_Area(geom_2975))`. En aval, **en contenance automatiquement** :

| Calcul | Fichier:ligne |
|---|---|
| Emprise au sol = surface × CES | `faisabilite/engine.py:553` (via `surface_m2` de la ctx) |
| Pleine terre = surface × % | `faisabilite/engine.py:577-578` |
| Densité = (surface/ha) × logts/ha | `faisabilite/engine.py:679-681` |
| SDP = footprint × niveaux (footprint = emprise ré-échelonnée) | `faisabilite/engine.py:635,653` |
| Seuil `terrain_exigu` (emprise < seuil) | `faisabilite/db.py` (emprise ré-échelonnée, cf. C3) |
| Charge foncière / m² + emprise plafond (bilan) | `faisabilite/bilan.py:641,680` (via `ctx.surface_m2`) |
| Emprise max & pleine terre affichées (fiche) | `api/traducteur.py:57,68` (via `ctx.surface_m2`) |
| « Valeur au prix du secteur » (contenance × médiane) | `api/app.py` (`_q_v2_fiche`, `_st_head.valeur`) |
| Valeur nue du portefeuille | `api/modules.py` (patrimoine, `surface_terrain`) |
| Prix saisi au m² de terrain | `api/scoreur.py:99` (`COALESCE` dans `_sel`) |
| Gabarit — plafond d'emprise (CES × surface) | `gabarit/builder.py:178` (`COALESCE`) |
| Assemblage — seuil de taille + surfaces cumulées | `assemblage.py:54-61` (`COALESCE`) |

### C2 — formes : DESSIN conservé

Reculs, zone d'implantation (géométrie), gabarit 3D, largeur/profondeur, intersections de couches
(PPR, ER, EBC, greve) : calculés sur `geom_2975` (le dessin). Inchangés.

### C3 — règle de passage (ré-échelle)

`faisabilite/db.py` : facteur `ParcelContext.terrain_sur_dessin = contenance/dessin` (1.0 en repli).
**Toute aire tirée du dessin et utilisée dans un ratio ou affichée est multipliée par ce facteur** :
zone d'implantation (`emprise_brute`), déductions ER/EBC/greve certaine & totale, portion U/AU, inset
reculs, détail par ER. Conséquence : l'emprise / la zone d'implantation **ne dépassent jamais la
contenance** et les proportions tiennent. Les **formes** (GeoJSON, reculs) restent le dessin.

### C4 — laissés sur le DESSIN (délibéré)

| Calcul | Fichier:ligne | Pourquoi |
|---|---|---|
| Couverture de sol COSIA (imper/vég/sol nu %) | `bati.py:212-214` | aires **mesurées** sur la géométrie ; la somme doit rester ≈ dessin (sinon ≠ 100 %) |
| Densité routière (étage 0) | `cascade/layers/etage0_ext.py:139` | métrique d'exclusion sur géométrie mesurée (voirie ∩ parcelle) |
| Parts de zonage U/AU/A/N d'une commune | `registre/moteurs/zonage.py:44` | agrégat **territoire** (somme de dessins), pas une surface de terrain d'une parcelle |
| « Diviser la parcelle » | servi depuis `division_or_candidates` | pré-calculé par run, pas un ratio de surface en direct (`_division_fiche` est du code mort) |

---

## Lot D — preuve

### D1 — tests

- `tests/test_contenance1_lot_a.py` (4) — parse entier/repli ; ingest écrit contenance **sans toucher
  le dessin** ; ré-ingestion actualise ; absence → NULL.
- `tests/test_contenance1_lot_b.py` (7) — `surface_terrain` contenance/repli ; `champs_terrain`
  **n'écrase pas** `surface_m2` ; `SURFACE_TERRAIN_SQL ≡` la fonction en base.
- `tests/test_contenance1_lot_c.py` (20) — facteur `terrain_sur_dessin` ; **propriété C3** (toute aire
  ≤ dessin, ré-échelonnée, ≤ contenance) ; base APP : surface servie = contenance (C1) et
  `zone_implantation_m2` / `emprise_constructible_m2` / `emprise_sol_max_m2` **≤ contenance** (C3) sur
  CW0658/AX0047/CP0427/AM0664.
- `frontend/src/lib/surface.test.ts` (9) — helper + seuil B3 (1 %) + repli B4.
- **Monotonicité inchangée sur les 30 témoins** : `tests/test_scoring6_*` (golden + monotonicité
  SDP↑→score≥) **92 verts** — le code CONTENANCE-1 n'altère **aucune donnée servie** (residuel/score)
  tant qu'un run n'a pas tourné ; les scores des 30 témoins sont donc identiques (cf. D3).

### D2 — dry-run faisabilité AVANT (dessin) / APRÈS (contenance), base `labuse`, sans run

`captures/contenance1/dryrun.py` (lecture seule ; BASE vs WORKTREE sur la même base).

| Parcelle | Surface A→P | SDP A→P | Cause |
|---|---|---|---|
| CW 0658 | 27 156 → **25 633** | 40 913 → **38 619** (×0,944) | — |
| AX 0047 | 2 138 → **2 142** | 1 213 → **1 215** | — |
| CP 0427 | 605 → **610** | 413 → **417** | — |
| CX 0664 | 179 → **168** | 15 → **14** | — |
| AM 0664 | 4 179 → **4 095** | 1 151 → **1 128** | — |
| AI 0166 | 7 448 → **7 580** | 3 352 → **3 411** | — |
| IR 0091 | 5 314 → **5 306** | 5 755 → **5 746** | — |
| BW 2390 | 2 880 → **2 768** | 4 779 → **4 593** | — |
| AY 0786 | 4 877 → **4 936** | 0 → 0 | terrain_exigu (inchangé) |
| AB 0010 (Les Avirons) | 8 024 → **7 600** | 0 → 0 | zone_transition (inchangé) |
| AS 0772 | 664 / 694 | — / — | pas de faisabilité (zone, inchangé) |

Lecture : la **SDP suit proportionnellement la surface** (facteur contenance/dessin) ; les causes de
non-constructibilité sont **stables** ; la SDP dépasse la contenance (plancher = aires empilées sur
plusieurs niveaux, normal), mais **l'emprise/zone d'implantation, elles, restent ≤ contenance** (D1).

### D3 — estimation du run & ordre de merge

- **Parcelles touchées** : le run de scoring recalcule **toute l'île** (431 663). Matériellement, la
  bande/SDP bougent là où contenance ≠ dessin : **274 305** parcelles > 1 %, **75 860** > 5 %, 30 327
  > 10 % — soit un déplacement **du même ordre que, voire supérieur à, PPR-PARTIEL-A** (≈ 3 888
  parcelles PPR partielles). La majorité des mouvements sont petits (médiane 1,62 %) et bornés au
  centime par la ré-échelle.
- **Durée** : c'est le run île standard (faisabilité → `parcel_residuel` → `score_labuse`), pas un
  nouveau pipeline — même coût qu'un run q_v16 nocturne (cf. QV16-VERIF-1 / SCORING-9 : échelle de la
  dizaine de minutes pour le résiduel + ~2 min pour le Score).
- **Un seul run suffit pour les deux** : CONTENANCE-1 (`faisabilite/db.py`, surface d'entrée) et
  PPR-PARTIEL-A (`gabarit/builder.py`, déduction pm1 PPR) modifient tous deux l'**assiette** calculée
  par la faisabilité → leurs effets se composent dans **le même `parcel_residuel`**. Les recalculer
  séparément serait un gaspillage.
- **Ordre de merge recommandé : CONTENANCE-1 d'abord** (il redéfinit la surface d'entrée et le facteur
  C3, fondation de toute aire d'assiette), **puis PPR-PARTIEL-A** (la déduction PPR s'applique ensuite
  sur une assiette déjà ré-échelonnée). Overlap à surveiller : la zone d'implantation du gabarit
  (`gabarit/builder.py`) — CONTENANCE-1 y lit la contenance pour le **plafond** (pas la forme),
  PPR-PARTIEL-A y retire pm1 ; les deux coexistent (plafond vs géométrie). Après merge des deux,
  **un seul run de nuit**, après le test de Stéphanie.

---

## État tests (surfaces touchées)

- Python : `test_contenance1_lot_a/b/c` 31 verts ; faisabilité/bilan/assemblage/scoreur/gabarit **268
  verts** ; scoring/témoins/monotonicité **92 verts** ; fiche/exports/flash/patrimoine/parcours/kmz
  **498 verts**. Échecs **PRÉ-EXISTANTS** (vérifiés identiques sur `origin/main`) : `test_faisabilite`
  U1pru/densité (calibrage zone absent en local), `test_projets_fix_vivier` (×3), `test_exports2_lot2`,
  `test_front_reliquats` ; `test_cloisonnement_1::copilote` = **environnement** (clé IA absente du
  worktree, vert avec `.env`).
- Front : **tsc 0**, **vitest 256 verts** (247 existants + 9 `surface.test.ts`).

## Hors mandat / gestes restants

Le run lui-même (nuit, après Stéphanie) · la bascule · le déploiement · le backfill contenance en
prod (la colonne s'ajoute seule au boot via `ensure_parcel_contenance` ; le remplissage se fait par
`labuse backfill-contenance` ou à la prochaine ré-ingestion cadastre).
