# A0 — Inventaire et mesure · Gabarit réglementaire (GABARIT-1)

Lecture seule. Chaque affirmation porte sa preuve `fichier:ligne` ou sa requête.
Base : PostGIS `labuse` (lecture seule), branche `feat/gabarit-1`, worktree `~/Desktop/labuse-gabarit`.

## Tableau de décision — par famille et par fait

| Fait / famille | Décision | Source réelle | Détail |
|---|---|---|---|
| Parcelle (géométrie, surface, source cadastre) | **RÉEL** | `parcels` (geom 4326 + `geom_2975` métrique, `surface_m2`, `idu`) | 431 663 parcelles ; `surface_parcelle_m2` déjà au registre (`donnees.py:88`). |
| Reculs — **valeurs** (voie, séparatives) | **RÉEL** | `zonage.py` → `ZoneRules.recul_voirie_m`, `recul_limites_sep_m` (+ flags `*_alignement`) | Validées-only ; `propose` → **bloquant** (`regle_non_validee`). |
| **Classification des limites** (voie / side / rear, géométrie par arête) | **BLOQUANT → GABARIT-2** | — (à construire) | Mesuré : échoue le seuil 0 faux / 30 (§ point 5). Faux-séparatives systématiques (rues cadastrées). |
| Hauteur réglementaire (faîtage / égout) | **RÉEL** | `zonage.py` → `ZoneRules.hf_m` (faîtage), `he_m` (égout) | Faîtage sert l'extrusion 3D ; égout affiché s'il existe. Pas d'id registre PLU aujourd'hui → à créer. |
| Emprise / CES → plafond d'emprise | **RÉEL** | `zonage.py` → `ZoneRules.emprise_sol_pct` | `plafond = surface × pct / 100`, calculé à part (jamais `min()`). |
| Exclusions — **PPR zone rouge** | **RÉEL** | `spatial_layers kind='ppr' subtype='INTERDICTION'` + `cascade_results` | 151 545 parcelles `HARD_EXCLUDE`, gradué **≥ 50 %** de couverture (`cascade_rules.yaml:149-175`). |
| PPR zone bleue (PRESCRIPTION) | **RÉEL, `not_integrated`** | `spatial_layers kind='ppr' subtype='PRESCRIPTION'` (88) | Constructible sous prescriptions → jamais exclue automatiquement. |
| Aléas informatifs (`georisque_alea`, `ravine`, `tri_zone`, `zone_humide`, SUP PM1…) | **RÉEL, `not_integrated`** | `spatial_layers` | Aucun règlement opposable → jamais une exclusion (CDC §3). |
| Multi-zones (à cheval ≥ 2 zones) | **RÉEL** (détection → bloc honnête) | `zone_servie.zone_dominante().a_cheval` (dominante < 90 %) | ~9 % mesuré ; bloquant GABARIT-1 (règle non unique). |
| Stationnement, espaces libres, règles non chiffrables (H/2, bandes…) | **RÉEL, `not_integrated`** | catalogue `applicableRules` | Comptées, sourcées, ne modifient jamais le calcul. |
| Parcelle fictive de démonstration (CDC §9) | **FICTIF-TESTS** | fixtures | Même contrat que le réel ; aucune logique spécifique au moteur. |

**Conséquence** (contingence explicite du mandat, point 5 & Hors mandat) : la classification des limites échouant la mesure, **les lots A–C sont livrés quand même**. Le moteur et l'outil portent le **contrat complet** ; ils sont démontrés sur **fixtures** (parcelle fictive CDC §9) derrière un **flag admin**. Le `builder` assemble déjà le réel pour tout le reste (cadastre, règles PLU, PPR, multi-zones) ; sur une parcelle réelle le résultat est honnêtement **« Calcul incomplet — donnée réglementaire manquante »** tant que la classification n'est pas certifiée (GABARIT-2). Aucune réécriture du moteur / carte / panneau / 3D ne sera nécessaire pour brancher la classification réelle (raccordement unique).

---

## 1. Prototype — aucun

Grep `gabarit|enveloppe|envelope|extrusion|extrude|footprint|implantation|emprise` sur `src/ frontend/ config/ scripts/` : **aucun outil « gabarit / enveloppe constructible »**. Occurrences sans rapport : `gabarit` = modèles de courriers (`emails.py:121,153`, `courrier.py:146-466`, `cli.py:371`) ; `enveloppe` = moteur PAU RNU (`rnu.py:10-192`) et « enveloppe restante » ZAN (`seed_sources.py:853`) ; `emprise` = calcul de faisabilité scalaire (`faisabilite/db.py`, `assemblage.py`). **On construit neuf**, sans risque d'outil parallèle.

## 2. Stack

- **Carte** : MapLibre GL `frontend/package.json:14` (`maplibre-gl ^4.7.1`) ; composant `frontend/src/components/map/MapView.tsx`, barre `MapToolbar.tsx`.
- **Bouton 3D à réutiliser** : `MapToolbar.tsx:101-110` (`<button onClick={toggleTerrain}>3D</button>`), état `terrain3d`/`toggleTerrain` dans `store/useApp.ts:443,867-868`. Extrusion bâtiments (RECETTE-6) : couche `batiments-3d` `type:'fill-extrusion'` `MapView.tsx:567-573`, source `batiments` `MapView.tsx:526`, alimentée par `GET /map/batiments.geojson` `api/app.py:5727-5762`, effet `terrain3d` `MapView.tsx:985-1010`. → la couche gabarit sera une source `fill-extrusion` supplémentaire pilotée par **ce** bouton.
- **Utilitaires géo Python** (à réutiliser) : `src/labuse/geo.py` — `to_metric` `:25`, `area_m2` `:30`, **`buffer_m(geom, meters)` `:40-42`** (négatif = recul/inset, **primitive de recul**), `intersection_area_ratio` `:45-52`, `geom_area_m2` `:64-72` (shapely+pyproj 4326→2975). Clip d'emprise de référence : `faisabilite/db.py:75-110` (`_EMPRISE`, inset `ST_Buffer(geom_2975,-d)` + clip sous-zone + soustraction ER/EBC), `parcel_faisabilite` `:204-271` (rend un **m²**, à étendre pour émettre la **géométrie**). Anneau de contact `ADJ_BUFFER_M = 0.5` `assemblage.py:17`.
- **Dépendances** : **Turf ABSENT** de `frontend/package.json` (conforme à l'adaptation « moteur Python back »). Python : `shapely>=2.0`, `pyproj>=3.6`, `GeoAlchemy2>=0.14` (`pyproject.toml`), PostGIS 3.6.4. ⚠ MEMORY signale un opt-in `assiette_clippee` (SCORING-6) : **absent de cette branche** — `parcel_faisabilite(session, parcel_id)` n'a pas ce paramètre.

## 3. Règles PLU — via `zonage.py` uniquement

- Contrat : `resolve_zone(code, commune) -> ZoneRules | None` `zonage.py:337-339` (alias `resolve_zone_v2 :343`) ; `load_rules(commune)` `:346-358`. **Entrée = code de zone** (pas d'IDU — le `builder` résout IDU→code, cf. point 7). Retour = dataclass `ZoneRules` `:34-80`.
- Champs lus par le moteur : `recul_voirie_m` `:44` (+ `recul_voirie_alignement` `:59` pour `forme: alignement`, recul 0 explicite) ; `recul_limites_sep_m` `:45` (+ `recul_limites_alignement` `:60`) ; **hauteur** `hf_m` (faîtage) `:42`, `he_m` (égout) `:41`, `niveaux_max` `:54`, `hauteur_mode` `:53` ; **CES** `emprise_sol_pct` `:43`. Sources par article : `ZoneRules.sources`.
- **`propose` = bloquant** : `_val` renvoie le sentinel `A_VERIFIER` si `statut=='propose'` `:113-131` ; l'overlay ne branche que `valide` `:403-426`. **Signal de blocage** = `ZoneRules.regle_non_validee` truthy `:57-58` (posé `:210-219`, `:296-298`, `:322-324`). Aussi : `calibree=False` `:52` = estimation générique (non validée). **Recette de lecture** : bloquer si `regle_non_validee` ou `not calibree` ou valeur non-`float` (None = silence prouvé, `"a_verifier"` = ambigu).
- Source de vérité : `config/plu_destinations/974*.yaml` (**23 communes**), bloc `regles.<rubrique>.<feuille>.<clé>` (`hauteur.faitage.m`, `hauteur.egout.m`, `emprise_sol.ces.pct`, `retraits.voie.min_m`, `retraits.limites_separatives.min_m`, `pleine_terre.pct.pct`, cf. `zonage.py:137-142`). Exemples : hauteur `97415_saint_paul.yaml:24-38` ; CES `97401_les_avirons.yaml:33-40` ; `forme: alignement` `97405_petite_ile.yaml:921-936` ; `propose` null `97415_saint_paul.yaml:39-47`. Comptes : `statut: valide` ~1926, `propose` 56, `forme: alignement` 14.

## 4. Risques — réglementaire vs informatif

- **Réglementaire (peut devenir exclusion)** : `spatial_layers kind='ppr'` (164) — `subtype='INTERDICTION'` (74, **zone rouge**, `attrs.statut='zonage_reglementaire'`, `document`, `approbation` datée, DEAL Réunion) vs `PRESCRIPTION` (88, **zone bleue**). Croisement per-parcelle **déjà matérialisé** : `cascade_results` couche `risques` → **151 545 `HARD_EXCLUDE`** (`detail='Exclue : PPR zone rouge (inconstructible).'`). Gradué **≥ 50 %** (`config/cascade_rules.yaml:149-175` : `ppr_red_exclude_pct: 50`, `ppr_red_marginal_pct: 2`). Producteur : `cascade/layers/phase1.py:641-727` (`RisquesLayer`) ; intersection batchée `cascade/context.py:87-160` (`ST_Subdivide`).
- **Informatif (jamais une exclusion)** : `georisque_alea` (1093, `attrs` = degré/niveau, aucun `document`/`approbation`), `ravine` (12716), `tri_zone` (128), `zone_humide` (3122), `mvt`/`cavite`/`endiguement`/`trait_de_cote`. SUP : `kind='sup'` (417) — `pm1` (311) = **périmètre** du PPR (assiette, pas le zonage rouge/bleu) ; « le doute NE CLASSE PAS » `phase1.py:662-663,702-709` ; `ac1-4`/`el10` ne contraignent pas l'emprise.
- **Verdict** : famille **Risques = RÉEL** pour la **zone rouge PPR** (exclusion dure, seuil ≥ 50 %) ; **zone bleue + tous les aléas + SUP = `not_integrated`**, sourcés, jamais « intégrés » par défaut (CDC §3). ⚠ Piège à ne pas copier : `courrier_compose.py:21` mélange `ravine`/`trait_de_cote` (informatif) dans des HARD_EXCLUDE — le builder ne dérivera l'exclusion QUE du `HARD_EXCLUDE` PPR rouge de `cascade_results`.

## 5. Classification des limites — le point dur — **ÉCHEC MESURÉ du seuil → GABARIT-2**

**Méthode testée** (mandat point 5, par segment du contour en 2975) : voisin cadastré ≤ 0,5 m → séparative ; sinon tronçon voirie BD TOPO (`spatial_layers kind='voirie'`, 235 643 lignes) ≤ 6 m → voie ; sinon **non classée = bloquant** ; `rear` = séparative ne partageant aucun sommet avec un segment voie. Script reproductible : `scripts/gabarit_a0_classification.py` (source de la classification servie : `LABUSE — adjacence cadastre + BD TOPO voirie`).

**Échantillon** : 30 parcelles **U** tirées (Saint-Denis, Saint-Pierre, Saint-Paul, 10/commune) + la parcelle nommée du mandat `97410000AN0347` (⚠ **arbitrage** : elle est en zone **N**, pas U — cf. base `parcel_zone_plu`). 31 captures ortho IGN + segments colorés : `docs/GABARIT/captures/a0-limites-*.png`, synthèse `a0-limites-synthese.csv`.

**Résultat** : **échoue le seuil 0 faux / 30.** Cause racine mesurée : **les rues des centres urbains sont cadastrées comme parcelles**, donc un segment de façade a un « voisin ≤ 0,5 m » et la règle « voisin → séparative » l'emporte → **la façade sur rue est faussement classée séparative**. Preuve : sur les 20 parcelles à `voie=0`, **7 ont un axe voirie à 0,00 m** de leur contour (façade avérée) et plusieurs autres à 0,5–3 m ; seules 3 sont réellement intérieures (> 10 m). Exemple visuel `97416000IE0601` (voirie à 0,00 m longeant l'arête SW, 4 segments tous « séparative »). À l'inverse, la méthode est **juste** là où la rue n'est pas cadastrée (`97411000IE0153`, `97411000DL0527` : façade correctement en « voie »).

**Nuances** : (a) pour le **calcul**, seule la distinction **voie vs séparative** compte — `side` et `rear` partagent l'unique `recul_limites_sep_m` de `zonage.py`, donc le split side/rear est **cosmétique** (aucun impact sur la zone d'implantation) ; (b) « non classée » est un blocage honnête, jamais un faux. Le défaut disqualifiant est la **fausse séparative sur façade cadastrée**.

**Fix identifié (GABARIT-2)** : détecter les **parcelles-voie** (un axe voirie court le long / à travers le voisin) et les exclure du test de séparative → séparative = voisin **non-voie** ; voie = voisin-voie **ou** voirie proche sans voisin bâti. Nécessite sa propre passe de validation (0 faux / 30) et une optimisation (le test parcelle-voie non indexé est lent). → **classification = GABARIT-2**.

## 6. Registre (V5f)

- Vit en Python : `src/labuse/registre/donnees.py:60` (`DONNEES`, un fait = une clé) + `robinets.py:33` (`ROBINETS`, `chiffres:tuple[str,...]` = ids servis). Déclaratif, pas de décorateur. Rattachements via `declarations/` (`declarations.py:238-239` : `quoi:` doit être un id de `DONNEES`).
- Existants utiles : `surface_parcelle_m2` `donnees.py:88`. **Aucun id pour la hauteur réglementaire PLU ni le CES** (internes au moteur `zonage.py`/`engine.py`). Les 3 chiffres du gabarit n'existent pas.
- **Nouveaux ids à créer** (convention `snake_case` + suffixe unité) : `gabarit_implantation_m2`, `gabarit_emprise_plafond_m2`, `gabarit_couverture_verdict`.
- **V5f** : `circuit_verrous.py:775-809` (`verrou_outils_registre`), enregistré `:885`. Vérifie (1) chaque outil visible du menu (`registry.ts`) → robinet mappé dans `OUTIL_ROBINET_MENU` `:742-760` ; (2) chaque chiffre d'un robinet d'outil ∈ `DONNEES` `:802-803`. **Rester vert** : déclarer les ids dans `DONNEES`, créer le robinet `outil_gabarit` (avec `chiffres`), mapper `"<key>": "outil_gabarit"`.

## 7. Multi-zones

- Résolution : `faisabilite/zone_servie.py:76-114` `zone_dominante(session, parcel_id)` = zone **dominante par surface** (pas centroïde) ; lit `parcel_zone_plu` (PK `idu`, une ligne = dominante) quand la table existe. Appelée par `faisabilite/db.py:149-152`.
- **Détection bloquante** : `ZoneServie.a_cheval` `:32` (posé quand dominante < `SEUIL_A_CHEVAL_PCT=90` `:24,:113`), ou `len(parts)>1` pour la version stricte. ~9 % mesuré (cohérent avec le mandat). Le builder bloque si `a_cheval`, message via `libelle_a_cheval(parts)`.

---

## Arbitrages CC (A0)

1. **Classification = GABARIT-2** (mesure à l'appui) ; lots A–C livrés sur fixtures + flag admin, contrat complet, raccordement réel déjà câblé pour cadastre/PLU/PPR/multi-zones.
2. **AN0347 est en zone N** (base) alors que le mandat la cite comme U : conservée comme parcelle nommée de recette (la classification est indépendante de la zone) ; la recette lot C ajoutera une vraie parcelle U.
3. **Adaptation CDC actée** : moteur Python back (pas Turf), contrat TS §2 → modèles pydantic `GabaritInput`/`GabaritResult` ; `build_gabarit_input(idu)` = point de raccordement unique.
4. **Risques = RÉEL** limité à la **zone rouge PPR** (≥ 50 %) ; bleu/aléas/SUP = `not_integrated` sourcés.
5. **side/rear cosmétiques** (un seul recul séparatif) : la distinction n'entre pas dans le calcul.

Commandes clés : `psql "$LABUSE_DATABASE_URL"` (lecture seule) ; `PYTHONPATH=src <venv>/python scripts/gabarit_a0_classification.py --sample`.
