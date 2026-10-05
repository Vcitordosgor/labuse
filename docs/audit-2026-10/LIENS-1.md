# LIENS-1 — démarrage sans verrou + en-tête de fiche (Errial, Google Earth)

Branche `fix/liens-1` depuis `origin/main` (`27624c22`). Worktree `~/Desktop/labuse-liens`, ports 8825 / 6025.
Un commit par lot ; aucun run ; aucune base touchée en écriture hors `labuse_test`.

---

## Lot 0 — démarrage de l'API sans verrou (prioritaire, avant déploiement)

### Le piège (vécu le 05/10)
Au démarrage, une API a exécuté `ALTER TABLE parcel_residuel_runs ADD COLUMN IF NOT EXISTS
assiette_source text`. **Même quand la colonne existe déjà**, cet `ALTER` prend un verrou
**ACCESS EXCLUSIVE** sur la table le temps de constater qu'il n'a rien à faire. Il s'est mis en
file derrière une transaction ouverte ; dès lors toutes les nouvelles lectures se sont empilées
derrière *lui* (équité de la file des verrous Postgres) → **toutes les lectures du résiduel figées
~8 min**. Même piège que `parcels.origine` (corrigé par SCORING-8) et `ensure_geom_2975`
(commit `70278401`).

### Recette appliquée (la même que `70278401`)
Chaque DDL de boot est précédé d'un **test du catalogue** (`to_regclass` / `information_schema` —
lectures pures, **aucun verrou de table**) et n'est émis **que s'il manque vraiment**. Sur le chemin
nominal (schéma déjà posé) **aucun DDL n'est exécuté** → aucun ACCESS EXCLUSIVE → le boot ne se met
jamais en file.

### 1. Inventaire des DDL exécutés au démarrage
Le boot passe par `_lifespan` (`api/app.py:106`) → **advisory lock `0x1ABE5C`** (sérialise la
réparation de schéma entre workers) → `models.ensure_schema` → `_ensure_schema_steps`
(`models.py:1112`) puis les `ensure_tables()` des routeurs.

**DDL touchant les tables CHAUDES (grosses, lues/écrites en continu — les seules où une
transaction tierce peut tenir le verrou et provoquer le gel) :**

| Fonction | Fichier:ligne | Table(s) | DDL | État |
|---|---|---|---|---|
| `ensure_geom_2975` (ALTER/TRIGGER) | `models.py:1409-1433` | parcels, spatial_layers | ADD COLUMN geom_2975, CREATE/DROP TRIGGER | **GARDÉ** `schema_pose` (info_schema + pg_trigger) |
| `ensure_parcel_origine` | `models.py:2197-2204` | parcels | ADD COLUMN origine | **GARDÉ** `_col_presente` |
| `ensure_parcel_eval_status_dropped` | `models.py:1088-1095` | parcel_evaluations | DROP COLUMN legacy | **GARDÉ** `_col_presente` |
| `ensure_residuel_cache` (ALTER parcel_residuel) | `models.py:1928-1935` | parcel_residuel | ADD COLUMN capacite_estimee/cause | **GARDÉ de fait** : court-circuit `relkind='v'` (base migrée = VUE, l'ALTER n'est jamais atteint) |
| **`ensure_runs_schema`** | **`faisabilite/residuel_runs.py:45-58`** | **parcel_residuel_runs** | **3× ADD COLUMN + CREATE INDEX** | **🔴 NON GARDÉ → corrigé par ce lot** |

**DDL sur tables FROIDES/petites** (admin, CRM, pige, dashboard, veille, signalements,
data_sources, watch_zones, documents_generes, etc. — `ensure_tables()` des routeurs,
`models.py` 1240-2107) : ce sont des `CREATE TABLE/INDEX IF NOT EXISTS` et `ADD COLUMN IF NOT
EXISTS` **non gardés**, mais sur des tables qu'**aucune transaction longue ne tient** → elles ne
peuvent pas provoquer le gel des lectures du résiduel décrit par l'incident. **Non modifiées par ce
lot** (périmètre strict, risque de régression de DDL multi-modules > bénéfice) ; listées ici comme
dette à traiter en passe dédiée si l'on veut le « zéro DDL au boot » absolu.

**Note `ensure_geom_2975`** : son bloc `CREATE INDEX IF NOT EXISTS` + `ANALYZE`
(`models.py:1468-1495`) tourne à **chaque** boot (non gardé), mais ne prend que des verrous
`SHARE`/`ShareUpdateExclusive` qui **ne conflictent pas avec un lecteur** (ACCESS SHARE) → pas de
gel des lectures ; laissé tel quel.

### 2. Correctif
`faisabilite/residuel_runs.py` — `ensure_runs_schema` réécrit avec deux aides locales
`_regclass_present` / `_colonne_presente` (catalogue, sans verrou) ; chaque `CREATE TABLE`,
`ADD COLUMN`, `CREATE INDEX`, `CREATE UNIQUE INDEX` n'est émis que si l'objet manque. Comportement
fonctionnel **strictement identique** (mêmes objets, même ordre) ; seule la **condition d'émission**
change. `migrate_to_runs` (qui réutilise `ensure_runs_schema`) et le court-circuit VUE restent
inchangés.

### 3. Test (bloque toute régression) — `tests/test_boot_sans_verrou.py`
Deux transactions tiennent un **ACCESS SHARE** sur `parcel_residuel_runs` ET `parcels` (la situation
exacte qui met un ALTER en file). Schéma déjà posé → `ensure_runs_schema` **n'émet aucun DDL** →
démarrage immédiat (`< 10 s`, mesuré ~0 s). Un `SET LOCAL lock_timeout = '4s'` transforme une
régression (DDL non gardé réintroduit) en **échec rapide** : l'ALTER buterait sur le verrou tenu et
lèverait, au lieu de geler le test (et la prod) 8 min.

**Preuve que le test mord** : un `ALTER … ADD COLUMN IF NOT EXISTS` *no-op* lancé sous le verrou tenu
lève bien `OperationalError` au bout de 2 s (vérifié hors suite). La version gardée, elle, passe sans
attendre.

**Résultat** : `tests/test_boot_sans_verrou.py` + `tests/test_residuel_runs.py` → **6 passed** (4,8 s).

> Commit autonome : mergeable **sans le lot 1**.

---

## Lot 1 — en-tête de la fiche parcelle (maquette validée par Vic)

### Avant / après (captures `captures/LIENS-1/`)
| | Avant | Après |
|---|---|---|
| **large** (pane 371 px) | `entete-large_avant.png` | `entete-large_apres.png` |
| **étroite** (pane 291 px) | `entete-etroite_avant.png` | `entete-etroite_apres.png` |

**Avant** : ligne « PARCELLE · COMMUNE » en haut à gauche ; à droite un bloc de 6 boutons carrés
(Cadastre · Pages Jaunes · Google Maps · cloche · loupe · croix). **Après** : plus de ligne
« PARCELLE · COMMUNE » (doublon avec l'adresse) ; UNE ligne de boutons pleine largeur en deux
groupes — à gauche les liens externes **Cadastre · Pages Jaunes · Google Maps · État des risques
(Errial) · Google Earth** ; à droite, séparées d'un trait vertical fin, les actions **cloche · loupe ·
croix** (+ « Voir la rue » si le serveur la sert). L'IDU en grand + copier, l'adresse + copier et le
secteur suivent, inchangés.

### Fichiers
- **`frontend/src/components/fiche/liensExternes.ts`** — deux fonctions pures testées :
  `errialUrl(adresse, commune)` et `googleEarthKmzUrl(idu)`.
- **`frontend/src/components/fiche/Fiche.tsx`** — en-tête restructuré (ligne `.head-actions` à deux
  groupes `.hbtns-ext` / `.hbtns-act` + `.hsep`) ; ligne « PARCELLE · COMMUNE » retirée ; IDU descendu
  sous la ligne ; chaque bouton enveloppé d'un `Tip` (infobulle au survol). Icônes Errial = triangle
  d'alerte, Google Earth = globe, monochrome (`currentColor`), sans style particulier — comme
  loupe/croix.
- **`frontend/src/styles/index.css`** — `.head-actions` / `.hbtns-act` / `.hsep` / `.ref-sous-actions`
  ; gaps serrés (`.hbtns gap:3px`, `.head-actions gap:4px`, `.hsep margin:0 2px`) pour tenir à la
  largeur minimale du panneau.
- **`src/labuse/api/app.py`** — endpoint **`GET /parcels/{idu}.kmz`** (KML zippé du contour servi).

### Infobulles (point 4)
Chaque bouton de la ligne porte son `Tip` au survol : « Cadastre », « Pages Jaunes », « Google
Maps », « État des risques (Errial) », « Ouvrir dans Google Earth », « Suivre cette parcelle »,
« Chercher dans la fiche », « Fermer » (+ « Voir la rue » si servie).

### Errial (point 5) — pré-remplissage par ADRESSE, PAS par parcelle
Le bundle de l'appli Errial (`errial.georisques.gouv.fr`, vérifié le 05/10) lit **uniquement**
`?adresse=` au montage (`mounted(){ this.adresseGeorisques = this.$route.query.adresse ; …
searchAdresse(...) }`, routeur en mode **hash**). **Il n'existe AUCUN paramètre d'URL de
pré-remplissage par parcelle/IDU/INSEE.** On pré-remplit donc par l'adresse exacte quand on l'a,
sinon par la commune seule (repli annoncé par `commune_seule`, comme Pages Jaunes). URL produite :
`https://errial.georisques.gouv.fr/#/?adresse=<adresse|commune>`.

### Google Earth (point 6) — KMZ du contour servi
`GET /parcels/{idu}.kmz` : `ST_AsKML(parcels.geom, 7)` (MÊME géométrie que la carte) emballé dans un
Placemark KML, zippé en `doc.kml` (convention Google Earth). `name` = IDU, `description` = commune +
surface servie (`surface_m2`). En-têtes `application/vnd.google-earth.kmz` +
`Content-Disposition: attachment; filename="{idu}.kmz"`. Lien front relatif (même origine, comme
`export.pdf`). IDU inconnu → 404.

### Dossier PDF (point 7) — rien à ajouter
Vérifié : le Dossier PDF **ne liste AUCUN lien externe de navigation** (ni Cadastre, ni Google Maps,
ni Pages Jaunes — ces liens vivent seulement dans l'en-tête de la fiche côté front ; recherche
exhaustive dans `exports/oracle_dossier.py`, `api/dossier.py`, `api/pre_dossier.py`,
`api/pdf_premium.py`). La condition « si le Dossier liste déjà des liens externes » n'est donc pas
remplie → **aucune modification du PDF** (et le KMZ n'y va jamais, conformément à la consigne).

### Street View — arbitrage de placement
Le bouton « Voir la rue » (conditionnel : seulement si `GOOGLE_MAPS_EMBED_KEY` est posée, absent en
local) ouvre un panneau **inline** = une action sur la fiche. Il est donc placé dans le groupe de
DROITE (actions), avant la cloche, et non parmi les liens externes (qui ouvrent tous un nouvel
onglet). Le groupe de gauche reste exactement la liste de la maquette.

### Tenue à l'étroit (point final)
Mesuré à la largeur minimale réelle du panneau (pane 291 px sur écran 390 px) : **8 boutons, tous à
leur taille pleine (26 px), 0 débordement, aucun retour à la ligne, aucun bouton coupé.** Le groupe
gauche peut rétrécir en premier (les actions ne rétrécissent jamais), les gaps sont serrés pour
garantir le tenue.

### Tests
- **`frontend/src/components/fiche/liensExternes.test.ts`** (+4 cas) : Errial avec/sans adresse/ni
  l'un ni l'autre, et KMZ relatif. → **vitest 239 verts** (52 fichiers).
- **`tests/test_parcel_kmz.py`** : insère une parcelle témoin, vérifie 200 + `vnd.google-earth.kmz` +
  `doc.kml` + `<Polygon>` + commune/surface dans la description + 404 sur IDU inconnu. → **1 passed**.
- **`tsc -b`** : 0 erreur.

### Harnais de captures
`frontend/qa/liens1_captures.mjs` (Playwright Node, `window.__labuse.select(idu)`, capture par clip
pour contourner le repeint continu de la carte) — rejouable `LABEL=avant|apres BASE=… node
qa/liens1_captures.mjs`.

---

## Clôture
- Lot 0 : commit `9de46f6b` (déjà poussable, mergeable seul).
- Lot 1 : commit séparé (ce lot).
- Aucun run, aucune écriture hors `labuse_test`, aucun backend tiers arrêté (captures servies par un
  vite local proxifié vers une API déjà en route, pas de nouveau boot d'API sur la base partagée).
- API (aucune bootée) & vite local : arrêtés en fin de session.
