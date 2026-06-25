# Réconciliation parcellaire LABUSE vs Cadastre Etalab officiel (974) — millésime mars 2026

> **Preuve de complétude parcellaire.** Audit **strictement lecture seule** prouvant que LABUSE contient
> **100 % des parcelles cadastrales officielles de La Réunion** pour le millésime audité — vérifié **parcelle
> par parcelle (IDU)**, pas seulement en volume. **Verdict : 🟢 GO — 100 % aligné, delta 0 sur 24/24 communes.**

## Objectif

Trancher : *les 431 663 parcelles LABUSE correspondent-elles à 100 % des parcelles cadastrales officielles de
La Réunion ?* Et si non, identifier les écarts par commune et par IDU. **Réponse : oui, à 100 %, sans aucun écart.**

## Source officielle & millésime

| | |
|---|---|
| **Source** | Cadastre Etalab (DGFiP / data.gouv.fr) |
| **URL** | `https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/974/<insee>/cadastre-<insee>-parcelles.json.gz` |
| **Format** | GeoJSON gzippé, une `Feature` par parcelle ; IDU = `properties.id` (14 caractères) |
| **Millésime audité** | **`latest` = millésime mars 2026** (`last-modified` 2026-03-28 / 2026-03-29) |
| **Cohérence millésime** | **stable** : tailles des fichiers identiques à celles vues lors des imports LABUSE (2026-06-20 → 2026-06-25) → **même millésime des deux côtés** |
| **Périmètre** | 24 INSEE officiels **97401–97424** (= référentiel complet La Réunion, 24 communes) |

## Méthode (read-only)

1. **Inventaire LABUSE** par commune depuis la base : `count(*)`, `count(DISTINCT idu)`, doublons IDU, `geom` nul,
   `geom_2975` nul. Résultat : **0 doublon, 0 géométrie nulle** sur les 24 communes.
2. **Inventaire officiel** : téléchargement des 24 fichiers per-commune (~54 Mo au total), extraction des IDU en
   streaming (`zcat | jq -r '.features[].properties.id'`), tri + dédoublonnage.
3. **Comparaison ensembliste des IDU** commune par commune via `comm` (et non un simple comparatif de volumes) :
   - `comm -23 officiel labuse` → IDU officiels **absents** de LABUSE (manquants) ;
   - `comm -13 officiel labuse` → IDU LABUSE **absents** de l'officiel (surplus).

> La comparaison porte sur les **identifiants parcellaires exacts**, garantissant qu'il n'y a ni parcelle
> officielle oubliée, ni parcelle fantôme dans LABUSE — au-delà d'une simple égalité de comptes.

## Résultat global

| | Officiel 974 | LABUSE | Delta |
|---|---:|---:|---:|
| **Parcelles** | **431 663** | **431 663** | **0** |
| IDU distincts | 431 663 | 431 663 | 0 |
| IDU officiels manquants dans LABUSE | — | — | **0** |
| IDU LABUSE en surplus / hors officiel | — | — | **0** |
| Doublons IDU (LABUSE) | — | — | **0** |

## Tableau des 24 communes

| INSEE | Commune | Parcelles officielles | Parcelles LABUSE | Delta | Manquants | Surplus |
|---|---|---:|---:|---:|---:|---:|
| 97401 | Les Avirons | 8 611 | 8 611 | 0 | 0 | 0 |
| 97402 | Bras-Panon | 6 041 | 6 041 | 0 | 0 | 0 |
| 97403 | Entre-Deux | 6 312 | 6 312 | 0 | 0 | 0 |
| 97404 | L'Étang-Salé | 9 070 | 9 070 | 0 | 0 | 0 |
| 97405 | Petite-Île | 13 137 | 13 137 | 0 | 0 | 0 |
| 97406 | La Plaine-des-Palmistes | 6 450 | 6 450 | 0 | 0 | 0 |
| 97407 | Le Port | 10 195 | 10 195 | 0 | 0 | 0 |
| 97408 | La Possession | 13 338 | 13 338 | 0 | 0 | 0 |
| 97409 | Saint-André | 22 600 | 22 600 | 0 | 0 | 0 |
| 97410 | Saint-Benoît | 21 671 | 21 671 | 0 | 0 | 0 |
| 97411 | Saint-Denis | 38 138 | 38 138 | 0 | 0 | 0 |
| 97412 | Saint-Joseph | 28 959 | 28 959 | 0 | 0 | 0 |
| 97413 | Saint-Leu | 22 959 | 22 959 | 0 | 0 | 0 |
| 97414 | Saint-Louis | 29 241 | 29 241 | 0 | 0 | 0 |
| 97415 | Saint-Paul | 51 129 | 51 129 | 0 | 0 | 0 |
| 97416 | Saint-Pierre | 42 425 | 42 425 | 0 | 0 | 0 |
| 97417 | Saint-Philippe | 4 162 | 4 162 | 0 | 0 | 0 |
| 97418 | Sainte-Marie | 16 746 | 16 746 | 0 | 0 | 0 |
| 97419 | Sainte-Rose | 6 287 | 6 287 | 0 | 0 | 0 |
| 97420 | Sainte-Suzanne | 12 527 | 12 527 | 0 | 0 | 0 |
| 97421 | Salazie | 7 035 | 7 035 | 0 | 0 | 0 |
| 97422 | Le Tampon | 42 756 | 42 756 | 0 | 0 | 0 |
| 97423 | Les Trois-Bassins | 5 314 | 5 314 | 0 | 0 | 0 |
| 97424 | Cilaos | 6 560 | 6 560 | 0 | 0 | 0 |
| **TOTAL** | **24 communes** | **431 663** | **431 663** | **0** | **0** | **0** |

## Verdict : 🟢 GO — 100 % aligné

**LABUSE contient 100 % des parcelles cadastrales officielles du millésime audité** (Cadastre Etalab « latest »,
mars 2026), pour les **24 communes de La Réunion**, **sans aucun écart** (ni manquant, ni surplus, ni doublon),
**égalité vérifiée IDU par IDU**. Aucune cause d'écart à investiguer (millésime différent, changement cadastral,
source alternative, bug d'import, doublon, format IDU) : toutes écartées par l'égalité ensembliste exacte.

## Phrase commerciale (défendable)

> **« LABUSE recense l'intégralité des parcelles cadastrales de La Réunion : 431 663 parcelles sur les
> 24 communes du département, soit 100 % du cadastre officiel (source DGFiP / Cadastre Etalab, millésime
> mars 2026), vérifié parcelle par parcelle. »**

## Limite

- **Valable pour le millésime mars 2026** (Cadastre Etalab `latest` au moment de l'audit, `last-modified`
  2026-03-28/29). Le cadastre évolue (~trimestriellement) : **re-vérifier à chaque nouveau millésime cadastral**
  pour maintenir le « 100 % ». Une dérive future serait une mise à jour officielle non encore re-synchronisée, pas
  un défaut d'import.
- La complétude prouvée ici porte sur la **présence des parcelles** (couverture), distincte de la **profondeur
  d'analyse** : 2 communes (Saint-Leu, Saint-Philippe) sont présentes mais non encore évaluées (PLU absent du GPU).

---

### Provenance (lecture seule)

- Aucune mutation : `SELECT` sur `parcels` (inventaire + IDU) ; téléchargement read-only des 24 fichiers officiels ;
  comparaison hors base (fichiers temporaires hors dépôt). DB inchangée (431 663 / 24 communes / 17 gold).
- Aucun import, aucune re-cascade, aucun passage gold, aucun changement code/config/scoring, aucun écart corrigé.
