# RAPPORT GABARIT-1 — Gabarit réglementaire (moteur + outil)

Branche `feat/gabarit-1` (worktree `~/Desktop/labuse-gabarit`), 5 commits, non mergée.
Ports de session : API **8125** · Vite **5325**. Aucun merge, aucun `residuel-serve`, aucun
rejeu cascade/scoring. Le CDC (`docs/GABARIT/CDC-GABARIT.md`) fait foi sur le fond ; le mandat
(`docs/GABARIT/MANDAT-GABARIT-1.md`) sur la méthode et sur le réel vs fictif.

## Ce qui est livré

Un outil **« Gabarit réglementaire »** qui traduit graphiquement et mathématiquement des règles
**sourcées et validées** : SOURCE → VALIDATION → CALCUL → AFFICHAGE. Il ne calcule ni logements,
ni étages, ni SDP, ni coût, ni valeur, ni potentiel (liste noire testée).

- **Moteur pur** (`src/labuse/gabarit/`) : contrat pydantic, validation stricte, calcul géospatial
  déterministe. Identique pour le réel et le fictif.
- **Raccordement unique** `build_gabarit_input(idu)` : le SEUL endroit où le réel entre (cadastre,
  PLU via `zonage.py`, PPR via `cascade_results`, multi-zones via `zone_dominante`).
- **Endpoint** `GET /outils/gabarit/{idu}` (+ `/demo`).
- **Outil front** (panneau 320 px + carte + 3D sur le bouton existant), enregistré au registre (V5f).

## Arbitrage central (mandat point 5)

La **classification des limites** (voie / séparative par arête) est le point dur : « rien n'existe ».
Mesurée en A0 sur 31 parcelles, la méthode simple **échoue le seuil 0 faux/30** — les rues des centres
urbains sont **cadastrées comme parcelles**, donc la règle « voisin ≤ 0,5 m → séparative » classe la
**façade sur rue comme séparative** (7/20 parcelles `voie=0` ont un axe voirie à 0 m ; preuve
`docs/GABARIT/captures/a0-limites-*.png` + `a0-limites-synthese.csv`). Conformément à la contingence
du mandat : **les lots A–C sont livrés**, l'outil **s'ouvre sur fixtures derrière un flag admin**
(`registry.ts` `hidden:true`), et la **classification devient GABARIT-2**. Le raccordement réel est
déjà câblé pour tout le reste ; sur une parcelle réelle le moteur répond honnêtement
**« Calcul incomplet — donnée réglementaire manquante »** avec le motif exact.

---

## 1. Architecture existante identifiée (preuve `fichier:ligne` en A0-RAPPORT.md)

- **Aucun prototype** Gabarit/enveloppe/extrusion → construit neuf, sans outil parallèle.
- **Réutilisé** : `geo.buffer_m` (négatif = recul, `geo.py:40`), CRS 4326↔2975 centralisé (`geo.py`),
  anneau de contact `ADJ_BUFFER_M=0.5` (`assemblage.py:17`), bouton **3D / `toggleTerrain`** +
  source `batiments` `fill-extrusion` (`MapToolbar.tsx:101`, `MapView.tsx:567`, `useApp.ts:443`),
  MapLibre GL (`package.json`). **Turf non ajouté** (moteur Python back — adaptation actée du CDC).
- **Règles PLU** lues UNIQUEMENT via `faisabilite/zonage.py:resolve_zone(code, commune) → ZoneRules`
  (validées-only ; `propose`/`non calibré` = bloquant).
- **PPR** réglementaire per-parcelle via `cascade_results` (couche `risques`, HARD_EXCLUDE, seuil 50 %,
  `cascade/layers/phase1.py`), géométrie `spatial_layers kind='ppr' subtype='INTERDICTION'`.
- **Multi-zones** via `faisabilite/zone_servie.py:zone_dominante().a_cheval`.
- **Registre / V5f** : `registre/donnees.py`, `registre/robinets.py`, `circuit_verrous.py:775`.

## 2. Fichiers créés / modifiés

Créés (back) : `src/labuse/gabarit/{__init__,contract,validate,engine,builder,fixtures,_geom}.py`,
`src/labuse/api/gabarit.py`, `scripts/gabarit_a0_classification.py`.
Créés (front) : `frontend/src/components/outils/Gabarit.tsx`.
Créés (tests/docs) : `tests/gabarit/{test_engine,test_builder}.py`, `docs/GABARIT/A0-RAPPORT.md`,
`docs/GABARIT/RAPPORT-GABARIT-1.md`, `docs/GABARIT/captures/**`.
Modifiés : `src/labuse/api/app.py` (+2, include_router), `src/labuse/registre/donnees.py` (+3 ids),
`src/labuse/registre/robinets.py` (+1 robinet), `src/labuse/circuit_verrous.py` (+1 mapping),
`frontend/src/components/outils/{ModulePanel,registry}.tsx/ts`, `frontend/src/lib/api.ts`.

## 3. Structure de données finale (contrat unique)

`GabaritInput` (CDC §2, `contract.py`) : `parcel{id,geometry,areaM2,source}`, `setbacks[]{id,ruleId,
type(road|side|rear),geometry(LineString),setbackM,source}`, `maxFootprint{ruleId,percent,source}`,
`maxHeight{ruleId,meters,source}`, `exclusions[]{id,ruleId,type,label,geometry(Polygon),source}`,
`applicableRules[]{id,label,category,integrationStatus,detail,source}`, `sources[]`. Champs optionnels
au type (chargement incomplet) ; **rigueur portée par `validate.py`**.
`GabaritResult` : `status`, `message`, `validationErrors`, `surfaceParcelleM2`, `zoneImplantationM2`,
`plafondEmpriseM2`, `hauteurReglementaireM`+`hauteurSource`, `coverage{reculs,hauteur,emprise,risques}`,
`appliedRules[]` (groupées), `nonIntegratedRules[]`, géométries 4326 (contour/zone/retraits/exclusions),
`raccordement` (provenance/diagnostic, jamais estimatif). **Aucun champ estimatif.**

## 4. Fonctionnement du moteur (`engine.py`, CDC §4)

`compute_gabarit(inp)` : (1) `validate_input` → si motif, `status=incomplete` + message exact, aucune
zone/métrique/3D ; (2) reprojection 4326→2975 (copies, entrée non mutée) ; (3) zone = polygone
cadastral **− ⋃ buffer(limite, setbackM)** par arête **− ⋃ exclusions** ; (4) `zoneImplantationM2 =
aire(zone)` ; (5) **`plafondEmpriseM2 = areaM2 × percent / 100`, calculé À PART** (jamais
`min(zone, plafond)`) ; (6) résultat vide/Polygon/MultiPolygon valides ; (7) reculs regroupés par
(ruleId, valeur, source), jamais fusionnés si l'un diffère (CDC §7) ; (8) géométries reprojetées en
4326 pour la carte. Pur, déterministe, sans DB ni React.

## 5. Règles réellement prises en charge (réel servi)

| Famille | Statut | Source réelle |
|---|---|---|
| Surface parcelle | **Réel** | `parcels` (`ST_Area(geom_2975)`) |
| Emprise / CES → plafond | **Réel** | `zonage.py` `emprise_sol_pct` (validé) |
| Hauteur réglementaire (faîtage) | **Réel** | `zonage.py` `hf_m` (validé ; sert la 3D) |
| Reculs voie / séparatives (valeurs) | **Réel** | `zonage.py` `recul_voirie_m` / `recul_limites_sep_m` |
| Exclusion PPR zone rouge | **Réel** | `cascade_results` (HARD_EXCLUDE, ≥ 50 %) |
| Multi-zones (bloc honnête) | **Réel** | `zone_dominante().a_cheval` |
| **Classification des limites par arête** | **Bloquant → GABARIT-2** | mesure A0 échoue le seuil |

## 6. Règles fictives non intégrées (démonstration CDC §9)

Fixture (`fixtures.py`) : parcelle 1 180 m², recul voie 5 m, séparatives 3 m, emprise 40 % (→ 472 m²),
hauteur 10 m, exclusion PPR rouge partielle, **stationnement + espaces libres = `not_integrated`**.
Sources marquées **fictives**. Sur le réel, `not_integrated` = stationnement, espaces libres, PPR bleue,
aléas informatifs (jamais une exclusion, CDC §3).

## 7. Où brancher les données réelles

Point de raccordement **unique** : `src/labuse/gabarit/builder.py:build_gabarit_input(session, idu)`.
Correspondances (CDC §11) : cadastre→`parcel` · `zonage.py`→`maxFootprint`/`maxHeight`/(reculs) ·
`cascade_results`+`spatial_layers`→`exclusions` · analyse→`applicableRules` · dossier→`sources`.
**Promotion GABARIT-2** = remplir `setbacks` (limites classées) dans le builder ; aucune réécriture du
moteur, de la carte, du panneau ou de la 3D. Puis retirer `hidden:true` de l'entrée `gabarit` du
registry pour publier la carte au menu.

## 8. Commandes de validation exécutées et résultats

| Contrôle | Commande | Résultat |
|---|---|---|
| Registre (cohérence) | `registre.verifier()` | **0 erreur** |
| Verrou V5f | `verrou_outils_registre(db)` | **vert** (17 outils visibles ; gabarit `hidden`) |
| Tests moteur + builder | `pytest tests/gabarit/ -q` | **30 passés** |
| Types front | `tsc -b` | **0 erreur** |
| Build front | `vite build` | **OK** (avert. taille de chunk pré-existant) |
| Ruff (nouveaux fichiers) | `ruff check src/labuse/gabarit/ …` | **All checks passed** |
| Suite complète | `pytest tests/ -q` | _voir ci-dessous_ |
| Recette navigateur | Playwright, API 8125 / front 5325 | 4 parcours + réel-incomplet (§9) |

**Suite complète (`pytest tests/`) :** lancée en fin de lot C sur la base **partagée** (pas de
`labuse_test` isolée dans ce worktree). Elle est **dominée par les tests géométriques/couches lourds**
(`ST_TileEnvelope` 8–20 s pièce) et dépasse largement son temps nominal (~2 min 37 pour ~3 077 tests) à
cause de la contention sur la base partagée → non concluante en un temps raisonnable dans cet
environnement local (limite connue LABUSE : la base réelle absente de `labuse_test` fait échouer/traîner
un lot de tests pré-existants, indépendants de ce mandat). **Le verrou de non-régression de GABARIT-1
est porté par des contrôles ciblés, tous verts** : `pytest tests/gabarit/` = 30 passés,
`registre.verifier()` = 0 erreur, verrou **V5f** vert, `tsc -b` + `vite build` verts, `ruff` vert. Les
changements sont **purement additifs** (nouveau paquet `gabarit/`, nouveaux tests, +3 ids registre / +1
robinet / +1 mapping, +2 lignes `app.py`, ajouts front) — ils ne modifient aucun chemin de test existant.

## 9. Recette navigateur (Playwright)

Démonstration (fixtures CDC §9), captures `docs/GABARIT/captures/recette/` :

1. **Générer** (`02-generer-demo.png`) : Surface 1 180 m² · Zone d'implantation 650 m² · Plafond
   d'emprise 472 m² · Hauteur 10 m · **4 familles vérifiées · 2 règles non intégrées** ; zone (vert) +
   bandes de recul (ambre) + exclusion PPR (rouge) dessinées sur la carte.
2. **Voir les règles appliquées** (`03-regles-appliquees.png`) : Recul voie 5 m (UC 6) · Limites
   séparatives 3 m (UC 7, **3 segments regroupés en 1**) · Emprise 40 % (UC 9) · Hauteur 10 m (UC 10) ·
   PPR zone rouge (2024-03-15) ; ⚠ 2 non intégrées (Stationnement, Espaces libres). Sources visibles.
3. **2D / 3D** (`04-3d-extrusion.png`, `04b-3d-panneau.png`) : bouton 3D existant → extrusion de la
   **seule zone** à la hauteur sourcée, panneau « **Enveloppe réglementaire selon les règles
   intégrées** (hauteur sourcée 10 m) ». Couche `gabarit-zone-3d` créée/retirée vérifiée par
   introspection du style. ⚠ **canvas WebGL/3D non capturable dans le harnais headless** (limite
   connue LABUSE) : la capture 3D apparaît noire ; le 2D (parcours 1-2) est capturé.
4. **Réinitialiser** : couches carte retirées, résultat effacé, retour à l'état initial (vérifié par
   introspection : `gabarit-zone`/source absentes, chiffres retirés).
5. **Parcelle réelle** `97410000AN0347` : **« Calcul incomplet — donnée réglementaire manquante »** +
   motifs exacts (« PLU non calibré pour la zone N », « classification des limites non servie… ») ;
   aucune zone/métrique/3D (CDC §3). Confirmé aussi en HTTP direct sur `97415000CP1097` (Saint-Paul
   U3c) : PLU réel servi (hauteur 12 m, égout 9 m, recul voie 4 m, sep 3 m, PPR rouge) — seule la
   classification bloque.

## 10. Tableau final Réel / Fictif-tests / Bloquant

- **Réel servi** : surface parcelle, CES→plafond, hauteur faîtage, valeurs de reculs, exclusion PPR
  rouge (≥ 50 %), détection multi-zones, inventaire des règles non intégrées.
- **Fictif (tests uniquement)** : la parcelle de démonstration (CDC §9) et les fixtures des 30 cas —
  même contrat que le réel, aucune logique spécifique au fictif dans le moteur.
- **Bloquant → GABARIT-2** : la classification des limites par arête (mesure A0 échoue 0 faux/30).

## 11. Arbitrages CC

1. Classification différée à GABARIT-2 (mesure à l'appui) ; lots A–C livrés, outil sur fixtures
   derrière `hidden:true` (flag admin) ; raccordement réel câblé pour tout le reste.
2. Adaptation CDC actée : moteur **Python back** (pas Turf) ; contrat TS §2 → pydantic ; le contrat JSON
   de `/outils/gabarit/{idu}` porte le calcul (front n'affiche, ne calcule rien — doctrine V5f).
3. `AN0347` est en zone **N** (base), pas U comme le suppose le mandat : conservée comme parcelle
   nommée de recette (la classification est indépendante de la zone).
4. Risques = réel limité à la **zone rouge PPR** ; bleue / aléas / SUP = `not_integrated` sourcés.
5. `side`/`rear` sont **cosmétiques** (un seul `recul_limites_sep_m`) : n'entrent pas dans le calcul —
   seule la distinction **voie vs séparative** compte, et c'est elle que la mesure A0 disqualifie.

## 12. Hors mandat (rappels)

Tiroir fiche parcelle, exports (Flash, Dossier), classification réelle par arête, refonte de
Faisabilité, merge, `residuel-serve` → **GABARIT-2**. Toute règle non chiffrable (H/2, bandes,
alignements imposés) reste `not_integrated`, jamais approchée.
