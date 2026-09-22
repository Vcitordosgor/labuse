# ÉTAT DES LIEUX vs critère DONE (§7) — Étape 0, lecture seule

> Demandé par la DIRECTIVE post-1.A (Décision 4, Étape 0). Constat factuel **avant** toute
> implémentation des Décisions 1–3. Références `fichier:ligne` vérifiées sur le code au
> 2026-06-12 (branche `claude/brave-davinci-NaRd4`).

## 1. Mode Audit pull (entrée à la demande)

| | Constat |
|---|---|
| **Existant** | Entrée **par IDU** : `GET /parcels/{idu}` (`api/app.py:417`) + **ré-évaluation à la demande** `POST /parcels/{idu}/evaluate` (`api/app.py:569`, option `?ai=true`). Connecteur cadastre **à la volée** déjà écrit : `fetch_by_section(insee, section, numero)` et `fetch_by_geom(geojson)` (`connectors/cadastre.py:95,104`) — API Carto IGN. |
| **Manquant** | **Pas d'entrée par adresse** (aucun géocodage BAN). **Pas d'entrée par polygone dessiné** (pas d'endpoint « parcelles dans ce polygone »). Surtout : **pas de chemin bout-en-bout pour auditer une parcelle HORS référentiel ingéré** — `GET /parcels/{idu}` fait un SELECT et 404 si absente (`api/app.py:436`) ; le connecteur à la volée n'est branché sur rien. |
| **À valider** | Le « pull » réel = fetch cadastre → ingestion 1 parcelle → prime → cascade → fiche. Toutes les briques existent (connecteur, `evaluate_parcels` accepte N=1), il manque l'orchestration + l'UI. |

## 2. Potentiel résiduel (utilisation bâti vs emprise max, SDP résiduelle)

| | Constat |
|---|---|
| **Existant** | Ratio bâti/parcelle calculé et classé en 6 classes (`bati.py:87-111`, seuils 5/15/30/50 %) ; déclassement « déjà bâtie » + motif. Emprise constructible sur géométrie réelle (contour inseté `ST_Buffer 2975`, `faisabilite/db.py:84-88`), SDP brute, shab vendable, fourchette logements (`faisabilite/engine.py:216-254`). |
| **Manquant** | **Aucun « résiduel » affiché** : pas de ligne « bâti existant X m² ≈ Y % de l'emprise max → SDP résiduelle ≈ Z m² ». Les deux moitiés du calcul existent (bâti d'un côté, capacité de l'autre) mais ne sont **jamais croisées**. |
| **À valider** | Sémantique exacte attendue par le brief (R1 bâti vs emprise max : au sol ? en SDP ?) avant de coder. |

## 3. Export (`api/export.py`)

| | Constat |
|---|---|
| **Existant** | `GET /parcels/{idu}/export?format=md|html` (`api/app.py:556-566`) : fiche **Markdown** (`export.py:20`) et **HTML mono-page imprimable** (`export.py:138`) — verdict, résumé, cascade, bâti, comparables DVF, voisinage, prospection, disclaimers. Plus `GET /map/parcels.geojson` (`api/app.py:374`). |
| **Manquant** | **Pas de PDF natif** (le « PDF 1 page » du brief = imprimer le HTML aujourd'hui), pas de CSV de liste (prospection en masse), pas d'export du pipeline. |
| **À valider** | Le HTML imprimé tient-il vraiment sur 1 page A4 pour une fiche complète ? (non testé automatiquement). |

## 4. Pipeline de prospection / comparateur / filtres sauvegardés

| | Constat |
|---|---|
| **Existant** | **Pipeline Kanban complet** : table `pipeline_entries` (`models.py:313-335`, statut/priorité/notes/rappel/prospection JSONB), endpoints CRUD (`api/app.py:719-817`), colonnes configurables (`config/pipeline.yaml`), rappels échus visibles (badge UI). **Prospection manuelle RGPD-safe** (`prospection.py`, validations + disclaimers, niveau de confiance, responsable, dates). |
| **Manquant** | **Comparateur** de parcelles (vue côte-à-côte) : n'existe pas. **Filtres sauvegardés** : n'existent pas (les filtres de la vue Découverte sont inline, non persistés). Assignation multi-utilisateurs : pas de colonne `assigned_to` (un seul champ libre « responsable » dans la prospection). |
| **À valider** | `reminder_date` est stocké et affiché, mais aucune notification (pas de scheduler) — suffisant pour le DONE ? |

## 5. Couches « Phase 3 » du brief

| Couche | État |
|---|---|
| Ravines (hydrographie) | ✅ Ingestion BD TOPO `kind='water'` + couche cascade `eau` (centroïde ou ≥50 % → HARD_EXCLUDE, `cascade/layers/phase1.py:40-56`). Pas de distinction nommée « ravine » vs rivière. |
| 50 pas géométriques / littoral | ⚠️ Approché par le **trait de côte DEAL** (`bande_courte` exclut, `bande_longue` flag, `phase1.py:334-351`). La zone juridique « 50 pas géométriques » en tant que telle n'est **pas** ingérée. |
| Personnes morales DGFiP | ⚠️ Lecture seule si fournis : Fichiers fonciers Cerema **sous convention**, source `manuel` (`api/enrichment.py:307-348`, couche cascade `proprietaire` phase 2). Aucun flux auto (légalement attendu). |
| SITADEL (permis) | ✅ Ingestion ODS (`ingestion/permits.py:29-70`), couche phase 2 `sitadel` (bonus permis rattaché/à proximité) + signal de veille. |
| Pente / exposition | ✅ Pente RGE ALTI (grille ~180 m, `layers_ingest.py` `ingest_pente`) + couche `pente` (affichée, non excluante) + modulation faisabilité (×0,7 / ×0,4 ; `faisabilite/engine.py:297-303`) + garde-fou déclassement. ❌ **Exposition** (orientation des pentes) : absente. |
| Assemblage contiguës | ✅ À la volée : `api/voisinage.py` (ST_DWithin 0,5 m en 2975, drapeau « assemblage à étudier »). Pas de recherche systématique d'assemblages côté Découverte. |

## 6. Recette existante (tests automatiques)

| | Constat |
|---|---|
| **Existant** | **204 tests verts** (24 fichiers). Cascade : statuts bout-en-bout sur fixtures synthétiques (`test_cascade.py`). Faisabilité : ~26 tests purs (zones, reculs, niveaux, plafond densité, modulations) dont un test d'**ordre de grandeur** de capacité. Bâti : seuils des 6 classes. Bilan : aberrants/fiabilité. API : statuts HTTP des endpoints. Démo : conformité des 8 parcelles réelles (`test_demo.py`). |
| **Manquant** | **Aucun test ne valide les CHIFFRES de capacité contre une application manuelle du règlement** (ex. « U1c, 1 000 m², hé 9 m → X-Y logements ») — c'est exactement l'Étape 2 demandée. Pas de test d'intégration « parcelle réelle → valeurs attendues » hors statuts. |
| **À valider** | La recette capacité ±15 % (Étape 2) tranchera « implémenté » vs « validé ». |

## Synthèse

| Item DONE §7 | Existant | Manquant | À valider |
|---|---|---|---|
| Audit pull | IDU + re-éval à la demande ; connecteur à la volée écrit | BAN, polygone, orchestration hors-référentiel | chemin bout-en-bout |
| Potentiel résiduel | bâti classé + capacité calculée | croisement « résiduel » affiché | sémantique brief |
| Export | MD + HTML + GeoJSON | PDF natif, CSV | tenue 1 page |
| Pipeline / comparateur / filtres | Kanban + prospection manuelle complets | comparateur, filtres sauvegardés, assignation | notifications rappels |
| Couches Phase 3 | eau, littoral (trait de côte), SITADEL, pente, propriétaire (convention), voisinage | 50 pas officiels, exposition, ravines nommées, flux DGFiP auto | seuils pente faisabilité |
| Recette | 204 tests (statuts, seuils, API) | tests de CHIFFRES de capacité | Étape 2 (±15 %) |
