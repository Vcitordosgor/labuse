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

## Populations demandées (`populations_filtre.csv`)
- **8 brûlantes connues** : 4 servies (étage 1 marginal) · 1 divisible · 3+1 saturées.
- **AR1511** : étage 3, **saturée** (24,6 %, année Absente→durcit, 397 m² libres < 600).
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
