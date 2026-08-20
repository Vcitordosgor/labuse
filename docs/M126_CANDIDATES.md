# M126 — LES COLONNES DES CANDIDATES : 8 SIGNAUX PRÊTS POUR M127

*Branche `feat/m126-features-candidates`. DONNÉE SEULEMENT : le modèle servi, le run et les écrans
ne lisent pas `p_model_candidates` avant M127. Grille **idu × année strictement alignée sur
`p_model_ext_dataset`** (2017-2026) = **4 316 630 lignes**. Config `config/candidates.yaml`
(rayons, fenêtres, familles, codes — rien en dur). Build : `labuse build-candidates` (~1 h).*

## LE TABLEAU DES 8 — profondeur × couverture × distribution

| # | Colonne | As-of | Profondeur source | Couverture | Distribution |
|---|---|---|---|---|---|
| 1 | `proc_collective` (+`depuis_mois`) | **DATÉE** (date_annonce < 01/01/Y) | BODACC **2008** | 19,0 % (820 650) — le reste : cause `pas_de_pm` 3 495 970 · `pm_sans_siren` 10 | TRUE **5 618** parcelle-années (rare, comme attendu) |
| 2 | `succession_indivision` | **STATIQUE consignée** (veille sans date d'événement) | snapshot RNE 2026 | 19,0 % | TRUE **71 290** (7 129 parcelles × 10) |
| 3 | `age_dirigeant` (+bins cascade) | **DATÉE par la naissance** (âge exact au 01/01/Y ; liste dirigeants = snapshot 2026 consigné) | RNE, 19 852 naissances | 5,0 % (217 563) — causes `pas_de_pm`/`dirigeant_non_date` | <55 : 69 017 · 55-64 : 54 534 · 65-74 : 56 252 · 75-84 : 32 600 · 85+ : 5 160 |
| 4 | `pm_nue_dormante` | **STATIQUE consignée** (prédicat `nu_pm` EXISTANT — chemin unique) | DGFiP 2025 | 19,0 % | TRUE **30 940** (= 3 094 parcelles ×10 — exactement la facette) |
| 5 | `division_recente` | — | — | **0 % — PRÉMISSE CORRIGÉE** | cause `filiation_cadastrale_absente` partout |
| 6 | `contagion_voisinage` (+`n_voisins`) | **DATÉE** (ventes L2 des adjacents, 24 mois < 01/01/Y) | DVF **2014** (archives M124 → fenêtres 2017-2026 TOUTES pleines) | **99,9 %** (reste : `aucun_voisin_adjacent`) | >0 : 564 032 · moyenne 3,4 % · 5,2 voisins/parcelle |
| 7 | `vente_tab_proximite` | **DATÉE** (nature DVF, rayon 300 m config, 24 mois) | DVF **2014** | **100 %** | TRUE **301 916** (7,0 %) |
| 8 | `permis_enrichi` (type/état/ancienneté/`pc_accorde_jamais_commence`) | Autorisation **DATÉE** < 01/01/Y ; **état = instantané 2026 consigné** | SITADEL 2013+ | 5,9 % (256 491) — cause `aucun_permis_anterieur` | achevé 121 768 · autorisé 60 939 · annulé 58 323 · commencé 15 461 · **PC jamais commencé 45 643** (le signal cible a du volume) |

## Les deux prémisses corrigées (mesurées, pas supposées)

1. **`division_recente` n'est pas constructible en l'état.** `division_or` détecte le **potentiel**
   de division (7 candidates revues O12 — parcelles À diviser), pas la filiation ; `parcels.origine`
   est 100 % NULL et la base n'a qu'UN millésime cadastre. La colonne existe, NULL + cause partout.
   La bâtir = **cadastre multi-millésimes** (diff des IDU entre éditions Etalab) — mandat dédié.
2. **La veille succession n'a pas de date d'événement** (prédicat score_v : SIREN confirmé ∧
   dirigeant ≥ 70 ∨ SCI dormante — instantané). Colonne STATIQUE consignée, même doctrine que les
   features `_STATIQUE` du modèle actuel. L'« indivision » réelle (Fichiers fonciers) reste
   inaccessible (convention).

## Les preuves (21 propriétés, toutes vertes)

- **As-of constructif** : chaque `proc_collective=TRUE` prouve une annonce pcl antérieure au
  01/01/Y (0 violation) ; `depuis_mois` jamais négatif ; `permis_age_mois` jamais négatif.
- **As-of arithmétique** : l'âge avance d'**exactement +1 par année** (0 écart) ; bornes 18-110
  (garde `age_implausible`).
- **As-of par recalcul exact** (échantillons 50) : contagion **0 écart** ; vente_tab **0 écart**
  contre la fenêtre stricte recalculée.
- **Contrats statiques** : succession et pm_nue constantes par idu (0 violation).
- **Aucun manquant muet** (leçon M125) : 7 × 0 NULL sans cause.
- **Grille** : différence avec p_model_ext_dataset = 0.
- Tests versionnés `tests/test_m126_candidates.py` (un par colonne ; skip honnête si table absente
  sur labuse_test — s'exercent sur la base réelle).

## Vérification servie

**Golden 0 FAIL** (86 PASS · 33 INDÉTERMINÉ env) · suite **1 619 passed** · rien de servi ne lit la
table (grep : seuls le builder et les tests). Table annexe `parcel_adjacence` (paires de contours à
≤ 0,5 m) construite une fois, réutilisable.
