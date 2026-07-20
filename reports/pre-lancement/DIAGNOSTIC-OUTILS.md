# DIAGNOSTIC OUTILS LABUSE — check pré-lancement (LECTURE SEULE)

**Date** : 2026-07-15. Méthode : lecture code + base (SELECT) + appels API GET en live (serveur 8010).
**Aucune écriture, aucun re-run, aucun fix.** Run servi : `Q_A_RUN_LABEL = "q_v6_m8"` (`src/labuse/scoring/score_v_constants.py:39`).

---

## SYNTHÈSE (triée par gravité)

### 🔴 Vrais CASSÉS (bug confirmé)
| Outil | Cause précise | Effort |
|---|---|---|
| **Baromètre — rapport PDF (500)** | **PAS** un bug `Decimal`. `FPDFException: Not enough horizontal space` : un `multi_cell` sans `new_x` (`moteurs.py:327`) laisse le curseur X à la marge droite → le `multi_cell` suivant (`:331`) a 0 mm → exception. Les DONNÉES sont bonnes. | **Trivial (1 ligne)** |
| **Simulateur PLU — liste non cliquable** | API saine (renvoie `idu`+`geom`). Le front M15 rend chaque parcelle en `<div>` inerte, `select` jamais branché (`frontend/src/components/outils/moteurs.tsx:25,54-60`) — seul moteur à parcelles laissé sans handler. | **Trivial (front only)** |
| **Vue mer (couche carte)** | Rendu + filtre trop restrictif. La couche n'est pas un overlay : elle re-liséré des parcelles déjà tracées, mais son filtre impose `PROMUES` (brûlante/chaude, hors étage 0) EN PLUS de `vue_mer='oui'` → sur 92 421 parcelles « oui », seules **255** sont dessinées, en liseré cyan 1,4 px souvent masqué par la braise 1,8 px + gaté sur la couche « Parcelles » + absent des tuiles z≤11. (`MapView.tsx:263,315,511,515`) | **Moyen** |
| **Radar permis — fenêtre glissante** | Une date SITADEL **future aberrante** (2026-08-17, 1 seul permis) ancre le `max(date)` de la fenêtre 24 mois (`modules.py:228`) → départ 2024-08-17 au lieu de 2024-05-30 → **~610 permis récents exclus à tort** de l'affichage radar. | **Trivial (`WHERE date<=now()`)** |

### 🟠 « Cassé » perçu mais explicable (pas un bug de branchement)
| Outil | Réalité | Effort |
|---|---|---|
| **Faisabilité programme (« toujours les mêmes 49 parcelles »)** | Le filtre de surface EST branché (`sdp_min` injecté `modules.py:888,894`) et le COUNT `n` VARIE bien (183→111→58→25 quand la taille monte). MAIS le tri `marge_capacite DESC` (`:911,920`) met en tête les parcelles à énorme SDP résiduelle **quel que soit le seuil** → le HAUT de liste (seul écran vu) ne bouge pas. « 49 » = un COUNT de commune, PAS un plafond (aucun `49` littéral). Défaut aggravant : `LIMIT 300` SQL AVANT le filtre hauteur PLU (`:895`). Les parcelles ne sont PAS bâties (étage 0 exclu, emprise ~6 %) : ce sont de grandes parcelles peu denses à statut faible. | **Moyen** (ranking + ordre du LIMIT) |

### 🔵 Chiffres « ronds » = LIMIT d'affichage, pas des COUNT réels
| Écran | Vrai COUNT | Cause |
|---|---|---|
| **Parkings APER « 500 »** | **736 assujettis** | `LIMIT 500` (`solaire.py:69,86`) + `total = len(items)` (`:111`) après LIMIT. (Dépassés = 24, vrai & stable.) |
| **Toiture tertiaire « 300 »** | **9 635** | `LIMIT 300` (`solaire.py:119,129`) + `total = len(items)` (`:138`). |
| Faisabilité programme « 49 » | COUNT commune réel | Pas un plafond (mais `LIMIT 300`/`[:200]` internes existent). |

### 🟡 Défauts mineurs (compteur / UX / couverture) — notés, non bloquants
- **Scan patrimoine** : recherche d'une boîte absente de la source → **écran vide muet** (aucun message « inconnue des fichiers fonciers ») → perçu « cassé ». `ModulePanel.tsx:121-126`. **Faible.**
- **Foncier fantôme** : compteur `total` **surestimé** (le recomptage `modules.py:480-484` omet le filtre INPI présent à l'affichage). **Faible.**
- **Mode bailleur** : couverture QPV = **13/24 communes** → 0 résultat ailleurs, sans bandeau. **Faible (UX).**
- **Deep-links fiche** (voir Groupe 4) : Maps sans épingle, Cadastre centre sans sélectionner, « 1950 » sans flyTo, radar permis sans deep-link malgré `geom` disponible.

### ✅ Marche bien — NE PAS TOUCHER
PDF fiche · Dossier + pré-dossier · Division parcellaire · Scan patrimoine (moteur) · Foncier fantôme (moteur) · Mode bailleur (moteur) · Matching promoteur (démo assumée) · Assemblage (×2) · Vélocité admin · Due diligence · ANRU/NPNRU · Parc national · Zonage PLU (2 couches) · Courrier propriétaire. **Table opérateur assainissement : existe** (`config/gestionnaires_via.yaml`, 24/24 communes).

### Données périmées : **AUCUN outil servi ne lit un ancien run.** 
Tous les outils qui touchent au scoring lisent **q_v6_m8** ; les autres lisent des tables d'enrichissement indépendantes du run (permis, DVF, OSM, géo). Voir tableau transversal ci-dessous.

---

## PRIORITÉ 0 — Tableau transversal `outil × run/source lu × à jour`

`Q_A_RUN_LABEL = "q_v6_m8"`. Les fonctions `_q_v2_*` (app.py) sont un **nommage legacy** (scoring « v2 »), elles lisent q_v6_m8 par défaut — ce n'est PAS l'ancien run q_v2.

| Outil | Run / source lu | À jour ? |
|---|---|---|
| Carte (tuiles `mvt_parcels`) | q_v6_m8 (meta confirme ; 120 brûlantes = compte réel) | ✅ |
| Liste / stats / fiche / geojson | `source` param → q_v6_m8 (défaut `Q_A_RUN_LABEL`) | ✅ |
| Scoring v2 (source des tiers) | dernier `p_score_v2` = q_v6_m8 (13:13) | ✅ (⚠ voir note) |
| Faisabilité (capacité + programme) | q_v6_m8 (`RUN` + `_v2run`) | ✅ |
| PDF fiche / Dossier / pré-dossier | q_v6_m8 (via `_q_v2_fiche`) | ✅ |
| Division parcellaire (M01) | étage 0 de q_v6_m8 | ✅ |
| Scan patrimoine (M02) | `parcelle_personne_morale` + enrichi q_v6_m8 | ✅ |
| Foncier fantôme (M07) | q_v6_m8 (q≥50) + `pm_dirigeants` | ✅ |
| Mode bailleur (M06) | q_v6_m8 + QPV `spatial_layers` | ✅ |
| Matching promoteur (M19) | bascules issues de q_v6_m8 (event_log) | ✅ |
| Assemblage (`/assemblages` + M16) | q_v6_m8 | ✅ |
| Due diligence (`/modules/duediligence`) | q_v6_m8 | ✅ |
| Simulateur PLU (M15) | q_v6_m8 | ✅ |
| Vélocité admin | `m10_permit_delais` (permis, indép. run) | ✅ (données à jour) |
| Radar permis | `sitadel_permits` (indép. run) | ✅ sauf 1 date aberrante |
| Parkings APER / Toiture tertiaire | `parkings_aper` / `mv_toitures_tertiaires` (indép. run) | ✅ |
| Vue mer | `parcel_vue_mer` via tuiles q_v6_m8 | ✅ (données) |
| ANRU / Parc national / Zonage | `spatial_layers` / `parcel_zone_plu` (statique, indép. run) | ✅ |
| Baromètre | DVF/Sitadel brut (marché, aucun run) | ✅ (cohérent) |
| Courrier propriétaire (M09) | `parcels` (templating, aucun run) | ✅ |

**Grep anciens runs (exécutables ?)** — `q_v3_datagap` / `q_v4_m6a` / `q_v5_m6b` : **uniquement en docstrings** (historique de bascule, `score_v_constants.py:30-35`, `p_v2/pipeline.py:219`). `q_v2` : 55 occ. dont les **fonctions `_q_v2_*` (nommage), et des données mortes** dans `dryrun_parcel_evaluations` (les vieux runs y subsistent mais ne sont **pas servis**). `q_v2_demo` = run démo **séparé** pour la détection d'événements (`events.py`), non servi.

**⚠ Latent (pas un bug servi)** : `_score_v2_run_id` (`app.py`) sélectionne le run v2 **le plus récent par `computed_at`**, pas épinglé à `Q_A_RUN_LABEL`. Coïncide aujourd'hui (q_v6_m8 = dernier), mais un futur run v2 d'un autre label deviendrait silencieusement la source des tiers. **Nettoyage optionnel** : purger les vieux runs de `dryrun_parcel_evaluations` (q_v2…q_v5, données mortes).

---

## GROUPE 1 — Outils signalés CASSÉS

### A. Faisabilité programme — `POST /modules/programme` (`faisabilite_sens2`, modules.py:871-930)
1. **Rôle** — Programme voulu (n bâtiments × logements × m²/unité) → parcelles dont la SDP résiduelle l'absorbe, triées par marge.
2. **Run** — q_v6_m8 (`RUN` + `_v2run`).
3. **État** — **MARCHE, tri trompeur.** Filtre surface branché (`sdp_min = unités×surf×1,15` → JOIN `parcel_residuel >= :sdp` `:888` ET `p.surface_m2 >= :smin` `:894`). En live (Saint-Denis), `n` varie **183→111→58→25** selon `surface_unite`, MAIS le top-3 est **identique** (BL0227, AM0480, BZ1481) : le tri `marge_capacite DESC` (`:911,920`) fige les plus grosses parcelles en tête. **Aucun `LIMIT 49`** (le « 49 » = COUNT de commune, reproductible : Saint-André b=8 → n=46). Parcelles NON bâties (étage 0 exclu, emprise ~6 %) — grandes parcelles peu denses à statut faible.
4. **Chiffres** — `n` réactif ✓. Deux LIMIT en dur : `300` SQL (`:895`, **avant** le filtre hauteur Python `:904-910`) + `[:200]` (`:929`). Sur commune >300 candidats, seules les 300 plus grosses sont vues.
5. **Effort** — **Moyen** : revoir le ranking (2e clé / pertinence, pas marge brute) + remonter le `LIMIT` après le filtre hauteur.

### B. Baromètre foncier — `GET /moteurs/barometre.pdf` (`barometre_pdf`, moteurs.py:270-334)
1. **Rôle** — Rapport PDF marketing (séries DVF, permis, prix/commune).
2. **Run** — Aucun (DVF/Sitadel brut, cohérent pour un baromètre marché).
3. **État** — **CASSÉ (HTTP 500 confirmé live).** **Ce n'est PAS le bug `Decimal`** : `_barometre_data(db)` s'exécute parfaitement (8 trimestres, Saint-Paul 4278 €/m²). Le crash est FPDF :
   ```
   moteurs.py:331 pdf.multi_cell(0,4,"Données publiques (DVF, Sitadel régional)…")
   → fpdf.errors.FPDFException: Not enough horizontal space to render a single character
   ```
   **Cause** : le `multi_cell` de `:327` sans `new_x` laisse le curseur X=194 mm (marge droite) → le `multi_cell` de `:331` hérite de 0 mm d'espace → exception.
4. **Chiffres** — Contenu correct, aucun LIMIT problématique. Le 500 est purement mise en page.
5. **Effort** — **Trivial (1 ligne)** : `new_x="LMARGIN", new_y="NEXT"` (ou `pdf.ln()`) au `multi_cell` `:327`.

### C. Simulateur PLU — `GET /moteurs/simulplu` (moteurs.py:48-93 ; front M15)
1. **Rôle** — « Et si cette zone AU passait en U ? » : recalcul à blanc de la SDP par ratio médian U de la commune + parcelles AU concernées + bascules.
2. **Run** — q_v6_m8 (`RUN` + `_v2run`).
3. **État** — **API MARCHE / FRONT CASSÉ.** Backend live (`?zone=AUc&commune=Saint-Denis`) → 200, `n_parcelles=400`, 196 bascules, chaque item porte **`idu`+`geom`+`sdp_estimee_m2`**. **Cause « pas cliquable » = 100 % front** : dans M15 (`moteurs.tsx:20-67`), chaque ligne est un **`<div>` inerte** (`:54-60`), `select` n'est même pas destructuré de `useApp()` (`:25`). Les autres moteurs (M17 `:170`, M22 `:90`) branchent bien `onClick={() => select(i.idu)}`.
4. **Chiffres** — Plausibles (ratio 0.204). `LIMIT 400` (`:71`) + `.slice(0,120)` front.
5. **Effort** — **Trivial (front only)** : destructurer `select` + transformer le `<div>` en `<button onClick={() => select(i.idu)}>`.

---

## GROUPE 2 — Chiffres suspects (LIMIT en dur ?)

### D. Parkings APER — `GET /solaire/parkings` (solaire.py:67-114)
1. **Rôle** — Parkings assujettis APER (ombrières PV obligatoires), tri échéance.
2. **Source** — table `parkings_aper` (OSM `spatial_layers`), indép. run.
3. **État** — **CASSÉ (affichage trompeur).** « 500 » = `LIMIT 500` (`:69,86`), `total = len(items)` **après** LIMIT (`:111`). Live : `limit=2000` → total=736.
4. **Chiffres** — `parkings_aper` = 901 lignes ; **assujettis réels = 736** (`tranche IS NOT NULL`, WHERE `:72`) ; dépassés = **24** (= tranche ≥10 000 m², échéance 2026-07-01 passée), vrai & **stable** quel que soit le LIMIT. « Dépassé » = `echeance < CURRENT_DATE` (`:79`), correct. OSM = plancher **dit** (`note` `:113`, `parkings_aper.py:18-22` : exemptions non déduites).
5. **Effort** — **Trivial** (COUNT séparé du `len(items)`).

### E. Toiture tertiaire — `GET /solaire/tertiaire` (solaire.py:117-141)
1. **Rôle** — Grandes toitures d'activité (décret tertiaire) × PM × PVGIS.
2. **Source** — vue matérialisée `mv_toitures_tertiaires`, indép. run.
3. **État** — **CASSÉ (même artefact).** « 300 » = `LIMIT 300` (`:119,129`), `total = len(items)` (`:138`). Live : `limit=5000` → total=5000 (pas de plateau → bien plus de lignes).
4. **Chiffres** — `COUNT(mv_toitures_tertiaires) = 9 635` (32× l'écran). Plausible (bâti non-résidentiel > seuil, île entière). Note honnête présente (poste source EDF indispo).
5. **Effort** — **Trivial.**

---

## GROUPE 3 — Couches carte

### F. Vue mer — toggle carte (MapView.tsx ; `parcel_vue_mer`)
1. **Rôle** — Surligner les parcelles à vue mer dégagée.
2. **Source** — `parcel_vue_mer` (150 643 lignes ; 92 421 'oui'), jointe dans la tuile (`tiles.py:129,138`).
3. **État** — **CASSÉ (rendu + filtre).** Trois causes cumulées : (1) pas un overlay — n'est pas dans `_MAP_LAYER_KINDS` (`kind=vue_mer` → 0 feature), c'est un re-liseré de la source parcelles (`parcels-vuemer`/`ile-vuemer`, cyan 1,4 px, `MapView.tsx:261-265,314-316`) ; (2) filtre `['all', PROMUES_FILTER, ['==', vue_mer,'oui']]` (`:263,315`) → sur 92 421 'oui', seules **255** (∩ brûlante/chaude hors étage0) sont dessinées ; (3) ces 255 sont déjà cerclées (contour statut + braise 1,8 px dessinée après) → le liseré cyan est masqué. + gaté sur `layers.parcelles` (`:511,515`) + `vue_mer` absent des tuiles z≤11 (`tiles.py:219`).
4. **Chiffres** — 92 421 'oui' en base, **255** rendus (vrai COUNT, pas un LIMIT).
5. **Effort** — **Moyen** (liseré distinct / retirer le gate PROMUES / vraie couche de remplissage + porter `vue_mer` en tuiles basses).

### G. ANRU / NPNRU — toggle carte (`spatial_layers kind='anru'`)
- **MARCHE.** Live `/map/layers.geojson?kind=anru` → **8 features** = COUNT base. `attrs` : `programme=NPNRU`, `code_qp_2024` (QPV 2024), `source=DEAL_REUNION_WFS`, intérêt national, 6 communes. Libellé UI « 8 quartiers » cohérent. **Rien à corriger.**

### H. Parc national — toggle carte (`spatial_layers kind='parc_national'`)
- **MARCHE.** Live → **72 features** = COUNT base. `subtype` distingue `coeur` (code 0) et `adhesion` (codes 6/7). Couverture intérieur/hauts cohérente. **Rien à corriger.**

---

## GROUPE 4 — Deep-links carte (ne centrent pas sur la parcelle)

La fiche EXPOSE le centroïde : `coords = [lon, lat]` (`app.py:1595`, 6 décimales). Le problème est la **construction des URL** (centrage vs désignation), pas l'absence de coordonnées.

| Pt | Lien | Fichier:ligne | URL/action actuelle | Cause | Param manquant | Effort |
|---|---|---|---|---|---|---|
| 22 | **Cadastre** | Fiche.tsx:1293 | `geoportail…?c=lon,lat&z=18&l0=CADASTRAL…` | `c=` **centre** mais ne **sélectionne** pas la parcelle (pas de halo) | sélection par **IDU** | Moyen |
| 23 | **Maps (« G »)** | Fiche.tsx:1301 | `google.com/maps/@lat,lon,19z/…` | `@` centre la caméra, **aucune épingle** | `maps/search/?api=1&query=LAT,LON` | Faible |
| 24 | **1950** | Fiche.tsx:1284 | `setModule('temps')` — **interne, pas d'URL externe** | pas de **flyTo(coords)** à l'ouverture → carte reste où elle est | flyTo(coords, z≈18) au clic | Faible-moyen |
| 37 | **Radar permis** | ModulePanel.tsx:161-203 | drawer **sans aucun deep-link** ; le plot carte = centroïde parcelle | le drawer n'exploite pas `d.geom` (pourtant renvoyé par l'API `modules.py:279,301`) | bouton Maps/Cadastre sur `d.geom` + fallback IDU | Faible |
| 21 | **libellé « G »** | Fiche.tsx:1305 | texte `G` | (renommage) | remplacer par « Maps » | Trivial |

**« Non géocodé »** = permis sans `geom` (`sitadel_permits.geom IS NULL`), non plaçable sur carte, listé avec badge (`ModulePanel.tsx:255`). **COUNT : 10 749 / 50 043 = 21,5 %** (39 294 géocodés). remonterletemps.fr **n'existe nulle part** dans le front (« 1950 » = comparateur interne WMTS IGN 1950-1965).

---

## GROUPE 5 — Rôle + état réel

### I. Outil tout en bas — **Courrier propriétaire (M09)** (`POST /modules/courriers`, modules.py:559-575)
Dernier du groupe « agir » du rail. **MARCHE.** Templating SQL→texte (3 gabarits standard/indivision/succession), aucun run, borné 100 IDU, rappel SPF/CERFA honnête. **Effort : 0.**

### J. Scan patrimoine (M02) — `GET/POST /modules/patrimoine` (modules.py:174-219)
- **Raccroché à** : **Fichiers fonciers DGFiP** (`parcelle_personne_morale`), **PAS INPI ni Pappers** pour la détection (INPI/`pm_dirigeants` sert seulement au foncier fantôme). Enrichit avec q_v6_m8 (tier, SDP, BODACC).
- **Prend** : **toutes les personnes morales** détentrices de foncier (SCI ET entreprises, groupé par SIREN sans filtre de forme). 82 701 lignes, 12 605 SIREN.
- **VISHOR** : `denomination ILIKE '%VISHOR%'` → **0 ligne**. **PAS cassé** — la boîte est **absente de la source foncière** (aucun immobilier recensé). Preuve : `A J P MATERIAUX` (SIREN 533853446) remonte 2 parcelles. → il faut un **message clair** « inconnue des fichiers fonciers », aujourd'hui écran vide muet (`ModulePanel.tsx:121-126`, **effort faible**).

### K. Division parcellaire (M01) — `/modules/division` (modules.py:69-169, table `module_division`)
Repère les grands terrains divisibles (C1-C5 géométriques). Calcul sur `parcels`+`spatial_layers` (pas de score), mais le service **applique l'étage 0 de q_v6_m8** (`:146-147`, `RUN`) et compte les exclues à part (`etage0_exclus`). Live Saint-Paul : total 376 / exclus 322 / 300 servis ; table = **4 433 candidats** (24 communes). `LIMIT 300` mais total exact. **MARCHE. Effort : 0.**

### L. Foncier fantôme (M07) — `/modules/fantome` (modules.py:459-491)
PM à fort Q « verrouillée » (introuvable au RNE/INPI ou dirigeant inactif). Croise q_v6_m8 (q≥50) × `parcelle_personne_morale` × `pm_dirigeants` (27 146 lignes). **MARCHE** (live Saint-Paul : total 6169 / 600 affichés). **Défaut mineur** : `true_total` (`:480-484`) omet le filtre INPI → **surestime** le gisement. **Effort faible.**

### M. Mode bailleur (M06) — `/modules/bailleur` (modules.py:496-525)
Gisement LLS **en QPV** (leviers TVA 2,1 %, TFPB). Remonte les parcelles intersectant `spatial_layers kind='qpv'` (`:507`), statut chaude/à surveiller/à creuser, tri SDP. **NE filtre PAS les communes carencées SRU** (le SRU est dans le volet Contexte commune, découplé). Lit q_v6_m8. **MARCHE** (île ≈ 2 034). **Limite** : 57 géoms QPV → 13/24 communes couvertes, 0 ailleurs sans bandeau. **Effort faible (UX).**

### N. Matching promoteur (M19) — `partners.py:88-112`
Matche les bascules « chaude » (event_log) × profils acquéreurs (commune/surface/sdp_min) → événements `kind='match'`. **Profils saisis à la main, 2 profils DÉMO `demo=true`**, pas de source promoteur externe. **MARCHE** (5 matchs déjà en base). Cadre fonctionnel **honnête** (démo assumée) ; activation = alimenter `match_profiles` (métier). **Effort technique : 0.**

### O. Assemblage — `GET /assemblages` (app.py:1816-1855 + assemblage.py) & `POST /moteurs/assemblage` (moteurs.py:96-154)
Regroupe des parcelles **contiguës** franchissant ensemble le seuil de constructibilité. **MARCHE** (live : Saint-Paul, paire AY0248+AY0247 = 1992 m², `/assemblage/study` → capacité/CA/charge foncière, contiguïté `ST_Union`). Lit q_v6_m8. Note honnête (SDP cumulée = somme des résiduels). **Effort : 0.**

### P. Vélocité admin — `GET /modules/velocite` (modules.py:389-454)
Délai médian dépôt→autorisation. Table `m10_permit_delais` : **42 603 valides** / 50 290, **PC médiane 9 mois** (DP 8, PD 7, PA 10), 15,2 % exclus (dépôt>autorisation). Méthodo robuste : cutoff maturité (dernier dépôt −12 mois), médiane, P25/P75, 3 biais **affichés**. Live : 24 communes, cohortes 2013-2026. **MARCHE, données justes. Effort : 0.** (429 lignes orphelines sans `permit_id`, sans impact.)

### Q. Due diligence — `POST /modules/duediligence` (modules.py:578-609) & `GET /pre-dossier/{idu}.zip`
Colle une liste de références → fiches synthétiques + lien PDF. Lit q_v6_m8. Simulation SELECT sur EL0387 → `{commune, surface, statut, q_score, tier_v2, pdf:…}`, non résolus → `{ref, erreur}`. **MARCHE.** Le pré-dossier ZIP est gaté **plan Intégral** (403 en Phase 0, code fonctionnel). **Effort : 0.**

### R. Radar permis (données) — `sitadel_permits`
**MARCHE, fraîches.** 50 043 permis, **2013→2026**, PC 45 742/DP 2 391/PD 1 108/PA 802, **78,5 % géocodés** (`via_permits_geo` 39 294). **Un défaut** : date max **2026-08-17** = outlier unique (1 permis futur) ; le vrai flux s'arrête au 2026-05-30. `/modules/permis` ancre sa fenêtre 24 mois sur ce `max(date)` (`modules.py:228`) → **~610 permis récents exclus à tort** (4 980 affichés vs 5 590). **Effort trivial** (`WHERE date<=now()`).

---

## GROUPE 6 — PDF & dossier

### S. PDF fiche — `GET /parcels/{idu}/export.pdf` (app.py:1731-1752, pdf_premium.py)
**OK live** (97423000AB1908 → 200, 2 pages, ~62 Ko). Lit **q_v6_m8** (`_q_v2_fiche`, footer « run q_v6_m8 »). **Contient** : en-tête + IDU + adresse BAN, verdict v2 (rang/×), scores Q/A/complétude, ICD (confiance + manques), Potentiel de transformation, Contexte commune (SRU/QPV/marché INSEE), RTAA DOM, lignes cascade tracées (poids+source+date), charge foncière conditionnelle. **Manque (mineur)** : pas de plan de situation (porté par le dossier), bloc gestionnaires assainissement non repris. **Effort : 0.**

### T. Dossier — `GET /dossier/{idu}.pdf` (dossier.py) & `/pre-dossier/{idu}.zip` (pre_dossier.py)
**OK live** (module Flash déployé ici) : dossier PDF **5 pages** (garde → identité → constructibilité → risques…), pré-dossier ZIP 1,2 Mo **4 fichiers** (CERFA 13406*17 pré-rempli, plan de situation, règles zonage, LISEZMOI). Champs PROJET du CERFA laissés vides (préparatoire, assumé). Dépendance souple au module Flash (501 ailleurs). **Effort : 0 ici.**

---

## GROUPE 7 — Deux questions de données

### U. Table opérateur assainissement (point 5) — **OUI, ça existe**
**PAS une table SQL** : config **`config/gestionnaires_via.yaml`** (194 lignes), lue par `resolve_gestionnaires` (`faisabilite/viabilisation.py:233-252`), exposée dans le bloc `gestionnaires` de la fiche faisabilité (`app.py:1605,1623`). **24/24 communes**, chacune : `eau`, `assainissement` (opérateur + type contrat + `confidence`), `spanc`, `epci`, note datée `a_jour_au:"2026-07"`. Exemples : Les Trois-Bassins « Régie La Créole », Le Tampon « Sud Assainissement Réunion (Runéo/Veolia) », Bras-Panon « Runéo → CISE 01/01/2027 », Salazie « ANC ». **Assez pour rédiger un mail** (opérateur + EPCI nommés). **Manque pour la feature** : aucune **adresse e-mail** directe d'opérateur (seuls contacts EPCI présents) → enrichissement **faible** du YAML. Aucune feature « mail » n'existe encore.

### V. Zonage PLU vs parcelles (point 12) — **confirmé, deux couches distinctes**
| Couche UI | Source | Nature | COUNT |
|---|---|---|---|
| **« Zonage PLU »** | `spatial_layers kind='plu_gpu_zone'` | polygones de zone **BRUTS** du GPU | **5 848** |
| **« Zonage PLU (parcelles) »** | `parcel_zone_plu` (`zone_lib`/`zone_fam`) | zone **rattachée par parcelle** (dominante) | **427 419** |
Wiring : front `LeftPanel.tsx:7,10` (libellés déjà distincts) → `getMapLayer('plu_gpu_zone')` (polygones) vs coloration `mvt_parcels.zone_fam` (parcelles). Répartition familles : U 306 630 · A 73 946 · N 36 306 · AU 10 537. `mvt_parcels` porte bien `zone_lib`+`zone_fam` (tuiles à jour). **C'est exactement ça.** Attention UI : `zone_lib` est un code court extrait heuristiquement du `name` GPU (`tiles.py:33-41`) — le libellé « (parcelles) » est justifié (dérivée par rattachement, pas la géométrie officielle).

---

*Diagnostic lecture seule. Aucun fix, aucune écriture, aucun re-run. Seul ce fichier est committé.*
