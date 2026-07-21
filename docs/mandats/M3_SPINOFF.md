# M3 — SPIN-OFF VUES + SOLAIRE : rapport (STOP final)

Deux branches, deux destins :
- **Archive** : `spinoff/vues-solaire` (commit `8f87e36`) + tag **`avant-spinoff-vues-solaire`** — pushés
  AVANT le premier retrait. Jamais mergée, jamais supprimée. Inventaire exhaustif :
  **`docs/spinoff/INVENTAIRE_VUES_SOLAIRE.md`** (tables + volumes, API, 8 modules d'ingestion, 9 CLI,
  front, configs, tests, ligne de coupe partagé/exclusif, checklist de reconstruction 6 mois).
- **Travail** : `fenetre/m3-retrait` (2 commits : `cf4d5af` front, `ed05aa4` back) — à merger par Vic.

## Ce qui a été retiré (code + exposition)

**Front** (`cf4d5af`) : `SolaireTab` (80 l.) + onglet « Solaire » — **Faisabilité occupe sa place dans la
nav** (ordre final : Synthèse · Règles · Risques · Marché · Proprio · **Faisabilité** · Bilan, comme prévu
M11 Surface C) ; couches carte vue mer + toggle + checkbox filtre + chip + badge ◠ + param URL ; modules
M23 Parkings APER / M24 Toitures tertiaires ; helpers API ; exemples NL « vue mer » ; presets SegmentsPage.

**Back** (`ed05aa4`) : routeur `/solaire` ; `vue_mer()` d'enrichment + bloc fiche ; param `vue_mer`
traversant de app.py (listes, exports, découverte) + SELECT/JOIN ; filtres NL (copilote + nl_semantics) ;
bonus vue mer du bilan (+ paramètre calibrable) ; `prime_vue_mer` modules ; 8 modules d'ingestion solaire
+ `parkings_aper` + pont végétation→solaire (`flag_solaire`) ; 9 commandes CLI + `warm-vue-mer` ; settings
PVGIS/Google Solar + `habitat_solaire.yaml` + presets seed `pv-residentiel`/`chauffe-eau-solaire` ;
FilterDefs/tris/exports segments ; DDL `parcel_vue_mer` ; entrées seed data_sources (PVGIS, EDF SEI, ODRÉ).

## Ce qui reste volontairement

| Élément | Pourquoi |
|---|---|
| **Toutes les tables** (`parcel_solar` 431 663 · `parcel_vue_mer` 150 643 · `solar_grid` · `parkings_aper` · `pv_registry` · MV tertiaires · 13 backups vuemer) | **Données intouchées** — elles dorment, prêtes pour le spin-off |
| `_alti_sample_points`/`_alti_query` + `exposition()` (enrichment) | Partagés (orientation cardinale, hors spin-off) |
| Couche `trait_de_cote` | Partagée (50 pas, littoral, cascade) |
| `ortho_pv.py` / `pv_detection.py` (+ « CES probable » fiche) | Module **Détection Ortho** (équipements toiture), pas le spin-off |
| Signaux `aper_deadline` en base (1 466) + leurs labels d'affichage (carnet O7, enums) | Données existantes ; la **génération** future est partie |
| Payloads `parcel_enrichment` en cache contenant un champ `vue_mer` | Cache = données ; champ ignoré (aucun code ne le lit/affiche) |
| Commentaires citant `parcel_solar` comme exemple de « source absente » (segments) | C'est le mécanisme voulu : table dormante = filtre grisé proprement |
| « protection solaire » (RTAA DOM), « chauffe-eau solaire probable » (ortho) | Homonymes hors périmètre |

## État golden / sentinelles

**GOLDEN 116/116 PASS, 0 FAIL — AUCUN changement de harnais.** Vérifié contre le **nouveau code** (instance
de la branche démarrée sur :8011, `LABUSE_API_BASE` pointé dessus) : la face DB de `golden_check.py` lit
`parcel_vue_mer`/`parcel_solar` **qui restent en base**, et la face API ne comparait aucun champ
vues/solaire (commune, surface, statut, scores, zonage, cascade, score V, copro, DVF, SIREN). Le gel des
triplets est intact.

## Vérifications

- **Suite complète : 1 072 verts / 0 rouge** (17 skips préexistants). Tests partis dans l'archive :
  `test_habitat_solaire.py`, `test_vue_mer.py`, `qa/e2e_habitat_solaire.mjs`. Tests **adaptés** (même
  mécanique, exemple non-solaire — documenté dans chaque test) : `test_nl_semantics` (booléen inventé →
  `veille`), `test_ux_v1` (cas NL vue mer retiré), `test_segments` (contrat presets sans les 2 slugs
  solaire ; disponibilité sans `score_solaire` ; badge « partiel » démontré sur le preset piscines),
  `test_vegetation` (test du pont `flag_solaire` retiré ; assertion preset PV retirée).
- **Front** : `tsc --noEmit` propre, `vite build` OK. Grep résidus front = 0 (hors homonymes légitimes).
- **Fiche API** : aucun résidu vues/solaire dans la réponse ; bloc `faisabilite` présent et non nul.
- **Nav** : la fiche passe de 8 à 7 onglets (+ « Pourquoi pas ? » conditionnel R5), Faisabilité à la place
  de Solaire. **Validation visuelle en local = Vic** (captures remplacées par ses yeux, comme aux
  reliquats ; harnais de capture = finding déjà noté au mandat précédent).

## Interdits respectés
- Zéro donnée supprimée, zéro réécriture d'historique ; l'archive était pushée **avant** le premier retrait.
- Aucune amélioration opportuniste. Envies notées pour plus tard : (1) `conso_baseline_commune` (EDF SEI)
  n'a plus d'usage actif — candidate à documentation « dormante » au même titre ; (2) `tarif_elec_eur_kwh`
  retiré avec le module — si un futur outil énergie en a besoin, il vit dans l'archive.

**STOP final** — Vic vérifie la fiche en local, merge `fenetre/m3-retrait`, et **la fenêtre pré-M7 est
VIDE : M7 se déclenche.**
