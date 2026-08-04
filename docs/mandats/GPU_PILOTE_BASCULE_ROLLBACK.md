# BASCULE GPU-PILOTE — journal & rollback (04/08/2026)

**Arbitrage Vic (04/08/2026).** Bascule du run servi **`q_v7_defisc` → `q_v9_apres`**.

## Ce que porte q_v9_apres
Rebuild unique du 04/08 : les 4 correctifs (ingestion `zone_lib` = 1er token `attrs.libelle` ;
2.2 `normalize_zone` ; 2.3 `_OUVERTURE_KW` resserré ; calibration ouverture Saint-Benoît) +
re-classif `au_statut` des 5 communes calibrées. Scoré à blanc, étage0 `q_v8_calibre`, prev `q_v8_calibre`.

## Mesure (à blanc, avant exceptions)
- Effet net île : `declasse_au_statut_inconnu` 713→560 (Saint-Benoît dé-déclassé) ; brûlante 119→119.
- **Score-neutre** : arène churn=0, RR@1158 et `p_raw` identiques → correctif de classification, pas de modèle.
- Golden 116/116 présents. 5 gardes OK (complétude 431663/0 NA, hystérésis, disque, code-sur-main, péremption AU <180j).

## Exceptions tracées (`served_run_exceptions`)
| idu | commune | origine | servi | motif |
|---|---|---|---|---|
| 97413000CX2555 | Saint-Leu | brulante | **chaude** | au_sous_plancher manque 94% — en attente pondération (dette #12) |
| 97414000CH1893 | Saint-Louis | brulante | **declasse_non_constructible** | bâti non capté par la couche batiment — angle mort dette #4, vérifié ortho 04/08 |

Tiers servis finaux : brûlante **117**, chaude 1042, a_creuser 63466, réserve 3092,
declasse_au_statut_inconnu 560, declasse_zone_fermee 2804, declasse_non_constructible 6169,
declasse_au_fermee 58, ecartee 354355. **Total 431663.**

## ROLLBACK (si régression)
1. `src/labuse/scoring/score_v_constants.py` : rétablir `Q_A_RUN_LABEL` défaut `"q_v7_defisc"`.
2. Rebuild tuiles sur le run rétabli : `build_mvt_table(s, "q_v7_defisc")` (+ `mvt_meta.run_label`).
3. `q_v7_defisc` est CONSERVÉ intact (431663 lignes) → rollback immédiat, aucune reconstruction de score.
   Les exceptions restent dans `served_run_exceptions` (historique) ; sans effet si q_v7_defisc redevient servi.

## Jetables purgés post-bascule
`q_v8_au_avant/apres/apres2/fix`, `q_v9_avant`. **Conservés** : `q_v9_apres` (servi), `q_v8_calibre`
(référence calibration), `q_v7_defisc` (hystérésis rollback).
