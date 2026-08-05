# M28 — PHASE A : IMPLÉMENTATION + MESURE À BLANC — POINT D'ARRÊT 1 (05/08/2026)

> Rien de servi ne bouge : mesure q_v12_m28 (prev/étage 0 = q_v8_calibre, lignes runs
> retirées). Étiquettes Sourcé/Estimé/Absent ; fraîcheurs = source amont.

## ÉCART A3 SIGNALÉ (à valider) : coeff_recul n'existe dans AUCUNE fiche calibration
Substitution implémentée, point de calcul unique : divisible = commune CALIBRÉE (fiche
calibration présente, 21 communes) ET zone U/AU ET (surface − emprise_max) ≥ 600 m² (le
plancher local déjà défini). Non calibrée → Absent, badge non servi. **Ton arbitrage.**

## Implémenté (kill-switches, rien de servi)
1. Filtre 3 étages (`faisabilite/filtre_bati.py`, cache `parcel_filtre_bati`, 9 s de build) —
   ratio via `p_model_bati` (= max BD TOPO éd. 2026-06-15 / CoSIA PVA 2025, UN point) ; année
   DPE Sourcé/Absent (A2 : Absente = récente, durcit) ; tier `declasse_bati_sature` (A4,
   même chemin pour les SDP-saturées pct≥100) ; préséance après E.
2. Départage D → SDP → surface → IDU (pipeline, seed en fallback ultime documenté).
3. Badge géométrie (`parcel_geometrie`, 431 663 lignes : largeur inscriptible + Polsby-Popper,
   contrainte <8 m ou PP<0,1) — signal de fiche Sourcé (cadastre Etalab 2026-06), jamais un
   déclassement. API gatée `LABUSE_M28_BADGES=1` (inerte jusqu'à la phase B).
4. Trou cache réparé : CW1553 (SDP 160, moteur→cache) ; les 3 Salazie légitimes (hors PLU).

## FAUTE CORRIGÉE EN COURS DE MESURE (transparence)
1ʳᵉ passe : j'avais omis d'exclure les saturées du pool de calibrage n_entrée → tête fondue
à 762 sans recomposition. Fix (miroir du pattern AU existant) + re-mesure : recomposition OK.

## Mesure (q_v12_m28, 148 s)
| effectif | servi | mesure |
|---|---:|---:|
| brûlantes | 117 | **120** |
| chaudes | 1 043 | **1 033** |
| declasse_bati_sature | — | **29 872** (motivées une à une) |

Mouvements : 291 chaudes + 5 brûlantes + 135 réserve → saturées · 29 440 a_creuser →
saturées (honnêteté étendue) · recomposition : 277 a_creuser→chaude + 12 →brûlante ·
recalibrages 7+3. Top 100 : chaque mouvement avec cause dans `top100_mouvements.csv`
(filtre / recomposition / recalibrage / départage — jamais « les deux »).

## Populations demandées (`populations_filtre.csv` — 497 lignes, 497 idu distincts, zéro doublon)
- **Brûlantes au filtre : 10** (critère A1 emprise_max ≥ 20) = les **8 connues BD TOPO** + 2
  CoSIA-seul en bande 20-40 (AP1216 : BD TOPO 0/max 27 ; AD0030 : BD TOPO 11/max 24 — jamais
  déclassées par la règle E, mais dans le périmètre du filtre). CORRECTION du 1er envoi qui
  titrait « 8 » un bucket de 9 (AR1511 à part). Nominatif :

| idu | commune | ratio (max) | BD TOPO | max | année | étage | décision |
|---|---|---:|---:|---:|---|---:|---|
| 97403000AR1511 | Entre-Deux | **49,9 %** | 130 | 263 | Absent | 3 | **saturée** |
| 97409000AR1260 | Saint-André | 28,1 % | 50 | 123 | Absent | 2 | saturée |
| 97411000AD0030 | Saint-Denis | 11,1 % | 11 | 24 | Absent | 1 | servie |
| 97411000EL0201 | Saint-Denis | 29,3 % | 93 | 165 | Absent | 2 | saturée |
| 97412000AM0938 | Saint-Joseph | 11,5 % | 76 | 115 | Absent | 1 | servie |
| 97415000CX1395 | Saint-Paul | 41,8 % | 113 | 254 | Absent | 3 | saturée |
| 97416000CX1241 | Saint-Pierre | 13,3 % | 70 | 70 | Absent | 1 | servie |
| 97416000EP0908 | Saint-Pierre | 33,5 % | 103 | 161 | Absent | 2 | saturée |
| 97422000AP1216 | Le Tampon | 7,7 % | 0 | 27 | Absent | 1 | servie |
| 97422000CY0197 | Le Tampon | 28,9 % | 194 | 251 | Absent | 2 | **divisible** |

  Bilan : 4 servies · 1 divisible · 5 saturées (AR1511 incluse).
- **AR1511 — correction** : ratio A1 = **49,9 %** (emprise_max CoSIA 263 m²), pas 24,6 %
  (qui était le ratio BD TOPO seul) → étage 3 DIRECT (> 40 %), saturée.
- **432 chaudes bâties** : 129 servies (ét. 1) · 66 divisibles · 1 servie (DPE ancien) ·
  291 saturées (188 ét. 2 + 103 ét. 3).
- **CY0104 : la règle la met `declasse_bati_sature`** (étage 3, non divisible) — l'exception
  (declasse_non_constructible) peut être SUPPRIMÉE (A8) : même effet produit, mieux motivé.
- **A9 (AT0870)** : à inscrire au registre des exceptions AU GESTE DE BASCULE (phase B),
  motif « toiture visible ortho (PVA 21/07/2025) non captée par BD TOPO éd. 2026-06-15
  (3 m²) ni CoSIA PVA 2025 (5 m²) — angle mort image, pas de code » (documenté, pas appliqué
  en phase A : rien de servi ne bouge).

## Deck : `deck20_mouvements.pdf` — les 20 plus gros mouvements en tête, cartes datées
(idu, commune, tiers avant→après, rangs, ratio bâti, ortho PVA + millésime).

## Livrables (ls -la)
total 2952
drwxr-xr-x   7 openclaw  staff      224  5 aoû 12:32 .
drwxr-xr-x  47 openclaw  staff     1504  5 aoû 12:23 ..
-rw-r--r--   1 openclaw  staff     3387  5 aoû 12:32 PHASE_A_MESURE.md
-rw-r--r--   1 openclaw  staff  1403392  5 aoû 12:32 deck20_mouvements.pdf
-rw-r--r--   1 openclaw  staff     1210  5 aoû 12:23 mesure_phase_a.py
-rw-r--r--   1 openclaw  staff    84889  5 aoû 12:31 populations_filtre.csv
-rw-r--r--   1 openclaw  staff     8664  5 aoû 12:31 top100_mouvements.csv

## Arbitrages point d'arrêt 1 (Vic, 05/08)
- **Bande 20-40 / AP1216 + AD0030 : OPTION A actée** — la règle A1 tranche (elles sont dans
  le périmètre du filtre, décision 'servie' étage 1). Elles SORTENT du périmètre de
  l'adjudication manuelle bande 20-40 : l'adjudication en attente ne porte plus que sur les
  cas HORS pool filtre.
