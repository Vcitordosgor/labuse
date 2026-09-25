# PISCINES-2 + DENSIFIER-PLI — refonte outil Piscines · Densifier plié dans les filtres

Suite d'OUTILS-S1. Branche `feat/piscines-densifier` · worktree `~/Desktop/labuse-piscines` · ports 8485/5685 · non mergé.
Base main `952ff1ca` (OUTILS-S1 mergé). DB `postgresql://openclaw@localhost:5432/labuse`.

---

## Lot A — Piscines refait

### A.1 — Précision MESURÉE par classe (la règle en découle, pas l'intuition)

Tirage **aléatoire 30/classe, seed `p2seed7`** (`ORDER BY md5(clé || 'p2seed7')`, requête `echantillon/sample_query.sql`, tirage `echantillon/sample_detections.csv`). Chaque détection vérifiée à l'œil sur l'ortho IGN — vignettes 40 m + grilles 15/image dans `echantillon/grid_*.jpg` (verdict vraie / fausse / douteuse). Bornes de décision : **servie ≥ 85 %**, **à confirmer 50–85 %**, **écartée < 50 %** (précision « douteuses exclues »). Détail : `echantillon/precision_par_classe.csv`.

| Classe (n=30) | vraie | fausse | douteuse | Précision (doute exclu) | Wilson 95 % | **Statut** |
|---|---|---|---|---|---|---|
| FLAIR haute (≥0,80) | 30 | 0 | 0 | **100 %** | [89–100] | **servie** |
| FLAIR incertaine (<0,80) | 27 | 1 | 2 | **96 %** | [82–99] | **servie** |
| CoSIA confirmée **avec** FLAIR ≤5 m | 30 | 0 | 0 | **100 %** | [89–100] | **servie** |
| CoSIA confirmée **sans** FLAIR | 26 | 0 | 4 | **100 %** (strict 87 %) | [87–100] | **servie** |
| CoSIA rare sans FLAIR | 4 | 16 | 10 | **20 %** | [8–42] | **écartée** |
| CoSIA probable **≥ 8 m²** sans FLAIR | 9 | 6 | 15 | **60 %** | [36–80] | **à confirmer** |
| CoSIA probable **< 8 m²** | 1 | 22 | 7 | **4 %** | [1–21] | **écartée** |

**Constats.** FLAIR (haute ET incertaine) = fiable → les 478 « incertaines » sont majoritairement de vraies piscines. CoSIA « confirmée » fiable qu'elle recoupe FLAIR ou non (vraies piscines que FLAIR a manquées : eau sombre/couverte). CoSIA « rare » = surtout des **toitures rouges/métalliques et terrains de sport** (couleur proche). CoSIA « probable » : **le plancher 8 m² sépare le bruit** (< 8 m² = 4 % : spas, reflets, bâches) **de l'ambigu** (≥ 8 m² = 60 % : petites piscines / couvertes / tarps — d'où « à confirmer »). Le plancher est **justifié par la distribution mesurée**, pas posé.

**Règle de fusion (statut) qui en découle :**
- **servie** : `flair` (haute/incertaine) · `flair+cosia` (concordance ≤5 m = confirmation) · `cosia` `confirmee`.
- **à_confirmer** : `cosia` `probable` **≥ 8 m²** sans FLAIR.
- **écartée** : `cosia` `rare` · `cosia` `probable` **< 8 m²**.

### A.2 — Source unique fusionnée `piscines`

Table `piscines` (`src/labuse/ingestion/piscines_fusion.py`) + CLI **`labuse piscines-build`** (idempotent, injection humaine). FLAIR (servi : `validation='ok'` ∪ juge FLAIR≥0,30 × probe≥0,50, comme `parcel_equipements`) ∪ CoSIA (`tuyau_piscines`), **dédoublonnées par jointure spatiale 5 m** (une CoSIA à ≤5 m d'une FLAIR → portée par la ligne FLAIR, `source='flair+cosia'`). Colonnes : `idu` (jointure spatiale au cadastre), `commune`, `surface_m2`, `source`, `classe`, `statut`, `confiance`, `geom`/`geom_2975`, `millesime_flair/cosia`. Les corrections `piscine_corrections` (par idu) s'appliquent. **Les deux anciennes tables (`parcel_equipements` piscine, `tuyau_piscines`) restent en base mais ne sont plus lues** par l'outil, la carte ni la fiche.

**Build LIVE (`labuse piscines-build`, 3 s) : 50 516 piscines.**

| statut | total | par source |
|---|---|---|
| **servie** | **12 576** | flair+cosia 8 366 · cosia (confirmée) 4 160 · flair seul 50 |
| à confirmer | 11 706 | cosia (probable ≥8 m²) |
| écartée | 26 234 | cosia (rare 4 326 + probable <8 m² 21 908) |

Servie par commune (top) : Saint-Paul 2 376 · Saint-Denis 1 766 · Saint-Pierre 1 444 · La Possession 876 · Le Tampon 763 · Saint-Louis 667. (~99 % des lignes ont un `idu` ; les rares hors parcelle — voirie — restent en base, écartées du listing.)

### A.3 — L'écran (proposition B.4 réalisée, deux réserves de Vic honorées)

- **Endpoints** `/modules/prospection-piscines` (agrégat), `/points` (carte), **`/liste` (nouveau)** : lisent `piscines`, statut `servie` par défaut, `+ a_confirmer` sur bascule, corrections exclues. Moteur nommé `n_piscines` (`compte_piscines`) rebranché sur `piscines`.
- **En-tête** « 💧 Piscines — à équiper » + phrase pisciniste (chauffage solaire, couverture/volet, PAC, entretien).
- **Liste par commune** : parcelle · surface bassin · **source** (FLAIR/CoSIA/FLAIR+CoSIA) · **statut** · **propriétaire** (PM : dénomination + SIREN ; PP : « particulier — non nommé », doctrine). **Aucune colonne ni tri « potentiel solaire ».**
- **Filtres** : commune (drill) · statut (bascule « inclure à confirmer ») · surface min · **propriétaire PM/PP**.
- **Réserve n°2** (81 % des propriétaires = particuliers non nommés) → **seul geste de sortie = Courrier « à l'occupant »** : sélection de piscines → « ✉ Écrire aux occupants → » ouvre le Courrier propriétaire pré-rempli.
- **« Pas une piscine » = Chip** explicite (plus un lien-texte) : écrit `piscine_corrections`, retire de la liste + carte, « Annuler » en session.
- **Carte** : une seule couche « Piscines » (points de `piscines` servie, goutte d'eau, clic → fiche). L'ancienne « Piscines (CoSIA) » était **déjà hors panneau strip** (recette antérieure `panneau_general=False`) → rien à retirer ; label vestigial nettoyé dans `layers.ts`.
- **Fiche** : la section Équipements (« Piscine détectée ») ET le croisement de la fiche soleil lisent la **même table `piscines`** (vérifié LIVE : `97415000CZ0238` → « Piscine détectée — 1 bassin · FLAIR ∪ CoSIA »).

Captures : `captures/apres_piscines_synthese.png`, `captures/apres_piscines_liste.png`. Tests adaptés (fixture `piscines`, bandes statut, `liste.total == compteur.total`).

---

## Lot B — Densifier plié dans les filtres

### B.1 — Case « Déjà bâti » dans le groupe Capacité
- Le filtre booléen `renouvellement` (clé legacy conservée pour les vues enregistrées, hash `rnv`) est
  **repointé** : il ne lit plus le précalcul figé `parcel_renouvellement` mais le **bâti existant BD TOPO**
  (`EXISTS p_model_bati WHERE emprise_bati_m2 > 0`, `app.py:1591`). Exposé en **case « Déjà bâti (extension ·
  surélévation) »** dans la section **Capacité** de `FiltreLabuse.tsx`, à combiner avec **« SDP restante ≥ X »**
  (`sdpMin`, qui lit `parcel_residuel` du **run servi 10** — la même SDP que la fiche).
- Entre dans le **hash/URL** (`rnv`), **Mes vues** (via `filtersToHash`) et le **badge « Filtres (N) »** (déjà
  dans `F_BOOLS`). Compteur SQL par `/filtre` (unifié). Capture : `captures/apres_filtre_deja_bati.png` (badge
  « 2 actifs » = Déjà bâti + SDP ≥ 200).

### B.2 — Outil « Densifier l'existant » retiré du menu (17 → 16 outils)
- Entrée `renouvellement` retirée de `registry.ts` → **16 outils** (verrou `test_v5f_vert_sur_les_16_outils`
  mis à jour, LIVE `captures/apres_menu_16_outils.png` : 16 tuiles, `renouvellement` absent).
- Composants retirés : `DensifierTablePanel` (App.tsx), `RenouvellementModule` (ModulePanel.tsx), fichier
  `Renouvellement.tsx` + `DensifierTable.test.tsx` supprimés, badge fiche « Densifier — rang N/M » retiré.
- **Redirections vers le filtre** : la porte fiche §Potentiel « Densifier l'existant → » et **tout** lien vers
  le module (Copilote « densifier », deep-link) passent par `setModule('renouvellement')` qui **ouvre désormais
  le panneau Filtre** (Capacité) avec **« Déjà bâti » coché + « SDP restante ≥ 200 m² » pré-rempli**, scopé sur
  la commune. La route Copilote `densifier → renouvellement` (testée) reste donc valide, mais atterrit sur le filtre.

### B.3 — `parcel_renouvellement` / `labuse renouv` : plus lus par aucun écran
- Les **trois** lecteurs frontend du précalcul figé sont retirés : l'outil (`/renouvellement/liste`), le badge
  fiche (`f.renouvellement`), le **calque carte** (`getRenouvGeojson` → `/map/renouvellement.geojson`). `getRenouvListe`,
  `getRenouvGeojson`, `RenouvItem/RenouvListe/RenouvFC` supprimés d'`api.ts`.
- **La table `parcel_renouvellement` est CONSERVÉE en base** (aucune suppression), ainsi que les endpoints backend
  `/renouvellement/liste`, `/map/renouvellement.geojson` et `_renouvellement_block` — simplement **plus servis à
  aucun écran**. **`labuse renouv` n'est plus une routine d'exploitation** : aucune doc active ne le référence
  (les mentions restantes sont des rapports d'archive historiques `docs/archive/…` et `docs/mandats/…`, non modifiés).

### B.4 — Compte « Déjà bâti + SDP ≥ 200 » vs l'ancien segment (67 260)

| Mesure (run servi) | Compte |
|---|---|
| `parcel_residuel` (run 10) total | 431 663 |
| Déjà bâti (BD TOPO emprise > 0) | ~329 152 |
| SDP restante ≥ 200 m² | 69 145 |
| **Déjà bâti + SDP ≥ 200 m²** (filtre LIVE `/filtre`) | **60 690** |
| Ancien segment `parcel_renouvellement` (q_v11_m137) | 67 260 |

**Écart 67 260 → 60 690 (−6 570, −10 %) expliqué :** (1) **run** — l'ancien segment lit `p_model_ext_dataset`
(snapshot q_v11_m137) ; le filtre lit `parcel_residuel` du **run servi 10 (q_v15 assiette gabarit)**, dont la
géométrie a modifié les résiduels. (2) **Périmètre** — l'ancien segment appliquait en plus zone U/AU, **hors
copropriété, hors foncier public**, et une **SDP nette** (contraintes déduites) au seuil mixte (> 100 m² ou surface
≥ 600) ; le filtre « Déjà bâti + SDP ≥ 200 » est plus simple (SDP brute résiduelle, sans exclusion copro/public).
Le nombre **60 690 est le compte vivant du run servi**, aligné sur la fiche.

---

## Vérification

| Contrôle | Résultat |
|---|---|
| `tsc --noEmit` | **0 erreur** |
| `vite build` | **exit 0** |
| `vitest run` | **184/184** (188 − 4 tests `DensifierTable.test.tsx` supprimés) |
| pytest (piscines/solaire/fiche/compteurs/filtres/copilote/verrous/renouv) | **verts** (49 + 12 + …) |
| `labuse piscines-build` LIVE | 50 516 piscines en 3 s |
| filtre « Déjà bâti + SDP ≥ 200 » LIVE | 60 690 (== recompte SQL) |
| menu outils LIVE | **16** (renouvellement absent) |
| verrou CIRCUIT `test_lot1_tables` | **V1a levé** ; `piscines` inscrite à la carte (fabrications, `registre/tables.py`) → retirée des orphelines |

**Verrous/garanties — triage honnête.** Le balayage large (12 min, 417 passed) a laissé 5 échecs, tous **triés** : `test_lot1_tables` V1a/V1c signalait `piscines` orpheline lue hors carte → **corrigé** (inscription CIRCUIT). Restent, **pré-existants et hors mandat** : `test_garanties` g2/g5/g6 (`etat_reservoir({})` rend `("gris","jamais vérifiée")` vs attendu `("rouge","jamais vérifié")` — dérive de libellé du module santé-source, jamais touché) ; V1c orphelines `mvt_tile_cache` + `taxe_amenagement_secteur` (table de la session taxe non mergée). Aucun de ces échecs ne provient de ce mandat (tous les tests couvrant les changements — filtres, copilote, verrou 16 outils, piscines, compteurs, fiche — sont verts).

## Captures (`docs/audit-2026-09/piscines-2/`)
- `echantillon/grid_*.jpg` (7 classes × 2), `echantillon/precision_par_classe.csv`, `echantillon/sample_*.{csv,sql}`.
- `captures/apres_piscines_synthese.png`, `captures/apres_piscines_liste.png`.
- `captures/apres_menu_16_outils.png`, `captures/apres_filtre_deja_bati.png`.

## Hors mandat (non touché)
Le Courrier lui-même · le scoring (`piscine_signal.py` déclassement, intact) · les autres outils · suppression des
anciennes tables (`parcel_equipements`, `tuyau_piscines`, `parcel_renouvellement` conservées) · merge.
