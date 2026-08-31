# OUTILS-2 — les refontes lourdes · compte-rendu

Poste : `~/Desktop/labuse` · branche : `feat/outils-1` (porte OUTILS-1 commité `e9278b3e` + les 5 commits
`feat/radar-depot-2` + la maquette v3). **Ne pas merger** — commande au dernier point, isolée.

Écriture Postgres : **une seule**, autorisée — la colonne `sirene_etablissements.date_creation` (A3-bis),
migration propre (ALTER + backfill de la seule colonne). Aucun fichier de scoring touché → golden intact.

---

## 0. Preuve que la branche est bien servie (leçon d'OUTILS-1)

Avant toute recette : API redémarrée (uvicorn tué puis relancé), front **rebâti** (`npm run build`), servi
sous `/socle/`. Preuves que le code SERVI est celui de la branche :
- `/modules/plu-annuaire/communes` renvoie `n_revision`/`n_rnu` — champs ajoutés en OUTILS-1 (présents ⇒ pas un uvicorn stale).
- `/parcels/{idu}/geojson` (endpoint neuf O2-4) répond `Feature`+centroïde — code O2 servi.
- `/outils/etude-zone` renvoie `annee_creation` sur les concurrents (colonne A3-bis) — migration + code O2 servis.
- Captures Playwright sur le build servi (`docs/OUTILS-2/captures/`) : segment Permis, onglets Solaire, bloc Radar Communes rendus.

---

## 1. Les 7 refontes

### 1 · PERMIS — une interface, deux couleurs ✅
`frontend/src/components/outils/ModulePanel.tsx` (M03) + `map/MapView.tsx`.
- **Recherche intelligente** pleine largeur (un seul champ `AddressAutocomplete`) : adresse/commune (autocomplete
  → recadre la carte) OU n° de permis (Entrée sur une saisie sans suggestion, motif alphanumérique compact
  ex. `97441116A0361` → ouvre la fiche permis). Fini les deux champs éclatés.
- **Segment plein** `[● En cours N | ● Point mort N | Tous]`, pastille VERTE / ROUGE, compteurs live.
- **Période puis type**, empilés pleine largeur (segments pleins).
- **VERT = en cours, ROUGE = point mort** sur la liste (pastille) ET la carte (`point_mort` dans les
  properties → `circle-color` MapView). Capture `02-permis-pointmort.png` : **toute la carte en points rouges**.
- **Items sur deux lignes** : (pastille · type · date · logements/surface) / (commune · badge).
- **Badge « Sans DAACT · X ans »** — ancienneté CALCULÉE depuis la date d'autorisation (vu « Sans DAACT · 13 ans »).
- **Compteur honnête** : « 15 475 au point mort · 1 000 sur la carte · les 1 000 plus anciens chargés — zoomez pour affiner ».
- **Anciens points d'entrée** : la clé `promesses` résout M03 avec le segment « Point mort » pré-actif (aucun écran orphelin).
- **Check compteurs = SQL** : En cours (radar 24 m) API **5 613** = `SELECT count(*) … date >= max-24m` **5 613** (exact) ; Point mort 36 m = **15 475**.

### 2 · PROSPECTION SOLAIRE — Ensoleillement ✅
`ProspectionSolaire.tsx` + `api/modules.py` (tri).
- **Onglets « Ma parcelle » / « Top parcelles »** : le par-parcelle (fiche soleil) et le listing ne
  s'entremêlent plus.
- **Top parcelles** : tri **potentiel DESC PUIS toiture DESC**, colonne **TOITURE M² en 2ᵉ position**.
  Subtilité corrigée : le potentiel est trié à la **maille affichée** (`round(prod_spec_kwh_kwc)`) — à pleine
  précision (431 614 valeurs distinctes), deux voisins diffèrent d'un millième et la toiture ne départagerait
  jamais ; arrondi comme l'écran (554 paliers), la toiture classe vraiment. Vérifié live : à 1 598, toiture
  242/10/9/3 ; à 1 597, 5 494/2 218/2 205…
- **Fil d'Ariane « ‹ Prospection solaire »** des deux côtés (Piscines + Ensoleillement).
- Mentions maille/ombrage/millésime **inchangées**.

### 3 · COMMUNES — bloc Marché des annonces (Radar) ✅
`Communes.tsx` (composant `MarcheAnnoncesRadar` sous la table comparative). Endpoint `/radar/marche` réutilisé
(`pige/marche.py`, `SEUIL_N = 5` constante nommée backend — jamais en dur au front).
- **Aucune commune ≥ SEUIL_N** → bloc replié en une ligne « en constitution · N biens collectés · affichage
  par commune à partir de 5 biens » + lien Radar.
- **Sinon** → seules les communes ≥ 5 s'affichent (les autres absentes, jamais un zéro). État live actuel
  (déployé) : Saint-Denis 65, Sainte-Marie 12, La Possession 7, Saint-André 5, Saint-Paul 5 · « 106 collectés en tout ».

### 4 · REMONTER LE TEMPS — contour de la parcelle ✅
`TimeMachine.tsx` + endpoint neuf `GET /parcels/{idu}/geojson` (lecture seule).
- **Bug trouvé** : l'ancienne épingle filtrait la source `p` (GeoJSON commune), **chargée seulement si une
  commune est sélectionnée** (`enabled: commune != null`) → en mode île, source vide, parcelle invisible sur
  les deux volets (tout l'objet de l'outil raté).
- **Correctif** : source DÉDIÉE `cible` (une feature, chargée par IDU, indépendante de la commune) →
  contour **trait vert #4ADE80 + halo** (`cible-casing`) sur les **deux volets**, MÊME code couleur que la
  carte principale. **Étiquette IDU** (Marker HTML, traverse la poignée du comparateur). **Vue recentrée** sur
  le centroïde. Endpoint vérifié live (Feature Polygon + centroïde).

### 5 · PÉRIMÈTRES — résiduel / potentiel ✅
Source de libellés UNIQUE `frontend/src/lib/perimetres.ts` (`PERIM_RESIDUEL` = « résiduel, bâti conservé » ;
`PERIM_POTENTIEL` = « potentiel, terrain libéré » + formes courtes). Appliquée partout où les deux chiffres
apparaissent :
- **Fiche.tsx** : « SDP résiduelle estimée · bâti conservé » (potentiel de transformation) ; « SHAB vendable
  (terrain libéré) » (constat sourcé + fourchette Faisabilité).
- **Étudier un bien** : l'alerte de cohérence porte « résiduel, bâti conservé : 26 m² » vs « … terrain
  libéré » (reliée à Pièges & risques).
- **Comparaison** (`ComparePanel`) : « SDP max estimée · terrain libéré » / « SDP résiduelle · bâti conservé ».
- Le résiduel « 26 m² » vit dans `potentiel_transformation` de la fiche (référencé par Pièges/Faisabilité) —
  étiqueté à la source. Vocabulaire unique : un seul fichier à changer.

### 6 · A6 — contre-calculs ✅ (doc `docs/OUTILS-2/CONTRE-CALCULS.md`)
Les trois moteurs tombent **pile** ; les écarts de l'audit sont **côté audit**, pas côté moteur :
- **Étudier un bien** : −122 911 € reconstitué à l'euro (`527 296 × 0,79 − 490 875 − 48 600`). Arrondi UNE fois
  à la fin. L'écart avec le « manuel » −123 410 = **499 € = 5,54 m² × 90 €/m² VRD** → surface de terrain
  divergente dans le contre-calcul manuel, **pas un défaut**.
- **Scan patrimoine (CBO TERRITORIA)** : valorisation **587 477 506 €** (≈587,5 M€) et SDP résiduelle
  **919 248 m²** — somme indépendante des lignes identique à l'euro. Écart **nul**.
- **Faisabilité (DK1169)** : SDP gabarit réellement servie = **281 875 m²** = `208 796 × 0,45 × 3` ; l'audit
  (281 159) est **obsolète** (+716 m²). Aux extrêmes, les 3 plafonds (pleine terre 40 %, hauteur, densité) sont actifs et cohérents.

### 7 · A3-bis — date de création des concurrents ✅
Décision Vic : **on affiche la date**.
- **Migration propre** : `ALTER TABLE sirene_etablissements ADD COLUMN date_creation date` (dans le DDL/_ALTERS
  de l'ingestion) + **backfill de la seule colonne** depuis `StockEtablissement.dateCreationEtablissement`
  (DuckDB → temp table → UPDATE) : **158 515/158 515** peuplées. L'ingestion prod la remplit désormais
  nativement (SELECT/INSERT enrichis).
- **Backend** : `zone.concurrents_zone` renvoie `annee_creation` (+ `enseigne` préférée à la dénomination).
  Vérifié live : « depuis 1987 / 2000 / 2025 », enseigne « PLP PATISSERIE 2 ».
- **Front** : « enseigne · distance · **depuis AAAA** », chaque concurrent **cliquable vers sa parcelle**
  (`parcelAt(lon,lat)` → fiche).
- **EXPLOITATION §12** mis à jour : l'ingestion VPS porte la colonne, aucun backfill séparé en prod.

---

## 2. Tableau de provenance (complète OUTILS-1)

Run servi unique `q_v11_m137`. Aucun barème/seuil/compte métier en dur au front.

| Outil | Chiffre | Table · colonne | Moteur | Écart |
|---|---|---|---|---|
| **Permis** | En cours 5 613 | `sitadel_permits.date` (fenêtre 24 m) | `/modules/permis` count | 0 (= SQL 5 613) |
| **Permis** | Point mort 15 475 | `sitadel_permits` (`type=PC`, `raw->>'daact'` NULL, `date < now-36m`) | `/modules/promesses` count | 0 |
| **Permis** | « X ans » | année(now) − année(`date`) | front (calcul) | ancienneté = dormance |
| **Solaire** | potentiel / toiture | `parcel_solar.prod_spec_kwh_kwc` · `p_model_bati.emprise_bati_m2` | `/modules/prospection-solaire` (tri `round(potentiel), emprise`) | gel 11/07/2026 |
| **Communes** | biens/commune, seuil 5 | `pige_biens` (validés) · `SEUIL_N` | `pige/marche.py` `stats()` | seuil = constante backend |
| **Remonter le temps** | contour parcelle | `parcels.geom` (4326) | `/parcels/{idu}/geojson` | même trame que carte principale |
| **Périmètres** | résiduel / potentiel | `potentiel_transformation.sdp_residuelle_m2` · `shab_vendable_m2` | run servi | libellés = source unique |
| **Étude de zone** | concurrent « depuis AAAA » | `sirene_etablissements.date_creation` (A3-bis) | `zone.concurrents_zone` | SIRENE Stock 2026-08 |
| **Étudier un bien** | charge −122 911 € | `faisabilite/bilan.py` (CA×coef − coût − VRD) | run servi | reconstitué à l'euro |
| **Scan patrimoine** | 587 477 506 € · 919 248 m² | Σ(surface×prix U/AU) · Σ(sdp_residuelle) | `modules.patrimoine` | écart nul |
| **Faisabilité** | SDP gabarit 281 875 m² | emprise×coef×niveaux | `faisabilite/engine.py` | audit 281 159 obsolète |

---

## 3. Gates

- **tsc** : 0. **build** : OK. **vitest** : **108/108** (tests de recette adaptés : segment Permis, périmètres, sort solaire).
- **pytest** : **2000 passed, 42 skipped, 0 failed** (348 s, `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`
  contourne le piège WeasyPrint/`libgobject` FZ-002). `test_zone_donnees` adapté à la colonne date_creation (6/6).
- **Golden** : **0 fichier de scoring touché** (mes écritures : `api/modules.py` tri solaire, `zone.py`,
  `api/app.py` endpoint géojson, `ingestion/sirene_etablissements.py`, front, docs) → intact par construction.
- **Écriture DB** : la seule autorisée — colonne `date_creation` (A3-bis).

---

## 4. Fichiers touchés

Backend : `api/modules.py` (tri solaire) · `zone.py` (concurrents enseigne+annee) · `api/app.py`
(`/parcels/{idu}/geojson`) · `ingestion/sirene_etablissements.py` (colonne date_creation) · `docs/EXPLOITATION.md` §12.
Front : `outils/ModulePanel.tsx` (Permis) · `outils/ProspectionSolaire.tsx` · `outils/Communes.tsx` ·
`outils/TimeMachine.tsx` · `outils/EtudierBien.tsx` · `fiche/Fiche.tsx` · `compare/ComparePanel.tsx` ·
`map/MapView.tsx` · `lib/api.ts` · `lib/types.ts` · **`lib/perimetres.ts`** (nouveau).
Tests : `PermisDouble` · `EtudierBien` · `test_zone_donnees`.
Docs : `docs/OUTILS-2/` (compte-rendu, contre-calculs, captures).

---

## 5. Merge

**Ne pas merger.** Après revue Vic :

```
git checkout main && git merge --no-ff feat/outils-1
```
