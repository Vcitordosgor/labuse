# AUDIT 4 — P ET C : composantes, poids, calibré vs hérité (+ mesure filtre client bâti)

## P — le modèle gelé
- Artifact `m36-l2f-2026` (joblib), **gelé le 12/07/2026**, sha vérifié à chaque run (refus
  si mismatch). Verdict de promotion : walk-forward 6 folds, RR@1158 = 6,9-11,0 (fold 2025 :
  6,73 vs 2,91 pour M3) — consigné au manifeste FREEZE-scoring2026.json.
- **Calibré à chaque run** : l'intercept SEUL (recalage sur la dernière année labellisée).
- **Hérité (gelé)** : binning + coefficients + calibration — re-train = décision humaine
  annuelle. 28 features (prix/rotation secteur, tenure, permis, densité, canopée, pente,
  zone, piscine…), toutes DISCRÉTISÉES → cf. audit 1 (paliers).

## C — le plancher
- Règle : SDP résiduelle > 0 OU surface ≥ 600 m² en U/AU (branche RNU : PAU + 600).
  **Hérité** du mandat 2.2 (600 ≈ division R+1 locale) — jamais recalibré depuis.
- SDP : chaîne `parcel_residuel` matérialisée à la bascule v8 — voir audit 6 pour sa
  limite sur les bâties.

## MESURE DEMANDÉE — les bâties-connues en tête : qui les porte ?
État post-bascule : **8 brûlantes** (p moyen 0,129, meilleur rang 48) et **432 chaudes sur
1 043 (41 %)** (p moyen 0,066, meilleur rang 33) ont une emprise BD TOPO ≥ 20 m².
Top features agrégées (top5 des 440) :
| feature | présence | log-hazard moyen |
|---|---:|---:|
| permis_bin (< 2 ans surtout) | 238 | **+1,27** |
| tenure_bin (ancienneté mutation) | 239 | +0,55 |
| **piscine** | 129 | **+0,41** |
| tenure×permis | 260 | +0,21 |
| zone_plu | 155 | +0,17 |

**Lecture** : elles sont portées par l'ancienneté de mutation/permis (momentum du secteur) —
des signaux INDIFFÉRENTS à l'état bâti de LA parcelle — et, ironie mesurée, la feature
`piscine` (+0,41 sur 129 d'entre elles) BONIFIE des parcelles déjà construites (la piscine
est un proxy patrimonial dans le modèle, pas un signal de disponibilité). Le futur filtre
client bâti devra donc être une RÈGLE produit (ratio/année/divisibilité), pas un poids de
modèle : le modèle n'a structurellement pas l'information « cette parcelle-ci est prise ».
Cas de calibrage consignés : AR1511 24,6 % (le max), les 8 brûlantes (7,6-24,6 %), 432 chaudes.
